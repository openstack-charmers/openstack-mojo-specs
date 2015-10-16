#!/usr/bin/python
import sys
import utils.mojo_utils as mojo_utils
import utils.mojo_os_utils as mojo_os_utils
import argparse


def main(argv):
    mojo_utils.setup_logging()
    parser = argparse.ArgumentParser()
    default_machines = ["precise:m1.small:1", "cirros:m1.tiny:1"]
    parser.add_argument("machines", default=default_machines, nargs="*")
    parser.add_argument("--active_wait", default=180)
    parser.add_argument("--cloudinit_wait", default=180)
    parser.add_argument("--ping_wait", default=180)
    options = parser.parse_args()
    machines = mojo_utils.parse_mojo_arg(options, 'machines', multiargs=True)
    active_wait = int(mojo_utils.parse_mojo_arg(options, 'active_wait'))
    cloudinit_wait = int(mojo_utils.parse_mojo_arg(options, 'cloudinit_wait'))
    ping_wait = int(mojo_utils.parse_mojo_arg(options, 'ping_wait'))
    overcloud_novarc = mojo_utils.get_overcloud_auth()
    novac = mojo_os_utils.get_nova_client(overcloud_novarc)
    priv_key = mojo_os_utils.create_keypair(novac, 'mojo')
    mojo_os_utils.add_secgroup_rules(novac)
    for instanceset in machines:
        image_name, flavor_name, count = instanceset.split(":")
        mojo_os_utils.boot_and_test(novac,
                                    image_name=image_name,
                                    flavor_name=flavor_name,
                                    number=int(count),
                                    privkey=priv_key,
                                    active_wait=active_wait,
                                    cloudinit_wait=cloudinit_wait,
                                    ping_wait=ping_wait)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
