from p4app import P4Mininet
from mininet.topo import SingleSwitchTopo

topo = SingleSwitchTopo(2)
net = P4Mininet(program='recirc.p4', topo=topo)
net.start()
h1 = net.get('h1')

# Send one ICMP packet (timeout after 2 seconds)
out = h1.cmd('ping -c1 -W2 10.0.0.2')

print(out)
assert "ttl=0" in out, "The switch should decrement the IP ttl field"

print("OK")
