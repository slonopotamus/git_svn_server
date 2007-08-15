
import generate as gen

commands = {}

def cmd_func(name):
    def _cmd_func(f):
        commands.setdefault(name, f)
        return f
    return _cmd_func

@cmd_func('get-latest-rev')
def get_latest_rev(args):
    return "%s %s" % (gen.success('( )', gen.string('test')),
                      gen.success('12'))

def handle_command(msg):
    command = msg[0]
    args = msg [1]

    if command not in commands:
        return gen.failure(gen.list('12',
                                    gen.string('unknown command: %s' % command),
                                    gen.string('commands.py'), '0'))

    return commands[command](args)
