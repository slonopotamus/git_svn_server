
import generate as gen
import parse

from commands import *
from cmd_base import commands

def process(link):
    msg = parse.msg(link.read_msg())

    command = msg[0]
    args = msg [1]

    if command not in commands:
        link.send_msg(gen.error(210001, "Unknown command '%s'" % command))
        return None

    print "found %s %s" % (command, commands[command](link, args))

    return commands[command](link, args)

