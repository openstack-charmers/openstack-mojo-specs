#!/usr/bin/env python3
import sys
import utils.mojo_os_utils as mojo_os_utils
import argparse

from zaza.utilities import (
    cli as cli_utils,
    openstack as openstack_utils,
)


FLAVORS = {
    'm1.tiny': {
        'flavorid': 1,
        'ram': 512,
        'disk': 1,
        'vcpus': 1},
    'm1.small': {
        'flavorid': 2,
        'ram': 2048,
        'disk': 10,
        'vcpus': 1},
    'm1.medium': {
        'flavorid': 3,
        'ram': 4096,
        'disk': 20,
        'vcpus': 2},
    'm1.large': {
        'flavorid': 4,
        'ram': 8192,
        'disk': 20,
        'vcpus': 4},
}


def init_flavors(nova_client):
    names = [flavor.name for flavor in nova_client.flavors.list()]
    for flavor in FLAVORS.keys():
        if flavor not in names:
            nova_client.flavors.create(
                name=flavor,
                ram=FLAVORS[flavor]['ram'],
                vcpus=FLAVORS[flavor]['vcpus'],
                disk=FLAVORS[flavor]['disk'],
                flavorid=FLAVORS[flavor]['flavorid'])


def main(argv):
    cli_utils.setup_logging()
    parser = argparse.ArgumentParser()
    default_machines = ["cirros:m1.tiny:1"]
    parser.add_argument("machines", default=default_machines, nargs="*")
    parser.add_argument("--active_wait", default=180)
    parser.add_argument("--cloudinit_wait", default=180)
    parser.add_argument("--ping_wait", default=180)
    options = parser.parse_args()
    machines = cli_utils.parse_arg(options, 'machines', multiargs=True)
    active_wait = int(cli_utils.parse_arg(options, 'active_wait'))
    cloudinit_wait = int(cli_utils.parse_arg(options, 'cloudinit_wait'))
    ping_wait = int(cli_utils.parse_arg(options, 'ping_wait'))
    overcloud_novarc = openstack_utils.get_overcloud_auth()
    keystone_session = openstack_utils.get_overcloud_keystone_session()
    keystonec = openstack_utils.get_keystone_session_client(
        keystone_session)
    domain = overcloud_novarc.get('OS_PROJECT_DOMAIN_NAME')
    project_id = openstack_utils.get_project_id(
        keystonec,
        'admin',
        api_version=overcloud_novarc['API_VERSION'],
        domain_name=domain
    )
    novac = openstack_utils.get_nova_session_client(keystone_session)
    neutronc = openstack_utils.get_neutron_session_client(keystone_session)

    init_flavors(novac)

    priv_key = mojo_os_utils.create_keypair(novac, 'mojo')
    openstack_utils.add_neutron_secgroup_rules(neutronc, project_id)
    for server in novac.servers.list():
        novac.servers.delete(server.id)
    for instanceset in machines:
        image_name, flavor_name, count = instanceset.split(":")
        mojo_os_utils.boot_and_test(novac, neutronc,
                                    image_name=image_name,
                                    flavor_name=flavor_name,
                                    number=int(count),
                                    privkey=priv_key,
                                    active_wait=active_wait,
                                    cloudinit_wait=cloudinit_wait,
                                    ping_wait=ping_wait)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
