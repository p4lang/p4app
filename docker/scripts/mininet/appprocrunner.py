import subprocess
import re
from time import sleep
import os

class AppProcess:

    def __init__(self, runner, host, host_conf):
        self.runner = runner
        self.host = host
        self.host_conf = host_conf
        self.proc = None
        self.stdout_file = None
        self.stdout_filename = os.path.join(self.runner.log_dir, self.host.name + '.stdout')

    def isDaemon(self):
        if 'wait' in self.host_conf and self.host_conf['wait']:
            return False
        return True

    def formatCmd(self, cmd):
        for h in self.runner.net.hosts:
            cmd = cmd.replace(h.name, h.defaultIntf().updateIP())
        return cmd


    def start(self):
        self.stdout_file = open(self.stdout_filename, 'w')
        self.cmd = self.formatCmd(self.host_conf['cmd'])
        self.proc = self.host.popen(self.cmd, stdout=self.stdout_file, shell=True, preexec_fn=os.setpgrp)

        print self.host.name, self.cmd

        if 'startup_sleep' in self.host_conf:
            sleep(self.host_conf['startup_sleep'])

    def cleanup(self):
        if self.stdout_file:
            self.stdout_file.flush()
            self.stdout_file.close()

    def waitForExit(self):
        print self.host.name, self.proc.communicate()
        if self.proc.returncode is None:
            self.proc.wait()
            print self.host.name, self.proc.communicate()

        self.cleanup()

        return self.proc.returncode

    def run_command(self, command):
        p = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
        p.wait()
        stdout, stderr = p.communicate()
        return (p.returncode, stdout, stderr)

    def killTree(self):
        _, stdout, _ = self.run_command('pstree -p %d' % self.proc.pid)
        descendants = re.findall("\(([^)]*)\)", stdout)

        cmd = 'kill -INT %s' % ' '.join(descendants)
        rc, stdout, _ = self.run_command(cmd)

        print "Sent INT to children of PID %d: `%s`. Return code: %d" % (self.proc.pid, cmd, rc)

    def kill(self):
        if self.proc.returncode is not None: # already exited
            return

        self.run_command('pkill -INT -P %d' % self.proc.pid)
        sleep(0.2)

        rc, _, _ = self.run_command('pkill -0 -P %d' % self.proc.pid) # check if it's still running
        if rc != 0: # the process group is not running
            return

        sleep(0.5) # give it a little more time to exit gracefully

        rc, _, _ = self.run_command('pkill -0 -P %d' % self.proc.pid) # check if it's still running
        if rc != 0: # the process group is not running
            return

        self.killTree()


class AppProcRunner:

    def __init__(self, manifest=None, target=None, topo=None, net=None, log_dir=None):
        self.manifest = manifest
        self.target = target
        self.conf = manifest['targets'][target]
        self.topo = topo
        self.net = net
        self.log_dir = log_dir
        self.AppProcessClass = AppProcess

        self.app_procs = []
        self.foreground_procs, self.background_procs = [], []
        self.return_codes = []

    def setupProcs(self):
        os.environ.update(dict(map(lambda (k,v): (k, str(v)), self.conf['parameters'].iteritems())))
        print '\n'.join(map(lambda (k,v): "%s: %s"%(k,v), self.conf['parameters'].iteritems())) + '\n'

        for host_name in sorted(self.conf['hosts'].keys()):
            host_conf = self.conf['hosts'][host_name]
            if 'cmd' not in host_conf: continue

            p = self.AppProcessClass(self, self.net.get(host_name), host_conf)
            self.app_procs.append(p)

    def startAllProcs(self):
        for p in self.app_procs:
            p.start()

            if p.isDaemon():
                self.background_procs.append(p)
            else:
                self.foreground_procs.append(p)

    def waitForForegroundProcs(self):
        for p in self.foreground_procs:
            rc = p.waitForExit()
            self.return_codes.append(rc)

    def killBackgroundProcs(self):
        for p in self.background_procs:
            p.kill()
            rc = p.waitForExit()
            self.return_codes.append(rc)

    def runAfterCmds(self):
        if 'after' in self.conf and 'cmd' in self.conf['after']:
            cmds = self.conf['after']['cmd'] if type(self.conf['after']['cmd']) == list else [self.conf['after']['cmd']]
            for cmd in cmds:
                os.system(cmd)

    def runall(self):
        self.setupProcs()

        self.startAllProcs()

        self.waitForForegroundProcs()

        self.killBackgroundProcs()

        self.runAfterCmds()

    def hadError(self):
        bad_codes = [rc for rc in self.return_codes if rc != 0]
        if len(bad_codes): return True
        return False
