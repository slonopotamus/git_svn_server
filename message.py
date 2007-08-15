#!/usr/bin/python

import os
import sys

import auth
import commands
import generate as gen
import parse

def greeting():
    return gen.success('2', '2', '( ANONYMOUS )', '( edit-pipeline )')

def auth_request():
    return gen.success('( CRAM-MD5 )', '4:test')

uuid = 'ffffffff-ffff-ffff-ffff-ffffffffffff'
repos_url = 'svn://localhost/'
def server_id():
    return gen.success(gen.string(uuid), gen.string(repos_url))

setup_steps = []
def setup(f):
    setup_steps.append(f)

@setup
def handle_client_greeting(msg):
    proto_ver = int(msg[0])
    client_caps = msg[1]
    url = parse.string(msg[2])

    print "ver: %d" % proto_ver
    print "caps: %s" % client_caps
    print "url: %s" % url

    return auth_request()

@setup
def handle_client_auth_resp(msg):
    auth_type = msg[0]

    if auth_type in auth.auths:
        raise auth.Needed(auth_type, server_id)

    return gen.failure(gen.string('unknown auth type: %s' % auth_type))

def handle_msg(msg_str):
    msg = parse.msg(msg_str)

    while len(setup_steps) > 0:
        fn = setup_steps.pop(0)
        return fn(msg)

    print "%d:%s" % (os.getpid(), msg)

    return commands.handle_command(msg)
