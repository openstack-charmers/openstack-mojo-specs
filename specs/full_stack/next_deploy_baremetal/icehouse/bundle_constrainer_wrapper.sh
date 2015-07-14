#!/bin/bash -e
#
#  Optionally consume juju tags passed by environment variable, such
#  as architecture or maas tags.

echo " . Env vars of interest:"
env | egrep 'osci|OSCI|juju|JUJU|mojo|MOJO|amulet|AMULET|proxy|PROXY' | sort

echo " . You are here:"
pwd
whoami

if [[ -n "$UOSCI_JUJU_TAGS" ]]; then
  echo " + Bundle constrainer triggered on: ${UOSCI_JUJU_TAGS}"
  scripts/bundle_constrainer.py -yd -i baremetal7.yaml -o baremetal7.yaml --constraints "$UOSCI_JUJU_TAGS" -e "ceilometer-agent,cinder-ceph,neutron-openvswitch"
else
  echo " - Bundle constrainer not triggered."
fi
