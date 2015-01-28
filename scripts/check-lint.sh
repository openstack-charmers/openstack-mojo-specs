#!/bin/bash

find {object_storage_specs,full_stack} -name manifest | \
while read spec; do
    spec_dir=$(dirname $spec)
    echo $spec_dir
    ./scripts/mojo-spec-check.py $spec_dir
    echo ""
done
