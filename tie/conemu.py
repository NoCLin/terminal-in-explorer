import subprocess


class ConEmu():
    def __init__(self, conemu, conemuc):
        self.conemu = conemu
        self.conemuc = conemuc
        self.process = None
        self.pid = 0

    def attach_to_hwnd(self, hwnd, init_command="cmd", admin=False):


        args = [
            self.conemu,
            "-NoUpdate",
            "-NoKeyHooks",
            "-InsideWnd", hex(hwnd),
            # "-LoadCfgFile", r"C:\Users\User\Desktop\conemu-inside-master\ConEmuInside\bin\Debug\ConEmu.xml",
            # "-Dir",r"C:\Users\User\Desktop\conemu-inside-master\ConEmuInside\bin\Debug",
            # "-detached",
            "-cmd",
            init_command,
            "-new_console" + ":a" if admin else "",

            # "-run",
            # "powershell.exe",
            # "",
        ]
        print(" ".join(args))
        self.process = subprocess.Popen(args)
        self.pid = int(self.process.pid)

    def execute(self, marco):
        args = [
            '"%s"' % self.conemuc,
            "-guimacro:%d" % (self.pid),
            marco
        ]

        print("execute ", " ".join(args))
        p = subprocess.Popen(" ".join(args),stdout=subprocess.PIPE,stderr=subprocess.PIPE, shell=True, universal_newlines=True)
        stdout, stderr = p.communicate(timeout=1)
        if stderr:
            raise RuntimeError(stderr)
        if stdout.startswith("FAILED:"):
            raise RuntimeError(stdout)

        result = stdout.rstrip().split(",")
        print(result)
        return result

    def input(self, command):
        marco = r'print("\e")  print(@"%s") print("\n")' % command.replace('"', '""')
        return self.execute(marco)

    def is_idle(self):
        # 多个窗口的时候,确定终端是否空闲需要取出当前的PID
        active_pid = int(self.execute(r'GetInfo("ActivePID")')[0])
        import tie.utils
        tabs = tie.utils.get_child_processes(self.pid)
        print(tabs)

        def find(node, parent_path, target):
            for p in node:
                _name, _pid, _child = p
                cur_path = parent_path + [_name]
                if _pid == target:
                    return cur_path
                if len(_child):
                    r = find(_child, cur_path, target)
                    if r:
                        return r

        process_path = find(tabs,parent_path=[],target=active_pid)
        print(process_path)
        # 检测 进程路径长度 判断是否空闲
        # FIXME: git-bash 不在子进程里
        # user_execute_process = [i[2] for tab in tabs if tab[1]==active_pid]
        # return len(user_execute_process) == 0
        return False
