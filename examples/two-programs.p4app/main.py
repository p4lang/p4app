from p4app import P4Mininet, P4Program
from mininet.topo import Topo

n = 3

basic_prog = P4Program('basic.p4')
wire_prog = P4Program('wire.p4')

class RingTopo(Topo):
    def __init__(self, n, **opts):
        Topo.__init__(self, **opts)

        switches = []

        for i in xrange(1, n+1):
            host = self.addHost('h%d' % i,
                                ip = "10.0.0.%d" % i,
                                mac = '00:00:00:00:00:%02x' % i)
            if i == 3:
                program = wire_prog  # switch s3 uses 'wire.p4'
            else:
                program = basic_prog # all other switches use 'basic.p4'

            switch = self.addSwitch('s%d' % i, program=program)
            self.addLink(host, switch, port2=1)
            switches.append(switch)

        # Port 2 connects to the next switch in the ring, and port 3 to the previous
        for i in xrange(n):
            self.addLink(switches[i], switches[(i+1)%n], port1=2, port2=3)

topo = RingTopo(n)
net = P4Mininet(program=basic_prog, topo=topo)
net.start()

for i in range(1, n+1):
    if i == 3: continue # skip s3, which uses 'wire.p4'

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


# h3 is unreachable because wire.p4 only forwards in the ring, so only test
# connectivity between h1 and h2:
net.pingPair()

print "OK"
