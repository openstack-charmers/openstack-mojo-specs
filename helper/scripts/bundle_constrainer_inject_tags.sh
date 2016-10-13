#!/bin/bash -e
#
#  Optionally inject juju tags passed by environment variable, such
#  as architecture or maas tags, excluding the listed subordinate charms.

SUBORDINATES="ceilometer-agent,cinder-ceph,neutron-openvswitch,ntp"

[[ -z "$BUNDLE_FILE" ]] && export BUNDLE_FILE="baremetal7.yaml"

echo " . Env vars of interest:"
env | egrep 'osci|OSCI|juju|JUJU|mojo|MOJO|amulet|AMULET|proxy|PROXY' | sort

echo " . You are here:"
pwd && whoami

if [[ -n "$UOSCI_JUJU_TAGS" ]]; then
  echo " + Bundle constrainer triggered on: ${UOSCI_JUJU_TAGS}"
  $MOJO_SPEC_DIR/$MOJO_STAGE/scripts/bundle_constrainer.py -yd \
    -i $MOJO_SPEC_DIR/$MOJO_STAGE/$BUNDLE_FILE \
    -o $MOJO_SPEC_DIR/$MOJO_STAGE/$BUNDLE_FILE \
    --constraints "$UOSCI_JUJU_TAGS" -e "$SUBORDINATES"
else
  echo " - Bundle constrainer not triggered."
fi
