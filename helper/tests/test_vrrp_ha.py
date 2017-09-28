#!/usr/bin/env python
import time
import sys
import utils.mojo_utils as mojo_utils
import utils.mojo_os_utils as mojo_os_utils
import logging


def lookup_cirros_server(cloud_auth):
    cirros_images = get_cirros_images(cloud_auth)
    nova_client = mojo_os_utils.get_nova_client(cloud_auth)
    for server in nova_client.servers.list():
        if server.image['id'] in cirros_images:
            return server


def get_cirros_server(cloud_auth, image_password):
    logging.info('Looking for existing cirros server')
    cirros_server = lookup_cirros_server(cloud_auth)
    if cirros_server:
        ip = get_server_floating_ip(cirros_server)
        logging.info('Checking connectivity to cirros guest')
        if not mojo_os_utils.ssh_test('cirros', ip, cirros_server.name,
                                      password=image_password):
            raise Exception('Cirros guest inaccessable')
    else:
        nova_client = mojo_os_utils.get_nova_client(cloud_auth)
        logging.info('Creating new cirros guest')
        mojo_os_utils.boot_and_test(
            nova_client,
            image_name='cirros',
            flavor_name='m1.small',
            number=1,
            privkey=None,
        )
        cirros_server = lookup_cirros_server(cloud_auth)
        ip = get_server_floating_ip(cirros_server)
    return cirros_server, ip


def get_cirros_images(cloud_auth):
    logging.info('Getting list of cirros images')
    glance_client = mojo_os_utils.get_glance_client(cloud_auth)
    cirros_images = []
    for image in glance_client.images.list():
        if 'cirros' in image.name:
            cirros_images.append(image.id)
    return cirros_images


def check_server_state(nova_client, state, server_id=None, server_name=None,
                       wait_time=120):
    sleep_time = 2
    if server_name:
        server_id = nova_client.servers.find(name=server_name).id
    server = nova_client.servers.find(id=server_id)
    while server.status != state and wait_time > 0:
        time.sleep(sleep_time)
        server = nova_client.servers.find(id=server_id)
        wait_time -= sleep_time
    return server.status == state


def check_neutron_agent_states(neutron_client, host_name, wait_time=120):
    sleep_time = 2
    statuses = [False]
    while False in statuses and wait_time > 0:
        time.sleep(sleep_time)
        statuses = []
        for agent in neutron_client.list_agents()['agents']:
            if agent['host'] == host_name:
                statuses.append(agent['admin_state_up'])
                statuses.append(agent['alive'])
        wait_time -= sleep_time
    return False not in statuses


def get_server_floating_ip(server):
    for addr in server.addresses['private']:
        if addr['OS-EXT-IPS:type'] == 'floating':
            return addr['addr']


def main(argv):
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    overcloud_novarc = mojo_utils.get_overcloud_auth()
    undercloud_novarc = mojo_utils.get_undercloud_auth()
    under_novac = mojo_os_utils.get_nova_client(undercloud_novarc)
    over_neutronc = mojo_os_utils.get_neutron_client(overcloud_novarc)
    image_config = mojo_utils.get_mojo_config('images.yaml')
    image_password = image_config['cirros']['password']
    # Look for existing Cirros guest
    server, ip = get_cirros_server(overcloud_novarc, image_password)
    router = over_neutronc.list_routers(name='provider-router')['routers'][0]
    l3_agents = over_neutronc.list_l3_agent_hosting_routers(
        router=router['id'])['agents']
    logging.info('Checking there are multiple L3 agents running tenant router')
    if len(l3_agents) != 2:
        raise Exception('Unexpected number of l3 agents')
    for agent in l3_agents:
        gateway_hostname = agent['host']
        gateway_server = under_novac.servers.find(name=gateway_hostname)
        logging.info('Shutting down neutron gateway {} ({})'.format(
            gateway_hostname,
            gateway_server.id)
        )
        gateway_server.stop()
        if not check_server_state(under_novac, 'SHUTOFF',
                                  server_name=gateway_hostname):
            raise Exception('Server failed to reach SHUTOFF state')
        logging.info('Neutron gateway %s has shutdown' % (gateway_hostname))
        logging.info('Checking connectivity to cirros guest')
        if not mojo_os_utils.wait_for_ping(ip, 90):
            raise Exception('Cirros guest not responding to ping')
        if not mojo_os_utils.ssh_test('cirros', ip, server.name,
                                      password=image_password):
            raise Exception('Cirros guest issh connection failed')
        logging.info('Starting neutron gateway: ' + gateway_hostname)
        gateway_server.start()
        if not check_server_state(under_novac, 'ACTIVE',
                                  server_name=gateway_hostname):
            raise Exception('Server failed to reach SHUTOFF state')
        if not check_neutron_agent_states(over_neutronc, gateway_hostname):
            raise Exception('Server agents failed to reach active state')


if __name__ == "__main__":
    sys.exit(main(sys.argv))
