
import re

from config import config

url_re = re.compile(r'^svn://(?P<host>[^/]+)/(?P<path>.*?)\s*$')

class Repos:
    def __init__(self, base_url):
        self.base_url = base_url

repos_list = {}

def get_repos(base_url):
    if base_url in repos_list:
         return repos_list[base_url]
    else:
         r = Repos(base_url)
         repos_list[base_url] = r
         return r

def find_repos(url):
    url_m = url_re.match(url)

    if url_m is None:
        return None

    host = url_m.group('host')
    path = url_m.group('path')

    for base_url, repos in config.repos.items():
        if path.startswith(base_url):
            return get_repos(base_url)

    return None
