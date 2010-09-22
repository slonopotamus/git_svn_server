

import os
import cStringIO as StringIO


git_binary = "git"
verbose_mode = False


try:
    from subprocess import Popen, PIPE
    def run_cmd(cmd):
        p = Popen(cmd, shell=True,
                  stdin=PIPE, stdout=PIPE, stderr=PIPE,
                  close_fds=True)
        return p.stdin, p.stdout, p.stderr
except ImportError:
    def run_cmd(cmd):
        return os.popen3(self._cmd)


class GitData (object):
    def __init__(self, location, command_string):
        self._cmd = "%s %s" % (git_binary, command_string)
        self._location = location
        self._data = None

    def open(self):
        if verbose_mode:
            print "  >> %s" % (self._cmd)

        cwd = os.getcwd()
        os.chdir(self._location)

        self._in, self._data, self._err = run_cmd(self._cmd)

        self._read = 0

        os.chdir(cwd)

    def tell(self):
        return self._read

    def read(self, l=-1):
        if self._data is None:
            self.open()

        data = self._data.read(l)
        self._read += len(data)
        return data

    def write(self, data):
        if self._data is None:
            self.open()

        self._in.write(data)

    def flush(self):
        if self._data is not None:
            self._in.flush()

    def close_stdin(self):
        if self._data is not None:
            self._in.close()

    def close(self):
        if self._data is not None:
            self._in.close()
            self._data.close()
            self._err.close()
            self._data = None

    def reopen(self):
        self.close()
        self.open()


class FakeData (object):
    def __init__(self, data):
        self._data = data
        self._string = None

    def open(self):
        self._string = StringIO.StringIO(self._data)

    def read(self, l=-1):
        if self._string is None:
            self.open()
        return self._string.read(l)

    def close(self):
        if self._string is not None:
            self._string.close()
        self._string = None

    def reopen(self):
        self.close()
        self.open()
