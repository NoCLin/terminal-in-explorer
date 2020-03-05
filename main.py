import logging
import os
import sys
import time

import win32api
import win32com.client
import win32con
import win32gui
from pywinauto.application import Application

logging.basicConfig(level=logging.DEBUG, filename="debug.log", filemode="a")


# TODO: logging


def is_terminal_idle(pid):
    wmi = win32com.client.GetObject('winmgmts:')
    children = wmi.ExecQuery('Select * from win32_process where ParentProcessId=%s' % pid)
    for child in children:
        print('child process of terminal\t', child.Name, child.Properties_('ProcessId'))

    # NOTE: terminal has one children named 'conhost.exe'
    return len([1 for child in children if child.Name != "conhost.exe"]) == 0


# TODO: 模仿 conemu set parent

def hide_titlebar_and_taskbar(hwnd):
    style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
    style = style & ~win32con.WS_CAPTION
    style = style & ~win32con.WS_THICKFRAME
    style = style & ~win32con.WS_MINIMIZE
    # style = style & ~win32con.WS_SYSMENU

    win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, style)


def set_transparent(hwnd, opacity=200):
    style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
    style = style | win32con.WS_EX_LAYERED
    win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, style)
    win32gui.SetLayeredWindowAttributes(
        hwnd, win32api.RGB(0, 0, 0), opacity, win32con.LWA_ALPHA)


def get_children_hwnd(hwnd, name):
    return win32gui.FindWindowEx(hwnd, None, name, None)


def get_children_recursively(hwnd, names):
    for name in names:
        hwnd = get_children_hwnd(hwnd, name)
    return hwnd


