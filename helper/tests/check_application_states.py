#!/usr/bin/env python3

import asyncio
from zaza import model
from zaza.openstack.utilities import (
    cli as cli_utils,
    openstack,
)

if __name__ == "__main__":
    cli_utils.setup_logging()
    target_model = model.get_juju_model()
    model.wait_for_application_states(
        model_name=target_model,
        states=openstack.WORKLOAD_STATUS_EXCEPTIONS)
    asyncio.get_event_loop().close()
