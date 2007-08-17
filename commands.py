
import generate as gen
import parse

commands = {}

def cmd_func(name):
    def _cmd_func(f):
        commands.setdefault(name, f)
        return f
    return _cmd_func

@cmd_func('get-latest-rev')
def get_latest_rev(url, repos, args):
    return "%s %s" % (gen.success('( )', gen.string('')),
                      gen.success('12'))

@cmd_func('check-path')
def check_path(url_base, repos, args):
    url = url_base
    rev = None

    path = parse.string(args[0])
    if len(path) > 0:
        url = '/'.join((url_base, path))

    if len(args) > 1:
        rev = int(args[1][0])

    ref, path = repos.parse_url(url)

    print "ref: %s" % ref
    print "path: %s" % path
    print "rev: %s" % rev

    if ref is None or path == '':
        type = 'dir'
    else:
        type = repos.svn_node_kind(url, rev)

    return "%s %s" % (gen.success('( )', gen.string('')),
                      gen.success(type))

@cmd_func('get-dir')
def get_dir(url_base, repos, args):
    url = url_base
    rev = None

    path = parse.string(args.pop(0))
    if len(path) > 0:
        url = '/'.join((url_base, path))

    arg = args.pop(0)
    if isinstance(arg, list):
        rev = int(arg[0])
        arg = args.pop(0)

    want_props = parse.bool(arg)

    want_contents = parse.bool(args.pop(0))

    fields = []
    if len(args) > 0:
        fields = args[0]

    ref, path = repos.parse_url(url)

    print "ref: %s" % ref
    print "path: %s" % path
    print "rev: %s" % rev
    print "want_props: %s" % want_props
    print "want_contents: %s" % want_contents
    print "fields: %s" % fields

    return gen.error(12, 'pah')

def handle_command(url, msg, repos):
    command = msg[0]
    args = msg [1]

    if command not in commands:
        return gen.error(210001, "Unknown command '%s'" % command)

    return commands[command](url, repos, args)
