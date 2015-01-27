#!/usr/bin/python
import utils.mojo_utils as mojo_utils
import utils.mojo_os_utils as mojo_os_utils
import netaddr
import logging


class VipPool():
    def __init__(self):
        undercloud_novarc = mojo_utils.get_undercload_auth()
        neutronc = mojo_os_utils.get_neutron_client(undercloud_novarc)
        prov_net_id = mojo_utils.get_undercload_netid()
        if prov_net_id:
            net = neutronc.list_networks(id=prov_net_id)['networks'][0]
        else:
            net = mojo_os_utils.get_admin_net(neutronc)
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

logging.basicConfig(level=logging.INFO)
vp = VipPool()
juju_status = mojo_utils.get_juju_status()
for svc in juju_status['services']:
    if 'vip' in mojo_utils.juju_get_config_keys(svc):
        mojo_utils.juju_set(svc, '%s=%s' % ('vip', vp.get_next()))
