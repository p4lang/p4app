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

from mininet.net import Mininet
from mininet.node import Switch, Host
from mininet.log import setLogLevel, info, error, debug
from mininet.moduledeps import pathCheck
from sys import exit
import os
import tempfile
import socket
from time import sleep
import subprocess

import grpc
import p4runtime_lib.bmv2
import p4runtime_lib.helper
from p4runtime_lib.error_utils import printGrpcError

from netstat import check_listening_on_port

SWITCH_START_TIMEOUT = 10 # seconds

def tableEntryToString(flow):
    if 'match' in flow:
        match_str = ['%s=%s' % (match_name, str(flow['match'][match_name])) for match_name in
                     flow['match']]
        match_str = ', '.join(match_str)
    elif 'default_action' in flow and flow['default_action']:
        match_str = '(default action)'
    else:
        match_str = '(any)'
    params = ['%s=%s' % (param_name, str(flow['action_params'][param_name])) for param_name in
              flow['action_params']]
    params = ', '.join(params)
    return "%s: %s => %s(%s)" % (
        flow['table'], match_str, flow['action_name'], params)

# object hook for josn library, use str instead of unicode object
# https://stackoverflow.com/questions/956867/how-to-get-string-objects-instead-of-unicode-from-json
def json_load_byteified(file_handle):
    return _byteify(json.load(file_handle, object_hook=_byteify),
                    ignore_dicts=True)
def _byteify(data, ignore_dicts=False):
    # if this is a unicode string, return its string representation
    if isinstance(data, unicode):
        return data.encode('utf-8')
    # if this is a list of values, return list of byteified values
    if isinstance(data, list):
        return [_byteify(item, ignore_dicts=True) for item in data]
    # if this is a dictionary, return dictionary of byteified keys and values
    # but only if we haven't already byteified it
    if isinstance(data, dict) and not ignore_dicts:
        return {
            _byteify(key, ignore_dicts=True): _byteify(value, ignore_dicts=True)
            for key, value in data.items()
        }
    # if it's anything else, return it in its original form
    return data

class P4Host(Host):
    def config(self, **params):
        r = super(Host, self).config(**params)

        self.defaultIntf().rename("eth0")

        for off in ["rx", "tx", "sg"]:
            cmd = "/sbin/ethtool --offload %s %s off" % (self.defaultIntf().name, off)
            self.cmd(cmd)

        # disable IPv6
        self.cmd("sysctl -w net.ipv6.conf.all.disable_ipv6=1")
        self.cmd("sysctl -w net.ipv6.conf.default.disable_ipv6=1")
        self.cmd("sysctl -w net.ipv6.conf.lo.disable_ipv6=1")

        return r

    def describe(self):
        print ("**********")
        print (self.name)
        print ("default interface: %s\t%s\t%s" %(
            self.defaultIntf().name,
            self.defaultIntf().IP(),
            self.defaultIntf().MAC()
        ))
        print ("**********")

