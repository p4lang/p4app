#!/usr/bin/env python2

from __future__ import print_function

import argparse
from collections import OrderedDict
import json
import os
import sys
import tarfile

parser = argparse.ArgumentParser(description='p4apprunner')
parser.add_argument('--build-dir', help='Directory to build in.',
                    type=str, action='store', required=False, default='/tmp')
parser.add_argument('--quiet', help='Suppress log messages.',
                    action='store_true', required=False, default=False)
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

    for target, target_config in manifest['targets'].iteritems():
        if args.target is None or args.target == target:
            return Manifest(program_file, language, target, target_config)

    log_error('Target not found in manifest:', args.target)
    sys.exit(1)

def compile_for_bmv2(manifest):
    # Compile the program.
    if manifest.language == 'p4-14':
        language_option = '--p4-14'
    elif manifest.language == 'p4-16':
        language_option = '--p4-16'
    else:
        log_error('Unknown language:', manifest.language)
        sys.exit(1)

    output_file = manifest.program_file + '.json'
    rv = os.system('p4c-bm2-ss %s "%s" -o "%s"'
                     % (language_option, manifest.program_file, output_file))
    if rv != 0:
        log_error('Compile failed.')
        sys.exit(1)

    return output_file

def run_mininet(manifest):
    output_file = compile_for_bmv2(manifest)

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

    if 'num_hosts' in manifest.target_config:
        switch_args.append('--num-hosts %s' % manifest.target_config['num_hosts'])

    if 'switch_config' in manifest.target_config:
        switch_args.append('--switch-config "%s"' % manifest.target_config['switch_config'])

    switch_args.append('--behavioral-exe "%s"' % 'simple_switch')
    switch_args.append('--json "%s"' % output_file)

    program = '"%s/mininet/single_switch_mininet.py"' % sys.path[0]
    os.system('python2 %s %s' % (program, ' '.join(switch_args)))

def run_stf(manifest):
    output_file = compile_for_bmv2(manifest)

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
    rv = os.system('python2 %s %s' % (program, ' '.join(stf_args)))
    if rv != 0:
        sys.exit(1)

def main():
    log('Entering build directory.')
    os.chdir(args.build_dir)

    # A '.p4app' package is really just a '.tar.gz' archive. Extract it so we
    # can process its contents.
    log('Extracting package.')
    tar = tarfile.open(args.app)
    tar.extractall()
    tar.close()

    log('Reading package manifest.')
    with open('p4app.json', 'r') as manifest_file:
        manifest = read_manifest(manifest_file)

    # Dispatch to the backend implementation for this target.
    backend = manifest.target
    if 'use' in manifest.target_config:
        backend = manifest.target_config['use']

    if backend == 'mininet':
        run_mininet(manifest)
    elif backend == 'stf':
        run_stf(manifest)
    else:
        log_error('Target specifies unknown backend:', backend)
        sys.exit(1)

if __name__ == '__main__':
    main()
