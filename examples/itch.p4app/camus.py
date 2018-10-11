import os
from tempfile import mktemp

COMPILER_PATH = './camus-compiler'
CAMUS_BIN = os.path.join(COMPILER_PATH, 'camus.exe')

def run_command(command):
    print '>', command
    return os.WEXITSTATUS(os.system(command))


def generateQueryPipeline(spec_path=None, out_path=None):
    cmd = '%s -prog-out "%s" "%s"' % (CAMUS_BIN, out_path, spec_path)
    rc = run_command(cmd)
    assert rc == 0
    return True

def compileRules(spec_path=None,
        rules=None, rules_path=None, out_prefix=None):

    if out_prefix is None:
        out_prefix = mktemp()

    if rules_path is None:
        assert rules is not None
        rules_path = mktemp()
        with open(rules_path, 'w') as f:
            rules_str = rules
            if not isinstance(rules, basestring):
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

    return dict(cli_commands=cli_commands, mcast_groups=mcast_groups)

def parseMcastGroups(mcast_groups_str):
    """ Parse a string of mcast groups to a dictionary """
    groups = {}
    for l in mcast_groups_str.split('\n'):
        print l
        mgid, ports = l.split(':')
        groups[int(mgid)] = map(int, ports.split())
    return groups

def parseCliCommands(cli_commands):
    """ Convert cli commands to P4Runtime """
    for l in cli_commands.split('\n'):
        p = l.split()
        if p[0] == 'table_add':
            is_ternary = '->' in l or '&&' in l
            table_name, action_name = p[1:3]
            matches = p[3:p.index('=>')]
            args = p[p.index('=>')+1 : (-1 if is_ternary else None)]
            priority = p[-1] if is_ternary else None
            print table_name, matches, args, priority
        else:
            raise Exception("Unsupported simple_cli command: " + p[0])

class RuntimeConfig:

    def __init__(self, raw):
        self.raw = raw

    def mcastGroups(self):
        return parseMcastGroups(self.raw['mcast_groups'])

    def p4runtime(self):
        return parseCliCommands(self.raw['cli_commands'])

class CamusApp:

    def __init__(self, spec_path=None):
        self.spec_path = spec_path

    def generateQueryPipeline(self, out_path):
        generateQueryPipeline(self.spec_path, out_path)

    def compileRules(self, **kwargs):
        if 'spec_path' not in kwargs: kwargs['spec_path'] = self.spec_path
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

    print parseMcastGroups(camus_runtime['mcast_groups'])
    print parseCliCommands(camus_runtime['cli_commands'])

