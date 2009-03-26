
from GitSvnServer import generate as gen
from GitSvnServer.cmd_base import *


class Commit (Command):
    _cmd = 'commit'

    def target_rev(self, rev):
        print "edit: target_rev"

    def open_root(self, rev, root_token):
        print "edit: open_root"

    def delete_entry(self, path, rev, dir_token):
        print "edit: delete_entry"

    def add_dir(self, path, parent_token, child_token, copy_path, copy_rev):
        print "edit: add_dir"

    def open_dir(self, path, parent_token, child_token, rev):
        print "edit: open_dir"

    def change_dir_prop(self, dir_token, name, value):
        print "edit: change_dir_prop"

    def close_dir(self, dir_token):
        print "edit: close_dir"

    def absent_dir(self, path, parent_token):
        print "edit: absent_dir"

    def add_file(self, path, dir_token, file_token, copy_path, copy_rev):
        print "edit: add_file"

    def open_file(self, path, dir_token, file_token, rev):
        print "edit: open_file"

    def apply_textdelta(self, file_token, base_checksum):
        print "edit: apply_textdelta"

    def textdelta_chunk(self, file_token, chunk):
        print "edit: textdelta_chunk"

    def textdelta_end(self, file_token):
        print "edit: textdelta_end"

    def change_file_prop(self, file_token, name, value):
        print "edit: change_file_prop"

    def close_file(self, file_token, text_checksum):
        print "edit: close_file"

    def absent_file(self, path, parent_token):
        print "edit: absent_file"

    @cmd_step
    def auth(self):
        raise ChangeMode('auth', 'command')

    @cmd_step
    def get_edits(self):
        self.link.send_msg(gen.success())
        raise ChangeMode('editor')

    @cmd_step
    def do_commit(self):
        self.link.send_msg(gen.error(1, "not implemented"))
