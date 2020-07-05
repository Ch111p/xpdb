import bdb
import pdb
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
        self.bplist = {}
        self.stepflag = True
        self.curFrame = None
        self.frameDict = {}

    def do_break(self, arg: str):
        try:
            int(arg)
        except ValueError:
            print('usage: b[reak] line')
            return
        if self.curFrame.__hash__() not in self.bplist.keys():
            self.bplist.update({self.curFrame.__hash__(): []})
        self.bplist[self.curFrame.__hash__()].append(arg)

    do_b = do_break

    def do_continue(self, arg):
        self.stepflag = False
        return 1

    do_c = do_continue

    def do_step(self, arg):
        self.stepflag = True
        return 1

    do_s = do_step

    def do_finish(self, arg):
        self.add_break(self.curFrame.f_back.f_lasti + 3, self.curFrame.f_back)
        self.stepflag = False
        return 1

    # TODO
    def do_stack(self, arg):
        return

    # TODO
    def do_x(self, arg):
        return

    def do_p(self, arg):
        try:
            print(arg, repr(eval(arg, self.curFrame.f_globals, self.curFrame.f_locals)))
        except Exception as e:
            print('Something wrong ', repr(e))

    def break_here(self, frame: FrameType) -> bool:
        if frame.__hash__() in self.bplist.keys():
            if frame.f_lasti in self.bplist[frame.__hash__()]:
                return True
        return False

    def __getcocode__(self, bytecode: bytes) -> CodeType:
        dcode = marshal.loads(bytecode)
        return dcode

    # modified from dis.disco
    def user_opcode(self, frame: FrameType):
        # dis.disco(frame.f_code, frame.f_lasti)
        if frame.__hash__() not in self.frameDict.keys():
            self.frameDict.update({frame.__hash__(): {}})
            linestarts = dict(dis.findlinestarts(frame.f_code))
            insList = []
            maxlineno = max(linestarts.values())
            length = 0
            cell_names = frame.f_code.co_cellvars + frame.f_code.co_freevars
            if maxlineno >= 10000:
                lineno_width = len(str(maxlineno))
            else:
                lineno_width = 4
            maxoffset = len(frame.f_code.co_code) - 2
            if maxoffset >= 10000:
                offset_width = len(str(maxoffset))
            else:
                offset_width = 4
            for instr in dis.get_instructions(frame.f_code):
                insList.append(instr)
            self.frameDict[frame.__hash__()].update({'insList': insList,
                                                     'lineno_width': lineno_width,
                                                     'offset_width': offset_width})
        lineno_width = self.frameDict[frame.__hash__()]['lineno_width']
        offset_width = self.frameDict[frame.__hash__()]['offset_width']
        insList = self.frameDict[frame.__hash__()]['insList']
        for instr in insList:
            is_current_instr = instr.offset == frame.f_lasti
            print(instr._disassemble(lineno_width, is_current_instr, offset_width))
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

    def codeObjectChange(self, arg: bytes):
        return

    def run(self, file: bytes, globals=None, locals=None):
        self.reset()
        self.dcode = self.__getcocode__(file)
        if globals is None:
            import __main__
            globals = __main__.__dict__
        if locals is None:
            locals = globals
        sys.settrace(self.trace_dispatch)
        try:
            exec(self.dcode, globals, locals)
        except Exception as e:
            print("Something Wrong")
            print(e, repr(e))
        finally:
            self.quitting = True
            sys.settrace(None)


if __name__ == "__main__":
    xpdb = Xpdb()
    if len(sys.argv) < 2:
        print("usage: python3 xpdb.py [*.pyc]")
        exit(0)
    fileName = sys.argv[1]
    with open(fileName, "rb") as f:
        f.seek(16)
        fileStr = f.read()
    xpdb.run(fileStr)