class P4Switch(Switch):
    """P4 virtual switch"""
    device_id = 0

    def __init__(self, name, sw_path = None, json_path = None,
                 thrift_port = None,
                 pcap_dump = False,
                 log_console = False,
                 log_file = None,
                 verbose = False,
                 device_id = None,
                 enable_debugger = False,
                 **kwargs):
        Switch.__init__(self, name, **kwargs)
        assert(sw_path)
        assert(json_path)
        # make sure that the provided sw_path is valid
        pathCheck(sw_path)
        # make sure that the provided JSON file exists
        if not os.path.isfile(json_path):
            error("Invalid JSON file.\n")
            exit(1)
        self.sw_path = sw_path
        self.json_path = json_path
        self.verbose = verbose
        logfile = "/tmp/p4s.{}.log".format(self.name)
        self.output = open(logfile, 'w')
        self.thrift_port = thrift_port
        if check_listening_on_port(self.thrift_port):
            error('%s cannot bind port %d because it is bound by another process\n' % (self.name, self.grpc_port))
            exit(1)
        self.pcap_dump = pcap_dump
        self.enable_debugger = enable_debugger
        self.log_console = log_console
        if log_file is not None:
            self.log_file = log_file
        else:
            self.log_file = "/tmp/p4s.{}.log".format(self.name)
        if device_id is not None:
            self.device_id = device_id
            P4Switch.device_id = max(P4Switch.device_id, device_id)
        else:
            self.device_id = P4Switch.device_id
            P4Switch.device_id += 1
        self.nanomsg = "ipc:///tmp/bm-{}-log.ipc".format(self.device_id)

    @classmethod
    def setup(cls):
        pass

    def check_switch_started(self, pid):
        """While the process is running (pid exists), we check if the Thrift
        server has been started. If the Thrift server is ready, we assume that
        the switch was started successfully. This is only reliable if the Thrift
        server is started at the end of the init process"""
        while True:
            if not os.path.exists(os.path.join("/proc", str(pid))):
                return False
            if check_listening_on_port(self.thrift_port):
                return True
            sleep(0.5)

    def start(self, controllers):
        "Start up a new P4 switch"
        info("Starting P4 switch {}.\n".format(self.name))
        args = [self.sw_path]
        for port, intf in self.intfs.items():
            if not intf.IP():
                args.extend(['-i', str(port) + "@" + intf.name])
        if self.pcap_dump:
            args.append("--pcap %s" % self.pcap_dump)
        if self.thrift_port:
            args.extend(['--thrift-port', str(self.thrift_port)])
        if self.nanomsg:
            args.extend(['--nanolog', self.nanomsg])
        args.extend(['--device-id', str(self.device_id)])
        P4Switch.device_id += 1
        args.append(self.json_path)
        if self.enable_debugger:
            args.append("--debugger")
        if self.log_console:
            args.append("--log-console")
        info(' '.join(args) + "\n")

        pid = None
        with tempfile.NamedTemporaryFile() as f:
            # self.cmd(' '.join(args) + ' > /dev/null 2>&1 &')
            self.cmd(' '.join(args) + ' >' + self.log_file + ' 2>&1 & echo $! >> ' + f.name)
            pid = int(f.read())
        debug("P4 switch {} PID is {}.\n".format(self.name, pid))
        if not self.check_switch_started(pid):
            error("P4 switch {} did not start correctly.\n".format(self.name))
            exit(1)
        info("P4 switch {} has been started.\n".format(self.name))

    def stop(self):
        "Terminate P4 switch."
        self.output.flush()
        self.cmd('kill %' + self.sw_path)
        self.cmd('wait')
        self.deleteIntfs()

    def attach(self, intf):
        "Connect a data port"
        assert(0)

    def detach(self, intf):
        "Disconnect a data port"
        assert(0)

