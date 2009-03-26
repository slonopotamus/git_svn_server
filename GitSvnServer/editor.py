
import parse

from errors import *

edit_cmds = {}

def edit_func(name):
    def _edit_func(f):
        edit_cmds.setdefault(name, f)
        return f
    return _edit_func

@edit_func('target-rev')
def target_rev(command, args):
    rev = int(args[0])

    command.target_rev(rev)

@edit_func('open-root')
def open_root(command, args):
    rev = None
    if len(args[0]) > 0:
        rev = int(args[0][0])

    root_token = parse.string(args[1])

    command.open_root(rev, root_token)

@edit_func('delete-entry')
def delete_entry(command, args):
    path = parse.string(args[0])
    rev = int(args[1])
    dir_token = parse.string(args[2])

    command.delete_entry(path, rev, dir_token)

@edit_func('add-dir')
def add_dir(command, args):
    path = parse.string(args[0])
    parent_token = parse.string(args[1])
    child_token = parse.string(args[2])

    copy_path = None
    copy_rev = None
    if len(args[3]) > 0:
        copy_path = parse.string(args[3][0])
        copy_rev = int(args[3][1])

    command.add_dir(path, parent_token, child_token, copy_path, copy_rev)

@edit_func('open-dir')
def open_dir(command, args):
    path = parse.string(args[0])
    parent_token = parse.string(args[1])
    child_token = parse.string(args[2])

    rev = None
    if len(args[3]) > 0:
        rev = int(args[3][0])

    command.open_dir(path, parent_token, child_token, rev)

@edit_func('change-dir-prop')
def change_dir_prop(command, args):
    dir_token = parse.string(args[0])
    name = parse.string(args[1])

    value = None
    if len(args[2]) > 0:
        value = parse.string(args[2][0])

    command.change_dir_prop(dir_token, name, value)

@edit_func('close-dir')
def close_dir(command, args):
    dir_token = parse.string(args[0])

    command.close_dir(dir_token)

@edit_func('absent-dir')
def absent_dir(command, args):
    path = parse.string(args[0])
    parent_token = parse.string(args[1])

    command.absent_dir(path, parent_token)

@edit_func('add-file')
def add_file(command, args):
    path = parse.string(args[0])
    dir_token = parse.string(args[1])
    file_token = parse.string(args[2])

    copy_path = None
    copy_rev = None
    if len(args[3]) > 0:
        copy_path = parse.string(args[3][0])
        copy_rev = int(args[3][1])

    command.add_file(path, dir_token, file_token, copy_path, copy_rev)

@edit_func('open-file')
def open_file(command, args):
    path = parse.string(args[0])
    dir_token = parse.string(args[1])
    file_token = parse.string(args[2])

    rev = None
    if len(args[3]) > 0:
        rev = int(args[3][0])

    command.open_file(path, dir_token, file_token, rev)

@edit_func('apply-textdelta')
def apply_textdelta(command, args):
    file_token = parse.string(args[0])

    base_checksum = None
    if len(args[1]) > 0:
        base_checksum = parse.string(args[1][0])

    command.apply_textdelta(file_token, base_checksum)

@edit_func('textdelta-chunk')
def textdelta_chunk(command, args):
    file_token = parse.string(args[0])
    chunk = parse.string(args[1])

    command.textdelta_chunk(file_token, chunk)

@edit_func('textdelta-end')
def textdelta_end(command, args):
    file_token = parse.string(args[0])

    command.textdelta_end(file_token)

@edit_func('change-file-prop')
def change_file_prop(command, args):
    file_token = parse.string(args[0])
    name = parse.string(args[1])

    value = None
    if len(args[2]) > 0:
        value = parse.string(args[2][0])

    command.change_file_prop(file_token, name, value)

@edit_func('close-file')
def close_file(command, args):
    file_token = parse.string(args[0])

    text_checksum = None
    if len(args[1]) > 0:
        text_checksum = parse.string(args[1][0])

    command.close_file(file_token, text_checksum)

@edit_func('absent-file')
def absent_file(command, args):
    path = parse.string(args[0])
    parent_token = parse.string(args[1])

    command.absent_file(path, parent_token)

@edit_func('close-edit')
def finish_edit(command, args):
    command.edit_finish()

@edit_func('abort-edit')
def abort_edit(command, args):
    command.edit_abort()

def process(link):
    msg = parse.msg(link.read_msg())

    command = link.command

    if command is None:
        raise ModeError('editor mode requires a current command')

    editor = msg[0]
    args = msg[1]

    if editor not in edit_cmds:
        command.log_edit_error(210001, "Unknown command '%s'" % editor)
        return

    edit_cmds[editor](command, args)
