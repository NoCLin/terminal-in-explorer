import json
import logging
import os
import sys
import threading
import time
import traceback
import signal
import pywintypes
import win32api
import win32con
import win32event
import win32gui
import ctypes
from pywinauto.application import Application
from win32con import *

from tie.hook import start_win_hook, keyboard_hook_thread
from tie.utils import get_executable_dir, \
    get_explorer_address_by_hwnd, is_terminal_idle, \
    hide_titlebar_and_taskbar, type_string_to, \
    type_ctrl_c_to, get_window_rect_and_size, \
    LastValueContainer, draw_text_to, translate_event_const, \
    debounce, set_transparent, set_dpi_awareness

set_dpi_awareness()

main_thread_id = win32api.GetCurrentThreadId()

kernel32 = ctypes.WinDLL("kernel32")

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
# TERMINAL_TYPE = "powershell"
# powershell 还需适配 cd

current_terminal_config = terminal_config.get(TERMINAL_TYPE)

explorer_hwnd = None
explorer_path = LastValueContainer(name="explorer_path",
                                   update_func=lambda: get_explorer_address_by_hwnd(explorer_hwnd))
terminal_app = None
terminal_hwnd = None
container_hwnd = None
should_terminal_hide = False


def update_terminal_position():
    global explorer_hwnd, terminal_height, terminal_hwnd, should_terminal_hide
    sw = win32gui.GetWindowPlacement(explorer_hwnd)[1]

    if should_terminal_hide:
        win32gui.SetWindowPos(terminal_hwnd, win32con.HWND_NOTOPMOST,
                              0, 0, 0, 0,
                              win32con.SWP_HIDEWINDOW)
        return

    if sw == win32con.SW_SHOWMAXIMIZED:
        logging.debug("最大化")
        # TODO: 多显示器适配
        # https://stackoverflow.com/questions/3129322/how-do-i-get-monitor-resolution-in-python

        # SM_CXSCREEN SM_CYSCREEN size of screen in pixels including size of taskbar
        # SM_CXFULLSCREEN SM_CYFULLSCREEN size of screen in pixels excluding size of taskbar

        # print("检测到最大化窗口", (left, top, right, bottom, width, height))

        # 防止explorer 的border 导致计算错误，我的环境(-13,-13)
        win32gui.SetWindowPos(terminal_hwnd, win32con.HWND_TOP,
                              0, win32api.GetSystemMetrics(SM_CYFULLSCREEN) - terminal_height,
                              win32api.GetSystemMetrics(SM_CXFULLSCREEN), terminal_height,
                              win32con.SWP_SHOWWINDOW)

    elif sw == win32con.SW_NORMAL:

        (left, top, right, bottom, width, height) = get_window_rect_and_size(explorer_hwnd)
        h_overflow = height + terminal_height - win32api.GetSystemMetrics(SM_CYFULLSCREEN)
        if h_overflow >= 30:
            win32gui.SetWindowPos(explorer_hwnd, win32con.HWND_TOP,
                                  0, 0, width, height - h_overflow,
                                  win32con.SWP_NOMOVE)
            logging.debug("窗口高度溢出 %d" % h_overflow)
            (left, top, right, bottom, width, height) = get_window_rect_and_size(explorer_hwnd)

        win32gui.SetWindowPos(terminal_hwnd, win32con.HWND_TOPMOST,
                              left, bottom, width, terminal_height,
                              SWP_SHOWWINDOW)

        win32gui.SetWindowPos(explorer_hwnd, win32con.HWND_TOP,
                              0, 0, 0, 0,
                              SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)

    else:
        pass


def win_hook_callback(hWinEventHook, event, hwnd, idObject, idChild, dwEventThread, dwmsEventTime):
    if hwnd not in (explorer_hwnd, terminal_hwnd) and \
            event == EVENT_SYSTEM_FOREGROUND:
        logging.debug("explorer丢失前台")
        win32gui.SetWindowPos(terminal_hwnd, win32con.HWND_NOTOPMOST,
                              0, 0, 0, 0,
                              win32con.SWP_HIDEWINDOW)
        return

    if hwnd == explorer_hwnd:

        # FIXME: （Aero Shake）按住标题栏晃动会只显示当前窗口，terminal 也无法显示

        if event == EVENT_SYSTEM_FOREGROUND:
            if win32gui.GetForegroundWindow() == explorer_hwnd:
                print("explorer置前台")
                update_terminal_position()

            pass
        elif event == EVENT_SYSTEM_MOVESIZEEND:
            # The movement or resizing of a window has finished. This event is sent by the system, never by servers.
            logging.debug("窗口移动结束")
            update_terminal_position()
        elif event == EVENT_OBJECT_LOCATIONCHANGE:
            # An object has changed location, shape, or size.
            # print("EVENT_OBJECT_LOCATIONCHANGE")
            update_terminal_position()
        else:
            pass
            # print("UNKNOWN", translate_event_const(event, "EVENT_"), event)


