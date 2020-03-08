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
    hide_titlebar_and_taskbar, type_string_to, \
    type_ctrl_c_to, get_window_rect_and_size, window_reposition, \
    LastValueContainer


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

terminal_height = 300

TERMINAL_TYPE = "cmd"
current_terminal_config = terminal_config.get(TERMINAL_TYPE)

explorer_hwnd = None
terminal_app = None


def run():
    logging.debug("started")
    global explorer_hwnd, terminal_app, terminal_hwnd, terminal_height
    global container_hwnd, DirectUIHWND_in_container_hwnd
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

    # 在explorer中找容器，将终端嵌入容器 并重新设置原有控件大小
    explorer_app = Application().connect(handle=explorer_hwnd)

    container = explorer_app.top_window()["ShellTabWindowClass"].child_window(class_name="DUIViewWndClassName",
                                                                              top_level_only=True)
    container_hwnd = container.handle

    # noinspection PyPep8Naming
    DirectUIHWND_in_container_hwnd = container.child_window(class_name="DirectUIHWND", top_level_only=True,
                                                            found_index=0).handle

    folder_tree_in_container_hwnd = container.child_window(class_name="SysTreeView32", top_level_only=False,
                                                           ).handle

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

    # noinspection PyPep8Naming
    def update_sub_DirectUIHWND_position():
        global terminal_height
        sub_DirectUIHWND_hwnd = container.child_window(class_name="DirectUIHWND", top_level_only=True,
                                                       found_index=1).handle
        (left, top, right, bottom, width, height) = get_window_rect_and_size(sub_DirectUIHWND_hwnd)
        new_container_h = height - terminal_height
        win32gui.MoveWindow(sub_DirectUIHWND_hwnd, 0, 0, width, new_container_h, 1)

    def update_terminal_position():
        global container_hwnd, DirectUIHWND_in_container_hwnd, terminal_height
        # 执行前需要确保窗口resize过 否则 existed_widget 高度不能恢复，会越来越小

        # 装入容器
        win32gui.SetParent(terminal_hwnd, container_hwnd)

        # 改变容器中树状目录的高度
        (left, top, right, bottom, width, height) = get_window_rect_and_size(folder_tree_in_container_hwnd)
        new_container_h = height - terminal_height
        win32gui.MoveWindow(folder_tree_in_container_hwnd, 0, 0, width, new_container_h, 1)

        # 改变容器中的第一个 DirectUIHWND 的高度，给终端腾出位置
        (left, top, right, bottom, width, height) = get_window_rect_and_size(DirectUIHWND_in_container_hwnd)
        new_container_h = height - terminal_height
        win32gui.MoveWindow(DirectUIHWND_in_container_hwnd, 0, 0, width, new_container_h, 1)

        # 移动 终端窗口 到刚刚腾出的位置
        win32gui.MoveWindow(terminal_hwnd, 0, new_container_h, width, terminal_height, 1)

        # 改变容器中的第二个 DirectUIHWND 的宽度
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

    explorer_path = LastValueContainer(name="explorer_path", update_func=get_explorer_address)
    # explorer_rect = LastValueContainer(name="explorer_rect", update_func=lambda: win32gui.GetWindowRect(explorer_hwnd))

    explorer_replacement = LastValueContainer(name="explorer_replacement",
                                              update_func=lambda: win32gui.GetWindowPlacement(explorer_hwnd)[1])

    def update_explorer_size():
        x, y, x1, y1 = win32gui.GetWindowRect(explorer_hwnd)
        return x1 - x, y1 - y

    explorer_size = LastValueContainer(name="explorer_size", update_func=update_explorer_size)
    fore_hwnd = LastValueContainer(name="fore hwnd", update_func=win32gui.GetForegroundWindow)
    update_terminal_position()

    # 策略
    # 只移动窗口 不更新
    # 改变大小 更新
    # 从最小化恢复 更新
    def refresh():

        try:
            win32gui.GetWindowRect(terminal_hwnd)
        except:
            raise TerminalGone

        try:
            fore_hwnd.update()
            explorer_size.update()
            explorer_replacement.update()
            explorer_path.update()

            # FIXME (低优先级): 快速点击任务栏图标 会导致响应不及时，以下代码能解决大部分
            # 除非手特别快
            if explorer_replacement.changed and explorer_replacement.last == win32con.SW_SHOWMINIMIZED:
                logging.info("从最小化恢复")
                window_reposition(container_hwnd)
                update_terminal_position()
                return

            if fore_hwnd.value != explorer_hwnd:
                return

        except:
            raise ExplorerGone

        # 尺寸改变
        if explorer_size.changed:
            # 如果是最小化则不需要更新终端
            # 实际上最小化了，fore不是explorer，不会执行到这里
            if win32gui.GetWindowPlacement(explorer_hwnd)[1] == win32con.SW_SHOWMINIMIZED:
                logging.info("最小化")
            else:
                logging.info("改变窗口大小")
                # 调用前 需要确保窗口已经重新绘制，不然高度越来越小
                window_reposition(container_hwnd)
                update_terminal_position()
            return

        if win32gui.GetForegroundWindow() != explorer_hwnd:
            return

        if explorer_path.changed:
            logging.info("改变路径")
            update_terminal_cwd(explorer_path.get())

            # 改变路径时，DirectUIHWND变了，重新改变大小
            update_sub_DirectUIHWND_position()
            return

    # TODO: non polling hook EVENT_或 监听窗口为激活状态 才进入循环
    while True:
        time.sleep(0.2)
        refresh()


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
            window_reposition(container_hwnd)
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
