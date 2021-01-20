from p4app import P4Mininet
from mininet.topo import SingleSwitchTopo

N = 2

topo = SingleSwitchTopo(N)
net = P4Mininet(program='basic.p4', topo=topo)
net.start()

table_entries = []
for i in range(1, N+1):
    table_entries.append(dict(table_name='MyIngress.ipv4_lpm',
                        match_fields={'hdr.ipv4.dstAddr': ["10.0.0.%d" % i, 32]},
                        action_name='MyIngress.ipv4_forward',
                        action_params={'dstAddr': net.get('h%d'%i).intfs[0].MAC(),
                                          'port': i}))

sw = net.get('s1')
for table_entry in table_entries:
    sw.insertTableEntry(table_entry)

sw.printTableEntries()

loss = net.pingAll()
assert loss == 0

# Cleanup: remove table entries
for table_entry in table_entries:
    sw.removeTableEntry(table_entry)
sw.printTableEntries()

print("OK")
