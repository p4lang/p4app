import subprocess

from shortest_path import ShortestPath

class AppController:

    def __init__(self, manifest=None, target=None, topo=None, net=None):
        self.manifest = manifest
        self.target = target
        self.conf = manifest['targets'][target]
        self.topo = topo
        self.net = net
        self.commands = dict()
        self.shortestpath = ShortestPath(self.conf['links'])

    def readCommands(self, filename):
        commands = []
        with open(filename, 'r') as f:
            for line in f:
                line = line.strip()
                if line == '': continue
                if line[0] == '#': continue # ignore comments
                commands.append(line)
        return commands

    def parseCliOutput(self, s):
        parsed = dict(raw=s)
        if 'node was created with handle' in s:
            parsed['handle'] = int(s.split('node was created with handle', 1)[-1].split()[0])
        return parsed

    def sendCommands(self, commands, thrift_port=9090, sw=None):
        if sw: thrift_port = sw.thrift_port

        print '\n'.join(commands)
        p = subprocess.Popen(['simple_switch_CLI', '--thrift-port', str(thrift_port)], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        stdout, nostderr = p.communicate(input='\n'.join(commands))
        print stdout
        raw_results = stdout.split('RuntimeCmd:')[1:len(commands)+1]
        parsed_results = map(self.parseCliOutput, raw_results)
        return parsed_results

    def readRegister(self, register, idx, thrift_port=9090, sw=None):
        if sw: thrift_port = sw.thrift_port
        p = subprocess.Popen(['simple_switch_CLI', '--thrift-port', str(thrift_port)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = p.communicate(input="register_read %s %d" % (register, idx))
        reg_val = filter(lambda l: ' %s[%d]' % (register, idx) in l, stdout.split('\n'))[0].split('= ', 1)[1]
        return long(reg_val)

    def configureHosts(self):
        for host_name in self.topo._host_links:
            h = self.net.get(host_name)
            for link in self.topo._host_links[host_name].values():
                sw = link['sw']
                iface = h.intfNames()[link['idx']]
                h.cmd('ifconfig %s %s hw ether %s' % (iface, link['host_ip'], link['host_mac']))
                h.cmd('arp -i %s -s %s %s' % (iface, link['sw_ip'], link['sw_mac']))
                h.cmd('ethtool --offload %s rx off tx off' % iface)
                h.cmd('ip route add %s dev %s' % (link['sw_ip'], iface))
            h.setDefaultRoute("via %s" % link['sw_ip'])

            for h2 in self.net.hosts:
                if h == h2: continue
                path = self.shortestpath.get(h.name, h2.name, exclude=lambda n: n in self.topo._host_links)
                if not path: continue
                h_link = self.topo._host_links[h.name][path[1]]
                h2_link = self.topo._host_links[h2.name][path[-2]]
                h.cmd('ip route add %s via %s' % (h2_link['host_ip'], h_link['sw_ip']))

    def start(self):
        self.generateCommands()
        self.sendGeneratedCommands()
        self.configureHosts()

    def generateCommands(self):
        self.loadCommandFiles()
        self.generateDefaultCommands()

    def sendGeneratedCommands(self):
        for sw_name in self.commands:
            sw = self.net.get(sw_name)
            self.sendCommands(self.commands[sw_name], sw=sw)

    def loadCommandFiles(self):
        for sw in self.topo.switches():
            if sw not in self.commands: self.commands[sw] = []
            if 'switches' not in self.conf or sw not in self.conf['switches'] or 'commands' not in self.conf['switches'][sw]:
                continue
            extra_commands = self.conf['switches'][sw]['commands']
            if type(extra_commands) == list: # array of commands
                self.commands[sw] += extra_commands
            else: # path to file that contains commands
                self.commands[sw] += self.readCommands(extra_commands)

    def generateDefaultCommands(self):
        for sw in self.topo.switches():
            if sw not in self.commands: self.commands[sw] = []
            self.commands[sw] += [
                'table_set_default send_frame _drop',
                'table_set_default forward _drop',
                'table_set_default ipv4_lpm _drop']

        for host_name in self.topo._host_links:
            h = self.net.get(host_name)
            for link in self.topo._host_links[host_name].values():
                sw = link['sw']
                self.commands[sw].append('table_add send_frame rewrite_mac %d => %s' % (link['sw_port'], link['sw_mac']))
                self.commands[sw].append('table_add forward set_dmac %s => %s' % (link['host_ip'], link['host_mac']))
                self.commands[sw].append('table_add ipv4_lpm set_nhop %s/32 => %s %d' % (link['host_ip'], link['host_ip'], link['sw_port']))


        for h in self.net.hosts:
            h_link = self.topo._host_links[h.name].values()[0]
            for sw in self.net.switches:
                path = self.shortestpath.get(sw.name, h.name, exclude=lambda n: n in self.topo._host_links)
                if not path: continue
                if not path[1] in self.topo._port_map: continue # next hop is a switch
                sw_link = self.topo._sw_links[sw.name][path[1]]
                self.commands[sw.name].append('table_add send_frame rewrite_mac %d => %s' % (sw_link[0]['port'], sw_link[0]['mac']))
                self.commands[sw.name].append('table_add forward set_dmac %s => %s' % (h_link['host_ip'], sw_link[1]['mac']))
                self.commands[sw.name].append('table_add ipv4_lpm set_nhop %s/32 => %s %d' % (h_link['host_ip'], h_link['host_ip'], sw_link[0]['port']))


    def stop(self):
        pass
