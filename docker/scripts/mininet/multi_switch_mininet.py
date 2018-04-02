#!/usr/bin/env python2

# Copyright 2013-present Barefoot Networks, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import signal
import os
import sys
import subprocess
import argparse
import json
import importlib
import re
from time import sleep

from mininet.net import Mininet
from mininet.topo import Topo
from mininet.link import TCLink
from mininet.log import setLogLevel, info
from mininet.cli import CLI

from p4_mininet import P4Switch, P4Host
import apptopo
import appcontroller
import appprocrunner

parser = argparse.ArgumentParser(description='Mininet demo')
parser.add_argument('--behavioral-exe', help='Path to behavioral executable',
                    type=str, action="store", required=True)
parser.add_argument('--thrift-port', help='Thrift server port for table updates',
                    type=int, action="store", default=9090)
parser.add_argument('--bmv2-log', help='verbose messages in log file', action="store_true")
parser.add_argument('--cli', help="start the mininet cli", action="store_true")
parser.add_argument('--cli-path', help="path to control utility for switch", default="simple_switch_CLI")
parser.add_argument('--auto-control-plane', help='enable automatic control plane population', action="store_true")
parser.add_argument('--json', help='Path to JSON config file',
                    type=str, action="store", required=True)
parser.add_argument('--pcap-dump', help='Dump packets on interfaces to pcap files',
                    action="store_true")
parser.add_argument('--manifest', '-m', help='Path to manifest file',
                    type=str, action="store", required=True)
parser.add_argument('--target', '-t', help='Target in manifest file to run',
                    type=str, action="store", required=True)
parser.add_argument('--log-dir', '-l', help='Location to save output to',
                    type=str, action="store", required=True)


args = parser.parse_args()


next_thrift_port = args.thrift_port

def run_command(command):
    return os.WEXITSTATUS(os.system(command))

def configureP4Switch(**switch_args):
    class ConfiguredP4Switch(P4Switch):
        def __init__(self, *opts, **kwargs):
            global next_thrift_port
            kwargs.update(switch_args)
            kwargs['thrift_port'] = next_thrift_port
            next_thrift_port += 1
            P4Switch.__init__(self, *opts, **kwargs)
    return ConfiguredP4Switch


def main():

    with open(args.manifest, 'r') as f:
        manifest = json.load(f)

    conf = manifest['targets'][args.target]
    if 'parameters' not in conf: conf['parameters'] = {}
    if 'hosts' not in conf: conf['hosts'] = {}
    if 'switches' not in conf: conf['switches'] = {}

    def formatParams(s):
        for param in conf['parameters']:
            s = re.sub('\$'+param+'(\W|$)', str(conf['parameters'][param]) + r'\1', s)
            s = s.replace('${'+param+'}', str(conf['parameters'][param]))
        return s

    AppTopo = apptopo.AppTopo
    AppController = appcontroller.AppController
    AppProcRunner = appprocrunner.AppProcRunner

    if 'topo_module' in conf or 'controller_module' in conf or 'procrunner_module' in conf:
        sys.path.insert(0, os.path.dirname(args.manifest))

    if 'topo_module' in conf:
        topo_module = importlib.import_module(conf['topo_module'])
        AppTopo = topo_module.CustomAppTopo

    if 'controller_module' in conf:
        controller_module = importlib.import_module(conf['controller_module'])
        AppController = controller_module.CustomAppController

    if 'procrunner_module' in conf:
        procrunner_module = importlib.import_module(conf['procrunner_module'])
        AppProcRunner = procrunner_module.CustomAppProcRunner

    if not os.path.isdir(args.log_dir):
        if os.path.exists(args.log_dir): raise Exception('Log dir exists and is not a dir')
        os.mkdir(args.log_dir)
    os.environ['P4APP_LOGDIR'] = args.log_dir


    def formatLatency(lat):
        if isinstance(lat, (str, unicode)): return formatParams(lat)
        else: return str(lat) + "ms"

    if 'links' not in conf: conf['links'] = []
    if 'latencies' not in conf: conf['latencies'] = {}

    conf['latencies'].update(dict((tuple(sorted(l[:2])), formatLatency(l[2])) for l in conf['links'] if len(l)==3))
    conf['links'] = [l[:2] for l in conf['links']]

    for host_name in sorted(conf['hosts'].keys()):
        host = conf['hosts'][host_name]
        if 'latency' not in host: continue
        for l in conf['links']:
            if host_name not in l: continue
            conf['latencies'][tuple(sorted(l))] = formatLatency(host['latency'])


    bmv2_log = args.bmv2_log or ('bmv2_log' in conf and conf['bmv2_log'])
    pcap_dump = args.pcap_dump or ('pcap_dump' in conf and conf['pcap_dump'])

    topo = AppTopo(manifest=manifest, target=args.target)
    switchClass = configureP4Switch(
            sw_path=args.behavioral_exe,
            json_path=args.json,
            log_console=bmv2_log,
            pcap_dump=pcap_dump)
    net = Mininet(topo = topo,
                  link = TCLink,
                  host = P4Host,
                  switch = switchClass,
                  controller = None)

    controller = None
    if args.auto_control_plane or 'controller_module' in conf:
        controller = AppController(manifest=manifest, target=args.target,
                                     topo=topo, net=net, cli_path=args.cli_path)

    net.start()

    sleep(1)

    if controller: controller.start()


    for h in net.hosts:
        h.describe()

    if args.cli or ('cli' in conf and conf['cli']):
        CLI(net)

    proc_runner = AppProcRunner(manifest=manifest, target=args.target,
                                    topo=topo, net=net, log_dir=args.log_dir)

    proc_runner.runall()

    if controller: controller.stop()

    net.stop()

    if pcap_dump:
        os.system('bash -c "cp *.pcap \'%s\'"' % args.log_dir)

    if proc_runner.hadError(): sys.exit(1)

if __name__ == '__main__':
    setLogLevel( 'info' )
    main()
