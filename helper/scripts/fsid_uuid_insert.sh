#!/bin/bash -e
#
#  Generate and insert uuid for fsid, to ensure uniqueness.

BUNDLE="$MOJO_SPEC_DIR/$MOJO_STAGE/baremetal7.yaml"
UUID_NEW="$(uuidgen)"
UUID_ORG="11111111-2222-3333-4444-555555555555"

echo " . Inserting automatically-generated uuid for fsid:"
sed "s/fsid: $UUID_ORG/fsid: $UUID_NEW/g" $BUNDLE -i
grep "fsid" $BUNDLE
