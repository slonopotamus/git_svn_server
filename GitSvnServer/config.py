import ConfigParser

from GitSvnServer.vcs.git.main import Git


def create_repos(config_file):
    config = ConfigParser.ConfigParser()

    with open(config_file) as fd:
        config.readfp(fd, filename=config_file)

    repo_map = {}
    for url_base in config.sections():
        location = config.get(url_base, 'location')
        repo_map[url_base] = Git(location)
        print "Inited repository for %s at /%s" % (location, url_base)

    return repo_map
