#!/usr/bin/python
import string
import os
import logging
import sys
import yaml

WHITELIST=['manifest', 'helper', 'utils', 'SPEC_INFO.txt']
YAML_MAP={
    'images.yaml': 'image_setup.py',
    'keystone_users.yaml': 'keystone_setup.py',
    'network.yaml': 'network_setup.py',
}
UBUNTU_RELEASES=['precise', 'trusty', 'utopic', 'vivid']

# Helpers
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
                                 'spec will not support multiple ubuntu '
                                 'releases, specify a target with ${MOJO_SERIES}')
    return releases


def get_manifest_referenced():
    """Return all files referenced in the manifest"""
    config_files=[]
    with open('manifest', 'r') as f: 
        for line in f.readlines():
            for word in line.split():
                if 'config=' in word:
                    config_files.extend(resolve_file(word.split('=')[1]))
    return config_files


def resolve_file(rfile):
    """Substitute runtime env variables into string and return list of possabilities"""
    check_files = []
    if 'MOJO_SERIES' in rfile:
        for series in ['trusty', 'precise']:
            bob = {}
            bob['MOJO_SERIES'] = series
            check_files.append(string.Template(rfile).substitute(bob))
    else:
        check_files.append(rfile)
    return check_files

# Checks
def check_manifest_ubuntu_release():
    """Check Ubuntu release is not hardcoded in manifest"""
    for target_arg in get_manifest_ubuntu_release():
        if len([rel for rel in UBUNTU_RELEASES if rel in target_arg]) > 0:
            logging.warn('juju deployer target contains a hardcoded '
                         'Ubuntu release. Consider using ${MOJO_SERIES}')

def check4spec(dir_list):
    """Check spec has a SPEC_INFO.txt file describing the spec"""
    if 'SPEC_INFO.txt' not in dir_list:
       logging.warn('No spec description file SPEC_INFO.txt')


def check_files_are_in_manifest(dir_list):
    """Check that all files are referenced in the manifest"""

    def _manifest_check(fname):
        if not fname in get_manifest_referenced():
            logging.warn('%s not referenced in manifest. Can this file be removed?' % fname)

    for f in dir_list:
        if f in WHITELIST:
            continue
        if f in YAML_MAP.keys():
            _manifest_check(YAML_MAP[f])
        else:
            _manifest_check(f)


def check_files_from_manifest(dir_list):
    """Check that all files referenced in the manifest are present"""
    for f in get_manifest_referenced():
        if f not in dir_list:
            logging.info('f: {}'.format(f))
            logging.info('dir_list: {}'.format(dir_list))
            logging.error('%s referenced in manifest but not present, mojo spec will fail' % f)
        for yamlfile in YAML_MAP.keys():
            if f == YAML_MAP[yamlfile]:
                if not yamlfile in dir_list:
                    logging.error('%s referenced in manifest but not present, mojo spec will fail' % f)


def check_local_changes(dir_list):
    """Check for local changes"""
    for f in dir_list:
        if not os.path.islink(f) and f not in WHITELIST:
            logging.warn('Spec file %s is a local copy, can this be replaced with a link to a helper copy?' % f)


def check_dead_symlinks(dir_list):
    """Check for dead symlink"""
    for f in dir_list:
        if os.path.islink(f) and not os.path.exists(os.readlink(f)):
            logging.error('%s is a dead symlink' % f)


def check_yaml_syntax(dir_list):
    """Check yamls are valid"""
    for f in dir_list:
        if f.endswith('.yaml'):
            stream = open(f, 'r')
            try:
                yaml.load(stream)
            except yaml.scanner.ScannerError:
                logging.error('%s contains errors, mojo spec will fail' % f)


def check_dirname():
    """Check tip dirname matches Openstack release referenced in manifest"""
    for target in get_manifest_ubuntu_release():
        if target.split('-')[1] != os.getcwd().split('/')[-1]:
            logging.warn('Openstack series referenced in manifest does not match dir')


def main(argv):
    logging.basicConfig(level=logging.INFO)
    os.chdir(sys.argv[1])
    dir_list = os.listdir('.')
    check4spec(dir_list)
    check_files_are_in_manifest(dir_list)
    check_files_from_manifest(dir_list)
    check_local_changes(dir_list)
    check_dead_symlinks(dir_list)
    check_manifest_ubuntu_release()
    check_yaml_syntax(dir_list)
    check_dirname()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
