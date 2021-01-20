from p4app import P4Mininet
from mininet.topo import SingleSwitchTopo

topo = SingleSwitchTopo(2)
net = P4Mininet(program='counter.p4', topo=topo)
net.start()

net.pingAll()

s1 = net.get('s1')

for port in [1, 2]:
    packet_count, byte_count = s1.readCounter('ingressPortCounter', port)
    assert packet_count == 2

print("OK")
