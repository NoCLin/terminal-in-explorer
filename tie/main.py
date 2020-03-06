import logging
import os
import sys
import time
import traceback

import pywintypes
import win32api
import win32com.client
import win32con
import win32gui
from pywinauto.application import Application
from pywinauto.findwindows import ElementAmbiguousError

from tie.utils import get_executable_dir, \
    get_explorer_address_by_hwnd, is_terminal_idle, \
    hide_titlebar_and_taskbar, set_transparent, \
    get_children_recursively, get_children_hwnd


class ExplorerGone(RuntimeError):
    pass


class TerminalGone(RuntimeError):
    pass


terminal_config = {
    "cmd": {
        "start": r"cmd /k ",
        "cd": "cd /D",
    },
    "powershell": {
        "start": "powershell -NoExit -NoLogo",
        "cd": "cd"
    }
}

TERMINAL_TYPE = "cmd"
current_terminal_config = terminal_config.get(TERMINAL_TYPE)


def run():
    terminal_app = None

    try:
        logging.debug("started")

        explorer_hwnd = win32gui.GetForegroundWindow()
        logging.debug("explorer_hwnd: %d" % explorer_hwnd)
        logging.debug("explorer_title: %s" % win32gui.GetWindowText(explorer_hwnd))

        # TODO: 本程序窗口作为cmd窗口?避免再开一个窗口？
        #  (virtualenv pythonw？)

        class_name = win32gui.GetClassName(explorer_hwnd)
        logging.debug("explorer_classname: %s" % class_name)

        if class_name != "CabinetWClass":

            # Should be last activated explorer window
            explorer_hwnd = win32gui.FindWindow("CabinetWClass", None)
            logging.debug("FindWindow: %s" % explorer_hwnd)
            logging.debug("title: %s" % win32gui.GetWindowText(explorer_hwnd))
            if explorer_hwnd == 0:
                raise RuntimeError("Cannot find explorer.")

        explorer_app = Application().connect(handle=explorer_hwnd)

        container = explorer_app.top_window()["SHELLDLL_DefView"]
        container_hwnd = container.handle
        try:
            existed_widget_hwnd = container.child_window().handle
        except ElementAmbiguousError:
            raise RuntimeError("May be another instance already exists.")
        print(container_hwnd, existed_widget_hwnd)

        explorer_tab_window_hwnd = get_children_hwnd(explorer_hwnd, "ShellTabWindowClass")
        logging.debug("explorer_tab_window_hwnd: %d" % explorer_tab_window_hwnd)
        if explorer_tab_window_hwnd == 0:
            print("Find ShellTabWindowClass failed.")
            exit(-1)

        def get_explorer_address():
            return get_explorer_address_by_hwnd(explorer_hwnd)

        # DONE: 设置起始路径

        terminal_app = Application().start(current_terminal_config["start"],
                                           work_dir=get_explorer_address(),
                                           create_new_console=True, wait_for_idle=False)

        # wait shell
        terminal_app["ConsoleWindowClass"].wait("exists")

        terminal_hwnd = terminal_app.top_window().handle
        # avoid flash
        win32gui.SetWindowPos(terminal_hwnd, win32con.HWND_TOP,
                              0, 0, 0, 0,
                              win32con.SWP_SHOWWINDOW)

        hide_titlebar_and_taskbar(terminal_hwnd)

        logging.info(terminal_hwnd)
        logging.info(win32gui.GetWindowText(terminal_hwnd))

        terminal_height = 300

        def update_terminal_position():
            nonlocal container_hwnd, existed_widget_hwnd, terminal_height

            # 执行前需要确保窗口resize过 否则 existed_widget 高度不能恢复，会越来越小

            win32gui.SetParent(terminal_hwnd, container_hwnd)

            (left, top, right, bottom) = win32gui.GetWindowRect(existed_widget_hwnd)
            width = right - left
            height = bottom - top
            new_container_h = height - terminal_height

            win32gui.MoveWindow(existed_widget_hwnd, 0, 0, width, new_container_h, 1)
            win32gui.MoveWindow(terminal_hwnd, 0, new_container_h, width, terminal_height, 1)

        def update_terminal_cwd(cur_path):
            if cur_path:

                # DONE: check for terminal IDLE
                if is_terminal_idle(terminal_app.process):

                    cd_command = current_terminal_config["cd"] + ' "%s"' % cur_path
                    # FIXED: 需要中断当前输入
                    terminal_app["ConsoleWindowClass"].type_keys('^c', pause=0)
                    terminal_app["ConsoleWindowClass"].type_keys(
                        '{ENTER}%s{ENTER}' % cd_command, pause=0, with_spaces=True)
                    win32gui.SetForegroundWindow(explorer_hwnd)
                else:
                    logging.debug("Terminal Busy.")
            else:
                print("no such path", cur_path)

        last_path = get_explorer_address()

        x, y, x1, y1 = win32gui.GetWindowRect(explorer_hwnd)
        explorer_last_size = x1 - x, y1 - y
        update_terminal_position()

        # TODO: non polling?
        while True:
            time.sleep(0.2)

            try:
                cur_path = get_explorer_address()
            except:
                raise ExplorerGone

            try:
                win32gui.GetWindowRect(terminal_hwnd)
            except:
                raise TerminalGone

            x, y, x1, y1 = win32gui.GetWindowRect(explorer_hwnd)
            explorer_cur_size = x1 - x, y1 - y

            if explorer_cur_size != explorer_last_size:
                update_terminal_position()
                explorer_last_size = explorer_cur_size

            if cur_path != last_path:
                print("new path", cur_path)
                update_terminal_cwd(cur_path)
                last_path = cur_path


    except ExplorerGone:
        win32api.MessageBox(0, "Explorer Bye", "", win32con.MB_TOPMOST | win32con.MB_SYSTEMMODAL)
    except TerminalGone:
        # 终端挂了 恢复explorer位置
        # SetWindowPos不能处理最大化情况

        (left, top, right, bottom) = win32gui.GetWindowRect(existed_widget_hwnd)
        width = right - left
        height = bottom - top
        # 补回高度
        win32gui.MoveWindow(existed_widget_hwnd, 0, 0, width, height + terminal_height, 1)
        win32api.MessageBox(0, "Terminal Bye", "", win32con.MB_TOPMOST | win32con.MB_SYSTEMMODAL)

    except Exception as e:
        logging.error(traceback.format_exc())
        win32api.MessageBox(0, traceback.format_exc(), "Error",
                            win32con.MB_TOPMOST | win32con.MB_SYSTEMMODAL | win32con.MB_ICONSTOP)
    finally:
        # DONE: 窗口关闭一并关闭shell
        terminal_app.kill()


def main():
    log_file = os.path.join(get_executable_dir(), "debug.log")
    logging.basicConfig(level=logging.DEBUG, filename=log_file, filemode="a")

    if len(sys.argv) > 1 and sys.argv[1] == "register":
        import tie.register

        tie.register.main()
        exit()

    run()


if __name__ == "__main__":
    main()
