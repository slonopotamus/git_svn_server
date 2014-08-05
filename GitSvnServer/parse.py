# !/usr/bin/python

import re

from GitSvnServer.errors import ClientError


class InvalidTokenString(Exception):
    pass


token_string_re = re.compile(r'^[\n ]*\([\n ]+(?P<tokens>.*)\)[\n ]*$',
                             re.MULTILINE | re.DOTALL)
string_re = re.compile(r'^(?P<len>\d+):(?P<data>.*)$', re.MULTILINE | re.DOTALL)
token_re = re.compile(r'^(?P<token>.*?)[\n ]+(?P<rest>.*)$',
                      re.MULTILINE | re.DOTALL)


def tokenise(input):
    token_m = token_string_re.match(input)

    if token_m is None:
        raise InvalidTokenString(input)

    ts = token_m.group('tokens')

    tokens = []

    while len(ts) > 0:
        string_m = string_re.match(ts)
        if string_m is not None:
            dl = int(string_m.group('len'))
            data = string_m.group('data')
            tokens.append("%d:%s" % (dl, data[:dl]))
            ts = data[dl:].lstrip()
            continue

        token_m = token_re.match(ts)
        if token_m is not None:
            tokens.append(token_m.group('token'))
            ts = token_m.group('rest')
            continue

        tokens.append(ts)
        ts = ''

    return tokens


def msg(input):
    tokens = tokenise(input)

    parsed = []

    i = 0
    while i < len(tokens):
        if tokens[i] != '(':
            parsed.append(tokens[i])
            i += 1
            continue

        j = i
        depth = 0
        while j < len(tokens):
            if tokens[j] == '(':
                depth += 1

            if tokens[j] == ')':
                depth -= 1

            if depth == 0:
                break

            j += 1

        parsed.append(msg(' '.join(tokens[i:j + 1])))
        i = j + 1

    return parsed


def string(str):
    string_m = string_re.match(str)

    if string_m is None:
        raise ClientError('not a string')

    data_len = int(string_m.group('len'))
    data = string_m.group('data')

    if len(data) != data_len:
        raise ClientError('len error: %d != %d' % (len(data), data_len))

    return data


def bool(str):
    return str.lower() == 'true'
