import os
import sys

import win32con
import win32gui
from win32com.client import Dispatch
from win32com.client.gencache import EnsureDispatch


def get_executable_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(__file__)


def is_terminal_idle(pid):
    wmi = win32com.client.GetObject('winmgmts:')
    children = wmi.ExecQuery('Select * from win32_process where ParentProcessId=%s' % pid)
    for child in children:
        print('child process of terminal\t', child.Name, child.Properties_('ProcessId'))

    # NOTE: terminal has one children named 'conhost.exe'
    return len([1 for child in children if child.Name != "conhost.exe"]) == 0


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


def get_explorer_address_by_hwnd(hwnd=None):
    for w in EnsureDispatch("Shell.Application").Windows():
        if hwnd is None or hwnd == w.HWnd:
            if w.LocationURL in ["此电脑", "This PC"]:
                return None
            return w.LocationURL[8:]  # file:///
    return None
