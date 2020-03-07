import logging
import os
import sys
import time

import win32api
import win32com
import win32con
import win32gui
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
            if w.LocationURL.startswith("file:///"):
                return w.LocationURL[8:].replace("/", "\\")
            # UNC 路径，如 file://Mac/.../...
            if w.LocationURL.startswith("file://"):
                return w.LocationURL[5:].replace("/", "\\")
            logging.warning("unknown address: " + w.LocationURL)
    return None


def type_string_to(hwnd, seq):
    _last_c = None
    for c in seq:
        if _last_c == c:
            time.sleep(0.1)
        _last_c = c
        if c == "\n":
            win32api.SendMessage(hwnd, win32con.WM_CHAR, win32con.VK_RETURN, 0)
        else:
            win32api.SendMessage(hwnd, win32con.WM_CHAR, ord(c), 0)


def type_ctrl_c_to(hwnd):
    win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
    win32api.SendMessage(hwnd, win32con.WM_KEYDOWN, ord('C'), 0)
    win32api.SendMessage(hwnd, win32con.WM_KEYUP, ord('C'), 0)
    win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)


def get_window_rect_and_size(hwnd):
    (left, top, right, bottom) = win32gui.GetWindowRect(hwnd)
    width = right - left
    height = bottom - top
    return left, top, right, bottom, width, height


def window_reposition(hwnd):
    tup = win32gui.GetWindowPlacement(hwnd)
    if tup[1] == win32con.SW_SHOWMAXIMIZED:
        # SetWindowPos不能处理最大化情况
        win32gui.ShowWindow(hwnd, win32con.SW_NORMAL)
        win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
    elif tup[1] == win32con.SW_SHOWMINIMIZED:
        logging.info("minimized")
    elif tup[1] == win32con.SW_SHOWNORMAL:
        left, top, right, bottom, width, height = get_window_rect_and_size(hwnd)
        # 避免闪烁
        win32gui.SetWindowPos(hwnd, win32con.HWND_TOP,
                              left, top, width, height + 1,
                              win32con.SWP_SHOWWINDOW)
        win32gui.SetWindowPos(hwnd, win32con.HWND_TOP,
                              left, top, width, height,
                              win32con.SWP_SHOWWINDOW)


def translate_event_to_const(event_id):
    for key in dir(win32con):
        value = getattr(win32con, key, None)
        if key.startswith("EVENT_SYSTEM_") and value == event_id:
            return key
    return None


class LastValueContainer:
    def __init__(self, init_value=None, update_func=None):
        if init_value:
            self.value = init_value

        elif callable(update_func):
            self.update_func = update_func
            self.value = self.update_func()

        self.last = self.value

    def update(self):
        self.put(self.update_func())

    def changed(self):
        return self.last != self.value

    def get(self):
        return self.value

    def put(self, value):
        if self.last != value:
            self.last = self.value
            self.value = value
