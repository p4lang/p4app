#!/usr/bin/env python

import sys
import socket
from itch_message import MoldPacket, AddOrderMessage

if len(sys.argv) != 3:
    print "Usage: %s HOST PORT" % sys.argv[0]
    sys.exit(1)

host = sys.argv[1]
port = int(sys.argv[2])
addr = (host, port)

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
for i in range(1):
    #print "// sent msg %d" % i
    msg = AddOrderMessage(Stock='GOOGL', Shares=1, Price=2)
    data = MoldPacket(Session=1, SequenceNumber=i, MessagePayloads=[msg])
    s.sendto(data, addr)

