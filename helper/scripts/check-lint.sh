#!/bin/bash

echo "Checking specs..."
for spec in $(find specs/{object_storage,full_stack} -name manifest); do
    spec_dir=$(dirname $spec)
    MSGS=$(./helper/scripts/mojo-spec-check.py $spec_dir 2>&1)
    if [[ "$MSGS" == *WARNING* ]] || [[ "$MSGS" == *ERROR* ]]; then
        result="(!)"
        failed=1
    else
        result="OK"
    fi
    echo -e "${result}\t${spec_dir}"
    [[ -n "$MSGS" ]] && echo -e "$MSGS\n"
done

if [[ -n "$failed" ]]; then
    echo "One or more specs failed a sanity check."
    exit 1
else
    echo "All spec sanity checks passed."
fi
