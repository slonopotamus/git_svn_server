import ConfigParser

from GitSvnServer.vcs.git.main import Git


class User(object):
    def __init__(self, password, name, email):
        self.password = password
        self.name = name
        self.email = email


def _load_users(config_file):
    config = _parse(config_file)

    result = {}

    for username in config.sections():
        result[username] = User(
            config.get(username, 'password'),
            config.get(username, 'name'),
            config.get(username, 'email')
        )

    return result


def _parse(config_file):
    """

    :type config_file: str
    """
    config = ConfigParser.ConfigParser()
    with open(config_file) as fd:
        config.readfp(fd, filename=config_file)
    return config


def load_config(config_file):
    config = _parse(config_file)

    users = _load_users(config.get('global', 'users_config'))

    repo_map = {}
    for section in config.sections():
        if section == 'global':
            continue

        location = config.get(section, 'location')
        repo_map[section] = Git(location, users)
        print "Inited repository for %s at /%s" % (location, section)

    return repo_map, users
