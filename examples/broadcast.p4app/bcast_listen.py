#!/usr/bin/env python
import sys
from socket import *

s = socket(AF_INET, SOCK_DGRAM)
s.bind(('', 1234))

sys.stderr.write("received '%s' from %s\n" % s.recvfrom(1024))
