#!/bin/bash

echo "Checking specs..."
for spec in $(find specs/{storage,full_stack} -name manifest); do
    spec_dir=$(dirname $spec)
    MSGS=$(./helper/scripts/mojo_spec_check.py $spec_dir 2>&1)
    if [[ "$MSGS" == *WARNING* ]] || [[ "$MSGS" == *ERROR* ]]; then
        result="(!)"
        failed=1
    else
        result="OK"
    fi
    echo -e "${result}\t${spec_dir}"
    [[ -n "$MSGS" ]] && echo -e "$MSGS\n"
done

# Keep bundle names consistent
bundle_names="$(ls -1 ./helper/bundles/*_* 2> /dev/null ||:)"
if [[ -n "$bundle_names" ]]; then
  echo -e "(!)\tFor consistency, bundle file names should not use underscores (hyphens are ok)."
  failed=1
  echo "$bundle_names"
else
  echo "Bundle file names OK"
fi

# Keep spec dir names consistent
spec_dir_names="$(find ./specs -type d | grep - ||:)"
if [[ -n "$spec_dir_names" ]]; then
  echo -e "(!)\tFor consistency, spec dir names should not use hyphens (underscores are ok)."
  failed=1
  echo "$spec_dir_names"
else
  echo "Spec dir names OK"
fi

if [[ -n "$failed" ]]; then
    echo "One or more specs failed a sanity check."
    exit 1
else
    echo "All spec sanity checks passed."
fi
