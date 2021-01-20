from mininet.topo import Topo

def getPort(link, node): return link['port1'] if link['node1'] == node else link['port2']

class CamusTopo(Topo):
    """ Abstract topology routing using Camus.
        Assumes that each host is connected to exactly one switch.
    """

    def __init__(self, **opts):
        Topo.__init__(self, **opts)
        self.subscriptions_for_sw = {}
        self.rules_for_sw = {}

    def hostSwitch(self, host):
        """ Return edge switch to which `host` is connected """
        for a,b in self.links():
            if host == a and self.isSwitch(b):
                return b
            if host == b and self.isSwitch(a):
                return a
        raise Exception("Could not find a link to any switch from host %s" % host)

    def switchPortForHost(self, host):
        """ Return the switch port to which `host` is connected """
        switch = self.hostSwitch(host)
        return getPort(self.linkInfo(host, switch), switch)

    def subscribe(self, host, queries):
        if isinstance(queries, str):
            queries = [queries]

        switch = self.hostSwitch(host)
        self.addSubscriptionRec(host, queries, switch, self.linkInfo(host, switch))

    def addSubscriptionRec(self, host, queries, switch, down_link):
        raise NotImplementedError()


class SingleSwitchTopo(CamusTopo):
    def __init__(self, n, **opts):
        CamusTopo.__init__(self, **opts)

        switch = self.addSwitch('s1')
        self.rules_for_sw['s1'] = []

        for i in xrange(1, n+1):
            host = self.addHost('h%d' % i,
                                ip = "10.0.0.%d" % i,
                                mac = '00:00:00:00:00:%02x' % i)
            self.addLink(host, switch, port2=i)

    def addSubscriptionRec(self, host, queries, switch, down_link):
        port = getPort(down_link, switch)
        for q in queries:
            self.rules_for_sw[switch].append('%s: fwd(%d);' % (q, port))


# Based on https://github.com/howar31/MiniNet/blob/master/topo-fat-tree.py
class FatTreeTopo(CamusTopo):

    def __init__(self, K, **opts):
        CamusTopo.__init__(self, **opts)

        self.pod_count = K
        self.core_count = (K/2) ** 2
        self.aggr_count = (K/2) * K
        self.edge_count = (K/2) * K

        self.upstream_for_sw = {}

        for core in range(int(self.core_count)):
            core_sw = 'cs_%d' % core
            self.addSwitch(core_sw)
            self.upstream_for_sw[core_sw] = []

        for pod in range(int(self.pod_count)):

            for aggr in range(int(self.aggr_count / self.pod_count)):
                aggr_sw = self.addSwitch('as_%d_%d' % (pod, aggr))
                self.upstream_for_sw[aggr_sw] = []
                for core in range(int((K/2)*aggr), int((K/2)*(aggr+1))):
                    core_sw = 'cs_%d' % core
                    self.addLink(aggr_sw, core_sw)
                    self.upstream_for_sw[aggr_sw].append(core_sw)

            for edge in range(int(self.edge_count / self.pod_count)):
                edge_sw = self.addSwitch('es_%d_%d' % (pod, edge))
                self.upstream_for_sw[edge_sw] = []
                for aggr in range(int(self.edge_count / self.pod_count)):
                    aggr_sw = 'as_%d_%d' % (pod, aggr)
                    self.addLink(edge_sw, aggr_sw)
                    self.upstream_for_sw[edge_sw].append(aggr_sw)

                for h in range(int(K/2)):
                    host = self.addHost('h_%d_%d_%d' % (pod, edge, h),
                                            ip = '10.%d.%d.%d' % (pod, edge, h+1),
                                            mac = '00:00:00:%02x:%02x:%02x' % (pod, edge, h+1))
                    self.addLink(edge_sw, host)


        for sw in self.switches():
            self.rules_for_sw[sw] = []


    def addSubscriptionRec(self, host, queries, switch, down_link):
        port = getPort(down_link, switch)
        for q in queries:
            self.rules_for_sw[switch].append('%s: fwd(%d);' % (q, port))
        for sw2 in self.upstream_for_sw[switch]:
            self.addSubscriptionRec(host, queries, sw2, self.linkInfo(switch, sw2))
