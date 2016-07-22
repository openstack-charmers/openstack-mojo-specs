#!/usr/bin/python
import six
import re
import argparse
import sys
import utils.mojo_utils as mojo_utils
import logging
from utils.os_versions import (
    OPENSTACK_CODENAMES,
    SWIFT_CODENAMES,
    PACKAGE_CODENAMES,
)

CHARM_TYPES = {
    'neutron': {
        'pkg': 'neutron-common',
        'origin_setting': 'openstack-origin'
    },
    'nova': {
        'pkg': 'nova-common',
        'origin_setting': 'openstack-origin'
    },
    'glance': {
        'pkg': 'glance-common',
        'origin_setting': 'openstack-origin'
    },
    'cinder': {
        'pkg': 'cinder-common',
        'origin_setting': 'openstack-origin'
    },
    'keystone': {
        'pkg': 'keystone',
        'origin_setting': 'openstack-origin'
    },
    'openstack-dashboard': {
        'pkg': 'openstack-dashboard',
        'origin_setting': 'openstack-origin'
    },
    'ceilometer': {
        'pkg': 'ceilometer-common',
        'origin_setting': 'openstack-origin'
    },
}
UPGRADE_SERVICES = [
    {'name': 'keystone', 'type': CHARM_TYPES['keystone']},
    {'name': 'nova-cloud-controller', 'type': CHARM_TYPES['nova']},
    {'name': 'nova-compute', 'type': CHARM_TYPES['nova']},
    {'name': 'neutron-api', 'type': CHARM_TYPES['neutron']},
    {'name': 'neutron-gateway', 'type': CHARM_TYPES['neutron']},
    {'name': 'glance', 'type': CHARM_TYPES['glance']},
    {'name': 'cinder', 'type': CHARM_TYPES['cinder']},
    {'name': 'openstack-dashboard',
     'type': CHARM_TYPES['openstack-dashboard']},
    {'name': 'ceilometer', 'type': CHARM_TYPES['ceilometer']},
]

# XXX get_swift_codename and get_os_code_info are based on the functions with
# the same name in ~charm-helpers/charmhelpers/contrib/openstack/utils.py
# It'd be neat if we actually shared a common library.


def get_swift_codename(version):
    '''Determine OpenStack codename that corresponds to swift version.'''
    codenames = [k for k, v in six.iteritems(SWIFT_CODENAMES) if version in v]
    return codenames[0]


def get_os_code_info(package, pkg_version):
    # {'code_num': entry, 'code_name': OPENSTACK_CODENAMES[entry]}
    # Remove epoch if it exists
    if ':' in pkg_version:
        pkg_version = pkg_version.split(':')[1:][0]
    if 'swift' in package:
        # Fully x.y.z match for swift versions
        match = re.match('^(\d+)\.(\d+)\.(\d+)', pkg_version)
    else:
        # x.y match only for 20XX.X
        # and ignore patch level for other packages
        match = re.match('^(\d+)\.(\d+)', pkg_version)

    if match:
        vers = match.group(0)
    # Generate a major version number for newer semantic
    # versions of openstack projects
    major_vers = vers.split('.')[0]
    if (package in PACKAGE_CODENAMES and
            major_vers in PACKAGE_CODENAMES[package]):
        return PACKAGE_CODENAMES[package][major_vers]
    else:
        # < Liberty co-ordinated project versions
        if 'swift' in package:
            return get_swift_codename(vers)
        else:
            return OPENSTACK_CODENAMES[vers]


def next_release(release):
    old_index = OPENSTACK_CODENAMES.values().index(release)
    new_index = old_index + 1
    return OPENSTACK_CODENAMES.items()[new_index]


def get_current_os_versions(deployed_services):
    versions = {}
    for service in UPGRADE_SERVICES:
        print(service)
        if service['name'] not in deployed_services:
            continue
        version = mojo_utils.get_pkg_version(service['name'],
                                             service['type']['pkg'])
        versions[service['name']] = get_os_code_info(service['type']['pkg'],
                                                     version)
    return versions


def get_lowest_os_version(current_versions):
    lowest_version = 'zebra'
    for svc in current_versions.keys():
        if current_versions[svc] < lowest_version:
            lowest_version = current_versions[svc]
    return lowest_version


def get_upgrade_targets(target_release, current_versions):
    upgrade_list = []
    for svc in current_versions.keys():
        if current_versions[svc] < target_release:
            upgrade_list.append(svc)
    return upgrade_list


def main(argv):
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--target_release",
        default='auto', help="Openstack release name to upgrade to or 'auto' "
                             "to have script upgrade based on the lowest value"
                             "across all services")
    options = parser.parse_args()
    target_release = mojo_utils.parse_mojo_arg(options, 'target_release')
    principle_services = mojo_utils.get_principle_services()
    current_versions = get_current_os_versions(principle_services)
    if target_release == 'auto':
        # If in auto mode find the lowest value openstack release across all
        # services and make sure all servcies are upgraded to one release
        # higher than the lowest
        lowest_release = get_lowest_os_version(current_versions)
        target_release = next_release(lowest_release)[1]
    # Get a list of services that need upgrading
    needs_upgrade = get_upgrade_targets(target_release, current_versions)
    for service in UPGRADE_SERVICES:
        if service['name'] not in principle_services:
            continue
        if service['name'] not in needs_upgrade:
            logging.info('Not upgrading {} it is at {} or higher'.format(
                service['name'],
                target_release)
            )
            continue
        logging.info('Upgrading {} to {}'.format(service['name'],
                                                 target_release))
        ubuntu_version = mojo_utils.get_ubuntu_version(service['name'])
        option = "{}=cloud:{}-{}/proposed".format(
            service['type']['origin_setting'],
            ubuntu_version, target_release
        )
        mojo_utils.juju_set(service['name'], option, wait=False)
        mojo_utils.juju_status_check_and_wait()
        svc_units = mojo_utils.get_juju_units(service=service['name'])
        mojo_utils.remote_runs(svc_units)
        mojo_utils.juju_status_check_and_wait()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
