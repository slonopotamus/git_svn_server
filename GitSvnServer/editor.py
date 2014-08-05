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
    rev = int(args.pop(0))

    command.target_rev(rev)


@edit_func('open-root')
def open_root(command, args):
    arg = args.pop(0)
    if len(arg) > 0:
        rev = int(arg[0])
    else:
        rev = None

    root_token = parse.string(args.pop(0))

    command.open_root(rev, root_token)


@edit_func('delete-entry')
def delete_entry(command, args):
    path = parse.string(args.pop(0))

    arg = args.pop(0)
    if len(arg) > 0:
        rev = int(arg[0])
    else:
        rev = None

    dir_token = parse.string(args.pop(0))

    command.delete_entry(path, rev, dir_token)


@edit_func('add-dir')
def add_dir(command, args):
    path = parse.string(args.pop(0))
    parent_token = parse.string(args.pop(0))
    child_token = parse.string(args.pop(0))

    arg = args.pop(0)
    if len(arg) > 0:
        copy_path = parse.string(arg[0])
        copy_rev = int(arg[1])
    else:
        copy_path = None
        copy_rev = None

    command.add_dir(path, parent_token, child_token, copy_path, copy_rev)


@edit_func('open-dir')
def open_dir(command, args):
    path = parse.string(args.pop(0))
    parent_token = parse.string(args.pop(0))
    child_token = parse.string(args.pop(0))

    arg = args.pop(0)
    if len(arg) > 0:
        rev = int(arg[0])
    else:
        rev = None

    command.open_dir(path, parent_token, child_token, rev)


@edit_func('change-dir-prop')
def change_dir_prop(command, args):
    dir_token = parse.string(args.pop(0))
    name = parse.string(args.pop(0))

    arg = args.pop(0)
    if len(arg) > 0:
        value = parse.string(arg[0])
    else:
        value = None

    command.change_dir_prop(dir_token, name, value)


@edit_func('close-dir')
def close_dir(command, args):
    dir_token = parse.string(args.pop(0))

    command.close_dir(dir_token)


@edit_func('absent-dir')
def absent_dir(command, args):
    path = parse.string(args.pop(0))
    parent_token = parse.string(args.pop(0))

    command.absent_dir(path, parent_token)


@edit_func('add-file')
def add_file(command, args):
    path = parse.string(args.pop(0))
    dir_token = parse.string(args.pop(0))
    file_token = parse.string(args.pop(0))

    arg = args.pop(0)
    if len(args) > 0:
        copy_path = parse.string(arg[0])
        copy_rev = int(arg[1])
    else:
        copy_path = None
        copy_rev = None

    command.add_file(path, dir_token, file_token, copy_path, copy_rev)


@edit_func('open-file')
def open_file(command, args):
    path = parse.string(args.pop(0))
    dir_token = parse.string(args.pop(0))
    file_token = parse.string(args.pop(0))

    arg = args.pop(0)
    if len(arg) > 0:
        rev = int(arg[0])
    else:
        rev = None

    command.open_file(path, dir_token, file_token, rev)


@edit_func('apply-textdelta')
def apply_textdelta(command, args):
    file_token = parse.string(args.pop(0))

    arg = args.pop(0)
    if len(arg) > 0:
        base_checksum = parse.string(arg[0])
    else:
        base_checksum = None

    command.apply_textdelta(file_token, base_checksum)


@edit_func('textdelta-chunk')
def textdelta_chunk(command, args):
    file_token = parse.string(args.pop(0))
    chunk = parse.string(args.pop(0))

    command.textdelta_chunk(file_token, chunk)


@edit_func('textdelta-end')
def textdelta_end(command, args):
    file_token = parse.string(args.pop(0))

    command.textdelta_end(file_token)


@edit_func('change-file-prop')
def change_file_prop(command, args):
    file_token = parse.string(args.pop(0))
    name = parse.string(args.pop(0))

    arg = args.pop(0)
    if len(arg) > 0:
        value = parse.string(arg[0])
    else:
        value = None

    command.change_file_prop(file_token, name, value)


@edit_func('close-file')
def close_file(command, args):
    file_token = parse.string(args.pop(0))

    arg = args.pop(0)
    if len(arg) > 0:
        checksum = parse.string(arg[0])
    else:
        checksum = None

    command.close_file(file_token, checksum)


@edit_func('absent-file')
def absent_file(command, args):
    path = parse.string(args.pop(0))
    parent_token = parse.string(args.pop(0))

    command.absent_file(path, parent_token)


@edit_func('close-edit')
def finish_edit(command, _):
    command.edit_finish()


@edit_func('abort-edit')
def abort_edit(command, _):
    command.edit_abort()


def process(link):
    msg = parse.msg(link.read_msg())

    command = link.command

    if command is None:
        raise ClientError('editor mode requires a current command')

    editor = msg[0]
    args = msg[1]

    if editor not in edit_cmds:
        raise ClientError("Unknown command '%s'" % editor)

    # noinspection PyCallingNonCallable
    edit_cmds[editor](command, args)
