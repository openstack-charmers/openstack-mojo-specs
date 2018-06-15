#!/usr/bin/env python3
import sys
import utils.mojo_utils as mojo_utils
import utils.mojo_os_utils as mojo_os_utils
import logging

from zaza import model
from zaza.utilities import (
    generic as generic_utils,
    openstack as openstack_utils,
)


class TempestRunException(Exception):
    pass


def raise_tempest_fail(msg):
    logging.error(msg)
    raise TempestRunException(msg)


def report_success(msg):
    logging.debug(msg)


def warn(msg):
    logging.warning(msg)


def keystone_v3_domain_setup():
    overcloud_novarc = openstack_utils.get_overcloud_auth()
    if overcloud_novarc.get('API_VERSION', 2) == 3:
        keystone_session = openstack_utils.get_overcloud_keystone_session()
        keystone_client = openstack_utils.get_keystone_session_client(
            keystone_session)
        mojo_os_utils.project_create(keystone_client,
                                     ['admin'],
                                     'admin_domain')
        admin_project_id = openstack_utils.get_project_id(
            keystone_client,
            'admin',
            api_version=3,
            domain_name='admin_domain')
        role = keystone_client.roles.find(name='admin')
        user = keystone_client.users.find(name='admin')
        keystone_client.roles.grant(role, user=user, project=admin_project_id)


def main(argv):
    # Tempest expects an admin project in the admin domain that the admin user
    # has admin role on so make sure that exists (pre-17.02)
    keystone_v3_domain_setup()

    results_file = mojo_utils.get_mojo_file('tempest_expected_results.yaml')
    expected_results = generic_utils.get_yaml_config(
        results_file)['smoke']
    action = model.run_action_on_leader(
        'tempest',
        'run-tempest',
        action_params={})
    logging.debug(action.message)
    actual_results = action.data['results']

    result_matrix = {
        'failed': {
            'on_more': raise_tempest_fail,
            'on_less': report_success},
        'skipped': {
            'on_more': warn,
            'on_less': report_success},
        'expected-fail': {
            'on_more': raise_tempest_fail,
            'on_less': report_success},
        'unexpected-success': {
            'on_more': report_success,
            'on_less': warn},
        'passed': {
            'on_more': report_success,
            'on_less': raise_tempest_fail}}

    for result_type, expected in expected_results.items():
        actual = actual_results[result_type]
        msg = "Number of tests {} was {} expected {}".format(result_type,
                                                             actual,
                                                             expected)
        if int(actual) > expected:
            result_matrix[result_type]['on_more'](msg)
        elif int(actual) == expected:
            report_success(msg)
        else:
            result_matrix[result_type]['on_less'](msg)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
