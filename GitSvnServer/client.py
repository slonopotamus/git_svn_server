
import parse
import generate as gen
from repos import find_repos
from errors import *

def parse_client_greeting(msg_str):
    msg = parse.msg(msg_str)

    proto_ver = int(msg[0])
    client_caps = msg[1]
    url = parse.string(msg[2])

    print "ver: %d" % proto_ver
    print "caps: %s" % client_caps
    print "url: %s" % url

    return proto_ver, client_caps, url

def connect(link):
    link.send_msg(gen.success(2, 2,
                              gen.list('ANONYMOUS'),
                              gen.list('edit-pipeline', 'svndiff1')))

    client_resp = link.read_msg()

    ver, caps, url = parse_client_greeting(client_resp)

    if ver != 2:
        raise BadProtoVersion()

    repos = find_repos(url)

    if repos is None:
        link.send_msg(gen.failure(gen.list(210005,
                                    gen.string("No repository found in '%s'" %
                                    url),
                                    gen.string('message.py'), 0)))

    return url, caps, repos
