#!/usr/bin/env python3
import utils.mojo_utils as mojo_utils
import netaddr
import logging

from zaza import model
from zaza.charm_lifecycle import utils as lifecycle_utils
from zaza.utilities import (
    cli_utils,
    juju_utils,
    openstack_utils,
)


class VipPool():
    def __init__(self, prov_net_id=None):
        keystone_session = openstack_utils.get_undercloud_keystone_session()
        neutronc = openstack_utils.get_neutron_session_client(
            keystone_session)
        if prov_net_id:
            net = neutronc.list_networks(id=prov_net_id)['networks'][0]
        else:
            net = openstack_utils.get_admin_net(neutronc)
        subnet_id = net['subnets'][0]
        subnet = neutronc.list_subnets(id=subnet_id)['subnets'][0]
        allocation_pools = subnet['allocation_pools']
        self.cidr = subnet['cidr']
        self.highest_assigned = netaddr.IPAddress(allocation_pools[0]['end'])
        # XXX look away now, nothing to see here, move along.
        #     If there is less than 30 free ips in the network after the top
        #     dhcp ip then eat into the top of the dhcp range
        available_ips = []
        for element in list(netaddr.IPNetwork(self.cidr)):
            if element == netaddr.IPAddress(self.highest_assigned) or \
                    available_ips:
                available_ips.append(element)
        if len(available_ips) < 30:
            self.highest_assigned = self.highest_assigned - 30

    def get_next(self):
        next_ip = self.highest_assigned + 1
        if next_ip in list(netaddr.IPNetwork(self.cidr)):
            self.highest_assigned = self.highest_assigned + 1
            return next_ip
        else:
            raise Exception("vip pool exhausted")


cli_utils.setup_logging()
vp = VipPool()
juju_status = juju_utils.get_full_juju_status()
model_name = lifecycle_utils.get_juju_model()
for application in juju_status.applications.keys():
    if 'vip' in model.get_application_config(model_name, application).keys():
        model.set_application_config(
            model_name, application, {'vip': vp.get_next()})
mojo_utils.juju_wait_finished()
