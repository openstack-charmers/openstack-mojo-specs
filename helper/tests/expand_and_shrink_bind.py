#!/usr/bin/env python
import sys
import utils.mojo_utils as mojo_utils
import utils.mojo_os_utils as mojo_os_utils
import argparse
import time

TEST_DOMAIN = 'mojo-ha-tests.com.'
TEST_DOMAIN_EMAIL = 'fred@mojo-ha-tests.com'
TEST_WWW_RECORD = "www.{}".format(TEST_DOMAIN)
TEST_RECORD = {TEST_WWW_RECORD: '10.0.0.23'}


def main(argv):
    mojo_utils.setup_logging()
    # Setup client
    overcloud_novarc = mojo_utils.get_overcloud_auth()
    keystone_session = mojo_os_utils.get_keystone_session(overcloud_novarc,
                                                          scope='PROJECT')
    client = mojo_os_utils.get_designate_session_client(keystone_session)
    os_version = mojo_os_utils.get_current_os_versions('keystone')['keystone']

    designate_api_version = 2
    zone = mojo_os_utils.create_or_return_zone(
        client,
        TEST_DOMAIN,
        TEST_DOMAIN_EMAIL)
    rs = mojo_os_utils.create_or_return_recordset(
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
