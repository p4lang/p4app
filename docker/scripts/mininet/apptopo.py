from mininet.topo import Topo

class AppTopo(Topo):

    def __init__(self, manifest=None, target=None, **opts):
        Topo.__init__(self, **opts)

        self.manifest = manifest
        self.target = target
        self.conf = manifest['targets'][target]

        nodes = sorted(list(set(sum(map(list, zip(*self.conf['links'])), []))))
        host_names, sw_names = [], []
        for node in nodes:
            if node in self.conf['hosts']: host_names.append(node)
            elif node in self.conf['switches']: sw_names.append(node)
            elif node[0] == 'h': host_names.append(node)
            elif node[0] == 's': sw_names.append(node)
            else:
                raise Exception("Unknown node type: " + str(node))

        self._host_links = {}
        self._sw_links = dict([(sw, {}) for sw in sw_names])
        self._sw_hosts = dict([(sw, {}) for sw in sw_names])
        self._port_map = dict([(sw, {}) for sw in sw_names])

        for sw_name in sw_names:
            self.addSwitch(sw_name)

        for host_name in host_names:
            host_num = host_names.index(host_name)+1

            self.addHost(host_name)

            self._host_links[host_name] = {}
            host_links = filter(lambda l: l[0]==host_name or l[1]==host_name, self.conf['links'])

            sw_idx = 0
            for link in host_links:
                sw = link[0] if link[0] != host_name else link[1]
                assert sw in sw_names, "Hosts should be connected to switches, not " + str(sw)
                sw_num = sw_names.index(sw)+1

                host_mac = '00:04:00:00:%02x:%02x' % (host_num, sw_idx+1)

                delay_key = tuple(sorted([host_name, sw]))
                delay = self.conf['latencies'][delay_key] if delay_key in self.conf['latencies'] else '0ms'
                self._port_map[sw][host_name] = len(self._port_map[sw])+1
                self._host_links[host_name][sw] = dict(
                        idx=sw_idx,
                        host_mac = host_mac,
                        host_ip = "10.0.%d.%d" % (host_num, 100+sw_idx+1),
                        sw = sw,
                        sw_mac = "00:aa:00:%02x:00:%02x" % (sw_num, host_num),
                        sw_ip = "10.0.%d.%d" % (host_num, sw_idx+1),
                        sw_port = self._port_map[sw][host_name]
                        )
                self._sw_hosts[sw][host_name] = self._host_links[host_name][sw]
                self.addLink(host_name, sw, delay=delay,
                        addr1=host_mac, addr2=self._host_links[host_name][sw]['sw_mac'])
                sw_idx += 1

        for link in self.conf['links']: # only check switch-switch links
            sw1, sw2 = link
            if sw1 not in sw_names or sw2 not in sw_names: continue

            delay_key = tuple(sorted(link))
            delay = self.conf['latencies'][delay_key] if delay_key in self.conf['latencies'] else '0ms'
            self.addLink(sw1, sw2, delay=delay)
            self._port_map[sw1][sw2] = len(self._port_map[sw1])+1
            self._port_map[sw2][sw1] = len(self._port_map[sw2])+1

            sw1_num, sw2_num = sw_names.index(sw1)+1, sw_names.index(sw2)+1
            sw1_port = dict(mac="00:aa:00:%02x:%02x:00" % (sw1_num, sw2_num), port=self._port_map[sw1][sw2])
            sw2_port = dict(mac="00:aa:00:%02x:%02x:00" % (sw2_num, sw1_num), port=self._port_map[sw2][sw1])

            self._sw_links[sw1][sw2] = [sw1_port, sw2_port]
            self._sw_links[sw2][sw1] = [sw2_port, sw1_port]

