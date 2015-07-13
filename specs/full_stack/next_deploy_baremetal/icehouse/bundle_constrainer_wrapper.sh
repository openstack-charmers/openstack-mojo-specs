#!/bin/bash -e
#
#  Optionally consume juju tags passed by environment variable, such
#  as architecture or maas tags.

if [[ -n "$UOSCI_JUJU_TAGS" ]]; then
  scripts/bundle_constrainer.py -yd -i baremetal7.yaml -o baremetal7.yaml --constraints "$UOSCI_JUJU_TAGS" -e "ceilometer-agent,cinder-ceph,neutron-openvswitch"
fi
