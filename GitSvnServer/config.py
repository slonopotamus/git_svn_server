import re
import sys

repos_re = re.compile(r'^\[repos "(?P<url_base>.*)"\]\s*$')
var_re = re.compile(r'^\s+(?P<name>\S+)\s*=\s*((?P<value>\S+)|"(?P<qvalue>.*)")\s*$')


class ConfigError(Exception):
    pass


class Config:
    def __init__(self, filename):
        self.repos = {}
        self.filename = filename

    def load(self):
        try:
            self.__parse()
        except Exception, e:
            print >> sys.stderr, "Failed to load configuration from '%s':\n%s" \
                                 % (self.filename, str(e))
            sys.exit(1)

    def __parse(self):
        repo_config = None

        if self.filename is None:
            return

        f = open(self.filename)
        for i, line in enumerate(f):
            line_no = i + 1
            repos_m = repos_re.match(line)
            var_m = var_re.match(line)
            if repos_m is not None:
                url_base = repos_m.group('url_base')
                while url_base[0] == '/':
                    url_base = url_base[1:]
                while url_base[-1] == '/':
                    url_base = url_base[:-2]
                if url_base in self.repos:
                    raise ConfigError('Duplicate repo_config specification', line_no)
                repo_config = {}
                self.repos[url_base] = repo_config
            elif var_m is not None and repo_config is not None:
                name = var_m.group('name').lower()
                value = var_m.group('qvalue')
                if value is None:
                    value = var_m.group('value')

                repo_config[name] = value
        f.close()

    def __str__(self):
        s = ""
        for name, repos in self.repos.items():
            s += "%s\n%s" % (name, repos)
        return s
