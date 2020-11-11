from p4app import P4Mininet
from mininet.topo import SingleSwitchTopo

topo = SingleSwitchTopo(2)
net = P4Mininet(program='registers.p4', topo=topo)
net.start()

h1 = net.get('h1')

out = h1.cmd('./send.py 10.0.0.2 write 1 4')
assert out.strip() == "1 4"

out = h1.cmd('./send.py 10.0.0.2 write 1 5')
assert out.strip() == "1 5"

out = h1.cmd('./send.py 10.0.0.2 read 1')
assert out.strip() == "1 5"

out = h1.cmd('./send.py 10.0.0.2 write 2 11')
assert out.strip() == "2 11"

# XXX GRPC errors with "Register reads are not supported yet"
# TODO: test this once there's support for reading registers with p4runtime
#s1 = net.get('s1')
#print("about to read reg")
#print(s1.readRegister('myReg', 1))

print("OK")
