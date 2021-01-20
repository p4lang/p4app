#!/usr/bin/env python

import sys
import socket
import struct

UDP_PORT = 1234
OP_READ  = 1
OP_WRITE = 2

hdr = struct.Struct('!B B I') # op_type idx [val]

if len(sys.argv) < 4:
    print("Usage: %s HOST READ|WRITE IDX [VALUE]" % sys.argv[0])
    sys.exit(1)

host = sys.argv[1]
read_or_write = sys.argv[2].lower()[:1]
idx = int(sys.argv[3])

addr = (host, UDP_PORT)

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

if read_or_write == 'r':
    req = hdr.pack(OP_READ, idx, 0)
else:
    assert len(sys.argv) == 5
    val = int(sys.argv[4])
    req = hdr.pack(OP_WRITE, idx, val)

s.sendto(req, addr)
res, addr2 = s.recvfrom(1024)

op_type, idx2, val2 = hdr.unpack(res)

print(idx2, val2)