def main():
    shell_app = None

    try:
        logging.debug("started")
        # 脚本显示窗口时 暂时先切换回explorer
        explorer_hwnd = win32gui.GetForegroundWindow()
        logging.debug("explorer_hwnd: %d" % explorer_hwnd)
        logging.debug("explorer_title: %s" % win32gui.GetWindowText(explorer_hwnd))

        # TODO: 本程序窗口作为cmd窗口?避免再开一个窗口？

        class_name = win32gui.GetClassName(explorer_hwnd)
        logging.debug("explorer_classname: %s" % class_name)

        if class_name != "CabinetWClass":

            # Should be last activated explorer window
            explorer_hwnd = win32gui.FindWindow("CabinetWClass", None)
            logging.debug("FindWindow: %s" % explorer_hwnd)
            logging.debug("title: %s" % win32gui.GetWindowText(explorer_hwnd))
            if explorer_hwnd == 0:
                win32api.MessageBox(0, "Cannot find explorer.", "Error", )
                exit(-1)

        explorer_tab_window_hwnd = get_children_hwnd(explorer_hwnd, "ShellTabWindowClass")
        logging.debug("explorer_tab_window_hwnd: %d" % explorer_tab_window_hwnd)
        if explorer_tab_window_hwnd == 0:
            print("Find ShellTabWindowClass failed.")
            exit(-1)

        # TODO: 效率
        # TODO: 适配其他系统？

        path1 = ["WorkerW", "ReBarWindow32",
                 "Address Band Root", "msctls_progress32",
                 "Breadcrumb Parent", "ToolbarWindow32"]

        path2 = ["WorkerW", "ReBarWindow32",
                 "ComboBoxEx32", "ComboBox",
                 "Edit"]

        explorer_address_hwnd = get_children_recursively(explorer_hwnd, path1)
        if explorer_address_hwnd == 0:
            explorer_address_hwnd = get_children_recursively(explorer_hwnd, path2)
        if explorer_address_hwnd == 0:
            win32api.MessageBox(0, "Get explorer address failed.", "Error", )
            exit()

        print("explorer_address_hwnd", explorer_address_hwnd)

        # TODO: 适配 cmd.exe powershell.exe WindowsTerminal.exe wsl
        #

        terminal_launcher_command = "cmd /k "

        # terminal_launcher_command = r'powershell -NoExit -NoLogo'

        def get_explorer_address():

            # TODO: parse 我的电脑 文档 等
            # 去除前缀
            address = " ".join(win32gui.GetWindowText(explorer_address_hwnd).split(" ")[1:])

            if os.path.isdir(address):
                return address
            if address in ["此电脑", "This PC"]:
                return None
            import knownpaths

            # TODO: english or other languages env
            mapping = {

                "桌面": knownpaths.FOLDERID.Desktop,
                "Desktop": knownpaths.FOLDERID.Desktop,

                "文档": knownpaths.FOLDERID.Documents,
                "Documents": knownpaths.FOLDERID.Documents,

                "下载": knownpaths.FOLDERID.Downloads,
                "Downloads": knownpaths.FOLDERID.Downloads,

                "Videos": knownpaths.FOLDERID.Videos,
                "视频": knownpaths.FOLDERID.Videos,

                "图片": knownpaths.FOLDERID.Pictures,
                "Pictures": knownpaths.FOLDERID.Pictures,

                "音乐": knownpaths.FOLDERID.Music,
                "Music": knownpaths.FOLDERID.Music,

            }

            folder_id = mapping.get(address, None)
            if folder_id:
                return knownpaths.get_path(folder_id)

            logging.debug("No Such Address: " + address)
            return None

        # DONE: 设置起始路径
        shell_app = Application().start(terminal_launcher_command,
                                        work_dir=get_explorer_address(),
                                        create_new_console=True, wait_for_idle=False)

        # wait shell
        shell_app["ConsoleWindowClass"].wait("exists")

        shell_hwnd = shell_app.top_window().handle
        # avoid flash
        win32gui.SetWindowPos(shell_hwnd, win32con.HWND_TOP,
                              0, 0, 0, 0,
                              win32con.SWP_SHOWWINDOW)

        hide_titlebar_and_taskbar(shell_hwnd)
        set_transparent(shell_hwnd)
        # TODO: hide task bar

        logging.info((shell_hwnd))
        logging.info(win32gui.GetWindowText(shell_hwnd))

        last_path = get_explorer_address()
        last_cur_hwnd = win32gui.GetForegroundWindow()

        def check_update():

            ### region calculate position

            (left, top, right, bottom) = win32gui.GetWindowRect(
                explorer_tab_window_hwnd)
            # print((left, top, right, bottom))
            width = right - left
            height = bottom - top
            # print(width,height)

            shell_left = left
            shell_top = top + (height - 300)
            shell_width = width
            shell_height = 300

            cur_fore_hwnd = win32gui.GetForegroundWindow()

            if cur_fore_hwnd == 0:
                return

            is_fore = cur_fore_hwnd in [shell_hwnd, explorer_hwnd]

            # print(is_fore, cur_fore_hwnd, [shell_hwnd, explorer_hwnd])
            # explorer_and_shell 失去焦点就取消 topmost
            z_order = win32con.HWND_TOPMOST if is_fore else win32con.HWND_NOTOPMOST
            flags = win32con.SWP_SHOWWINDOW if is_fore else win32con.SWP_HIDEWINDOW
            # x,y,cx,cy
            win32gui.SetWindowPos(shell_hwnd, z_order,
                                  shell_left, shell_top,
                                  shell_width, shell_height, flags)

            ### region
            nonlocal last_path, last_cur_hwnd

            cur_path = get_explorer_address()
            last_cur_hwnd = cur_fore_hwnd

            if cur_path != last_path:
                print("new path", cur_path)

                if cur_path:
                    # DONE: check for terminal IDLE
                    if is_terminal_idle(shell_app.process):
                        # cmd need cd /D
                        shell_app["ConsoleWindowClass"].type_keys(
                            '{ENTER}cd "%s"{ENTER}' % cur_path, pause=0, with_spaces=True)
                    else:
                        logging.debug("Terminal Busy.")
                else:
                    print("no such path", cur_path)

            last_path = cur_path

            # logging.info(title)

        while True:
            time.sleep(0.2)
            check_update()



    except Exception as e:
        # DONE: 窗口关闭一并关闭shell
        try:
            shell_app.kill()
        except:
            pass
        import pywintypes
        if isinstance(e, pywintypes.error):
            print("window closed.", e)

        logging.error(e)
        import traceback
        logging.error(traceback.format_exc())


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "register":
        import register

        register.main()
        exit()

    main()
