from p4app import P4Mininet
from mininet.topolib import TreeTopo

def printDot(topo): print 'digraph {\n' + '\n'.join('%s -> %s;' % l for l in topo.links()) + '\n}'

topo = TreeTopo(depth=2, fanout=2)

printDot(topo)

net = P4Mininet(program='basic.p4', topo=topo)
net.start()

s1, s2, s3 = net.get('s1'), net.get('s2'), net.get('s3')

# By default send the packet up
for sw in [s2, s3]:
    sw.insertTableEntry(table_name='MyIngress.ipv4_lpm',
                        default_action=True,
                        action_name='MyIngress.ipv4_forward',
                        action_params={'dstAddr': '00:00:00:00:00:00', # the last hop will set this correctly
                                          'port': 3})
def addForwardingRule(sw, host, port):
    sw.insertTableEntry(table_name='MyIngress.ipv4_lpm',
                        match_fields={'hdr.ipv4.dstAddr': ["10.0.0.%d" % host, 32]},
                        action_name='MyIngress.ipv4_forward',
                        action_params={'dstAddr': net.get('h%d' % host).intfs[0].mac,
                                          'port': port})
# Core switch s1 forwarding
for host, port in [(1, 1), (2, 1), (3, 2), (4, 2)]:
    addForwardingRule(s1, host, port)

# Edge switch s2
for host, port in [(1, 1), (2, 2)]:
    addForwardingRule(s2, host, port)

# Edge switch s3
for host, port in [(3, 1), (4, 2)]:
    addForwardingRule(s3, host, port)


loss = net.pingAll()
assert loss == 0

print "OK"
