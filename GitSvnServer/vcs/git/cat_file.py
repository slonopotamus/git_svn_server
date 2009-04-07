
from data import *


class GitObject (object):
    def __init__(self, cat_file, sha1):
        self.cat_file = cat_file
        self.sha1 = sha1
        self.type = ''
        self.size = 0
        self._read = 0

    def read_header(self):
        self.cat_file.data.write('%s\n' % self.sha1)
        self.cat_file.data.flush()

        c = ''
        while len(c) == 0 or c[-1] != '\n':
            c += self.cat_file.read(1)
        c = c[:-1]

        sha1, info = c.split(' ', 1)

        if info == 'missing':
            self.type = 'missing'
            return

        self.type, size = info.split(' ', 1)
        self.size = int(size)

    def read(self, l=None):
        if self.type == '':
            self.read_header()

        if self._read >= self.size:
            return ''

        if l is None:
            l = self.size - self._read
        else:
            l = min(l, self.size - self._read)

        data = self.cat_file.read(l)
        self._read += len(data)
        return data

    def close(self):
        while self._read < self.size:
            data = self.read(min(8192, self.size - self.read))
        if self._read == self.size:
            self.cat_file.read(1)
            self._read += 1


class GitCatFile (object):
    def __init__(self, location):
        self.data = GitData(location, 'cat-file --batch')
        self.data.open()

    def get_object(self, sha1):
        return GitObject(self, sha1)

    def read(self, l=-1):
        return self.data.read(l)
