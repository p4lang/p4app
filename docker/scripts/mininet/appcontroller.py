import subprocess

from shortest_path import ShortestPath

class AppController:

    def __init__(self, manifest=None, target=None, topo=None, net=None, links=None):
        self.manifest = manifest
        self.target = target
        self.conf = manifest['targets'][target]
        self.topo = topo
        self.net = net
        self.links = links

    def read_entries(self, filename):
        entries = []
        with open(filename, 'r') as f:
            for line in f:
                line = line.strip()
                if line == '': continue
                entries.append(line)
        return entries

    def add_entries(self, thrift_port=9090, sw=None, entries=None):
        assert entries
        if sw: thrift_port = sw.thrift_port

        print '\n'.join(entries)
        p = subprocess.Popen(['simple_switch_CLI', '--thrift-port', str(thrift_port)], stdin=subprocess.PIPE)
        p.communicate(input='\n'.join(entries))

    def start(self):
        shortestpath = ShortestPath(self.links)
        entries = {}
        for sw in self.topo.switches():
            entries[sw] = []
            if 'switches' in self.conf and sw in self.conf['switches'] and 'entries' in self.conf['switches'][sw]:
                extra_entries = self.conf['switches'][sw]['entries']
                if type(extra_entries) == list: # array of entries
                    entries[sw] += extra_entries
                else: # path to file that contains entries
                    entries[sw] += self.read_entries(extra_entries)
            entries[sw] += [
                'table_set_default send_frame _drop',
                'table_set_default forward _drop',
                'table_set_default ipv4_lpm _drop']


        for host_name in self.topo._host_links:
            link = self.topo._host_links[host_name]
            h = self.net.get(host_name)
            h.setARP(link['sw_ip'], link['sw_mac'])
            h.setDefaultRoute("via %s" % link['sw_ip'])
            sw = link['sw']
            entries[sw].append('table_add send_frame rewrite_mac %d => %s' % (link['sw_port'], link['sw_mac']))
            entries[sw].append('table_add forward set_dmac %s => %s' % (link['host_ip'], link['host_mac']))
            entries[sw].append('table_add ipv4_lpm set_nhop %s/32 => %s %d' % (link['host_ip'], link['host_ip'], link['sw_port']))

        for h in self.net.hosts:
            for sw in self.net.switches:
                path = shortestpath.get(sw.name, h.name)
                if not path: continue
                if not path[1][0] == 's': continue # next hop is a switch
                sw_link = self.topo._sw_links[sw.name][path[1]]
                h_link = self.topo._host_links[h.name]
                entries[sw.name].append('table_add send_frame rewrite_mac %d => %s' % (sw_link[0]['port'], sw_link[0]['mac']))
                entries[sw.name].append('table_add forward set_dmac %s => %s' % (h_link['host_ip'], sw_link[1]['mac']))
                entries[sw.name].append('table_add ipv4_lpm set_nhop %s/32 => %s %d' % (h_link['host_ip'], h_link['host_ip'], sw_link[0]['port']))

        for sw_name in entries:
            sw = self.net.get(sw_name)
            self.add_entries(sw=sw, entries=entries[sw_name])

    def stop(self):
        pass