def monitor_explorer_address():
    global explorer_hwnd, terminal_app, terminal_hwnd, current_terminal_config
    try:
        while True:
            time.sleep(0.5)

            if not win32gui.IsWindow(terminal_hwnd):
                logging.debug("Terminal Gone")
                win32api.PostThreadMessage(main_thread_id, win32con.WM_QUIT, 0, 0)
                break
            if not win32gui.IsWindow(explorer_hwnd):
                terminal_app.kill()
                win32api.PostThreadMessage(main_thread_id, win32con.WM_QUIT, 0, 0)
                break

            if win32gui.GetForegroundWindow() not in (explorer_hwnd, terminal_hwnd):
                continue

            explorer_path.update()
            if explorer_path.changed:
                logging.info("改变路径")
                if explorer_path.value:

                    # DONE: check for terminal IDLE
                    if is_terminal_idle(terminal_app.process):
                        cd_command = current_terminal_config["cd"] + ' "%s"' % explorer_path.value
                        logging.debug("CD command: " + cd_command)

                        # FIXED: 需要Ctrl+C中断当前输入
                        global TERMINAL_TYPE
                        if TERMINAL_TYPE == "cmd":
                            type_ctrl_c_to(terminal_hwnd)
                            type_ctrl_c_to(terminal_hwnd)
                            type_string_to(terminal_hwnd, cd_command)
                            type_string_to(terminal_hwnd, "\n")
                        elif TERMINAL_TYPE == "powershell":
                            # FIXME: type_keys 可能涉及转义字符，需要先处理
                            #   并且会导致窗口失去焦点，导致无法连续使用键盘
                            terminal_app.top_window().type_keys('^c', pause=0)
                            terminal_app.top_window().type_keys('^c', pause=0)
                            terminal_app.top_window().type_keys(
                                '%s{ENTER}' % cd_command, pause=0, with_spaces=True)

                        win32gui.SetForegroundWindow(explorer_hwnd)
                    else:
                        draw_text_to(explorer_hwnd, "Terminal Busy.")
                        logging.warning("Terminal Busy.")
                else:
                    logging.error("no such path: " + str(explorer_path.value))
    except Exception as e:
        logging.error(e)
        logging.error(traceback.format_exc())


def run():
    logging.debug("started")

    sz_mutex = "TerminalInExplorer"
    ERROR_ALREADY_EXISTS = 183
    mutex = win32event.CreateMutex(None, pywintypes.FALSE, sz_mutex)
    if win32api.GetLastError() == ERROR_ALREADY_EXISTS:
        raise RuntimeError("Only one instance is allowed.")

    global explorer_hwnd, terminal_app, terminal_hwnd, terminal_height
    # Should be last activated explorer window
    explorer_hwnd = win32gui.FindWindow("CabinetWClass", None)
    logging.debug("explorer_hwnd: %d" % explorer_hwnd)
    logging.debug("title: %s" % win32gui.GetWindowText(explorer_hwnd))
    if explorer_hwnd == 0:
        raise RuntimeError("Cannot find explorer.")

    # 只能启动一次
    # 一个实例 附加到所有的explorer
    # 切换时自动识别路径 如果idle且路径不一致 就切换

    # FIXED: work_dir 导致启动失败
    explorer_path.update()
    work_dir = explorer_path.value
    work_dir = work_dir if work_dir else "C:\\"
    # DONE: 设置起始路径
    logging.debug("create new terminal %s at %s" % (current_terminal_config["start"],
                                                    work_dir))

    terminal_app = Application().start(current_terminal_config["start"],
                                       work_dir=work_dir,
                                       create_new_console=True, wait_for_idle=False)

    # wait shell
    terminal_hwnd = terminal_app.top_window().wait("exists").handle
    # avoid flash
    win32gui.SetWindowPos(terminal_hwnd, win32con.HWND_TOP,
                          0, 0, 0, 0,
                          win32con.SWP_SHOWWINDOW)

    hide_titlebar_and_taskbar(terminal_hwnd)
    set_transparent(terminal_hwnd, 200)

    logging.info(terminal_hwnd)
    logging.info(win32gui.GetWindowText(terminal_hwnd))

    # FIXME: 有的时候从非explorer启动 terminal不显示
    # 也许是万恶之源...
    update_terminal_position()
    update_terminal_position()
    win32gui.SetForegroundWindow(explorer_hwnd)
    win32gui.SetWindowPos(explorer_hwnd, win32con.HWND_TOP,
                          0, 0, 0, 0,
                          win32con.SWP_SHOWWINDOW | SWP_NOMOVE | SWP_NOSIZE)
    win32gui.SetWindowPos(terminal_hwnd, win32con.HWND_TOP,
                          0, 0, 0, 0,
                          win32con.SWP_SHOWWINDOW | SWP_NOMOVE | SWP_NOSIZE)

    threading.Thread(target=monitor_explorer_address, daemon=True).start()

    signal.signal(signal.SIGINT, signal.SIG_DFL)

    def cb():
        global should_terminal_hide
        should_terminal_hide = not should_terminal_hide
        update_terminal_position()

    threading.Thread(target=keyboard_hook_thread, args=(cb,), daemon=True).start()
    start_win_hook(callback=win_hook_callback)


def main():
    log_file = os.path.join(get_executable_dir(), "debug.log")
    fmt = '[%(levelname)s][%(asctime)s][%(filename)s:%(lineno)d][%(threadName)s]: %(message)s'
    logging.basicConfig(level=logging.DEBUG, format=fmt, )
    handler = logging.FileHandler(log_file, mode='a')
    handler.setFormatter(logging.Formatter(fmt))
    logging.root.addHandler(handler)

    if len(sys.argv) > 1:
        import tie.register

        if sys.argv[1] == "register":
            tie.register.main(True)
        elif sys.argv[1] == "unregister":
            tie.register.main(False)
        exit()

    try:
        run()
    except Exception as e:
        logging.error(traceback.format_exc())
        win32api.MessageBox(0, traceback.format_exc(), "Error",
                            win32con.MB_TOPMOST | win32con.MB_SYSTEMMODAL | win32con.MB_ICONSTOP)
    finally:
        # DONE: 窗口关闭一并关闭shell
        try:
            terminal_app.kill()
        except:
            pass


if __name__ == "__main__":
    main()
