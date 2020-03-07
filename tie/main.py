import logging
import os
import sys
import time
import traceback

import win32api
import win32con
import win32gui
from pywinauto.application import Application

from tie.utils import get_executable_dir, \
    get_explorer_address_by_hwnd, is_terminal_idle, \
    hide_titlebar_and_taskbar, type_string_to, type_ctrl_c_to, get_window_rect_and_size, window_reposition


class ExplorerGone(RuntimeError):
    pass


class TerminalGone(RuntimeError):
    pass


terminal_config = {
    "cmd": {
        "start": r"cmd /k",
        "cd": "cd /D",
    },
    "powershell": {
        "start": "powershell -NoExit -NoLogo",
        "cd": "cd"
    }
}

TERMINAL_TYPE = "cmd"
current_terminal_config = terminal_config.get(TERMINAL_TYPE)

explorer_hwnd = None
terminal_app = None


def run():
    logging.debug("started")
    global explorer_hwnd, terminal_app

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

    # 在explorerh中找容器，将终端嵌入容器 并重新设置原有控件大小
    explorer_app = Application().connect(handle=explorer_hwnd)

    container = explorer_app.top_window()["ShellTabWindowClass"].child_window(class_name="DUIViewWndClassName",
                                                                              top_level_only=True)
    container_hwnd = container.handle

    # noinspection PyPep8Naming
    DirectUIHWND_in_container_hwnd = container.child_window(class_name="DirectUIHWND", top_level_only=True,
                                                            found_index=0).handle

    # 里面还有一个 DirectUIHWND

    def get_explorer_address():
        return get_explorer_address_by_hwnd(explorer_hwnd)

    # FIXED: work_dir 导致启动失败
    work_dir = get_explorer_address()
    work_dir = work_dir if work_dir else "C:\\"
    # DONE: 设置起始路径
    logging.debug("create new terminal %s at %s" % (current_terminal_config["start"],
                                                    work_dir))

    terminal_app = Application().start(current_terminal_config["start"],
                                       work_dir=work_dir,
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
    # noinspection PyPep8Naming
    sub_DirectUIHWND_hwnd = None

    # noinspection PyPep8Naming
    def update_sub_DirectUIHWND_position():
        nonlocal sub_DirectUIHWND_hwnd, terminal_height
        sub_DirectUIHWND_hwnd = container.child_window(class_name="DirectUIHWND", top_level_only=True,
                                                       found_index=1).handle
        (left, top, right, bottom, width, height) = get_window_rect_and_size(sub_DirectUIHWND_hwnd)
        new_container_h = height - terminal_height
        win32gui.MoveWindow(sub_DirectUIHWND_hwnd, 0, 0, width, new_container_h, 1)

    def update_terminal_position():
        nonlocal container_hwnd, DirectUIHWND_in_container_hwnd, terminal_height

        # 执行前需要确保窗口resize过 否则 existed_widget 高度不能恢复，会越来越小

        win32gui.SetParent(terminal_hwnd, container_hwnd)

        (left, top, right, bottom, width, height) = get_window_rect_and_size(DirectUIHWND_in_container_hwnd)
        new_container_h = height - terminal_height
        win32gui.MoveWindow(DirectUIHWND_in_container_hwnd, 0, 0, width, new_container_h, 1)
        win32gui.MoveWindow(terminal_hwnd, 0, new_container_h, width, terminal_height, 1)

        # 窗口resize 和改变路径 时 改变 existed_sub_widget 的大小
        update_sub_DirectUIHWND_position()

    def update_terminal_cwd(path):
        if path:

            # DONE: check for terminal IDLE
            if is_terminal_idle(terminal_app.process):
                cd_command = current_terminal_config["cd"] + ' "%s"' % path
                logging.debug("CD command: " + cd_command)

                # FIXED: 需要中断当前输入
                # NOTE: SetParent后 pywinauto无法操作Terminal了

                type_ctrl_c_to(terminal_hwnd)
                type_ctrl_c_to(terminal_hwnd)
                type_string_to(terminal_hwnd, cd_command + "\n")
                win32gui.SetForegroundWindow(explorer_hwnd)
            else:
                logging.warning("Terminal Busy.")
        else:
            logging.error("no such path: " + str(path))

    last_path = get_explorer_address()

    explorer_last_rect = win32gui.GetWindowRect(explorer_hwnd)
    x, y, x1, y1 = explorer_last_rect
    explorer_last_size = x1 - x, y1 - y
    update_terminal_position()

    # TODO: non polling?
    while True:
        time.sleep(0.2)

        # TODO: hook EVENT_SYSTEM_MOVESIZESTART
        #  或 监听窗口为激活状态 才进入循环

        if explorer_hwnd != win32gui.GetForegroundWindow():
            continue

        try:
            cur_path = get_explorer_address()
        except:
            raise ExplorerGone

        try:
            win32gui.GetWindowRect(terminal_hwnd)
        except:
            raise TerminalGone

        explorer_cur_rect = win32gui.GetWindowRect(explorer_hwnd)
        x, y, x1, y1 = explorer_cur_rect
        explorer_cur_size = x1 - x, y1 - y

        # 位置/尺寸改变
        if explorer_cur_rect != explorer_last_rect:
            # 尺寸改变
            if explorer_cur_size != explorer_last_size:
                logging.info("explorer size changed")
            else:
                # TODO: 仅在从最小化中还原才重新定位
                logging.info("explorer position changed")
                window_reposition(explorer_hwnd)

            if explorer_hwnd != win32gui.GetForegroundWindow():
                continue

            update_terminal_position()
            explorer_last_size = explorer_cur_size
            explorer_last_rect = explorer_cur_rect

        if cur_path != last_path:
            logging.info("explorer address changed: " + str(cur_path))
            update_terminal_cwd(cur_path)

            # 改变路径时，DirectUIHWND变了，重新改变大小
            update_sub_DirectUIHWND_position()
            last_path = cur_path


def main():
    log_file = os.path.join(get_executable_dir(), "debug.log")
    fmt = '[%(levelname)s][%(asctime)s][%(filename)s:%(lineno)d][%(threadName)s]: %(message)s'
    logging.basicConfig(level=logging.DEBUG, format=fmt, )
    handler = logging.FileHandler(log_file, mode='a')
    handler.setFormatter(logging.Formatter(fmt))
    logging.root.addHandler(handler)

    try:

        if len(sys.argv) > 1:
            import tie.register
            if sys.argv[1] == "register":
                tie.register.main(True)
            elif sys.argv[1] == "unregister":
                tie.register.main(False)
            exit()

        run()

    except ExplorerGone:
        logging.info("Explorer Gone")
    except TerminalGone:
        logging.info("Terminal Gone")
        # 终端挂了 恢复explorer位置(可能此时explorer也挂了
        try:
            window_reposition(explorer_hwnd)
            # win32api.MessageBox(0, "Terminal Bye", "", win32con.MB_TOPMOST | win32con.MB_SYSTEMMODAL)
        except:
            pass
    except Exception as e:
        logging.error(traceback.format_exc())
        win32api.MessageBox(0, traceback.format_exc(), "Error",
                            win32con.MB_TOPMOST | win32con.MB_SYSTEMMODAL | win32con.MB_ICONSTOP)
    finally:
        # DONE: 窗口关闭一并关闭shell
        terminal_app.kill()


if __name__ == "__main__":
    main()
