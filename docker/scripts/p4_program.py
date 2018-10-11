import os
from p4app_util import run_command

class P4Program:

    def __init__(self, prog_filename, version=16, compile_flags=[]):
        self.prog_filename = os.path.join('/p4app', prog_filename)

        assert isinstance(version, str) or isinstance(version, int)
        if version in [14, '14', 'P4_14']:
            self.version = 14
        elif version in [16, '16', 'P4_16']:
            self.version = 16
        else:
            raise Exception("Unrecognized P4 version: " + str(version))

        self.compile_flags = compile_flags
        assert isinstance(compile_flags, list)
        self._json_path = None
        self._p4info_path = None

    def name(self):
        return os.path.basename(self.prog_filename).rstrip('.p4')

    def compile(self):
        compiler_args = []

        compiler_args.append('--std p4-%d' % self.version)

        compiler_args.extend(self.compile_flags)

        # Compile the program.
        self._json_path = os.path.join('/tmp/p4app-logs', self.name() + '.json')
        compiler_args.append('"%s"' % self.prog_filename)
        compiler_args.append('-o "%s"' % self._json_path)
        if self.supportsP4Runtime():
            self._p4info_path = os.path.join('/tmp/p4app-logs', self.name() + '.p4info')
            compiler_args.append('--p4runtime-format text --p4runtime-file "%s"' % self._p4info_path)
        rv = run_command('p4c-bm2-ss %s' % ' '.join(compiler_args))

        if rv != 0:
            raise Exception("Compile failed. Compiler return value: %d" % rv)

    def json(self):
        if self._json_path is None:
            self.compile()
        return self._json_path

    def p4info(self):
        if not self.supportsP4Runtime(): return None
        if self._p4info_path is None:
            self.compile()
        return self._p4info_path

    def supportsP4Runtime(self):
        return self.version == 16
