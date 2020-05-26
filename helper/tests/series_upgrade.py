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

from zaza.openstack.utilities import (
    cli as cli_utils,
)

from zaza.openstack.charm_tests.series_upgrade.tests import (
    TrustyXenialSeriesUpgrade,
    XenialBionicSeriesUpgrade,
)

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
    logging.info("Preparing series upgrade test from {} to {}".format(
        from_series, to_series))
    logging.info("Setting up...")
    series_upgrade_test.setUpClass()
    logging.info("Running series upgrade test...")
    sys.exit(series_upgrade_test.test_200_run_series_upgrade())
