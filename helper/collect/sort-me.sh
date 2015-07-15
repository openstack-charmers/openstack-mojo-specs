#!/bin/bash -e
# Sort collect and repo files in current directory.

for f in collect* repo*; do
  echo "$f $f_tmp"
  f_tmp="$(mktemp)"
  sort < $f > $f_tmp
  cat $f_tmp > $f
  rm -fv $f_tmp
done
