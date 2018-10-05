from p4app import P4Mininet, P4Program
from mininet.topo import SingleSwitchTopo

topo = SingleSwitchTopo(2)
prog = P4Program('wire14.p4', version=14)
net = P4Mininet(program=prog, topo=topo)
net.start()

h1 = net.get('h1')
proc = h1.popen('ping -c2 ' + net.get('h2').intfs[0].ip)
stdout, stderr = proc.communicate()
print stdout, stderr
assert proc.returncode == 0

print "OK"
