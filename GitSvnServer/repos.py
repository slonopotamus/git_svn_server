
import inspect
import re

from config import config

url_re = re.compile(r'^svn://(?P<host>[^/]+)/(?P<path>.*?)\s*$')


class ReposError (Exception):
    pass

repos_types = {}
class ReposMeta (type):
    def __new__(mcs, name, bases, dict):
        klass = type.__new__(mcs, name, bases, dict)
        if klass._kind is not None:
            repos_types[klass._kind] = klass
        return klass


class Repos (object):
    __metaclass__ = ReposMeta
    _kind = None

    def __init__(self, host, base, config):
        self.repos_base = base
        self.uuid = None
        self.base_url = 'svn://%s/%s' % (host, base)
        self.config = config

    def _calc_uuid(self):
        raise NotImplemented()

    def get_uuid(self):
        if self.uuid is None:
            self._calc_uuid()

        return self.uuid

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


repos_list = {}


repos_types_loaded = False
def load_repos_types():
    global repos_types_loaded

    if repos_types_loaded:
        return

    import vcs

    repos_types_loaded = True


def get_repos(host, base, config):
    if base in repos_list:
        return repos_list[base]
    else:
        if config.kind in repos_types:
            r = repos_types[config.kind](host, base, config)
        else:
            raise ReposError('Unknown repository kind: %s' % config.kind)
        repos_list[base] = r
        return r


def find_repos(url):
    url_m = url_re.match(url)

    if url_m is None:
        return None

    load_repos_types()

    host = url_m.group('host')
    path = url_m.group('path')

    for base, repos in config.repos.items():
        if path.startswith(base):
            return get_repos(host, base, repos)

    return None
