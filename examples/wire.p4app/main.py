from p4app import P4Mininet
from mininet.topo import SingleSwitchTopo

topo = SingleSwitchTopo(2)
net = P4Mininet(program='wire.p4', topo=topo)
net.start()

loss = net.pingAll()
assert loss == 0

print "OK"
