import subprocess

from shortest_path import ShortestPath

def isInt(s):
    try:
        int(s)
        return True
    except ValueError:
        return False

class AppController:

    def __init__(self, manifest=None, target=None, topo=None, net=None, cli_path='simple_switch_CLI'):
        self.manifest = manifest
        self.target = target
        self.cli_path = cli_path
        self.conf = manifest['targets'][target]
        self.topo = topo
        self.net = net

        self.switches = self.topo.switches()
        self.host_for_ip = self.findHostIPs()

        self.command_files = dict((sw, []) for sw in self.switches)
        self.commands = dict((sw, []) for sw in self.switches)

        self.mcast_groups_files = dict((sw, []) for sw in self.switches)
        self.mcast_groups = dict((sw, {}) for sw in self.switches)
        self.last_mcnoderid = -1

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
        if 'created with handle' in s:
            parsed['handle'] = int(s.split('created with handle', 1)[-1].split()[0])
        return parsed

    def sendCommands(self, commands, thrift_port=9090, sw=None):
        if sw: thrift_port = sw.thrift_port

        print '\n'.join(commands)
        p = subprocess.Popen([self.cli_path, '--thrift-port', str(thrift_port)], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        stdout, nostderr = p.communicate(input='\n'.join(commands))
        print stdout
        raw_results = stdout.split('RuntimeCmd:')[1:len(commands)+1]
        parsed_results = map(self.parseCliOutput, raw_results)
        return parsed_results

    def readMcastGroups(self, filename, sw):
        def portForStr(s):
            if isInt(s): return int(s)
            elif s[0] == 'h': return self.getPortForHost(sw, s)
            else: return self.getPortForHost(sw, ip=s)

        groups = {}
        with open(filename, 'r') as f:
            for line in f:
                a,b = line.split(':')
                mgid = int(a)
                ports = map(portForStr, b.split())
                groups[mgid] = ports

        return groups

    def createMcastGroup(self, mgid, ports, sw=None):
        self.last_mcnoderid += 1
        commands = ['mc_node_create %d %s' % (self.last_mcnoderid, ' '.join(map(str, ports)))]
        results = self.sendCommands(commands, sw=sw)

        handle = results[-1]['handle']
        commands = ['mc_mgrp_create %d' % mgid]

        if 'model' in self.conf and self.conf['model'] != 'BMV2':
            commands += ['mc_associate_node %d %d 0 0' % (mgid, results[-1]['handle'])]
        else:
            commands += ['mc_node_associate %d %d' % (mgid, results[-1]['handle'])]

        self.sendCommands(commands, sw=sw)

    def readRegister(self, register, idx, thrift_port=9090, sw=None):
        if sw: thrift_port = sw.thrift_port
        p = subprocess.Popen([self.cli_path, '--thrift-port', str(thrift_port)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
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
        self.setupMcastGroups()
        self.configureHosts()

    def generateCommands(self):
        self.loadCommands()
        self.generateDefaultCommands()

    def sendGeneratedCommands(self):
        for sw_name in self.commands:
            sw = self.net.get(sw_name)
            self.sendCommands(self.commands[sw_name], sw=sw)

    def loadCommands(self):
        for sw in self.switches:
            if 'switches' not in self.conf or sw not in self.conf['switches'] or 'commands' not in self.conf['switches'][sw]:
                continue

            extra_commands = self.conf['switches'][sw]['commands']

            if type(extra_commands) == list: # array of commands and/or command files
                for x in extra_commands:
                    if x.endswith('.txt'):
                        self.command_files[sw].append(x)
                    else:
                        self.commands[sw].append(x)

            else: # path to file that contains commands
                self.command_files[sw].append(extra_commands)

        for sw in self.switches:
            for filename in self.command_files[sw]:
                self.commands[sw] += self.readCommands(filename)

    def setupMcastGroups(self):
        self.loadMcastGroups()

        for sw in self.switches:
            for mgid, ports in self.mcast_groups[sw].iteritems():
                self.createMcastGroup(mgid, ports, sw=self.net.get(sw))

    def loadMcastGroups(self):
        for sw in self.switches:
            if 'switches' not in self.conf or sw not in self.conf['switches'] or 'mcast_groups' not in self.conf['switches'][sw]:
                continue

            mcast_groups_files = self.conf['switches'][sw]['mcast_groups']
            if type(mcast_groups_files) == list:
                pass
            elif type(mcast_groups_files) in (str, unicode):
                mcast_groups_files = [mcast_groups_files]
            else:
                raise Exception("`mcast_groups` should either be a filename or a list of filenames")

            self.mcast_groups_files[sw] += mcast_groups_files

        for sw in self.switches:
            for filename in self.mcast_groups_files[sw]:
                self.mcast_groups[sw].update(self.readMcastGroups(filename, sw))




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

    def getPortForHost(self, sw, h=None, ip=None):
        if ip is not None:
            assert ip in self.host_for_ip, "IP address %s is not assigned to any host" % ip
            h = self.host_for_ip[ip]

        assert h is not None, "Must specify either host or IP"
        assert h in self.topo._host_links, "Could not find host %s" % h
        assert sw in self.topo._host_links[h], "Could not find switch %s for hostname %s" % (sw, h)
        return self.topo._host_links[h][sw]['sw_port']

    def findHostIPs(self):
        mapping = {}
        for h in self.net.hosts:
            for sw in self.topo._host_links[h.name]:
                link = self.topo._host_links[h.name][sw]
                mapping[link['host_ip']] = h.name
        return mapping


    def stop(self):
        pass
