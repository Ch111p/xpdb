import bdb
import code
import marshal
import dis
import sys
import cmd
import new
import types
import sys
import types

from opcode import *

# https://nedbatchelder.com/blog/200804/wicked_hack_python_bytecode_tracing.html

class PycFile:
    def read(self, f):
        if isinstance(f, basestring):
            f = open(f, "rb")
        self.magic = f.read(4)
        self.modtime = f.read(4)
        self.code = marshal.load(f)

    def write(self, f):
        if isinstance(f, basestring):
            f = open(f, "wb")
        f.write(self.magic)
        f.write(self.modtime)
        marshal.dump(self.code, f)

    def hack_line_numbers(self):
        self.code = hack_line_numbers(self.code)


def hack_line_numbers(code):
    """ Replace a code object's line number information to claim that every
        byte of the bytecode is a new line.  Returns a new code object.
        Also recurses to hack the line numbers in nested code objects.
    """
    n_bytes = len(code.co_code)
    new_lnotab = "\x01\x01" * (n_bytes - 1)
    new_consts = []
    for const in code.co_consts:
        if type(const) == types.CodeType:
            new_consts.append(hack_line_numbers(const))
        else:
            new_consts.append(const)
    new_code = new.code(
        code.co_argcount, code.co_nlocals, code.co_stacksize, code.co_flags,
        code.co_code, tuple(new_consts), code.co_names, code.co_varnames,
        code.co_filename, code.co_name, 0, new_lnotab, code.co_freevars,
        code.co_cellvars
    )
    return new_code

class Xpdb(bdb.Bdb, cmd.Cmd):
    prompt = '(Xpdb2)'
    intro = 'A debugger for pyc file'

    def __init__(self):
        bdb.Bdb.__init__(self)
        cmd.Cmd.__init__(self)
        self.bplist = {}
        self.stepflag = True
        self.curFrame = None
        self.frameDict = {}

    def add_break(self, line, frame=None):
        if frame is None:
            frame = self.curFrame
        if frame.__hash__() not in self.bplist.keys():
            self.bplist.update({frame.__hash__(): []})
        self.bplist[frame.__hash__()].append(line)

    def do_break(self, arg):
        try:
            int(arg)
        except ValueError:
            print('usage: b[reak] line')
            return
        self.add_break(arg)

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

    def do_global(self, arg):
        print(self.curFrame.f_globals)

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

    def break_here(self, frame):
        if frame.__hash__() in self.bplist.keys():
            if frame.f_lasti in self.bplist[frame.__hash__()]:
                return True
        return False

    def __getcocode__(self, bytecode):
        dcode = marshal.loads(bytecode)
        return dcode

    def user_opcode(self, frame):
        flag = 1
        co = frame.f_code
        code = co.co_code
        n = len(code)
        i = frame.f_lasti
        extended_arg = 0
        free = None
        try:
            while i < n:
                c = code[i]
                op = ord(c)
                print '   ',
                if i == frame.f_lasti:
                    print '-->',
                else:
                    print '   ',
                print repr(i).rjust(4),
                print opname[op].ljust(20),
                i = i + 1
                if op >= HAVE_ARGUMENT:
                    oparg = ord(code[i]) + ord(code[i + 1]) * 256 + extended_arg
                    extended_arg = 0
                    i = i + 2
                    if op == EXTENDED_ARG:
                        extended_arg = oparg * 65536L
                    print repr(oparg).rjust(5),
                    if op in hasconst:
                        print '(' + repr(co.co_consts[oparg]) + ')',
                    elif op in hasname:
                        print '(' + co.co_names[oparg] + ')',
                    elif op in hasjrel:
                        print '(to ' + repr(i + oparg) + ')',
                    elif op in haslocal:
                        print '(' + co.co_varnames[oparg] + ')',
                    elif op in hascompare:
                        print '(' + cmp_op[oparg] + ')',
                    elif op in hasfree:
                        if free is None:
                            free = co.co_cellvars + co.co_freevars
                        print '(' + free[oparg] + ')',
                print
        except IndexError:
            if flag:
                print
                print 'this file might be confused, RECOMMEND STEP DEBUG'
            else:
                pass
        self.interaction(frame)

    def dispatch_line(self, frame):
        self.curFrame = frame
        if self.stepflag or self.break_here(frame):
            self.user_opcode(frame)
        return self.trace_dispatch

    def trace_dispatch(self, frame, event, arg):
        if self.quitting:
            return
        if event == 'line':
            return self.dispatch_line(frame)
        if event == 'call':
            return self.dispatch_call(frame, arg)
        if event == 'exception':
            return self.dispatch_exception(frame, arg)
        if event == 'c_call':
            return self.trace_dispatch
        if event == 'c_exception':
            return self.trace_dispatch
        if event == 'c_return':
            return self.trace_dispatch
        return self.trace_dispatch

    def interaction(self, frame):
        self.cmdloop()

    def user_call(self, frame, argument_list):
        name = frame.f_code.co_name
        if not name: name = '<Unknown>'
        print('call ' + name, argument_list)

    def user_exception(self, frame, exc_info):
        print('exception ', exc_info)

    def user_line(self, frame):
        print('line ', frame.f_lineno)


    def run(self, file, globals=None, locals=None):
        self.reset()
        self.dcode = hack_line_numbers(self.__getcocode__(file))
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
        print("usage: python xpdb2.py [*.pyc]")
        exit(0)
    fileName = sys.argv[1]
    with open(fileName, "rb") as f:
        f.seek(8)
        fileStr = f.read()
    xpdb.run(fileStr)
