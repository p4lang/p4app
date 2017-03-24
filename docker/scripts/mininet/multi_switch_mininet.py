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
from time import sleep

from mininet.net import Mininet
from mininet.topo import Topo
from mininet.link import TCLink
from mininet.log import setLogLevel, info
from mininet.cli import CLI

from p4_mininet import P4Switch, P4Host

from shortest_path import ShortestPath

parser = argparse.ArgumentParser(description='Mininet demo')
parser.add_argument('--behavioral-exe', help='Path to behavioral executable',
                    type=str, action="store", required=True)
parser.add_argument('--thrift-port', help='Thrift server port for table updates',
                    type=int, action="store", default=9090)
parser.add_argument('--bmv2-log', help='verbose messages in log file', action="store_true")
parser.add_argument('--cli', help="start the mininet cli", action="store_true")
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


def configureP4Switch(**switch_args):
    class ConfiguredP4Switch(P4Switch):
        def __init__(self, *opts, **kwargs):
            global next_thrift_port
            kwargs.update(switch_args)
            kwargs['thrift_port'] = next_thrift_port
            next_thrift_port += 1
            P4Switch.__init__(self, *opts, **kwargs)
    return ConfiguredP4Switch


class MultiSwitchTopo(Topo):

    def __init__(self, links, latencies={}, **opts):
        Topo.__init__(self, **opts)

        nodes = sum(map(list, zip(*links)), [])
        host_names = sorted(list(set(filter(lambda n: n[0] == 'h', nodes))))
        sw_names = sorted(list(set(filter(lambda n: n[0] == 's', nodes))))
        sw_ports = dict([(sw, []) for sw in sw_names])

        self._host_links = {}
        self._sw_links = dict([(sw, {}) for sw in sw_names])

        for sw_name in sw_names:
            self.addSwitch(sw_name)

        for host_name in host_names:
            host_num = int(host_name[1:])

            host_ip = "10.0.%d.10" % host_num
            host_mac = '00:04:00:00:00:%02x' % host_num

            self.addHost(host_name, ip=host_ip+'/24', mac=host_mac)

            host_links = filter(lambda l: l[0]==host_name or l[1]==host_name, links)
            assert len(host_links) == 1, "Host sholud be connected to exactly one switch, not " + str(host_links)
            link = host_links[0]
            sw = link[0] if link[0] != host_name else link[1]
            sw_num = int(sw[1:])
            assert sw[0]=='s', "Hosts should be connected to switches, not " + str(s)

            delay_key = ''.join([host_name, sw])
            delay = latencies[delay_key] if delay_key in latencies else 0
            self.addLink(host_name, sw, delay="%dms"%delay)
            sw_ports[sw].append(host_name)
            self._host_links[host_name] = dict(
                    host_mac = host_mac,
                    host_ip = host_ip,
                    sw = sw,
                    sw_mac = "00:aa:00:%02x:00:%02x" % (sw_num, host_num),
                    sw_ip = "10.0.%d.1" % host_num,
                    sw_port = sw_ports[sw].index(host_name)+1
                    )

        for link in links: # only check switch-switch links
            sw1, sw2 = link
            if sw1[0] != 's' or sw2[0] != 's': continue

            delay_key = ''.join(sorted([host_name, sw]))
            delay = latencies[delay_key] if delay_key in latencies else 0
            self.addLink(sw1, sw2, delay="%dms"%delay)
            sw_ports[sw1].append(sw2)
            sw_ports[sw2].append(sw1)

            sw1_num, sw2_num = int(sw1[1:]), int(sw2[1:])
            sw1_port = dict(mac="00:aa:00:%02x:%02x:00" % (sw1_num, sw2_num), port=sw_ports[sw1].index(sw2)+1)
            sw2_port = dict(mac="00:aa:00:%02x:%02x:00" % (sw2_num, sw1_num), port=sw_ports[sw2].index(sw1)+1)

            self._sw_links[sw1][sw2] = [sw1_port, sw2_port]
            self._sw_links[sw2][sw1] = [sw2_port, sw1_port]

def read_entries(filename):
    entries = []
    with open(filename, 'r') as f:
        for line in f:
            line = line.strip()
            if line == '': continue
            entries.append(line)
    return entries


def add_entries(thrift_port=9090, sw=None, entries=None):
    assert entries
    if sw: thrift_port = sw.thrift_port

    print '\n'.join(entries)
    p = subprocess.Popen(['simple_switch_CLI', '--json', args.json, '--thrift-port', str(thrift_port)], stdin=subprocess.PIPE)
    p.communicate(input='\n'.join(entries))


