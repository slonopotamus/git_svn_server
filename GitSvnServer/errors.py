
class EOF(Exception):
    pass

class ReadError(Exception):
    pass

class ModeError(Exception):
    pass

class ChangeMode(Exception):
    pass

class BadProtoVersion(Exception):
    pass

class PathChanged(Exception):
    pass

class HookFailure(Exception):
    def __init__(self, code, text):
        self.code = code
        self.text = text
    def __str__(self):
        return "HookFailed(%d): %s" % (self.code, self.text)
