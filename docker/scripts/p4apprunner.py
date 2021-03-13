#!/usr/bin/env python2
# Copyright 2013-present Barefoot Networks, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import print_function

import argparse
from collections import OrderedDict
import json
import os
import sys
import tarfile

DEFAULT_BEHAVIORAL_EXE = 'simple_switch'

def default_cli_path(behavioral_exe):
    return '%s_CLI' % behavioral_exe

parser = argparse.ArgumentParser(description='p4apprunner')
parser.add_argument('--build-dir', help='Directory to build in.',
                    type=str, action='store', required=False, default='/tmp')
parser.add_argument('--quiet', help='Suppress log messages.',
                    action='store_true', required=False, default=False)
parser.add_argument('--build-only', help='Compile the program, but do not run it.',
                    action='store_true', required=False, default=False)
parser.add_argument('--json', help='Use this compiled JSON file instead of compiling.',
                    type=str, action='store', required=False, default=None)
parser.add_argument('--manifest', help='Path to manifest file.',
                    type=str, action='store', required=False, default='./p4app.json')
parser.add_argument('app', help='.p4app package to run.', type=str)
parser.add_argument('target', help=('Target to run. Defaults to the first target '
                                    'in the package.'),
                    nargs='?', type=str)

args = parser.parse_args()

def log(*items):
    if args.quiet != True:
        print(*items)

def log_error(*items):
    print(*items, file=sys.stderr)

def run_command(command):
    log('>', command)
    return os.WEXITSTATUS(os.system(command))

class Manifest:
    def __init__(self, program_file, language, target, target_config):
        self.program_file = program_file
        self.language = language
        self.target = target
        self.target_config = target_config

def read_manifest(manifest_file):
    manifest = json.load(manifest_file, object_pairs_hook=OrderedDict)

    if 'program' not in manifest:
        log_error('No program defined in manifest.')
        sys.exit(1)
    program_file = manifest['program']

    if 'language' not in manifest:
        log_error('No language defined in manifest.')
        sys.exit(1)
    language = manifest['language']

    if 'targets' not in manifest or len(manifest['targets']) < 1:
        log_error('No targets defined in manifest.')
        sys.exit(1)

    if args.target is not None:
        chosen_target = args.target
    elif 'default-target' in manifest:
        chosen_target = manifest['default-target']
    else:
        chosen_target = manifest['targets'].keys()[0]

    if chosen_target not in manifest['targets']:
        log_error('Target not found in manifest:', chosen_target)
        sys.exit(1)

    return Manifest(program_file, language, chosen_target, manifest['targets'][chosen_target])

def get_program_name(program_file):
    return os.path.basename(program_file).rstrip('.p4')

def run_compile_bmv2(manifest):
    compiler = manifest.target_config.get('compiler', 'p4c-bm2-ss')

    if 'run-before-compile' in manifest.target_config:
        commands = manifest.target_config['run-before-compile']
        if not isinstance(commands, list):
            log_error('run-before-compile should be a list:', commands)
            sys.exit(1)
        for command in commands:
            run_command(command)

    compiler_args = []

    if manifest.language == 'p4-14':
        compiler_args.append('--p4v 14')
    elif manifest.language == 'p4-16':
        compiler_args.append('--p4v 16')
    else:
        log_error('Unknown language:', manifest.language)
        sys.exit(1)

    if 'compiler-flags' in manifest.target_config:
        flags = manifest.target_config['compiler-flags']
        if not isinstance(flags, list):
            log_error('compiler-flags should be a list:', flags)
            sys.exit(1)
        compiler_args.extend(flags)

    # Compile the program.
    output_file = get_program_name(manifest.program_file) + '.json'
    compiler_args.append('"%s"' % manifest.program_file)
    compiler_args.append('-o "%s"' % output_file)
    rv = run_command('%s %s' % (compiler, ' '.join(compiler_args)))

    if 'run-after-compile' in manifest.target_config:
        commands = manifest.target_config['run-after-compile']
        if not isinstance(commands, list):
            log_error('run-after-compile should be a list:', commands)
            sys.exit(1)
        for command in commands:
            run_command(command)

    if rv != 0:
        log_error('Compile failed.')
        sys.exit(1)

    return output_file

def run_mininet(manifest):
    print(manifest)

    output_file = run_compile_bmv2(manifest)

    # Run the program using the BMV2 Mininet simple switch.
    switch_args = []

    # We'll place the switch's log file in '/var/log'. The Dockerfile places a
    # volume at this path. This works around the fact that Ubuntu 14.04 includes
    # a version of 'tail' which doesn't interact well with overlayfs.
    log_file = os.path.join('/var/log', manifest.program_file + '.log')
    switch_args.append('--log-file "%s"' % log_file)

    # Generate a message that will be printed by the Mininet CLI to make
    # interacting with the simple switch a little easier.
    message_file = 'mininet_message.txt'
    with open(message_file, 'w') as message:
        container = os.environ['HOSTNAME']

        print(file=message)
        print('======================================================================',
              file=message)
        print('Welcome to the BMV2 Mininet CLI!', file=message)
        print('======================================================================',
              file=message)
        print('Your P4 program is installed into the BMV2 software switch', file=message)
        print('and your initial configuration is loaded. You can interact', file=message)
        print('with the network using the mininet CLI below.', file=message)
        print(file=message)
        print('To inspect or change the switch configuration, connect to', file=message)
        print('its CLI from your host operating system using this command:', file=message)
        print('  docker exec -t -i %s simple_switch_CLI' % container, file=message)
        print(file=message)
        print('To view the switch log, run this command from your host OS:', file=message)
        print('  docker exec -t -i %s tail -f %s' % (container, log_file), file=message)
        print(file=message)
        print('To run the switch debugger, run this command from your host OS:', file=message)
        print('  docker exec -t -i %s bm_p4dbg' % container, file=message)
        print(file=message)

    switch_args.append('--cli-message "%s"' % message_file)

    if 'pcap_dump' in manifest.target_config and manifest.target_config['pcap_dump']:
        switch_args.append('--pcap-dump')

    if 'num-hosts' in manifest.target_config:
        switch_args.append('--num-hosts %s' % manifest.target_config['num-hosts'])

    if 'switch-config' in manifest.target_config:
        switch_args.append('--switch-config "%s"' % manifest.target_config['switch-config'])

    behavioral_exe = manifest.target_config.get('behavioral-exe', DEFAULT_BEHAVIORAL_EXE)
    cli_path = manifest.target_config.get('cli-path', default_cli_path(behavioral_exe))

    switch_args.append('--behavioral-exe "%s"' % behavioral_exe)
    switch_args.append('--cli-path "%s"' % cli_path)
    switch_args.append('--json "%s"' % output_file)

    program = '"%s/mininet/single_switch_mininet.py"' % sys.path[0]
    return run_command('python2 %s %s' % (program, ' '.join(switch_args)))

