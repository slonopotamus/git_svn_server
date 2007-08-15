
def list(*args):
    return "( %s )" % (' '.join(args))

def tuple(n, *args):
    return "( %s %s )" % (n, list(*args))

def string(s):
    return "%d:%s" % (len(s), s)

def success(*args):
    return tuple('success', *args)

def failure(*args):
    return tuple('failure', *args)

