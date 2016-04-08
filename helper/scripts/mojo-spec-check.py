#!/usr/bin/python
import logging
import os
import string
import sys
import yaml

#LOGLEVEL = logging.DEBUG
#LOGLEVEL = logging.INFO
LOGLEVEL = logging.WARN

WHITELIST = ['manifest', 'helper', 'utils', 'scripts', 'SPEC_INFO.txt']

YAML_MAP = {
    'images.yaml': 'image_setup.py',
    'keystone_users.yaml': 'keystone_setup.py',
    'network.yaml': 'network_setup.py',
}


# OpenStack-to-Ubuntu Release Map
UBUNTU_RELEASES = {}
OPENSTACK_RELEASES = {
    'icehouse': ['precise', 'trusty'],
    'juno': ['trusty'],
    'kilo': ['trusty'],
    'liberty': ['trusty', 'wily'],
    'mitaka': ['trusty', 'xenial'],
}


# Helpers
def invert_dict_of_lists(d):
    """Inverts a dictionary of lists."""
    _inverted = {}
    for k, v in d.iteritems():
        for item in v:
            if item in _inverted.keys():
                _inverted[item].append(k)
            else:
                _inverted[item] = [k]
    return _inverted


def get_directive_opt(line, opt):
    """Return value for kv pair in manifest line"""
    for word in line:
        if opt in word:
            return word.split('=')[1]


def get_manifest_ubuntu_release():
    """Return Ubuntu release referenced in deploy manifest directive"""
    releases = []
    with open('manifest', 'r') as f:
        for line in f.readlines():
            words = line.split()
            if words and words[0] == "deploy":
                target_arg = get_directive_opt(words, 'target')
                if target_arg:
                    releases.append(target_arg)
                else:
                    logging.warn('No target is set for juju deployer, this '
                                 'spec will not support multiple Ubuntu '
                                 'releases, specify a target with '
                                 '${MOJO_SERIES}')
    logging.debug('Releases: {}'.format(releases))
    return releases


def get_manifest_referenced(openstack_release):
    """Return all files referenced in the manifest"""
    config_files = []
    with open('manifest', 'r') as f:
        for line in f.readlines():
            for word in line.split():
                if 'config=' in word:
                    config_files.extend(resolve_file(word.split('=')[1],
                                                     openstack_release))
    logging.debug('Expected files: {}'.format(config_files))
    return config_files


def resolve_file(rfile, openstack_release):
    """Substitute vars into string and return list of possibilities"""
    check_files = []
    if 'MOJO_SERIES' in rfile:
        # Add expected Ubuntu series based on OpenStack release
        if openstack_release:
            logging.debug('Expecting {} x {}'.format(
                rfile, OPENSTACK_RELEASES[openstack_release]))
            for series in OPENSTACK_RELEASES[openstack_release]:
                template_data = {'MOJO_SERIES': series}
                check_files.append(
                    string.Template(rfile).substitute(template_data))
        else:
            logging.warn('Skipping {}'.format(rfile))
    else:
        check_files.append(rfile)
    return check_files


def get_openstack_release_name():
    """Return OpenStack release name based on the current directory."""
    openstack_release = os.getcwd().split('/')[-1]
    logging.debug('OpenStack release: {}'.format(openstack_release))
    if openstack_release not in OPENSTACK_RELEASES.keys():
        logging.error('Unable to determine OpenStack release name '
                      'from spec directory')
        return None
    else:
        return openstack_release


# Checks
def check_manifest_ubuntu_release():
    """Check Ubuntu release is not hardcoded in manifest"""
    logging.info('Checking that Ubuntu release is not '
                 'hard-coded in manifest...')
    for target_arg in get_manifest_ubuntu_release():
        for rel in UBUNTU_RELEASES.keys():
            if rel in target_arg:
                logging.warn('Manifest deploy target contains a hard-coded '
                             'Ubuntu release. Consider using ${MOJO_SERIES}')


def check_spec_info(dir_list):
    """Check spec has a SPEC_INFO.txt file describing the spec"""
    if 'SPEC_INFO.txt' not in dir_list:
        logging.warn('No spec description file SPEC_INFO.txt')


