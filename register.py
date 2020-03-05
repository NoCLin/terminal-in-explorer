import ctypes
import os
import subprocess
import sys

import winreg


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def request_admin():
    if not is_admin():
        # TODO: fix for bundle env
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, subprocess.list2cmdline(sys.argv), None, 1)
        exit()


def delete_sub_key(key0, current_key, arch_key=0):
    open_key = winreg.OpenKey(key0, current_key, 0, winreg.KEY_ALL_ACCESS | arch_key)
    info_key = winreg.QueryInfoKey(open_key)
    for x in range(0, info_key[0]):
        # NOTE:: This code is to delete the key and all sub_keys.
        # If you just want to walk through them, then
        # you should pass x to EnumKey. sub_key = winreg.EnumKey(open_key, x)
        # Deleting the sub_key will change the sub_key count used by EnumKey.
        # We must always pass 0 to EnumKey so we
        # always get back the new first sub_key.
        sub_key = winreg.EnumKey(open_key, 0)
        try:
            winreg.DeleteKey(open_key, sub_key)
            print("Removed %s\\%s " % (current_key, sub_key))
        except OSError:
            delete_sub_key(key0, current_key, sub_key)
            # No extra delete here since each call
            # to delete_sub_key will try to delete itself when its empty.

    winreg.DeleteKey(open_key, "")
    open_key.Close()
    print("Removed %s" % current_key)
    return


def main():
    request_admin()
    choice = None
    while choice not in ["Y", "N"]:
        choice = input("Input Y for register, N for unregister,Q for exit.").strip().upper()
        print(choice)
        if choice == "Q":
            exit()

    is_register = choice == "Y"

    try:
        background_shell = r"Directory\Background\shell"
        name = "Terminal In Explorer"
        if is_register:
            icon = "cmd.exe"
            if getattr(sys, 'frozen', False):
                command = os.path.abspath(os.path.join(os.path.dirname(__file__), "TIE.exe"))
            else:
                command = sys.executable.replace("python.exe", "pythonw.exe") + " " + os.path.abspath(
                    os.path.join(os.path.dirname(__file__), "main.py"))

            print(command)

            base_key = winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, background_shell)
            # base_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\*\shell") # file context menu
            app_key = winreg.CreateKey(base_key, name)
            winreg.SetValue(base_key, name, winreg.REG_SZ, name)
            winreg.SetValueEx(app_key, "Icon", 0, winreg.REG_SZ, icon)

            command_key = winreg.CreateKey(app_key, "command")
            winreg.SetValue(app_key, "command", winreg.REG_SZ, command)
            winreg.CloseKey(base_key)
            print("register successful.")
        else:
            delete_sub_key(winreg.HKEY_CLASSES_ROOT, background_shell + "\\" + name)
            print("unregister successful.")
    except Exception as e:
        print(e)
    os.system("pause")


if __name__ == '__main__':
    main()
