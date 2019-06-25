#!/usr/bin/env python3
import sys
import utils.mojo_utils as mojo_utils
import utils.mojo_os_utils as mojo_os_utils

from zaza.openstack.utilities import (
    cli as cli_utils,
    openstack as openstack_utils,
)


TEST_DOMAIN = 'mojo-ha-tests.com.'
TEST_DOMAIN_EMAIL = 'fred@mojo-ha-tests.com'
TEST_WWW_RECORD = "www.{}".format(TEST_DOMAIN)
TEST_RECORD = {TEST_WWW_RECORD: '10.0.0.23'}


def main(argv):
    cli_utils.setup_logging()
    # Setup client
    keystone_session = openstack_utils.get_overcloud_keystone_session()
    os_version = openstack_utils.get_current_os_versions(
        'keystone')['keystone']

    if os_version >= 'mitaka':
        designate_api_version = '2'
    else:
        designate_api_version = '1'
    client = mojo_os_utils.get_designate_session_client(
        keystone_session, client_version=designate_api_version)

    zone = mojo_os_utils.create_or_return_zone(
        client,
        TEST_DOMAIN,
        TEST_DOMAIN_EMAIL)
    mojo_os_utils.create_or_return_recordset(
        client,
        zone['id'],
        'www',
        'A',
        [TEST_RECORD[TEST_WWW_RECORD]])

    # Test record is in bind and designate
    mojo_os_utils.check_dns_entry(
        client,
        TEST_RECORD[TEST_WWW_RECORD],
        TEST_DOMAIN,
        record_name=TEST_WWW_RECORD,
        designate_api=designate_api_version)

    mojo_utils.add_unit('designate-bind')

    mojo_os_utils.check_dns_entry(
        client,
        TEST_RECORD[TEST_WWW_RECORD],
        TEST_DOMAIN,
        record_name=TEST_WWW_RECORD,
        designate_api=designate_api_version)

    mojo_utils.delete_oldest('designate-bind')

    mojo_os_utils.check_dns_entry(
        client,
        TEST_RECORD[TEST_WWW_RECORD],
        TEST_DOMAIN,
        record_name=TEST_WWW_RECORD,
        designate_api=designate_api_version)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
