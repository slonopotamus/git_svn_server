
import parse

from errors import *

rpt_cmds = {}

def rpt_func(name):
    def _rpt_func(f):
        rpt_cmds.setdefault(name, f)
        return f
    return _rpt_func

@rpt_func('set-path')
def set_path(command, args):
    path = parse.string(args[0])
    rev = int(args[1])
    start_empty = args[2].lower() == 'true'

    lock_token = None
    if len(args) > 3 and len(args[3]) != 0:
        lock_token = parse.string(args[3][0])

    depth = None
    if len(args) > 4:
        depth = args[4]

    command.report_set_path(path, rev, start_empty, lock_token, depth)

@rpt_func('delete-path')
def delete_path(command, args):
    path = parse.string(args[0])

    command.report_delete_path(path)

@rpt_func('link-path')
def link_path(command, args):
    path = parse.string(args[0])
    url = parse.string(args[1])
    rev = int(args[2])
    start_empty = parse.bool(args[3])

    lock_token = None
    if len(args) > 4:
        lock_token = parse.string(args[4][0])

    depth = None
    if len(args) > 5:
        depth = args[5]

    command.report_link_path(path, url, rev, start_empty, lock_token, depth)

@rpt_func('finish-report')
def finish_report(command, args):
    command.report_finish()

@rpt_func('abort-report')
def abort_report(command, args):
    command.report_abort()

def process(link):
    msg = parse.msg(link.read_msg())

    command = link.command

    if command is None:
        raise ModeError('report mode requires a current command')

    report = msg[0]
    args = msg[1]

    if report not in rpt_cmds:
        command.log_report_error(210001, "Unknown command '%s'" % report)
        return

    rpt_cmds[report](command, args)
