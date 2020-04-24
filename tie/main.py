# very basic terminal emulator in pyqt
# https://pythonbasics.org/pyqt/
import logging
import os
import platform
import signal
import subprocess
import sys
import threading
import time

import pysnooper
import win32con
import win32gui
from PyQt5 import QtWidgets
from PyQt5.QtGui import QWindow
from PyQt5.QtWidgets import QMessageBox, QWidget, QHBoxLayout

from tie.conemu import ConEmu
from tie.mainwindow_ui import Ui_MainWindow
from tie.utils import LastValueContainer, get_explorer_address_by_hwnd, is_terminal_idle, draw_text_to, \
    get_window_rect_and_size, set_dpi_awareness, get_executable_dir

terminal_config = {
    "cmd": {
        "start": r"cmd /k",
        "command": r"cmd.exe",
        "cd": "cd /D",
    },
    "powershell": {
        "start": "powershell -NoExit -NoLogo",
        "command": "powershell.exe",
        "cd": "cd"
    }
}

TERMINAL_TYPE = "cmd"
# TERMINAL_TYPE = "powershell"
# powershell 还需适配 cd

CONEMUC = r"C:\Program Files\ConEmu\ConEmu\ConEmuC64.exe"
CONEMU = r"C:\Program Files\ConEmu\ConEmu64.exe"

current_terminal_config = terminal_config.get(TERMINAL_TYPE)

@pysnooper.snoop(watch_explode=['self'],prefix="Debug: ")
class MainWindow(QtWidgets.QMainWindow):

    def __init__(self):
        super(MainWindow, self).__init__()
        # 这样才能有代码提示
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        # 调试用
        # os.system("explorer")
        # time.sleep(0.5)
        self.platform = platform.win32_ver()

        self.this_hwnd = int(self.winId())

        self.explorer_init()

        self.explorer_path = LastValueContainer(name="explorer_path",
                                                update_func=lambda: get_explorer_address_by_hwnd(self.this_hwnd))

        self.conemu = ConEmu(CONEMU,CONEMUC)
        self.conemu.attach_to_hwnd(int(self.ui.terminal_frame.winId()),admin=False,init_command="cmd")

        self.t1 = threading.Thread(target=self.monitor_explorer_path, daemon=True)
        self.t1.start()

        from functools import partial
        self.ui.button_toggle_terminal.clicked.connect(lambda:self.on_toggle_terminal())
        print(self.ui.button_toggle_terminal)


    def explorer_init(self):
        self.explorer_hwnd = win32gui.FindWindow("CabinetWClass", None)
        if self.explorer_hwnd == 0:
            QMessageBox.warning(self, "错误", "Explorer not found", buttons=QMessageBox.Yes)
            raise Exception("Explorer not found")

        explorer_title = win32gui.GetWindowText(self.explorer_hwnd)

        (left, top, right, bottom, width, height) = get_window_rect_and_size(self.explorer_hwnd)

        sw = win32gui.GetWindowPlacement(self.explorer_hwnd)[1]

        if sw == win32con.SW_SHOWMAXIMIZED:
            # check foreground
            self.showMaximized()
        else:
            self.resize(width, height)
            self.move(left, top)

        style = win32gui.GetWindowLong(self.explorer_hwnd, win32con.GWL_STYLE)
        # exstyle = win32gui.GetWindowLong(explorer_hwnd, win32con.GWL_EXSTYLE)

        style = style & ~win32con.WS_CAPTION
        style = style & ~win32con.WS_THICKFRAME
        style = style & ~win32con.WS_DLGFRAME
        style = style & ~win32con.WS_POPUP
        win32gui.SetWindowLong(self.explorer_hwnd, win32con.GWL_STYLE, style)

        self.explorer_widget = QWidget.createWindowContainer(QWindow.fromWinId(self.explorer_hwnd))
        self.explorer_widget.hwnd = self.explorer_hwnd
        self.ui.explorer_container_layout.addWidget(self.explorer_widget)


    def on_toggle_terminal(self):
        self.ui.terminal_group.setHidden(not self.ui.terminal_group.isHidden())
        if self.ui.button_toggle_terminal.text() == "↓":
            self.ui.button_toggle_terminal.setText("↑")
        else:
            self.ui.button_toggle_terminal.setText( "↓")


    def monitor_explorer_path(self):

        try:
            while True:
                time.sleep(0.5)

                if win32gui.GetForegroundWindow() not in (self.this_hwnd,):
                    continue
                # TODO:

                self.explorer_path.update()
                if self.explorer_path.changed:

                    if self.explorer_path.value:
                        logging.info("改变路径 " + self.explorer_path.value)
                        self.setWindowTitle(self.explorer_path.value)
                        # DONE: check for terminal IDLE

                        if self.conemu.is_idle():
                            cd_command = current_terminal_config["cd"] + ' "%s"' % self.explorer_path.value
                            logging.debug("CD command: " + cd_command)
                            self.conemu.input(cd_command)
                        else:
                            draw_text_to(self.explorer_hwnd, "Terminal Busy.")
                            logging.warning("Terminal Busy.")
                    else:
                        logging.error("no such path: " + str(self.explorer_path.value))
        except Exception as e:
            logging.exception(e)

    # TODO: 抓取是否有subprocess在运行
    # TODO: 优化启动速度


def main():

    # TODO: 检测多次打开

    set_dpi_awareness()
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    log_file = os.path.join(get_executable_dir(), "debug.log")
    fmt = '[%(levelname)s][%(asctime)s][%(filename)s:%(lineno)d][%(threadName)s]: %(message)s'
    logging.basicConfig(level=logging.DEBUG, format=fmt, )
    handler = logging.FileHandler(log_file, mode='a')
    handler.setFormatter(logging.Formatter(fmt))
    logging.root.addHandler(handler)

    # TODO: 类似于make 检查一下target 与其requirements的时间
    app = QtWidgets.QApplication(sys.argv)

    # from system_hotkey import SystemHotkey
    # hk = SystemHotkey()
    # hk.register(('control','h'), callback=lambda x: print("Easy!"))

    win = MainWindow()
    win.show()



    sys.exit(app.exec())


if __name__ == '__main__':
    main()
