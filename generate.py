
def list(*args):
    return "( %s )" % (' '.join([str(x) for x in args]))

def tuple(n, *args):
    return "( %s %s )" % (n, list(*args))

def string(s):
    return "%d:%s" % (len(s), s)

def success(*args):
    return tuple('success', *args)

def failure(*args):
    return tuple('failure', *args)

def error(errno, errstr):
    return failure(list(str(errno), string(errstr), string('...'), '0'))

def cmd_success(*args):
    return "%s %s" % (success('( )', string('')), success(*args))
