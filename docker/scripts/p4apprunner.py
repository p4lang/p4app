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
import os
import sys

parser = argparse.ArgumentParser(description='p4apprunner')
parser.add_argument('app', help='.p4app package to run.', type=str)
parser.add_argument('--quiet', help='Suppress log messages.',
                    action='store_true', required=False, default=False)
args = parser.parse_args()

def log(*items):
    if args.quiet != True:
        print(*items)

def log_error(*items):
    print(*items, file=sys.stderr)

def run_command(command):
    log('>', command)
    return os.WEXITSTATUS(os.system(command))

def main():
    rc = run_command("python main.py")

    sys.exit(rc)

if __name__ == '__main__':
    main()
