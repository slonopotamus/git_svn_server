
import re

from config import config

url_re = re.compile(r'^svn://(?P<host>[^/]+)/(?P<path>.*?)\s*$')


class ReposError (Exception):
    pass


repos_types = {}
class ReposMeta (type):
    def __new__(mcs, name, bases, dict):
        klass = type.__new__(mcs, name, bases, dict)
        if klass.kind is not None:
            repos_types[klass.kind] = klass
        return klass


class Repos (object):
    __metaclass__ = ReposMeta
    kind = None

    def __init__(self, host, base, config):
        pass


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
