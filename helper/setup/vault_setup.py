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


if __name__ == "__main__":
    cli_utils.setup_logging()
    target_model = model.get_juju_model()
    certificate_directory = mojo_utils.get_local_certificate_directory()
    certfile = mojo_utils.get_overcloud_cacert_file()
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
    wl_statuses = copy.deepcopy(openstack.WORKLOAD_STATUS_EXCEPTIONS)
    del wl_statuses['vault']
    model.block_until_file_has_contents(
        'keystone',
        '/usr/local/share/ca-certificates/keystone_juju_ca_cert.crt',
        cacert.decode().strip())
    model.wait_for_application_states(
        states=wl_statuses)
