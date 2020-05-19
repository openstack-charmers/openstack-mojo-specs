#!/usr/bin/env python3

import logging
import glob
import mojo_spec_check
import sys

logging.basicConfig(level=logging.WARN)

ambiguous_relations = mojo_spec_check.check_for_ambiguous_relations(
    glob.glob('helper/bundles/*yaml'))
sys.exit(len(ambiguous_relations))
