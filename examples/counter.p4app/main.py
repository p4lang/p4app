from p4app import P4Mininet
from mininet.topo import SingleSwitchTopo
import struct

N = 2
TABLE_NAME = 'MyIngress.egress_port_stats_counting_table'
MATCH_FIELD = 'standard_metadata.egress_spec'
ACTION_NAME = 'MyIngress.count_egress_spec'

topo = SingleSwitchTopo(N)
net = P4Mininet(program='counter.p4', topo=topo)
net.start()

table_entries = []
for i in range(1, N+1):
    table_entries.append(dict(table_name=TABLE_NAME,
                              match_fields={MATCH_FIELD: [i]},
                              action_name=ACTION_NAME,
                              action_params={}))

s1 = net.get('s1')

for table_entry in table_entries:
    s1.insertTableEntry(table_entry)

net.pingAll()

for port in range(1, N+1):
    packet_count, byte_count = s1.readCounter('ingressPortCounter', port)
    print("ingressPortCounter value for port {} : ".format(port) +\
          "{} packets, {} bytes".format(packet_count, byte_count))
    assert packet_count == 2

for match_values, packet_count, byte_count \
  in s1.readDirectCounter('MyIngress.egress_port_stats_counting_table'):
    egress_port = struct.unpack(">B", match_values[0])[0]
    print("egressPortDirectCounter value for port {} : ".format(egress_port) +\
          "{} packets, {} bytes".format(packet_count, byte_count))
    assert packet_count == 2

print("OK")
