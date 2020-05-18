import bdb
import code
import marshal
import dis
import sys
import opcode
import builtins
from types import CodeType
from types import FrameType
from typing import Any

num = 0

class Xpdb(bdb.Bdb):

    def __getcocode__(self, bytecode: bytes) -> CodeType:
        dcode = marshal.loads(bytecode)
        return dcode

    def user_opcode(self, frame: FrameType):
        dis.disco(self.dcode, frame.f_lasti)

    def dispatch_opcode(self, frame: FrameType):
        if self.stop_here(frame) or self.break_here(frame):
            self.user_opcode(frame)
        return self.trace_dispatch

    def trace_dispatch(self, frame: FrameType, event: str, arg: Any):
        if not frame.f_trace_opcodes:
            frame.f_trace_opcodes = True
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

    def user_call(self, frame, argument_list) -> None:
        name = frame.f_code.co_name
        if not name: name = '<Unknown>'
        print('call ' + name, argument_list)

    def user_exception(self, frame, exc_info) -> None:
        print('exception ', exc_info)

    def user_line(self, frame: FrameType) -> None:
        print('line ', frame.f_lineno)

    def run(self, cmd):
        self.reset()
        self.dcode = self.__getcocode__(cmd)
        sys.settrace(self.trace_dispatch)
        print(self.dcode.co_name)
        try:
            exec(self.dcode)
        # except:
        #     print("Something Wrong")
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