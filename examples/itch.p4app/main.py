from p4app import P4Mininet
from camus import CamusApp
from camus_topo import SingleSwitchTopo, FatTreeTopo, getPort
import subprocess
import sys
import time

K = 4

itch_app = CamusApp('spec.p4', ingress_name='MyIngress')
itch_app.generateQueryPipeline('itch_camus.p4')

topo = FatTreeTopo(K)
topo.subscribe('h_0_0_0', 'add_order.shares = 1')
topo.subscribe('h_0_0_1', 'add_order.price = 2')
topo.subscribe('h_2_1_0', 'add_order.stock = "GOOGL"')

net = P4Mininet(program='itch.p4', topo=topo)
net.start()


# Core switches should forward all traffic down
for core in range(topo.core_count):
    sw = net.get('cs_%d' % core)
    sw.insertTableEntry(table_name='MyIngress.packet_direction',
                        default_action=True,
                        action_name='MyIngress.direction_is_down')

non_core_switches = [(t, pod, x) for t in ['as', 'es'] for pod in range(topo.pod_count) for x in range(topo.edge_count/topo.pod_count)]

# Add rules for detecting whether a packet is going up or down the tree
for sw_type,pod,x in non_core_switches:
    sw = net.get('%s_%d_%d' % (sw_type, pod, x))
    port = None
    for sw2 in topo.upstream_for_sw[sw.name]:
        link = topo.linkInfo(sw.name, sw2)
        port = getPort(link, sw.name)
        sw.insertTableEntry(table_name='MyIngress.packet_direction',
                            match_fields={'standard_metadata.ingress_port': port},
                            action_name='MyIngress.direction_is_down')

    if port is not None:
        sw.insertTableEntry(table_name='MyIngress.forward_up',
                            default_action=True,
                            action_name='MyIngress.ipv4_forward',
                            action_params={'port': port})



hosts = [(pod, edge, host) for pod in range(K) for edge in range(K/2) for host in range(K/2)]

# IPv4 routing
for pod,edge,host in hosts:
    hops = []
    host_name = 'h_%d_%d_%d'% (pod, edge, host)

    edge_sw = net.get('es_%d_%d' % (pod, edge))
    edge_port = getPort(topo.linkInfo(edge_sw.name, host_name), edge_sw.name)
    hops.append((edge_sw, edge_port))

    for aggr in range(topo.aggr_count / topo.pod_count):
        aggr_sw = net.get('as_%d_%d' % (pod, aggr))
        port = getPort(topo.linkInfo(edge_sw.name, aggr_sw.name), aggr_sw.name)
        hops.append((aggr_sw, port))

        for core in range((K/2)*aggr, (K/2)*(aggr+1)):
            core_sw = net.get('cs_%d' % core)
            port = getPort(topo.linkInfo(aggr_sw.name, core_sw.name), core_sw.name)
            hops.append((core_sw, port))

    edge_sw.insertTableEntry(table_name='MyEgress.rewrite_dst',
                        match_fields={'standard_metadata.egress_port': edge_port},
                        action_name='MyEgress.set_dst',
                        action_params={'mac': '00:00:00:%02x:%02x:%02x' % (pod, edge, host+1),
                                       'ip': '10.%d.%d.%d' % (pod, edge, host+1)})

    for sw,port in hops:
        sw.insertTableEntry(table_name='MyIngress.ipv4_lpm',
                            match_fields={'hdr.ipv4.dstAddr': ["10.%d.%d.%d" % (pod, edge, host+1), 32]},
                            action_name='MyIngress.ipv4_forward',
                            action_params={'port': port})



# Compile rules and install them on each switch
for sw_name in topo.switches():
    rules = topo.rules_for_sw[sw_name]
    if not rules: continue

    runtime_config = itch_app.compileRules(rules=rules, ingress_name='MyIngress')

    sw = net.get(sw_name)
    for entry in runtime_config.entries():
        sw.insertTableEntry(**entry)
    for mgid,ports in runtime_config.mcastGroups().iteritems():
        sw.addMulticastGroup(mgid=mgid, ports=ports)


#net.pingAll()

h1, h2, h3, h4 = net.get('h_0_0_0'), net.get('h_0_0_1'), net.get('h_2_1_0'), net.get('h_3_1_1')

subscriber1 = h1.popen('./subscriber.py 1234', stdout=sys.stdout, stderr=sys.stdout)
subscriber2 = h2.popen('./subscriber.py 1234', stdout=sys.stdout, stderr=sys.stdout)
subscriber3 = h3.popen('./subscriber.py 1234', stdout=sys.stdout, stderr=sys.stdout)
time.sleep(0.4)

h4.cmd('./publisher.py 10.255.255.255 1234')
time.sleep(0.4)

subscriber1.terminate()
subscriber2.terminate()
subscriber3.terminate()
