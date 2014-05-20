import cStringIO as StringIO

from GitSvnServer import generate as gen
from GitSvnServer.cmd_base import *
from GitSvnServer import parse, svndiff, hooks
from GitSvnServer.errors import HookFailure


class Dir(object):
    def __init__(self, commit, path, token, dirs, parent_token=None, rev=None):
        self.commit = commit
        self.path = path
        self.token = token
        self.parent = None
        self.rev = rev

        self.props = {}
        self.files = {}

        if parent_token is not None:
            self.parent = dirs[parent_token]
            self.parent.add(self)

        dirs[token] = self

    def set_prop(self, name, value):
        self.props[name] = value
        self.commit.set_dir_prop(self.path, name, value)

    def add(self, f):
        name = f.path
        if name.startswith('%s/' % self.path):
            name = name[len(self.path) + 1:]
        self.files[name] = f

    def close(self):
        pass

    def __str__(self):
        f = ""
        for path, obj in self.files.items():
            f += "\n    %s: %s" % (path, obj)
        return "Dir(%s %s%s)" % (self.token, self.path, f)


class File(object):
    def __init__(self, path, token, dir_token, commit, dirs, files, rev=None, source=None):
        self.path = path
        self.token = token
        self.dir = dirs[dir_token]
        self.dir.add(self)
        self.commit = commit
        self.rev = rev
        if source is None:
            self.source = StringIO.StringIO()
        else:
            self.source = source
        self.target = None
        self.props = {}
        self.diff = None

        files[token] = self

    def set_prop(self, name, value):
        self.props[name] = value
        self.commit.set_file_prop(self.path, name, value)

    def delta_start(self, base_checksum):
        rev = self.rev
        if rev is None:
            rev = self.dir.rev
        self.target = self.commit.modify_file(self.path, rev)
        self.diff = svndiff.Decoder(self.source, self.target)

    def chunk(self, chunk):
        if self.diff is not None:
            self.diff.feed(chunk)

    def delta_complete(self):
        if self.diff is not None:
            self.diff.complete()
        self.source.close()
        if self.target is not None:
            self.target.close()

    def close(self, checksum):
        print "check checksum here ..."

    def __str__(self):
        return "File(%s %s)" % (self.token, self.path)


class Commit(Command):
    _cmd = 'commit'

    def target_rev(self, rev):
        print "edit: target_rev"

    def open_root(self, rev, root_token):
        print "edit: open_root"
        self.root = Dir(self.commit, '', root_token, self.dirs)

    def delete_entry(self, path, rev, dir_token):
        print "edit: delete_entry"
        self.commit.remove_path(path)

    def add_dir(self, path, parent_token, child_token, copy_path, copy_rev):
        print "edit: add_dir -", path, parent_token, child_token, copy_path, copy_rev
        Dir(self.commit, path, child_token, self.dirs, parent_token)
        self.commit.add_dir(path, original=(copy_path, copy_rev))

    def open_dir(self, path, parent_token, child_token, rev):
        Dir(self.commit, path, child_token, self.dirs, parent_token, rev)
        self.commit.open_dir(path)

    def change_dir_prop(self, dir_token, name, value):
        self.dirs[dir_token].set_prop(name, value)

    def close_dir(self, dir_token):
        self.dirs[dir_token].close()

    def absent_dir(self, path, parent_token):
        print "edit: absent_dir"

    def add_file(self, path, dir_token, file_token, copy_path, copy_rev):
        File(path, file_token, dir_token, self.commit, self.dirs, self.files)

    def open_file(self, path, dir_token, file_token, rev):
        contents = None
        if rev is not None:
            url = '/'.join((self.link.url, path))
            r, pl, contents = self.link.repos.get_file(url, rev)
        File(path, file_token, dir_token, self.commit, self.dirs, self.files, rev, contents)

    def apply_textdelta(self, file_token, base_checksum):
        try:
            self.files[file_token].delta_start(base_checksum)
        except PathChanged as e:
            self.aborted = True
            self.link.send_msg(gen.error(1, "File '%s' is out of date" % e))

    def textdelta_chunk(self, file_token, chunk):
        self.files[file_token].chunk(chunk)

    def textdelta_end(self, file_token):
        self.files[file_token].delta_complete()

    def change_file_prop(self, file_token, name, value):
        print "edit: change_file_prop"
        self.files[file_token].set_prop(name, value)

    def close_file(self, file_token, text_checksum):
        self.files[file_token].close(text_checksum)

    def absent_file(self, path, parent_token):
        print "edit: absent_file"

    def auth(self):
        raise ChangeMode('auth', 'command')

    def get_edits(self):
        self.root = None
        self.aborted = False
        self.commit = self.link.repos.start_commit(self.link.url, self.link.username)

        self.link.send_msg(gen.success())
        raise ChangeMode('editor')

    def do_commit(self):
        repos = self.link.repos

        msg = parse.string(self.args[0])

        self.commit_info = None

        if self.aborted:
            self.link.send_msg(gen.error(1, "aborted"))
            return

        try:
            rev, date, author, error = repos.complete_commit(self.commit, msg)
        except HookFailure as hf:
            err, msg = hooks.pre_commit(hf.code, hf.text)
            self.link.send_msg(gen.error(err, msg))
            return

        print rev, date, author, error

        if rev is None:
            self.link.send_msg(gen.error(1, "vcs error: %s" % error))
            return

        self.commit_info = gen.list(rev, gen.list(gen.string(date)),
                                    gen.list(gen.string(author)), gen.list())

        self.link.send_msg(gen.success())
        raise ChangeMode('auth', 'command')

    def send_commit_info(self):
        if self.commit_info is None:
            return

        self.link.send_msg(self.commit_info)

    def __init__(self, link, args):
        Command.__init__(self, link, args)
        self.steps = [Commit.auth, Commit.get_edits, Commit.do_commit, Commit.send_commit_info]
        self.dirs = {}
        self.files = {}
        self.aborted = False
        self.root = None
        self.commit = None
        self.commit_info = None
