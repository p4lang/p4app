import os
import json
from tempfile import mktemp

COMPILER_PATH = './camus-compiler'
CAMUS_BIN = os.path.join(COMPILER_PATH, 'camus.exe')

def run_command(command):
    print('>', command)
    return os.WEXITSTATUS(os.system(command))


def generateQueryPipeline(spec_path=None, out_path=None):
    cmd = '%s -prog-out "%s" "%s"' % (CAMUS_BIN, out_path, spec_path)
    rc = run_command(cmd)
    assert rc == 0
    return True

def compileRules(spec_path=None,
        ingress_name=None,
        rules=None, rules_path=None, out_prefix=None):

    if out_prefix is None:
        out_prefix = mktemp()

    if rules_path is None:
        assert rules is not None
        rules_path = mktemp()
        with open(rules_path, 'w') as f:
            rules_str = rules
            if not isinstance(rules, str):
                rules_str = ''
                for r in rules:
                    r = r.strip()
                    if r[-1] != ';': r += ';'
                    rules_str += r + '\n'
            f.write(rules_str)

    cmd = '%s -rt-out "%s" -rules "%s" "%s"' % (CAMUS_BIN, out_prefix, rules_path, spec_path)
    rc = run_command(cmd)
    assert rc == 0

    with open(out_prefix + '_commands.txt', 'r') as f:
        cli_commands = f.read()
    with open(out_prefix + '_mcast_groups.txt', 'r') as f:
        mcast_groups = f.read()
    with open(out_prefix + '_entries.json', 'r') as f:
        entries = json.load(f)

    def prependIngressName(entry):
        if 'table_name' in entry: entry['table_name'] = '%s.%s' % (ingress_name, entry['table_name'])
        if 'action_name' in entry: entry['action_name'] = '%s.%s' % (ingress_name, entry['action_name'])
        return entry

    if ingress_name:
        entries = map(prependIngressName, [e for e in entries if e is not None])

    return dict(cli_commands=cli_commands, mcast_groups=mcast_groups, entries=entries)

def parseMcastGroups(mcast_groups_str):
    """ Parse a string of mcast groups to a dictionary """
    groups = {}
    for l in mcast_groups_str.split('\n'):
        mgid, ports = l.split(':')
        groups[int(mgid)] = map(int, ports.split())
    return groups

class RuntimeConfig:

    def __init__(self, raw):
        self.raw = raw

    def mcastGroups(self):
        return parseMcastGroups(self.raw['mcast_groups'])

    def entries(self):
        return self.raw['entries']

class CamusApp:

    def __init__(self, spec_path=None, ingress_name=None):
        self.spec_path = spec_path
        self.ingress_name = ingress_name

    def generateQueryPipeline(self, out_path):
        generateQueryPipeline(self.spec_path, out_path)

    def compileRules(self, **kwargs):
        if 'spec_path' not in kwargs: kwargs['spec_path'] = self.spec_path
        if self.ingress_name and 'ingress_name' not in kwargs: kwargs['ingress_name'] = self.ingress_name
        config = compileRules(**kwargs)
        assert config
        return RuntimeConfig(config)


if __name__ == '__main__':
    generateQueryPipeline('spec.p4', 'camus.p4')

    rules = ['add_order.shares = 1: fwd(1);',
             'add_order.price = 2: fwd(2);',
             'add_order.shares = 3 and add_order.price = 4: fwd(3);',
             'add_order.shares > 100 and add_order.stock = "BFN": fwd(2);']

    camus_runtime = compileRules(spec_path='spec.p4', rules=rules)

    print(parseMcastGroups(camus_runtime['mcast_groups']))

