#!/usr/bin/env python3

import asyncio
import copy
import os
from zaza import model
from zaza.openstack.utilities import (
    cli as cli_utils,
    openstack,
)
from zaza.openstack.charm_tests.vault import (
    setup as vault_setup,
    utils as vault_utils
)
import zaza.openstack.utilities.cert
import utils.mojo_utils as mojo_utils
import logging


if __name__ == "__main__":
    cli_utils.setup_logging()
    target_model = model.get_juju_model()
    wl_statuses = copy.deepcopy(openstack.WORKLOAD_STATUS_EXCEPTIONS)
    os_version = openstack.get_current_os_versions(
        'designate').get('designate')
    if os_version == 'pike':
        # Remove the memcached relation to disable designate. This is a
        # workaround for Bug #1848307
        logging.info("Removing designate memcached relation")
        model.remove_relation(
            'designate',
            'coordinator-memcached',
            'memcached:cache')
        wl_statuses['designate'] = {
            'workload-status-message': """'coordinator-memcached' missing""",
            'workload-status': 'blocked'}
    logging.info("Waiting for statuses with exceptions ...")
    model.wait_for_application_states(
        states=wl_statuses)
    certificate_directory = mojo_utils.get_local_certificate_directory()
    certfile = mojo_utils.get_overcloud_cacert_file()
    logging.info("Valut setup basic ...")
    vault_setup.basic_setup(cacert=certfile)
    clients = vault_utils.get_clients(cacert=certfile)
    vault_creds = vault_utils.get_credentails()
    vault_utils.unseal_all(clients, vault_creds['keys'][0])
    action = vault_utils.run_charm_authorize(
        vault_creds['root_token'])
    action = vault_utils.run_get_csr()
    intermediate_csr = action.data['results']['output']
    with open(os.path.join(certificate_directory, 'ca.key'), 'rb') as f:
        cakey = f.read()
    with open(os.path.join(certificate_directory, 'cacert.pem'), 'rb') as f:
        cacert = f.read()
    intermediate_cert = zaza.openstack.utilities.cert.sign_csr(
        intermediate_csr,
        cakey.decode(),
        cacert.decode(),
        generate_ca=True)
    action = vault_utils.run_upload_signed_csr(
        pem=intermediate_cert,
        root_ca=cacert,
        allowed_domains='openstack.local')
    del wl_statuses['vault']
    model.block_until_file_has_contents(
        'keystone',
        '/usr/local/share/ca-certificates/keystone_juju_ca_cert.crt',
        cacert.decode().strip())
    model.wait_for_application_states(
        states=wl_statuses)
    if os_version == 'pike':
        logging.info("Restoring designate memcached relation")
        model.add_relation(
            'designate',
            'coordinator-memcached',
            'memcached:cache')
        del wl_statuses['designate']
        model.wait_for_application_states(
            states=wl_statuses)