def build_only(manifest):

    model = 'bmv2'
    if 'model' in manifest.target_config:
        model = manifest.target_config['model']

    if model == 'bmv2':
        output_file = run_compile_bmv2(manifest)
    else:
        log_error('Unrecognized model:', model)
        sys.exit(1)

    rc = run_command('cp %s /tmp/p4app_logs/program.json' % output_file)

    if rc != 0:
        log_error("Failed to copy compiled program to output location")
        sys.exit(1)

def run_multiswitch(manifest):

    model = 'bmv2'
    if 'model' in manifest.target_config:
        model = manifest.target_config['model'].lower()

    if model == 'bmv2':
        if args.json: json_file = os.path.abspath(args.json)
        else:         json_file = run_compile_bmv2(manifest)
    else:
        log_error('Unrecognized model:', model)
        sys.exit(1)

    behavioral_exe = manifest.target_config.get('behavioral-exe', DEFAULT_BEHAVIORAL_EXE)
    cli_path = manifest.target_config.get('cli-path', default_cli_path(behavioral_exe))
    script_args = []
    script_args.append('--log-dir "/tmp/p4app_logs"')
    script_args.append('--manifest "%s"' % args.manifest)
    script_args.append('--target "%s"' % manifest.target)
    if 'auto-control-plane' in manifest.target_config and manifest.target_config['auto-control-plane']:
        script_args.append('--auto-control-plane' )
    script_args.append('--behavioral-exe "%s"' % behavioral_exe)
    script_args.append('--cli-path "%s"' % cli_path)
    script_args.append('--json "%s"' % json_file)

    program = '"%s/mininet/multi_switch_mininet.py"' % sys.path[0]
    return run_command('python2 %s %s' % (program, ' '.join(script_args)))

def run_stf(manifest):
    output_file = run_compile_bmv2(manifest)

    if not 'test' in manifest.target_config:
        log_error('No STF test file provided.')
        sys.exit(1)
    stf_file = manifest.target_config['test']

    # Run the program using the BMV2 STF interpreter.
    stf_args = []
    stf_args.append('-v')
    stf_args.append(os.path.join(args.build_dir, output_file))
    stf_args.append(os.path.join(args.build_dir, stf_file))

    program = '"%s/stf/bmv2stf.py"' % sys.path[0]
    rv = run_command('python2 %s %s' % (program, ' '.join(stf_args)))
    if rv != 0:
        sys.exit(1)
    return rv

def run_custom(manifest):
    behavioral_exe = manifest.target_config.get('behavioral-exe', DEFAULT_BEHAVIORAL_EXE)
    cli_path = manifest.target_config.get('cli-path', default_cli_path(behavioral_exe))
    output_file = run_compile_bmv2(manifest)
    python_path = 'PYTHONPATH=$PYTHONPATH:/scripts/mininet/'
    script_args = []
    script_args.append('--behavioral-exe "%s"' % behavioral_exe)
    script_args.append('--json "%s"' % output_file)
    script_args.append('--cli "%s"' % cli_path)
    if not 'program' in manifest.target_config:
         log_error('No mininet program file provided.')
         sys.exit(1)
    program = manifest.target_config['program']
    rv = run_command('%s python2 %s %s' % (python_path, program, ' '.join(script_args)))

    if rv != 0:
        sys.exit(1)
    return rv

def main():
    log('Entering build directory.')
    os.chdir(args.build_dir)

    # A '.p4app' package is really just a '.tar.gz' archive. Extract it so we
    # can process its contents.
    log('Extracting package.')
    tar = tarfile.open(args.app)
    tar.extractall()
    tar.close()

    run_command('touch /tmp/p4app_logs/p4s.s1.log')
    run_command('ln -s /tmp/p4app_logs/p4s.s1.log /tmp/p4s.s1.log')

    log('Reading package manifest.')
    with open(args.manifest, 'r') as manifest_file:
        manifest = read_manifest(manifest_file)

    # Dispatch to the backend implementation for this target.
    backend = manifest.target
    if 'use' in manifest.target_config:
        backend = manifest.target_config['use']

    if args.build_only or backend == 'compile-bmv2':
        build_only(manifest)
        rc = 0
    elif backend == 'mininet':
        rc = run_mininet(manifest)
    elif backend == 'multiswitch':
        rc = run_multiswitch(manifest)
    elif backend == 'stf':
        rc = run_stf(manifest)
    elif backend == 'custom':
        rc = run_custom(manifest)
    else:
        log_error('Target specifies unknown backend:', backend)
        sys.exit(1)

    sys.exit(rc)

if __name__ == '__main__':
    main()
