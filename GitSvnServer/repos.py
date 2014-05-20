from multiprocessing import Lock
import uuid


class Repos(object):
    def __init__(self, location):
        self.lock = Lock()
        self.location = location
        self.uuid = str(uuid.uuid5(uuid.NAMESPACE_URL, self.location))

    def get_latest_rev(self):
        raise NotImplemented()

    def check_path(self, url, rev):
        raise NotImplemented()

    def stat(self, url, rev):
        raise NotImplemented()

    def ls(self, url, rev):
        raise NotImplemented()

    def log(self, url, target_paths, start_rev, end_rev, limit):
        raise NotImplemented()

    def rev_proplist(self, rev):
        raise NotImplemented()

    def get_props(self, url, rev, include_internal=True):
        raise NotImplemented()

    def path_changed(self, url, rev, prev_rev):
        raise NotImplemented()

    def get_file(self, url, rev):
        raise NotImplemented()

    def get_files(self, url, rev):
        raise NotImplemented()

    def start_commit(self, url, username):
        raise NotImplemented()

    def complete_commit(self, commit, msg):
        raise NotImplemented()

    def get_auth(self):
        raise NotImplemented()
