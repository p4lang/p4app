from p4app import P4Mininet
from mininet.topo import Topo

n = 3
mgid = 10

class SingleSwitchTopo(Topo):
    def __init__(self, n, **opts):
        Topo.__init__(self, **opts)

        sw = self.addSwitch('s1')

        for i in xrange(1, n+1):
            host = self.addHost('h%d' % i,
                                ip = "10.0.0.%d" % i,
                                mac = '00:00:00:00:00:%02x' % i)
            self.addLink(host, sw, port2=i)

topo = SingleSwitchTopo(n)
net = P4Mininet(program='multicast.p4', topo=topo)
net.start()

sw = net.get('s1')

for i in range(1, n+1):
    h = net.get('h%d' % i)
    h.cmd('arp -s 10.0.0.255 ff:ff:ff:ff:ff:ff')

    sw.insertTableEntry(table_name='MyIngress.ipv4_lpm',
                        match_fields={'hdr.ipv4.dstAddr': ["10.0.0.%d" % i, 32]},
                        action_name='MyIngress.set_egr',
                        action_params={'port': i})
    sw.insertTableEntry(table_name='MyEgress.send_frame',
                        match_fields={'standard_metadata.egress_port': i},
                        action_name='MyEgress.rewrite_dst',
                        action_params={'mac': '00:00:00:00:00:%02x' % i,
                                        'ip': '10.0.0.%d' % i})

sw.insertTableEntry(table_name='MyIngress.ipv4_lpm',
                    match_fields={'hdr.ipv4.dstAddr': ["10.0.0.255", 32]},
                    action_name='MyIngress.set_mgid',
                    action_params={'mgid': mgid})

sw.addMulticastGroup(mgid=mgid, ports=range(1, n+1))

loss = net.pingAll()
assert loss == 0

# Should receive a pong from h2 and h3 (i.e. a duplicate pong).
out = net.get('h1').cmd('ping -c2 10.0.0.255')
print out
assert 'from 10.0.0.3' in out
assert 'from 10.0.0.2' in out

# Update group. Should only receive a pong from h2.
sw.updateMulticastGroup(mgid=mgid, ports=[2])
out = net.get('h1').cmd('ping -c2 10.0.0.255')
assert 'from 10.0.0.2' in out
assert 'from 10.0.0.3' not in out

# Delete group. Packets should not be forwarded.
sw.deleteMulticastGroup(mgid=mgid, ports=[])
out = net.get('h1').cmd('ping -W1 -c2 10.0.0.255')
assert '0 received, 100% packet loss' in out

print "OK"