class P4RuntimeSwitch(P4Switch):
    "BMv2 switch with gRPC support"
    next_grpc_port = 50051
    next_thrift_port = 9090

    def __init__(self, name, sw_path = None,
                 enable_grpc = True,
                 grpc_port = None,
                 thrift_port = None,
                 pcap_dump = False,
                 log_console = False,
                 start_controller = True,
                 program = None,
                 verbose = False,
                 device_id = None,
                 enable_debugger = False,
                 cli_path = None,
                 log_file = None,
                 **kwargs):
        Switch.__init__(self, name, **kwargs)
        assert (sw_path)
        self.sw_path = sw_path
        # make sure that the provided sw_path is valid
        pathCheck(sw_path)

        self.cli_path = cli_path
        self.program = program
        self.enable_grpc = enable_grpc
        json_path = None
        p4info_path = None
        if self.program:
            json_path = self.program.json()
            if self.program.p4info():
                p4info_path = self.program.p4info()

        if json_path is not None:
            # make sure that the provided JSON file exists
            if not os.path.isfile(json_path):
                error("Invalid JSON file.\n")
                exit(1)
            self.json_path = json_path
        else:
            self.json_path = None

        if p4info_path is not None:
            if not os.path.isfile(p4info_path):
                error("Invalid P4Info file.\n")
                exit(1)
            self.p4info_path = p4info_path
        else:
            self.p4info_path = None

        self.grpc_port = grpc_port
        if self.enable_grpc and grpc_port is None:
            self.grpc_port = P4RuntimeSwitch.next_grpc_port
            P4RuntimeSwitch.next_grpc_port += 1

        if thrift_port is not None:
            self.thrift_port = thrift_port
        else:
            self.thrift_port = P4RuntimeSwitch.next_thrift_port
            P4RuntimeSwitch.next_thrift_port += 1

        if enable_grpc and check_listening_on_port(self.grpc_port):
            error('%s cannot bind port %d because it is bound by another process\n' % (self.name, self.grpc_port))
            exit(1)

        self.verbose = verbose
        logfile = "/tmp/p4app-logs/p4s.{}.log".format(self.name)
        self.output = open(logfile, 'w')
        self.pcap_dump = pcap_dump
        self.enable_debugger = enable_debugger
        self.log_console = log_console
        self.start_controller = start_controller
        if not self.program.supportsP4Runtime():
            self.start_controller = False
        self.sw_conn = None
        if log_file is not None:
            self.log_file = log_file
        else:
            self.log_file = logfile
        if device_id is not None:
            self.device_id = device_id
            P4Switch.device_id = max(P4Switch.device_id, device_id)
        else:
            self.device_id = P4Switch.device_id
            P4Switch.device_id += 1
        self.nanomsg = "ipc:///tmp/bm-{}-log.ipc".format(self.device_id)


    def check_switch_started(self, pid):
        for _ in range(SWITCH_START_TIMEOUT * 2):
            if not os.path.exists(os.path.join("/proc", str(pid))):
                return False
            if self.enable_grpc and check_listening_on_port(self.grpc_port):
                return True
            elif self.thrift_port and check_listening_on_port(self.thrift_port):
                return True
            sleep(0.5)

    def start(self, controllers):
        info("Starting P4 switch {}.\n".format(self.name))
        args = [self.sw_path]
        for port, intf in self.intfs.items():
            if not intf.IP():
                args.extend(['-i', str(port) + "@" + intf.name])
        if self.pcap_dump:
            args.append("--pcap %s" % self.pcap_dump)
        if self.nanomsg:
            args.extend(['--nanolog', self.nanomsg])
        args.extend(['--device-id', str(self.device_id)])
        P4Switch.device_id += 1
        if self.json_path:
            args.append(self.json_path)
        else:
            args.append("--no-p4")
        if self.enable_debugger:
            args.append("--debugger")
        if self.log_console:
            args.append("--log-console")
        if self.thrift_port:
            args.append('--thrift-port ' + str(self.thrift_port))
        if self.grpc_port:
            args.append("-- --grpc-server-addr 0.0.0.0:" + str(self.grpc_port))
        cmd = ' '.join(args)
        info(cmd + "\n")


        pid = None
        with tempfile.NamedTemporaryFile() as f:
            self.cmd(cmd + ' >' + self.log_file + ' 2>&1 & echo $! >> ' + f.name)
            pid = int(f.read())
        debug("P4 switch {} PID is {}.\n".format(self.name, pid))
        if not self.check_switch_started(pid):
            error("P4 switch {} did not start correctly.\n".format(self.name))
            exit(1)
        info("P4 switch {} has been started.\n".format(self.name))

        if self.start_controller:
            self.sw_conn = p4runtime_lib.bmv2.Bmv2SwitchConnection(
                    name=self.name,
                    address='127.0.0.1:' + str(self.grpc_port),
                    device_id=self.device_id,
                    proto_dump_file='/tmp/p4app-logs/' + self.name + '-p4runtime-requests.txt')

            try:
                self.sw_conn.MasterArbitrationUpdate()
            except grpc.RpcError as e:
                printGrpcError(e)

            if self.p4info_path:
                self.loadP4Info()
            self.loadJSON()

    def stop(self):
        if self.sw_conn: self.sw_conn.shutdown()
        P4Switch.stop(self)

    def commands(self, cmd_list):
        if not self.thrift_port:
            raise Exception("Switch %s doesn't use Thrift, so there's no CLI support" % self.name)
        print('\n'.join(cmd_list))
        p = subprocess.Popen([self.cli_path, '--thrift-port', str(self.thrift_port)], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        stdout, nostderr = p.communicate(input='\n'.join(cmd_list) + '\nEOF\n')
        print(stdout)
        raw_results = stdout.split('RuntimeCmd:')[1:len(cmd_list)+1]
        return raw_results

    def command(self, cmd):
        return self.commands([cmd])[0]

    def loadP4Info(self):
        self.p4info_helper = p4runtime_lib.helper.P4InfoHelper(self.p4info_path)

    def loadJSON(self):
        try:
            self.sw_conn.SetForwardingPipelineConfig(p4info=self.p4info_helper.p4info,
                    bmv2_json_file_path=self.json_path)
        except grpc.RpcError as e:
            printGrpcError(e)

    def loadConf(self, sw_conf_or_filename):
        if isinstance(sw_conf_or_filename, dict):
            sw_conf = sw_conf_or_filename
        else:
            conf_path = os.path.join('/p4app', sw_conf_or_filename)
            with open(conf_path, 'r') as f:
                sw_conf = json_load_byteified(f)

        if 'p4info' in sw_conf:
            info('Using P4Info file %s...' % sw_conf['p4info'])
            self.p4info_path = os.path.join('/tmp/p4app-logs/', sw_conf['p4info'])
            self.loadP4Info()

        assert sw_conf['target'] == 'bmv2'

        if 'bmv2_json' in sw_conf:
            info("Setting pipeline config (%s)..." % sw_conf['bmv2_json'])
            self.json_path = os.path.join('/tmp/p4app-logs/', sw_conf['bmv2_json'])
            self.loadJSON()

        if 'table_entries' in sw_conf:
            info("Inserting %d table entries..." % len(sw_conf['table_entries']))
            for entry in sw_conf['table_entries']:
                info(tableEntryToString(entry))
                self.insertTableEntry(entry)

    def insertTableEntry(self, entry=None,
                        table_name=None, match_fields=None, action_name=None,
                        default_action=None, action_params=None, priority=None):
        if entry is not None:
            table_name = entry['table_name']
            match_fields = entry.get('match_fields') # None if not found
            action_name = entry['action_name']
            default_action = entry.get('default_action') # None if not found
            action_params = entry['action_params']
            priority = entry.get('priority')  # None if not found

        table_entry = self.p4info_helper.buildTableEntry(
            table_name=table_name,
            match_fields=match_fields,
            default_action=default_action,
            action_name=action_name,
            action_params=action_params,
            priority=priority)
        try:
            self.sw_conn.WriteTableEntry(table_entry)
        except grpc.RpcError as e:
            printGrpcError(e)

    def removeTableEntry(self, entry=None,
                        table_name=None, match_fields=None, action_name=None,
                        default_action=None, action_params=None, priority=None):
        if entry is not None:
            table_name = entry['table_name']
            match_fields = entry.get('match_fields') # None if not found
            action_name = entry['action_name']
            default_action = entry.get('default_action') # None if not found
            action_params = entry['action_params']
            priority = entry.get('priority')  # None if not found

        table_entry = self.p4info_helper.buildTableEntry(
            table_name=table_name,
            match_fields=match_fields,
            default_action=default_action,
            action_name=action_name,
            action_params=action_params,
            priority=priority)
        try:
            self.sw_conn.DeleteTableEntry(table_entry)
        except grpc.RpcError as e:
            printGrpcError(e)


    def addMulticastGroup(self, mgid=None, ports=None):
        group = self.p4info_helper.buildMulticastGroup(mgid=mgid, ports=ports)
        try:
            self.sw_conn.CreateMulticastGroup(group)
        except grpc.RpcError as e:
            printGrpcError(e)

    def deleteMulticastGroup(self, mgid=None, ports=None):
        group = self.p4info_helper.buildMulticastGroup(mgid=mgid, ports=ports)
        try:
            self.sw_conn.DeleteMulticastGroup(group)
        except grpc.RpcError as e:
            printGrpcError(e)

    def updateMulticastGroup(self, mgid=None, ports=None):
        group = self.p4info_helper.buildMulticastGroup(mgid=mgid, ports=ports)
        try:
            self.sw_conn.UpdateMulticastGroup(group)
        except grpc.RpcError as e:
            printGrpcError(e)

    def printTableEntries(self):
        """
        Prints the table entries from all tables on the switch.
        :param p4info_helper: the P4Info helper
        :param sw: the switch connection
        """
        print('\n----- Reading tables rules for %s -----' % self.sw_conn.name)
        for response in self.sw_conn.ReadTableEntries():
            for entity in response.entities:
                entry = entity.table_entry
                table_name = self.p4info_helper.get_tables_name(entry.table_id)
                print ('%s: ' % table_name, end=' ')
                for m in entry.match:
                    print(self.p4info_helper.get_match_field_name(table_name, m.field_id), end=' ')
                    print('%r' % (self.p4info_helper.get_match_field_value(m),), end=' ')
                action = entry.action.action
                action_name = self.p4info_helper.get_actions_name(action.action_id)
                print('->', action_name, end=' ')
                for p in action.params:
                    print(self.p4info_helper.get_action_param_name(action_name, p.param_id), end=' ')
                    print('%r' % p.value, end=' ')
                print()

    def readCounter(self, counter_name, index):
        """
        Reads the specified counter at the specified index from the switch.

        :param counter_name: the name of the counter from the P4 program
        :param index: the counter index
        """
        for response in self.sw_conn.ReadCounters(self.p4info_helper.get_counters_id(counter_name), index):
            for entity in response.entities:
                counter = entity.counter_entry
                return counter.data.packet_count, counter.data.byte_count

    def readDirectCounter(self, table_name):
        for response in self.sw_conn.ReadDirectCounters(self.p4info_helper.get_tables_id(table_name)):
            for entity in response.entities:
                entry = entity.table_entry
                match_values = []
                for m in entry.match:
                    match_values.append(self.p4info_helper.get_match_field_value(m))
                counter = entry.counter_data
                yield match_values, counter.packet_count, counter.byte_count
