from p4app import P4Mininet
from mininet.topo import SingleSwitchTopo
from mininet.cli import CLI

topo = SingleSwitchTopo(2)
net = P4Mininet(program='wire.p4', topo=topo)
net.start()

#CLI(net)

h1 = net.get('h1')
proc = h1.popen('ping -c2 ' + net.get('h2').intfs[0].ip)
stdout, stderr = proc.communicate()
print stdout, stderr
assert proc.returncode == 0
