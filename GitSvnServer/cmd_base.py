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


def need_repo_lock(f):
    def call(self):
        with self.link.repos.lock:
            f(self)

    return call


class Command:
    __metaclass__ = MetaCommand

    _cmd = None

    def __init__(self, link, args):
        """

        :type link: SvnRequestHandler
        """
        self.steps = []
        self.next_step = 0
        self.link = link
        self.args = args
        self.report_errors = []
        self.edit_errors = []

    def process(self):
        if self.next_step >= len(self.steps):
            return None

        next_step = self.next_step
        self.next_step += 1

        self.steps[next_step](self)

        return self

    #
    # report command set functions
    #

    def report_set_path(self, path, rev, start_empty, lock_token, depth):
        raise NotImplementedError()

    def report_link_path(self, path, url, rev, start_empty, lock_token, depth):
        raise NotImplementedError()

    def report_delete_path(self, path):
        raise NotImplementedError()

    def report_finish(self):
        raise ChangeMode('auth', 'command')

    def report_abort(self):
        raise NotImplementedError()

    def log_report_error(self, errno, errstr):
        self.report_errors.append((errno, errstr))

    #
    # editor command set functions
    #

    def target_rev(self, rev):
        raise NotImplementedError()

    def open_root(self, rev, root_token):
        raise NotImplementedError()

    def delete_entry(self, path, rev, dir_token):
        raise NotImplementedError()

    def add_dir(self, path, parent_token, child_token, copy_path, copy_rev):
        raise NotImplementedError()

    def open_dir(self, path, parent_token, child_token, rev):
        raise NotImplementedError()

    def change_dir_prop(self, dir_token, name, value):
        raise NotImplementedError()

    def close_dir(self, dir_token):
        raise NotImplementedError()

    def absent_dir(self, path, parent_token):
        raise NotImplementedError()

    def add_file(self, path, dir_token, file_token, copy_path, copy_rev):
        raise NotImplementedError()

    def open_file(self, path, dir_token, file_token, rev):
        raise NotImplementedError()

    def apply_textdelta(self, file_token, base_checksum):
        raise NotImplementedError()

    def textdelta_chunk(self, file_token, chunk):
        raise NotImplementedError()

    def textdelta_end(self, file_token):
        raise NotImplementedError()

    def change_file_prop(self, file_token, name, value):
        raise NotImplementedError()

    def close_file(self, file_token, text_checksum):
        raise NotImplementedError()

    def absent_file(self, path, parent_token):
        raise NotImplementedError()

    def edit_finish(self):
        raise ChangeMode('command')

    def edit_abort(self):
        raise NotImplementedError()

    def log_edit_error(self, errno, errstr):
        self.edit_errors.append((errno, errstr))


class SimpleCommand(Command):
    def auth(self):
        raise ChangeMode('auth', 'command')

    def main(self):
        self.do_cmd()

    def do_cmd(self):
        raise NotImplemented()

    def __init__(self, link, args):
        Command.__init__(self, link, args)
        self.steps = [SimpleCommand.auth, SimpleCommand.main]
