import re

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


def parse_client_greeting(msg_str):
    msg = parse.msg(msg_str)

    proto_ver = int(msg[0])
    client_caps = msg[1]
    url = parse.string(msg[2])

    print "ver: %d" % proto_ver
    print "caps: %s" % client_caps
    print "url: %s" % url

    return proto_ver, client_caps, url


url_re = re.compile(r'^svn://(?P<host>[^/]+)/(?P<path>.*?)\s*$')


def find_repo(link, url):
    url_m = url_re.match(url)

    if url_m is None:
        return None

    host = url_m.group('host')
    path = url_m.group('path')

    for base, repo in link.server.repo_map.items():
        if path.startswith(base + '/'):
            return repo, path[len(base) + 1:], 'svn://%s/%s' % (host, base)
        elif path == base:
            return repo, '', 'svn://%s/%s' % (host, base)

    return None, None, None


def connect(link):
    # Send the announce message - we only support protocol version 2.
    """

    :type link: SvnRequestHandler
    """
    link.send_msg(gen.success(2, 2, gen.list(), gen.list(*server_capabilities)))

    client_resp = link.read_msg()

    ver, caps, url = parse_client_greeting(client_resp)

    if ver != 2:
        raise BadProtoVersion()

    repo, path, base_url = find_repo(link, url)

    if repo is None:
        link.send_msg(gen.failure(gen.list(210005,
                                           gen.string("No repository found in '%s'" % url),
                                           gen.string('message.py'), 0)))

    return path, caps, repo, base_url
