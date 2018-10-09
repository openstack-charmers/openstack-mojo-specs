#!/usr/bin/env python3

# Copyright 2018 Canonical Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
import os
import sys

from utils import mojo_utils
from zaza import model
from zaza.utilities import (
    cli as cli_utils,
    generic as generic_utils,
)

from zaza.charm_tests.series_upgrade.tests import (
    TrustyXenialSeriesUpgrade,
    XenialBionicSeriesUpgrade,
)


"""
def series_upgrade_all(from_series="trusty", to_series="xenial"):

    # Set Feature Flag
    os.environ["JUJU_DEV_FEATURE_FLAGS"] = "upgrade-series"

    applications = model.get_status().applications
    completed_machines = []
    for application in applications:
        # Defaults
        origin = "openstack-origin"
        pause_non_leader_subordinate = True
        pause_non_leader_primary = True
        # Skip subordinates
        if applications[application]["subordinate-to"]:
            continue
        if "percona-cluster" in applications[application]["charm"]:
            origin = "source"
            pause_non_leader_primary = True
            pause_non_leader_subordinate = True
        if "rabbitmq-server" in applications[application]["charm"]:
            origin = "source"
            pause_non_leader_primary = True
            pause_non_leader_subordinate = False
        if "nova-compute" in applications[application]["charm"]:
            pause_non_leader_primary = False
            pause_non_leader_subordinate = False
        if "ceph" in applications[application]["charm"]:
            origin = "source"
            pause_non_leader_primary = False
            pause_non_leader_subordinate = False
        # The rest are likley APIs use defaults

        generic_utils.series_upgrade_application(
            application,
            pause_non_leader_primary=pause_non_leader_primary,
            pause_non_leader_subordinate=pause_non_leader_subordinate,
            from_series=from_series,
            to_series=to_series,
            origin=origin,
            completed_machines=completed_machines)

"""

if __name__ == "__main__":
    cli_utils.setup_logging()
    from_series = os.environ.get("MOJO_SERIES")
    if from_series == "trusty":
        to_series = "xenial"
        series_upgrade_test = TrustyXenialSeriesUpgrade()
    elif from_series == "xenial":
        to_series = "bionic"
        series_upgrade_test = XenialBionicSeriesUpgrade()

    else:
        raise Exception("MOJO_SERIES is not set to a vailid LTS series")
    series_upgrade_test.setUpClass()
    sys.exit(series_upgrade_test.test_200_run_series_upgrade())
    #sys.exit(series_upgrade_all(from_series=from_series, to_series=to_series))
