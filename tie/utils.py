import logging
import os
import sys
import time
from threading import Timer
from urllib.parse import unquote

import win32api
import win32com
import win32con
import win32gui
from win32com.client.gencache import EnsureDispatch


def get_executable_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(__file__)


def debounce(wait):
    """ Decorator that will postpone a functions
        execution until after wait seconds
        have elapsed since the last time it was invoked. """

    def decorator(fn):
        def debounced(*args, **kwargs):
            def call_it():
                fn(*args, **kwargs)

            try:
                debounced.t.cancel()
            except(AttributeError):
                pass
            debounced.t = Timer(wait, call_it)
            debounced.t.start()

        return debounced

    return decorator


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
            address = w.LocationURL

            if w.LocationURL.startswith("file:///"):
                address = w.LocationURL[8:]
            # UNC 路径，如 file://Mac/.../...
            elif w.LocationURL.startswith("file://"):
                address = w.LocationURL[5:]
            address = address.replace("/", "\\")
            address = unquote(address)
            if os.path.isdir(address):
                return address
            else:
                logging.warning("unknown address: " + w.LocationURL)
                return None
    return None


def type_string_to(hwnd, seq):
    for i in range(len(seq)):
        c = seq[i]
        if i > 0 and c == seq[i - 1]:
            time.sleep(0.1)
        if c == "\n":
            # cmd 有效，powershell变成^M
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


def translate_event_const(event_id, prefix):
    for key in dir(win32con):
        value = getattr(win32con, key, None)
        if key.startswith(prefix) and value == event_id:
            return key
    return None


def draw_text_to(hwnd, text):
    dc = win32gui.CreateDC("DISPLAY", None, None, )
    rect = win32gui.GetWindowRect(hwnd)
    ret = win32gui.DrawText(dc, text, len(text), rect, win32con.DT_SINGLELINE)
    win32gui.DeleteDC(dc)


def set_dpi_awareness():
    import ctypes
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(True)
    except:
        pass


class LastValueContainer:
    def __init__(self, init_value=None, update_func=None, name="NoName"):
        self.name = name
        if init_value:
            self.value = init_value

        elif callable(update_func):
            self.update_func = update_func
            self.value = self.update_func()

        self.last = self.value
        self.changed = False

    def update(self):
        self.put(self.update_func())

    def get(self):
        return self.value

    def put(self, value):
        self.last = self.value
        self.value = value
        self.changed = self.last != self.value
        if self.changed:
            logging.debug("[%s] %s => %s" % (self.name, self.last, self.value))
