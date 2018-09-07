from p4app import P4Mininet
from mininet.topolib import TreeTopo
from mininet.cli import CLI

topo = TreeTopo(depth=2, fanout=2)

net = P4Mininet(program='wire.p4', topo=topo)
net.start()

h1 = net.get('h1')
proc = h1.popen('ping -c2 10.0.0.2'.split())
stdout, stderr = proc.communicate()
print stdout, stderr
assert proc.returncode == 0


#CLI(net)
