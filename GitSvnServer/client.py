import parse
import generate as gen
from errors import *

server_capabilities = [
    'edit-pipeline',  # This is required.
    'svndiff1',  # We support svndiff1
    'absent-entries',  # We support absent-dir and absent-dir editor commands
    #'commit-revprops', # We don't currently have _any_ revprop support
    #'mergeinfo',       # Nope, not yet
    #'depth',           # Nope, not yet
]


def connect(link):
    # Send the announce message - we only support protocol version 2.
    """

    :type link: SvnRequestHandler
    """
    link.send_msg(gen.success(2, 2, gen.list(), gen.list(*server_capabilities)))
    msg = parse.msg(link.read_msg())

    proto_ver = int(msg[0])
    client_caps = msg[1]
    url = parse.string(msg[2])

    print "ver: %d" % proto_ver
    print "caps: %s" % client_caps
    print "url: %s" % url

    if proto_ver != 2:
        raise BadProtoVersion()

    repo, path, base_url = link.server.find_repo(url)

    if repo is None:
        link.send_msg(gen.failure(gen.list(210005,
                                           gen.string("No repository found in '%s'" % url),
                                           gen.string('message.py'), 0)))

    return path, client_caps, repo, base_url
