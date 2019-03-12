from __future__ import print_function
import os

def log(*items):
    print(*items)

def log_error(*items):
    print(*items, file=sys.stderr)

def run_command(command):
    log('>', command)
    return os.WEXITSTATUS(os.system(command))

