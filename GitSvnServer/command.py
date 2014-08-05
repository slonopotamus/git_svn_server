from GitSvnServer.errors import ClientError
import parse

# noinspection PyUnresolvedReferences
from commands import *
from cmd_base import commands


def process(link):
    """

    :type link: GitSvnServer.server.SvnRequestHandler
    """
    msg = parse.msg(link.read_msg())

    command_name = msg[0]
    args = msg[1]

    command = commands.get(command_name, None)

    print "%s: %s(%s)" % (link.client_address[0], command_name, args)

    if command is None:
        raise ClientError("Unknown command '%s'" % command_name)

    # noinspection PyCallingNonCallable
    return command(link, args)