def run_control_plane(conf, topo, net, shortestpath):
    entries = {}
    for sw in topo.switches():
        entries[sw] = []
        if 'switches' in conf and sw in conf['switches'] and 'entries' in conf['switches'][sw]:
            extra_entries = conf['switches'][sw]['entries']
            if type(extra_entries) == list: # array of entries
                entries[sw] += extra_entries
            else: # path to file that contains entries
                entries[sw] += read_entries(extra_entries)
        entries[sw] += [
            'table_set_default send_frame _drop',
            'table_set_default forward _drop',
            'table_set_default ipv4_lpm _drop']

        
    for host_name in topo._host_links:
        link = topo._host_links[host_name]
        h = net.get(host_name)
        h.setARP(link['sw_ip'], link['sw_mac'])
        h.setDefaultRoute("via %s" % link['sw_ip'])
        sw = link['sw']
        entries[sw].append('table_add send_frame rewrite_mac %d => %s' % (link['sw_port'], link['sw_mac']))
        entries[sw].append('table_add forward set_dmac %s => %s' % (link['host_ip'], link['host_mac']))
        entries[sw].append('table_add ipv4_lpm set_nhop %s/32 => %s %d' % (link['host_ip'], link['host_ip'], link['sw_port']))

    for h in net.hosts:
        for sw in net.switches:
            path = shortestpath.get(sw.name, h.name)
            if not path: continue
            if not path[1][0] == 's': continue # next hop is a switch
            sw_link = topo._sw_links[sw.name][path[1]]
            h_link = topo._host_links[h.name]
            entries[sw.name].append('table_add send_frame rewrite_mac %d => %s' % (sw_link[0]['port'], sw_link[0]['mac']))
            entries[sw.name].append('table_add forward set_dmac %s => %s' % (h_link['host_ip'], sw_link[1]['mac']))
            entries[sw.name].append('table_add ipv4_lpm set_nhop %s/32 => %s %d' % (h_link['host_ip'], h_link['host_ip'], sw_link[0]['port']))

    for sw_name in entries:
        sw = net.get(sw_name)
        add_entries(sw=sw, entries=entries[sw_name])



def main():

    with open(args.manifest, 'r') as f:
        manifest = json.load(f)

    conf = manifest['targets'][args.target]

    if not os.path.isdir(args.log_dir):
        if os.path.exists(args.log_dir): raise Exception('Log dir exists and is not a dir')
        os.mkdir(args.log_dir)


    links = [l[:2] for l in conf['links']]
    latencies = dict([(''.join(sorted(l[:2])), l[2]) for l in conf['links'] if len(l)==3])

    bmv2_log = args.bmv2_log or ('bmv2_log' in conf and conf['bmv2_log'])
    pcap_dump = args.pcap_dump or ('pcap_dump' in conf and conf['pcap_dump'])
    
    topo = MultiSwitchTopo(links, latencies)
    switchClass = configureP4Switch(
            sw_path=args.behavioral_exe,
            json_path=args.json,
            log_console=args.bmv2_log,
            pcap_dump=args.pcap_dump)
    net = Mininet(topo = topo,
                  link = TCLink,
                  host = P4Host,
                  switch = switchClass,
                  controller = None)
    net.start()

    sleep(1)

    shortestpath = ShortestPath(links)

    if args.auto_control_plane: run_control_plane(conf, topo, net, shortestpath)

            
    for h in net.hosts:
        h.describe()

    if args.cli or ('cli' in conf and conf['cli']):
        CLI(net)

    stdout_files = dict()
    return_codes = []
    host_procs = []


    def formatCmd(cmd):
        params = conf['parameters'] if 'parameters' in conf else {}
        for param in params:
            cmd = cmd.replace('%'+param+'%', str(params[param]))
        cmd = cmd.replace('%log_dir%', args.log_dir)
        for h in net.hosts:
            cmd = cmd.replace(h.name, h.defaultIntf().updateIP())
        return cmd

    def _wait_for_exit(p, host):
        print p.communicate()
        if p.returncode is None:
            p.wait()
            print p.communicate()
        return_codes.append(p.returncode)
        if host_name in stdout_files:
            stdout_files[host_name].flush()
            stdout_files[host_name].close()

    for host_name in sorted(conf['hosts'].keys()):
        host = conf['hosts'][host_name]
        if 'cmd' not in host: continue

        h = net.get(host_name)
        stdout_filename = os.path.join(args.log_dir, h.name + '.stdout')
        stdout_files[h.name] = open(stdout_filename, 'w')
        cmd = formatCmd(host['cmd'])
        print h.name, cmd
        p = h.popen(cmd, stdout=stdout_files[h.name])
        if 'startup_sleep' in host: sleep(host['startup_sleep'])

        if 'wait' in host and host['wait']:
            _wait_for_exit(p, host_name)
        else:
            host_procs.append((p, host_name))

    for p, host_name in host_procs:
        if 'wait' in conf['hosts'][host_name] and conf['hosts'][host_name]['wait']:
            _wait_for_exit(p, host_name)

    for p, host_name in host_procs:
        if 'wait' in conf['hosts'][host_name] and conf['hosts'][host_name]['wait']:
            continue
        if p.returncode is None:
            p.send_signal(signal.SIGINT)
            sleep(0.2)
            if p.returncode is None: p.kill()
            print p.communicate()
            return_codes.append(p.returncode)

    net.stop()

    if bmv2_log:
        os.system('bash -c "cp /tmp/p4s.s*.log \'%s\'"' % args.log_dir)
    if pcap_dump:
        os.system('bash -c "cp *.pcap \'%s\'"' % args.log_dir)

    bad_codes = [rc for rc in return_codes if rc != 0]
    if len(bad_codes): sys.exit(1)

if __name__ == '__main__':
    setLogLevel( 'info' )
    main()
