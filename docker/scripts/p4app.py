from mininet.net import Mininet
from mininet.topo import Topo, SingleSwitchTopo

from p4_mininet import P4Host, P4RuntimeSwitch
from p4_program import P4Program

class P4AppConfig:
    def __init__(self):
        self.simple_switch_path = 'simple_switch'
        self.simple_switch_grpc_path = 'simple_switch_grpc'
        self.bmv2_log = True
        self.log_dir = '/tmp/p4app-logs'
        self.pcap_dump = self.log_dir

config = P4AppConfig()



def configureP4RuntimeSimpleSwitch(prog_or_filename, **switch_args):
    if isinstance(prog_or_filename, P4Program):
        prog = prog_or_filename
    else:
        prog = P4Program(prog_or_filename)

    class ConfiguredP4RuntimeSwitch(P4RuntimeSwitch):
        def __init__(self, *opts, **kwargs):

            kwargs2 = dict(
                sw_path=config.simple_switch_grpc_path,
                log_console=config.bmv2_log,
                program=prog,
                pcap_dump=config.pcap_dump,
                )
            kwargs2.update(switch_args)
            kwargs2.update(kwargs)
            P4RuntimeSwitch.__init__(self, *opts, **kwargs2)

        def describe(self):
            print "%s -> gRPC port: %d" % (self.name, self.grpc_port)
    return ConfiguredP4RuntimeSwitch

class P4Mininet(Mininet):
    def __init__(self, *args, **kwargs):
        if 'controller' not in kwargs:
            kwargs['controller'] = None
        if 'host' not in kwargs:
            kwargs['host'] = P4Host
        if 'topo' not in kwargs:
            kwargs['topo'] = SingleSwitchTopo(2)
        if 'program' not in kwargs:
            raise Exception("Must specify p4 program")

        start_controller = True
        if 'start_controller' in kwargs:
            start_controller = kwargs['start_controller']
            del kwargs['start_controller']

        enable_debugger = False
        if 'enable_debugger' in kwargs:
            enable_debugger = kwargs['enable_debugger']
            del kwargs['enable_debugger']

        if 'switch' not in kwargs:
            assert 'program' in kwargs
            prog_or_filename = kwargs['program']
            kwargs['switch'] = configureP4RuntimeSimpleSwitch(prog_or_filename,
                                                start_controller=start_controller,
                                                enable_debugger=enable_debugger)

        if 'program' in kwargs: del kwargs['program']

        self.auto_arp = True
        if 'auto_arp' in kwargs:
            self.auto_arp = kwargs['auto_arp']
            del kwargs['auto_arp']

        Mininet.__init__(self, *args, **kwargs)

    def start(self, *args, **kwargs):
        Mininet.start(self, *args, **kwargs)

        if self.auto_arp:
            self.setupARP()

    def setupARP(self):
        tbl = [(intf.ip, intf.mac) for h in self.hosts for intf in h.intfs.values()]
        for h in self.hosts:
            for intf in h.intfs.values():
                for ip, mac in tbl:
                    h.cmd('arp -i %s -s %s %s' % (intf.name, ip, mac))



