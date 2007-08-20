from errors import *

commands = {}

class MetaCommand(type):
    def __new__(cls, name, bases, klassDict):
        stepsd = {}
        for name, x in klassDict.items():
            try:
                stepsd[x._step_idx] = x
            except AttributeError:
                pass
        steps = []
        for step in sorted(stepsd.keys()):
            steps.append(stepsd[step])
        klassDict['steps'] = steps
        theKlass = type.__new__(cls, name, bases, klassDict)
        if theKlass._cmd is not None:
            commands[theKlass._cmd] = theKlass
        return theKlass

class CmdStep:
    def __init__(self):
        self.next = 1

    def __call__(self, f):
        f._step_idx = self.next
        self.next += 1
        return f

cmd_step = CmdStep()

class Command:
    __metaclass__ = MetaCommand

    _cmd = None

    def __init__(self, link, args):
        self.next_step = 0
        self.link = link
        self.args = args

    def process(self):
        if self.next_step >= len(self.steps):
            return None

        next_step = self.next_step
        self.next_step += 1

        self.steps[next_step](self)

        return self

class SimpleCommand(Command):
    def auth(self):
        raise ChangeMode('auth', 'command')

    def main(self):
        self.do_cmd()

    def do_cmd(self):
        pass

    def __init__(self, link, args):
        self.steps = [SimpleCommand.auth, SimpleCommand.main]
        Command.__init__(self, link, args)
