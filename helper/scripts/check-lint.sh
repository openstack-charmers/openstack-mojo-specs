#!/bin/bash

find specs/{object_storage,full_stack} -name manifest | \
while read spec; do
    spec_dir=$(dirname $spec)
    MSGS=$(./helper/scripts/mojo-spec-check.py $spec_dir 2>&1)
    if [[ ! -z $MSGS ]]; then
        echo $spec_dir
	echo "$MSGS"
        echo ""
    fi
done
