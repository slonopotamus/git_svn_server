import ConfigParser
import uuid

from GitSvnServer.repository import Repository


class User(object):
    def __init__(self, username, password, name, email):
        """
        :type username: str
        :type password: str
        :type name: str
        :type email: str
        """
        self.username = username
        self.password = password
        self.name = name
        self.email = email

    def __str__(self):
        return self.username


def _load_users(config_file):
    config = _parse(config_file)

    result = {}

    for username in config.sections():
        result[username] = User(
            username,
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

        try:
            repo_uuid = config.get(section, 'uuid')
        except ConfigParser.NoOptionError:
            repo_uuid = str(uuid.uuid5(uuid.NAMESPACE_URL, location))

        repo_map[section] = Repository(location, repo_uuid, users)

        print "Inited repository for %s at /%s" % (location, section)

    return repo_map, users
