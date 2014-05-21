import generate as gen
import parse

# noinspection PyUnresolvedReferences
from commands import *
from cmd_base import commands


def process(link):
    msg = parse.msg(link.read_msg())

    command_name = msg[0]
    args = msg[1]

    command = commands.get(command_name, None)

    if command is None:
        link.send_msg(gen.error(210001, "Unknown command '%s'" % command_name))
        return None

    print "found %s" % command_name
    # noinspection PyCallingNonCallable
    return command(link, args)
