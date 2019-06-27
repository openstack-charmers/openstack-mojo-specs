#!/usr/bin/env python3

import sys

from zaza.openstack.configure import bgp_speaker


if __name__ == "__main__":
    sys.exit(bgp_speaker.run_from_cli())
