#!/usr/bin/python3

# This file is part of juju-wait, a juju plugin to wait for environment
# steady state.
#
# Copyright 2015 Canonical Ltd.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranties of
# MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR
# PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import argparse
from datetime import datetime, timedelta
from distutils.version import LooseVersion
import json
import logging
import os
import subprocess
import sys
from textwrap import dedent
import time
import yaml


__version__ = '2.4.3'


class DescriptionAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        parser.exit(0, parser.description.splitlines()[0] + '\n')


class EnvironmentAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        os.environ['JUJU_ENV'] = values[0]
        # also set JUJU_MODEL environment variable for juju 2.x
        os.environ['JUJU_MODEL'] = values[0]


def parse_ts(ts):
    '''Parse the Juju provided timestamp, which must be UTC.'''
    return datetime.strptime(ts, '%d %b %Y %H:%M:%SZ')


class JujuWaitException(Exception):
    '''A fatal exception'''
    pass


def run_or_die(cmd, env=None):
    try:
        # It is important we don't mix stdout and stderr, as stderr
        # will often contain SSH noise we need to ignore due to Juju's
        # lack of SSH host key handling.
        p = subprocess.Popen(cmd, universal_newlines=True, env=env,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (out, err) = p.communicate()
    except OSError as x:
        logging.error("{} failed: {}".format(' '.join(cmd), x.errno))
        raise JujuWaitException(x.errno or 41)
    except Exception as x:
        logging.error("{} failed: {}".format(' '.join(cmd), x))
        raise JujuWaitException(42)
    if p.returncode != 0:
        logging.error(err)
        logging.error("{} failed: {}".format(' '.join(cmd), p.returncode))
        raise JujuWaitException(p.returncode or 43)
    return out


def juju_exe():
    # Allow override using environment variable(s)
    if os.environ.get('JUJU_BINARY'):
        # JUJU_BINARY can be a full path: /path/to/juju
        juju = os.environ.get('JUJU_BINARY')
    elif os.environ.get('JUJU_VERSION'):
        # JUJU_VERSION can specify just the version
        # and select from juju-$VER in PATH
        ver = (".".join(os.environ.get('JUJU_VERSION')
               .split('-')[0].split('.')[:2]))
        juju = 'juju-{}'.format(ver)
    else:
        # Default to juju in PATH
        juju = 'juju'
    return juju


def juju_run(unit, cmd, timeout=None):
    if timeout is None:
        timeout = 6 * 60 * 60
    return run_or_die([juju_exe(), 'run', '--timeout={}s'.format(timeout),
                       '--unit', unit, cmd])


def juju_run_many(units, cmd, timeout=None):
    units = list(units)
    if not units:
        return {}
    args = [juju_exe(), 'run', '--format=yaml', '--unit', ','.join(units)]
    if timeout is not None:
        args.append('--timeout={}s'.format(timeout))
    args.extend(['--', cmd])
    out = yaml.safe_load(run_or_die(args))
    # ReturnCode is omitted from the YAML when 0, so assume absence is
    # success.
    return {d['UnitId']: (d.get('ReturnCode', 0), d['Stdout']) for d in out}


def get_status():
    # Older juju versions don't support --utc, so force UTC timestamps
    # using the environment variable.
    env = os.environ.copy()
    env['TZ'] = 'UTC'
    json_status = run_or_die([juju_exe(), 'status', '--format=json'], env=env)
    if json_status is None:
        return None
    return json.loads(json_status)


def get_log_tail(unit, timeout=None):
    log = 'unit-{}.log'.format(unit.replace('/', '-'))
    cmd = 'sudo tail -1 /var/log/juju/{}'.format(log)
    return juju_run(unit, cmd, timeout=timeout)


def leadership_poll(units):
    is_leader_results = juju_run_many(units, 'is-leader --format=json')
    unit_map = {}
    failed = False
    for unit, (return_code, stdout) in is_leader_results.items():
        if return_code != 0:
            logging.error("{} has failed. Unable to run leadership check."
                          "".format(unit))
            failed = True
            continue
        try:
            unit_map[unit] = json.loads(stdout)
        except ValueError:
            logging.error("{} has failed. Insane output from commands."
                          "".format(unit))
            failed = True
    if failed:
        raise JujuWaitException(44)
    return unit_map


# Juju 1.24+ provides us with the timestamp the status last changed.
# If all units are idle more than this many seconds, the system is
# quiescent. This may be unnecessary, but protects against races
# where all units report they are currently idle but there are hooks
# still due to be run.
IDLE_CONFIRMATION = timedelta(seconds=15)

# If all units have one of the following workload status values,
# consider them ready.  Not all charms use workload the status feature.
# Those that do not will be represented by the 'unknown' value and
# workload status will be ignored.  For charms that do, wait for an
# 'active' workload status value.  FYI: blocked, waiting, maintenance
# values indicate not-ready workload states.
WORKLOAD_OK_STATES = ['active', 'unknown']

# If any unit ever reaches one of the following workload status
# values, consider that fatal and raise.
WORKLOAD_ERROR_STATES = ['error']


def wait_cmd(args=sys.argv[1:]):
    description = dedent("""\
        Wait for environment steady state.

        The environment is considered in a steady state once all hooks
        have completed running and there are no hooks queued to run,
        on all units.
        """)
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('-e', '-m', '--environment', '--model',
                        metavar="MODEL", type=str,
                        action=EnvironmentAction, nargs=1)
    parser.add_argument('--description', action=DescriptionAction, nargs=0)
    parser.add_argument('-q', '--quiet', dest='quiet',
                        action='store_true', default=False)
    # XXX Delta from upstream: default = True
    parser.add_argument('-v', '--verbose', dest='verbose',
                        action='store_true', default=True)
    # XXX Delta from upstream: default = True
    parser.add_argument('-w', '--workload', dest='wait_for_workload',
                        help='Wait for unit workload status active state',
                        action='store_true', default=True)
    # XXX Delta from upstream: default = 2700
    parser.add_argument('-t', '--max_wait', dest='max_wait',
                        help='Maximum time to wait for readiness (seconds)',
                        action='store', default=2700)
    parser.add_argument('--version', default=False, action='store_true')
    args = parser.parse_args(args)

    if args.version:
        parser.exit(0, __version__ + '\n')

    # Parser did not exit, so continue.
    logging.basicConfig()
    log = logging.getLogger()
    if args.quiet:
        log.setLevel(logging.WARN)
    elif args.verbose:
        log.setLevel(logging.DEBUG)
    else:
        log.setLevel(logging.INFO)

    # Set max_wait integer value if specified, otherwise None.
    # This preserves the existing behavior while allowing the
    # user to optionally specify a maximum wait time.
    if args.max_wait:
        max_wait = int(args.max_wait)
    else:
        max_wait = None

    # Begin watching and waiting
    try:
        wait(log, args.wait_for_workload, max_wait)
        return 0
    except JujuWaitException as x:
        return x.args[0]


def reset_logging():
    """If we are running Juju 1.23 or earlier, we require default logging.

    Reset the environment log settings to match default juju stable.
    """
    run_or_die([juju_exe(), 'set-environment',
                'logging-config=juju=WARNING;unit=INFO'])


def wait(log=None, wait_for_workload=False, max_wait=None):
    # Note that wait_for_workload is only useful as a workaround for
    # broken setups. It is impossible for a charm to report that it has
    # completed setup, because a charm has no information about units
    # still being provisioned or relations that have not yet been joined.
    # A charm might report an active state, but there may still be hours
    # worth of setup hooks to run before it is complete. wait_for_workload
    # does allow you to ignore infinite hook loops and other similar bugs
    # in your charms.
    if log is None:
        log = logging.getLogger()

    # pre-juju 1.24, we can only detect idleless by looking for changes
    # in the logs.
    prev_logs = {}

    epoch_started = time.time()
    ready_since = None
    logging_reset = False

    while True:
        status = get_status()
        ready = True

        # If defined, fail if max_wait is exceeded
        epoch_elapsed = time.time() - epoch_started
        if max_wait and epoch_elapsed > max_wait:
            ready = False
            logging.error('Not ready in {}s (max_wait)'.format(max_wait))
            raise JujuWaitException(44)

        # If there is a dying service, environment is not quiescent.
        services = status.get('services') or status.get('applications', {})
        for sname, service in sorted(services.items()):
            if service.get('life') in ('dying', 'dead'):
                logging.debug('{} is dying'.format(sname))
                ready = False

        all_units = set()  # All units, including subordinates.

        # 'ready' units are up, and might be idle. They need to have their
        # logs sniffed because they are running Juju 1.23 or earlier.
        ready_units = {}

        # Flattened agent and workload status and leadership for all units
        # and subordinates that provide it. Note that 'agent status' is only
        # available in Juju 1.24 and later. This is easily confused with
        # 'agent state' which is available in earlier versions of Juju.
        workload_status = {}
        agent_status = {}
        agent_version = {}
        unit_leadership = {}
        for sname, service in services.items():
            for uname, unit in service.get('units', {}).items():
                all_units.add(uname)
                unit_leadership[uname] = unit.get('leader', None)
                if 'agent-version' in unit:
                    agent_version[uname] = unit.get('agent-version')
                elif 'juju-status' in unit and ('version'
                                                in unit['juju-status']):
                    # agent-version disappeared and was replaced by
                    # a subkey of juju-status some time during the Juju
                    # 2.0 beta cycle.
                    agent_version[uname] = unit['juju-status']['version']
                if ('workload-status' in unit and
                        'current' in unit['workload-status']):
                    workload_status[uname] = unit['workload-status']

                if 'agent-status' in unit and unit['agent-status'] != {}:
                    agent_status[uname] = unit['agent-status']
                elif 'juju-status' in unit and unit['juju-status'] != {}:
                    # agent-status was renamed to juju-status some time
                    # during the Juju 2.0 beta cycle.
                    agent_status[uname] = unit['juju-status']
                else:
                    ready_units[uname] = unit  # Schedule for sniffing.
                for subname, sub in unit.get('subordinates', {}).items():
                    unit_leadership[subname] = sub.get('leader', None)
                    if ('workload-status' in sub and
                            'current' in sub['workload-status']):
                        workload_status[subname] = sub['workload-status']

                    if 'agent-version' in sub:
                        agent_version[subname] = sub['agent-version']
                    elif 'juju-status' in sub and ('version' in
                                                   sub['juju-status']):
                        agent_version[subname] = sub['juju-status']['version']
                    if 'agent-status' in sub and unit['agent-status'] != {}:
                        agent_status[subname] = sub['agent-status']
                    elif 'juju-status' in sub and unit['juju-status'] != {}:
                        # agent-status was renamed to juju-status some time
                        # during the Juju 2.0 beta cycle.
                        agent_status[subname] = sub['juju-status']
                    else:
                        ready_units[subname] = sub  # Schedule for sniffing.

        for uname, wstatus in sorted(workload_status.items()):
            if not ('current' in wstatus and 'since' in wstatus):
                ready = False
                continue
            current = wstatus['current']
            since = parse_ts(wstatus['since'])

            # Check workload status
            if current not in WORKLOAD_OK_STATES and wait_for_workload:
                logging.debug('{} workload status is {} since '
                              '{}Z'.format(uname, current, since))
                ready = False

            # Fail and raise if workload state is ever in error
            if current in WORKLOAD_ERROR_STATES and wait_for_workload:
                logging.error('{} failed: workload status is '
                              '{}'.format(uname, current))
                ready = False
                raise JujuWaitException(1)

        for uname, astatus in sorted(agent_status.items()):
            if not ('current' in astatus and 'since' in astatus):
                ready = False
                continue
            current = astatus['current']
            since = parse_ts(astatus['since'])
            if 'message' in astatus:
                message = astatus['message']
            else:
                message = ''

            # Check agent status
            if (current == 'executing' and
                    message == 'running update-status hook'):
                # update-status is an idle hook event
                pass
            elif current != 'idle':
                logging.debug('{} juju agent status is {} since '
                              '{}Z'.format(uname, current, since))
                ready = False

        # Log storage to compare with prev_logs.
        logs = {}

        # Sniff logs of units that don't provide agent-status, if necessary.
        # This section can go when we drop support for Juju < 1.24.
        for uname, unit in sorted(ready_units.items()):
            dying = unit.get('life') in ('dying', 'dead')
            agent_state = unit.get('agent-state')
            agent_state_info = unit.get('agent-state-info')
            if dying:
                logging.debug('{} is dying'.format(uname))
                ready = False
            elif agent_state == 'error':
                logging.error('{} failed: {}'.format(uname, agent_state_info))
                ready = False
                raise JujuWaitException(1)
            elif agent_state != 'started':
                logging.debug('{} is {}'.format(uname, agent_state))
                ready = False
            elif ready:
                # We only start grabbing the logs once all the units
                # are in a suitable lifecycle state. If we don't do this,
                # we risk attempting to grab logs from units or subordinates
                # that are not yet ready to respond, or have disappeared
                # since we last checked the environment status.
                if not logging_reset:
                    reset_logging()
                    logging_reset = True
                logs[uname] = get_log_tail(uname)
                if logs[uname] == prev_logs.get(uname):
                    logging.debug('{} is idle - no hook activity'
                                  ''.format(uname))
                else:
                    logging.debug('{} is active: {}'
                                  ''.format(uname, logs[uname].strip()))
                    ready = False

        if ready:
            # We are never ready until this check has been running until
            # IDLE_CONFIRMATION time has passed. This ensures that if we
            # run 'juju wait' immediately after an operation such as
            # 'juju upgrade-charm', then the scheduled operation has had
            # a chance to fire any hooks it is going to.
            if ready_since is None:
                ready_since = datetime.utcnow()
                ready = False
            elif ready_since + IDLE_CONFIRMATION < datetime.utcnow():
                logging.info('All units idle since {}Z ({})'
                             ''.format(ready_since,
                                       ', '.join(sorted(all_units))))
            else:
                ready = False
        else:
            ready_since = None
            ready = False

        # Ensure every service has a leader. If there is no leader, then
        # one will be appointed soon and hooks should kick off.
        # Run last as it can take quite awhile on environments with a
        # large number of services.
        if ready:
            for uname, ver in agent_version.items():
                if ver and LooseVersion(ver) < LooseVersion('1.24'):
                    # Leadership was added in 1.24, so short-circuit to true
                    # anything older.
                    unit_leadership[uname] = True
                elif (ver and LooseVersion(ver) >= LooseVersion('2.1') and
                      unit_leadership[uname] is None):
                    # Leadership is set in the status output
                    # only when leader = True
                    # Avoid the costly juju run when unnecessary
                    unit_leadership[uname] = False

            # Ask all the other units in parallel whether they're the
            # leader if leader is not set.
            unit_leadership.update(leadership_poll(
                uname for uname, leader in unit_leadership.items()
                if leader is None))

            # Aggregate and log the leader status by service.
            services = set()
            services_with_leader = set()
            for uname, is_leader in unit_leadership.items():
                sname = uname.split('/', 1)[0]
                services.add(sname)
                if sname not in services_with_leader and is_leader:
                    services_with_leader.add(sname)
                    logging.debug('{} is lead by {}'.format(sname, uname))
            for sname in services:
                # Note that we only collected services that have 1 or more
                # units. A service with no units will not have a leader
                # and this is fine and juju-wait should ignore it.
                if sname not in services_with_leader:
                    logging.info('{} does not have a leader'.format(sname))
                    ready_since = None
                    ready = False

        # If everything looks good, return.
        if ready:
            return

        prev_logs = logs
        time.sleep(4)


if __name__ == '__main__':
    # I use these to launch the entry points from the source tree.
    # Most installations will be using the setuptools generated
    # launchers.
    script = os.path.basename(sys.argv[0])
    # XXX Delta from upstream
    if script == 'juju-wait' or 'juju_wait':
        sys.exit(wait_cmd())
    else:
        raise RuntimeError('Unknown script {}'.format(script))