def check_files_are_in_manifest(dir_list, openstack_release):
    """Check that all files are referenced in the manifest"""
    logging.info('Checking that all files are referenced in the manifest...')
    _referenced = get_manifest_referenced(openstack_release)

    def _manifest_check(fname):
        if not fname in _referenced:
            logging.warn('%s is not referenced by the manifest. '
                         'Can this file be removed?' % fname)

    for f in dir_list:
        if f in WHITELIST:
            continue
        if f in YAML_MAP.keys():
            _manifest_check(YAML_MAP[f])
        else:
            _manifest_check(f)


def check_files_from_manifest(dir_list, openstack_release):
    """Check that all files referenced in the manifest are present"""
    logging.info('Checking that all files referenced in the '
                 'manifest are present...')

    for f in get_manifest_referenced(openstack_release):
        # Use actual file check to address file within symlinked directories
        if f not in dir_list and not os.path.exists(f):
            logging.error('%s not found.  It is referenced by the '
                          'manifest, or expected based on Ubuntu-'
                          'OpenStack version table.  Mojo spec '
                          'will fail.' % f)
            logging.debug('{} not in {}'.format(f, dir_list))
        for yamlfile in YAML_MAP.keys():
            if f == YAML_MAP[yamlfile]:
                if not yamlfile in dir_list:
                    logging.error('%s not found.  It is referenced by the '
                                  'manifest, or expected based on Ubuntu-'
                                  'OpenStack version table.  Mojo spec '
                                  'will fail.' % f)


def check_local_changes(dir_list):
    """Check for local changes"""
    logging.info('Checking for local files...')
    for f in dir_list:
        if not os.path.islink(f) and f not in WHITELIST:
            logging.warn('Spec file %s is a local copy. Can this be replaced '
                         'with a link to a helper copy?' % f)


def check_dead_symlinks(dir_list):
    """Check for dead symlink"""
    logging.info('Checking for dead symlinks...')
    for f in dir_list:
        if os.path.islink(f) and not os.path.exists(os.readlink(f)):
            logging.error('%s is a dead symlink' % f)


def check_yaml_syntax(dir_list):
    """Check yamls are valid"""
    logging.info('Checking syntax of yaml files...')
    for f in dir_list:
        if f.endswith('.yaml'):
            stream = open(f, 'r')
            try:
                yaml.load(stream)
            except yaml.scanner.ScannerError:
                logging.error('%s contains yaml errors, '
                              'mojo spec will fail.' % f)


def check_dirname(openstack_release):
    """Check tip dirname matches Openstack release referenced in manifest"""
    logging.info('Checking dir name matches OpenStack release in manifest...')
    for target in get_manifest_ubuntu_release():
        if target.split('-')[1] != openstack_release:
            logging.warn('OpenStack series referenced in manifest'
                         'does not match directory name')


def main(argv):
    logging.basicConfig(level=LOGLEVEL)

    # Ubuntu-to-OpenStack Release Map
    global UBUNTU_RELEASES
    UBUNTU_RELEASES = invert_dict_of_lists(OPENSTACK_RELEASES)

    spec = sys.argv[1]
    os.chdir(spec)
    dir_list = os.listdir('.')
    openstack_release = get_openstack_release_name()

    logging.info('Spec: {}'.format(spec))
    logging.debug('Ubuntu release map:  {}'.format(UBUNTU_RELEASES))
    logging.debug('OpenStack release map:  {}'.format(OPENSTACK_RELEASES))
    logging.debug('Current dir: {}'.format(os.getcwd()))
    logging.debug('dir_list: {}'.format(dir_list))
    check_spec_info(dir_list)
    check_files_are_in_manifest(dir_list, openstack_release)
    check_files_from_manifest(dir_list, openstack_release)
    check_local_changes(dir_list)
    check_dead_symlinks(dir_list)
    check_manifest_ubuntu_release()
    check_yaml_syntax(dir_list)
    check_dirname(openstack_release)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
