from p4app import P4Mininet
from mininet.topo import Topo
from camus import CamusApp

n = 3

class RingTopo(Topo):
    def __init__(self, n, **opts):
        Topo.__init__(self, **opts)

        switches = []

        for i in xrange(1, n+1):
            host = self.addHost('h%d' % i,
                                ip = "10.0.0.%d" % i,
                                mac = '00:00:00:00:00:%02x' % i)
            switch = self.addSwitch('s%d' % i)
            self.addLink(host, switch, port2=1)
            switches.append(switch)

        # Port 2 connects to the next switch in the ring, and port 3 to the previous
        for i in xrange(n):
            self.addLink(switches[i], switches[(i+1)%n], port1=2, port2=3)

topo = RingTopo(n)
net = P4Mininet(program='itch.p4', topo=topo)
net.start()

for i in range(1, n+1):
    sw = net.get('s%d'% i)

    # Forward to the host connected to this switch
    sw.insertTableEntry(table_name='MyIngress.ipv4_lpm',
                        match_fields={'hdr.ipv4.dstAddr': ["10.0.0.%d" % i, 32]},
                        action_name='MyIngress.ipv4_forward',
                        action_params={'dstAddr': '00:00:00:00:00:%02x' % i,
                                          'port': 1})

    # Otherwise send the packet clockwise
    sw.insertTableEntry(table_name='MyIngress.ipv4_lpm',
                        default_action=True,
                        action_name='MyIngress.ipv4_forward',
                        action_params={'dstAddr': '00:00:00:00:00:00', # the last hop will set this correctly
                                          'port': 2})


net.pingAll()

itch_app = CamusApp('spec.p4')
itch_app.generateQueryPipeline('itch_camus.p4')

rules = ['add_order.shares = 1: fwd(1);',
         'add_order.price = 2: fwd(2);',
         'add_order.shares = 3 and add_order.price = 4: fwd(3);',
         'add_order.shares > 100 and add_order.stock = "BFN": fwd(2);']

runtime_config = itch_app.compileRules(rules=rules)

print runtime_config.mcastGroups()
print runtime_config.p4runtime()
