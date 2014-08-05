try:
    from hashlib import md5
except ImportError:
    from md5 import new as md5

from cStringIO import StringIO

import pygit2

from GitSvnServer import generate as gen
from GitSvnServer.cmd_base import *
from GitSvnServer import parse, svndiff


class Dir(object):
    def __init__(self, path, token, parent_token, rev, dirs):
        """
        :type dirs: dict[str, Dir]
        :type path: str
        :type token: str
        :type parent_token: str | None
        :type rev: int | None
        """

        self.files = {}
        """:type : dict[str, File]"""

        self.deleted = {}
        """:type : dict[str, int | None]"""

        self.path = path

        if parent_token is None:
            self.full_path = path
        else:
            parent = dirs[parent_token]
            parent.add(self)
            self.full_path = '/'.join([parent.full_path, path])

            if rev is None:
                rev = parent.rev

        assert rev is not None
        self.rev = rev

        dirs[token] = self

    def add(self, f):
        self.files[f.path] = f

    def set_prop(self, name, value):
        raise NotImplementedError("Unsupported dir property: %s" % name)

    def __str__(self):
        return "%s@%s" % (self.full_path, self.rev)


class File(object):
    def __init__(self, path, token, dir_token, commit_info, rev, dirs, files):
        """
        :type dirs: dict
        :type path: str
        :type token: str
        :type dir_token: str
        :type commit_info: GitSvnServer.repository.CommitInfo
        :type rev: int | None
        """

        parent = dirs[dir_token]

        self.path = path
        self.full_path = '/'.join([parent.full_path, path])

        if rev is None:
            rev = parent.rev
        assert rev is not None
        self.rev = rev

        self.commit_info = commit_info
        self.mode = None

        self.decoder = None
        """:type : svndiff.Decoder | None"""

        self.source = StringIO()
        """:type : StringIO"""

        self.target = StringIO()
        """:type : StringIO"""

        self.blob_id = None
        """:type : pygit2.Oid | None"""

        parent.add(self)
        files[token] = self

    def set_prop(self, name, value):
        if name == 'svn:executable':
            if value == '':
                self.mode = pygit2.GIT_FILEMODE_BLOB
            else:
                self.mode = pygit2.GIT_FILEMODE_BLOB_EXECUTABLE
        else:
            raise NotImplementedError("Unsupported file property: %s" % name)

    def delta_start(self, base_checksum):
        with self.commit_info.repo.read_lock:
            base = self.commit_info.repo.find_file(self.full_path, self.rev)

            if base != self.commit_info.repo.find_file(self.full_path, self.commit_info.parent_rev):
                raise PathChanged("File '%s' is out of date" % self.full_path)

        if base is None or base.blob_id is None:
            csum = None
        else:
            blob = self.commit_info.repo.pygit[base.blob_id]
            csum = md5(blob.data).hexdigest().hexdigest()

            self.source = StringIO(blob.data)

        if csum != base_checksum:
            raise ClientError("File '%s': checksum mismatch", self.full_path)

        self.decoder = svndiff.Decoder(self.source, self.target)

    def chunk(self, chunk):
        self.decoder.feed(chunk)

    def delta_complete(self):
        self.decoder.complete()
        self.decoder = None

        pygit = self.commit_info.repo.pygit
        self.blob_id = pygit.create_blob(self.target.getvalue())

        self.source.close()
        self.target.close()

    def close(self, checksum):
        """
        :type checksum: str | None
        """
        if self.blob_id is None:
            assert checksum is None
            return

        blob = self.commit_info.repo.pygit[self.blob_id]
        csum = md5(blob.data).hexdigest()
        if csum != checksum:
            raise ClientError("File '%s': checksum mismatch", self.full_path)

    def __str__(self):
        return "%s@%s" % (self.full_path, self.rev)


class Commit(Command):
    _cmd = 'commit'

    def __init__(self, link, args):
        Command.__init__(self, link, args)
        self.steps = [Commit.auth, Commit.get_edits, Commit.do_commit, Commit.auth, Commit.send_result]

        self.dirs = {}
        """:type : dict[str, Dir]"""

        self.files = {}
        """:type : dict[str, File]"""

        self.root = None
        """:type : Dir | None"""

        self.commit_info = None
        """:type : GitSvnServer.repository.CommitInfo"""

        self.result = None
        """:type : str | None"""

    def open_root(self, rev, root_token):
        if rev is None:
            rev = self.commit_info.parent_rev
        self.root = Dir(self.link.url, root_token, None, rev, self.dirs)

    def add_dir(self, path, parent_token, child_token, copy_path, copy_rev):
        # TODO(marat): copy_path/copy_rev
        Dir(path, child_token, parent_token, None, self.dirs)

    def open_dir(self, path, parent_token, child_token, rev):
        Dir(path, child_token, parent_token, rev, self.dirs)

    def close_dir(self, dir_token):
        pass

    def delete_entry(self, path, rev, dir_token):
        self.dirs[dir_token].deleted[path] = rev

    def add_file(self, path, dir_token, file_token, copy_path, copy_rev):
        # TODO(marat): copy_path/copy_rev
        File(path, file_token, dir_token, self.commit_info, None, self.dirs, self.files)

    def open_file(self, path, dir_token, file_token, rev):
        File(path, file_token, dir_token, self.commit_info, rev, self.dirs, self.files)

    def apply_textdelta(self, file_token, base_checksum):
        self.files[file_token].delta_start(base_checksum)

    def textdelta_chunk(self, file_token, chunk):
        self.files[file_token].chunk(chunk)

    def textdelta_end(self, file_token):
        self.files[file_token].delta_complete()

    def close_file(self, file_token, checksum):
        self.files[file_token].close(checksum)

    def change_file_prop(self, file_token, name, value):
        self.files[file_token].set_prop(name, value)

    def change_dir_prop(self, dir_token, name, value):
        self.dirs[dir_token].set_prop(name, value)

    # noinspection PyMethodMayBeStatic
    def auth(self):
        raise ChangeMode('auth', 'command')

    def get_edits(self):
        with self.link.repo.read_lock:
            self.commit_info = self.link.repo.start_commit()

        self.link.send_msg(gen.success())
        raise ChangeMode('editor')

    def do_commit(self):
        msg = parse.string(self.args.pop(0))

        with self.link.repo.write_lock:
            rev = self.link.repo.complete_commit(self.commit_info, msg, self.root, self.link.user)

        self.link.send_msg(gen.success())
        self.result = gen.list(rev.number, rev.gen_date(), rev.gen_author(), gen.list())

    def send_result(self):
        self.link.send_msg(self.result)
