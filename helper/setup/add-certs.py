#!/usr/bin/env python3

import base64
import copy
import logging
import os
import zaza.openstack.utilities.cert
from zaza.openstack.utilities import (
    cli as cli_utils,
    openstack,
)
from zaza import model

ISSUER_NAME = 'OSCI'
CERT_DIR = os.environ.get('MOJO_LOCAL_DIR')


def write_cert(path, filename, data, mode=0o600):
    """
    Helper function for writing certificate data to disk.

    :param path: Directory file should be put in
    :type path: str
    :param filename: Name of file
    :type filename: str
    :param data: Data to write
    :type data: any
    :param mode: Create mode (permissions) of file
    :type mode: Octal(int)
    """
    with os.fdopen(os.open(os.path.join(path, filename),
                           os.O_WRONLY | os.O_CREAT, mode), 'wb') as f:
        f.write(data)


def create_certs(application_name, ip, issuer_name, signing_key):
    """Generate a certificate for with the given info and store it.

    Generate a certificate for with the given info and write it to disk.

    :param application_name: Name of application, used to derive path to store
                             artefacts.
    :type application_name: str
    :param ip: IP address that service will be accessed via.
    :type ip: str
    :param issuer_name: Name to be used as cert issuer.
    :type issuer_name: str
    :param signing_key: Key to sign cert with.
    :type signing_key: str
    """
    logging.info("Creating cert for {}".format(application_name))
    # The IP is used as the CN for backward compatability and as an
    # alternative_name for forward comapability.
    (key, cert) = zaza.openstack.utilities.cert.generate_cert(
        ip,
        issuer_name=ISSUER_NAME,
        alternative_names=[ip],
        signing_key=signing_key)
    APP_CERT_DIR = os.path.join(CERT_DIR, application_name)
    if not os.path.exists(APP_CERT_DIR):
        os.makedirs(APP_CERT_DIR)
    write_cert(APP_CERT_DIR, 'cert.pem', cert)
    write_cert(APP_CERT_DIR, 'cert.key', key)


def apply_certs(application_name):
    """Read certs from disk and apply them to runninch charms.

    :param application_name: Name of application, used to derive path to store
                             artefacts.
    :type application_name: str
    """
    APP_CERT_DIR = os.path.join(CERT_DIR, application_name)
    ssl_options = [
        ('ssl_ca', os.path.join(CERT_DIR, 'cacert.pem')),
        ('ssl_cert', os.path.join(APP_CERT_DIR, 'cert.pem')),
        ('ssl_key', os.path.join(APP_CERT_DIR, 'cert.key'))]
    charm_config = {}
    for (charm_option, ssl_file) in ssl_options:
        with open(ssl_file, 'rb') as f:
            ssl_data = f.read()
        charm_config[charm_option] = base64.b64encode(ssl_data).decode('utf8')
    model.set_application_config(
        application_name,
        configuration=charm_config)


def create_ca():
    """Create a CA

    :returns: A tuple of CA key and cert.
    :rtype: (str, str)
    """
    (cakey, cacert) = zaza.openstack.utilities.cert.generate_cert(
        ISSUER_NAME,
        generate_ca=True)
    write_cert(CERT_DIR, 'cacert.pem', cacert)
    write_cert(CERT_DIR, 'ca.key', cakey)
    return (cakey, cacert)


def encrypt_vip_endpoints():
    """Apply certs and keys to all charms that support them."""
    (cakey, cacert) = create_ca()
    ssl_vip_keys = ['vip', 'ssl_ca', 'ssl_cert', 'ssl_key']
    status = model.get_status()
    for application_name in status.applications.keys():
        app_config = model.get_application_config(application_name)
        if all(k in app_config for k in ssl_vip_keys):
            cn = app_config['vip'].get('value')
            # If there is no vip check if its a non-ha deploy.
            if not cn:
                units = model.get_units(application_name)
                if len(units) == 1:
                    cn = units[0].public_address
            if cn:
                create_certs(
                    application_name,
                    cn,
                    ISSUER_NAME,
                    cakey)
                apply_certs(application_name)
    model.block_until_all_units_idle()


if __name__ == "__main__":
    cli_utils.setup_logging()
    os_version = openstack.get_current_os_versions(
        'designate').get('designate')
    wl_statuses = copy.deepcopy(openstack.WORKLOAD_STATUS_EXCEPTIONS)
    if os_version <= 'pike':
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
    model.wait_for_application_states(
        states=wl_statuses)
    encrypt_vip_endpoints()
    model.block_until_all_units_idle()
    if os_version <= 'pike':
        logging.info("Restoring designate memcached relation")
        model.add_relation(
            'designate',
            'coordinator-memcached',
            'memcached:cache')
        del wl_statuses['designate']
        model.wait_for_application_states(
            states=wl_statuses)
