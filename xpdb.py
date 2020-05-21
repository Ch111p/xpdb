import bdb
import code
import marshal
import dis
import sys
import cmd
import opcode
import builtins
from types import CodeType
from types import FrameType
from typing import Any


class Xpdb(bdb.Bdb, cmd.Cmd):
    prompt = '(Xpdb)'
    intro = 'A debugger for pyc file'

    def __init__(self):
        bdb.Bdb.__init__(self)
        cmd.Cmd.__init__(self)
        self.bplist = []
        self.stepflag = True
        self.curFrame = None

    def do_break(self, arg: str):
        try:
            self.bplist.append(int(arg))
        except ValueError:
            print('usage: b[reak] line')
            return
        self.bplist.append(arg)
    do_b = do_break

    def do_continue(self, arg):
        print(arg)
        self.stepflag = False
        return 1
    do_c = do_continue

    def do_step(self, arg):
        print('arg:', arg)
        self.stepflag = True
        return 1
    do_s = do_step

    # TODO
    def do_stack(self, arg):
        return

    def do_p(self, arg):
        try:
            print(arg, repr(eval(arg, self.curFrame.f_globals, self.curFrame.f_locals)))
        except Exception as e:
            print('Something wrong ', repr(e))


    def break_here(self, frame: FrameType) -> bool:
        if frame.f_lasti in self.bplist:
            return True
        return False

    def __getcocode__(self, bytecode: bytes) -> CodeType:
        dcode = marshal.loads(bytecode)
        return dcode

    def user_opcode(self, frame: FrameType):
        dis.disco(frame.f_code, frame.f_lasti)
        self.interaction(frame)

    def dispatch_opcode(self, frame: FrameType):
        self.curFrame = frame
        if self.stepflag or self.break_here(frame):
            self.user_opcode(frame)
        return self.trace_dispatch

    def trace_dispatch(self, frame: FrameType, event: str, arg: Any):
        if not frame.f_trace_opcodes:
            frame.f_trace_opcodes = True
            self.curFrame = frame
        if self.quitting:
            return
        if event == 'line':
            return self.dispatch_line(frame)
        if event == 'call':
            return self.dispatch_call(frame, arg)
        if event == 'exception':
            return self.dispatch_exception(frame, arg)
        if event == 'opcode':
            return self.dispatch_opcode(frame)
        if event == 'c_call':
            return self.trace_dispatch
        if event == 'c_exception':
            return self.trace_dispatch
        if event == 'c_return':
            return self.trace_dispatch
        return self.trace_dispatch

    def interaction(self, frame):
        self.cmdloop()

    def user_call(self, frame, argument_list) -> None:
        name = frame.f_code.co_name
        if not name: name = '<Unknown>'
        print('call ' + name, argument_list)

    def user_exception(self, frame, exc_info) -> None:
        print('exception ', exc_info)

    def user_line(self, frame: FrameType) -> None:
        print('line ', frame.f_lineno)

    def run(self, file: bytes):
        self.reset()
        self.dcode = self.__getcocode__(file)
        sys.settrace(self.trace_dispatch)
        print(self.dcode.co_name)
        try:
            exec(self.dcode)
        except:
            print("Something Wrong")
        finally:
            self.quitting = True
            sys.settrace(None)


if __name__ == "__main__":
    xpdb = Xpdb()
    with open("test.pyc", "rb") as f:
        f.seek(16)
        fileStr = f.read()
    print(fileStr)
    xpdb.run(fileStr)