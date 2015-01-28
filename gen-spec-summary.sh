#!/bin/bash

find . -name "SPEC_INFO.txt" | \
while read spec; do
    echo ${spec/SPEC_INFO.txt/}
    cat $spec
    echo ""
done > SPEC_SUMMARY.txt
