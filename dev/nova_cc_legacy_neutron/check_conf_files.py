#!/usr/bin/python
import logging
import sys
import utils.mojo_utils as mojo_utils


def main(argv):
    addr = mojo_utils.juju_get('nova-cloud-controller', 'vip')
    # The second vip is the os-internal-network one
    addr = addr.split(' ')[1]
    for unit in mojo_utils.get_juju_units(service='nova-cloud-controller'):
        for conf, entry, url in [['/etc/nova/nova.conf', 'neutron_url',
                                  "http://%s:9696" % (addr)],
                                 ['/etc/neutron/neutron.conf', 'nova_url',
                                  "http://%s:8774/v2" % (addr)]]:
            out = mojo_utils.remote_run(unit, 'grep %s %s' % (entry, conf))
            if url not in out[0]:
                raise Exception("Did not get expected %s in %s (got='%s', "
                                "wanted='%s')" % (entry, conf, out, url))

            logging.info("%s checked and good." % (conf))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
