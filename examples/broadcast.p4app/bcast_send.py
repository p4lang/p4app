#!/usr/bin/env python
from socket import *

s = socket(AF_INET, SOCK_DGRAM)
s.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
s.sendto('hello everyone', ('255.255.255.255', 1234))
