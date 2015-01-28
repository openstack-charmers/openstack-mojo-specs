#!/usr/bin/python
import string
import os
import logging
import sys

WHITELIST=['manifest', 'helper', 'utils', 'SPEC_INFO.txt']
YAML_MAP={
    'images.yaml': 'image_setup.py',
    'keystone_users.yaml': 'keystone_setup.py',
    'network.yaml': 'network_setup.py',
}

def get_manifest_referenced():
    config_files=[]
    with open('manifest', 'r') as f: 
        for line in f.readlines():
            for word in line.split():
                if 'config=' in word:
                    config_files.extend(resolve_file(word.split('=')[1]))
    return config_files

def resolve_file(rfile):
    check_files = []
    if 'MOJO_SERIES' in rfile:
        for series in ['trusty', 'precise']:
            bob = {}
            bob['MOJO_SERIES'] = series
            check_files.append(string.Template(rfile).substitute(bob))
    else:
        check_files.append(rfile)
    return check_files

def manifest_check(fname):
    if not fname in get_manifest_referenced():
        logging.warn('%s not referenced in manifest. Can this file be removed?' % fname)

logging.basicConfig(level=logging.INFO)
# Check that all files are referenced in the manifest otherwise why are they
# here?
os.chdir(sys.argv[1])
dir_list = os.listdir('.')
for f in dir_list:
    if f in WHITELIST:
        continue
    if f in YAML_MAP.keys():
        manifest_check(YAML_MAP[f])
    else:
        manifest_check(f)

# Check that all files referenced in the manifest are present
for f in get_manifest_referenced():
    if f not in dir_list:
        logging.error('%s referenced in manifest but not present, mojo spec will fail' % f)
    for yamlfile in YAML_MAP.keys():
        if f == YAML_MAP[yamlfile]:
            if not yamlfile in dir_list:
                logging.error('%s referenced in manifest but not present, mojo spec will fail' % f)

# look for local changes
for f in dir_list:
    if not os.path.islink(f) and f not in WHITELIST:
        logging.warn('Spec file %s is a local copy, can this be replaced with a link to a helper copy?' % f)
