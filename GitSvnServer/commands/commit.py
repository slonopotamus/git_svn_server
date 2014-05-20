
import cStringIO as StringIO
import os

from GitSvnServer import generate as gen
from GitSvnServer.cmd_base import *
from GitSvnServer import parse, svndiff, hooks
from GitSvnServer.errors import HookFailure


class Dir (object):
    dirs = {}
    def __init__(self, commit, path, token, parent_token=None, rev=None):
        self.commit = commit
        self.path = path
        self.token = token
        self.parent = None
        self.rev = rev

        self.props = {}
        self.files = {}

        if parent_token is not None:
            self.parent = Dir.dirs[parent_token]
            self.parent.add(self)

        Dir.dirs[token] = self

    def set_prop(self, name, value):
        self.props[name] = value
        self.commit.set_dir_prop(self.path, name, value)

    def add(self, file):
        name = file.path
        if name.startswith('%s/' % self.path):
            name = name[len(self.path) + 1:]
        self.files[name] = file

    def close(self):
        pass

    def __str__(self):
        f = ""
        for path, obj in self.files.items():
            f += "\n    %s: %s" % (path, obj)
        return "Dir(%s %s%s)" % (self.token, self.path, f)


class File (object):
    files = {}
    def __init__(self, path, token, dir_token, commit, rev=None, source=None):
        self.path = path
        self.token = token
        self.dir = Dir.dirs[dir_token]
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
        File.files[token] = self

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


class Commit (Command):
    _cmd = 'commit'

    def target_rev(self, rev):
        print "edit: target_rev"

    def open_root(self, rev, root_token):
        print "edit: open_root"
        self.root = Dir(self.commit, '', root_token)

    def delete_entry(self, path, rev, dir_token):
        print "edit: delete_entry"
        self.commit.remove_path(path)

    def add_dir(self, path, parent_token, child_token, copy_path, copy_rev):
        print "edit: add_dir -", path, parent_token, child_token, copy_path, copy_rev
        Dir(self.commit, path, child_token, parent_token)
        self.commit.add_dir(path, original=(copy_path, copy_rev))

    def open_dir(self, path, parent_token, child_token, rev):
        Dir(self.commit, path, child_token, parent_token, rev)
        self.commit.open_dir(path)

    def change_dir_prop(self, dir_token, name, value):
        Dir.dirs[dir_token].set_prop(name, value)

    def close_dir(self, dir_token):
        Dir.dirs[dir_token].close()

    def absent_dir(self, path, parent_token):
        print "edit: absent_dir"

    def add_file(self, path, dir_token, file_token, copy_path, copy_rev):
        File(path, file_token, dir_token, self.commit)

    def open_file(self, path, dir_token, file_token, rev):
        contents = None
        if rev is not None:
            url = '/'.join((self.link.url, path))
            r, pl, contents = self.link.repos.get_file(url, rev)
        File(path, file_token, dir_token, self.commit, rev, contents)

    def apply_textdelta(self, file_token, base_checksum):
        try:
            File.files[file_token].delta_start(base_checksum)
        except PathChanged, e:
            self.aborted = True
            self.link.send_msg(gen.error(1, "File '%s' is out of date" % e))

    def textdelta_chunk(self, file_token, chunk):
        File.files[file_token].chunk(chunk)

    def textdelta_end(self, file_token):
        File.files[file_token].delta_complete()

    def change_file_prop(self, file_token, name, value):
        print "edit: change_file_prop"
        File.files[file_token].set_prop(name, value)

    def close_file(self, file_token, text_checksum):
        File.files[file_token].close(text_checksum)

    def absent_file(self, path, parent_token):
        print "edit: absent_file"

    @cmd_step
    def auth(self):
        raise ChangeMode('auth', 'command')

    @cmd_step
    def get_edits(self):
        self.root = None
        self.aborted = False
        self.commit = self.link.repos.start_commit(self.link.url, self.link.username)

        self.link.send_msg(gen.success())
        raise ChangeMode('editor')

    @cmd_step
    def do_commit(self):
        repos = self.link.repos

        msg = parse.string(self.args[0])

        self.commit_info = None

        if self.aborted:
            self.link.send_msg(gen.error(1, "aborted"))
            return

        try:
            rev, date, author, error = repos.complete_commit(self.commit, msg)
        except HookFailure, hf:
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

    @cmd_step
    def send_commit_info(self):
        if self.commit_info is None:
            return

        self.link.send_msg(self.commit_info)
