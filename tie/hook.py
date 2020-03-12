import ctypes
import time
from ctypes.wintypes import HANDLE, DWORD, HWND, LONG, MSG
from threading import Thread

import win32con
from pywinauto.win32_hooks import KeyboardEvent, Hook
from win32con import EVENT_SYSTEM_FOREGROUND, EVENT_OBJECT_LOCATIONCHANGE


def start_win_hook(callback):
    user32 = ctypes.windll.LoadLibrary("user32")
    ole32 = ctypes.windll.LoadLibrary("ole32")
    user32.SetWinEventHook.restype = HANDLE
    WinEventProcType = ctypes.WINFUNCTYPE(None, HANDLE, DWORD, HWND,
                                          LONG, LONG, DWORD, DWORD)
    ole32.CoInitialize(0)

    WinEventProc = WinEventProcType(callback)

    # ref: https://docs.microsoft.com/en-us/windows/win32/winauto/event-constants

    hook = user32.SetWinEventHook(
        EVENT_SYSTEM_FOREGROUND, EVENT_OBJECT_LOCATIONCHANGE,
        0, WinEventProc, 0, 0, win32con.WINEVENT_OUTOFCONTEXT
    )

    if hook == 0:
        raise RuntimeError('SetWinEventHook failed')

    msg = MSG()
    while user32.GetMessageW(ctypes.byref(msg), 0, 0, 0) != 0:
        user32.TranslateMessageW(msg)
        user32.DispatchMessageW(msg)

    user32.UnhookWinEvent(hook)
    ole32.CoUninitialize()


def ms():
    return time.perf_counter() * 1000


def keyboard_hook_thread(double_ctrl_callback):
    INTERVAL = 500
    last_emit_time = -INTERVAL

    # TODO: 扩展性
    def on_event(args):
        nonlocal last_emit_time

        if args.event_type == 'key down':
            if 'Lcontrol' in args.pressed_key:
                now_time = ms()
                if now_time - last_emit_time < INTERVAL:
                    double_ctrl_callback()
                last_emit_time = ms()
            else:
                pass

    hk = Hook()
    hk.handler = on_event
    hk.hook(keyboard=True, mouse=False)


if __name__ == '__main__':
    def cb():
        print("double_ctrl_callback")


    Thread(target=keyboard_hook_thread, args=(cb,), daemon=True).start()
    while True:
        pass
