#!/usr/bin/python
import sys
import utils.mojo_utils as mojo_utils
import utils.mojo_os_utils as mojo_os_utils
import logging


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
    overcloud_novarc = mojo_utils.get_overcloud_auth()
    if overcloud_novarc.get('API_VERSION', 2) == 3:
        keystone_session = mojo_os_utils.get_keystone_session(overcloud_novarc)
        keystone_client = mojo_os_utils.get_keystone_session_client(
            keystone_session)
        mojo_os_utils.project_create(keystone_client,
                                     ['admin'],
                                     'admin_domain')
        admin_project_id = mojo_os_utils.get_tenant_id(
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

    expected_results = mojo_utils.get_mojo_config(
        'tempest_expected_results.yaml')['smoke']
    tempest_unit = mojo_utils.get_juju_units(service='tempest')
    action_id = mojo_utils.action_run(
        tempest_unit[0],
        'run-tempest',
        timeout=18000)
    action_output = mojo_utils.action_get_output(action_id)
    logging.debug(action_output)
    actual_results = action_output['results']

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

    for result_type in expected_results.keys():
        msg = "Number of tests {} was {} expected {}".format(
            result_type,
            actual_results[result_type],
            expected_results[result_type])
        if int(actual_results[result_type]) > expected_results[result_type]:
            result_matrix[result_type]['on_more'](msg)
        elif int(actual_results[result_type]) == expected_results[result_type]:
            report_success(msg)
        else:
            result_matrix[result_type]['on_less'](msg)

if __name__ == "__main__":
    sys.exit(main(sys.argv))
