class EOF(Exception):
    pass


class ChangeMode(Exception):
    pass


class ClientError(Exception):
    pass


class PathChanged(ClientError):
    pass


class ReadError(ClientError):
    pass


class ModeError(ClientError):
    pass
