#!/bin/bash

find specs/{full_stack,object_storage,dev} -name manifest | \
while read spec; do
    dirname $spec
done
