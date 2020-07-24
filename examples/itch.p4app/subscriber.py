#!/usr/bin/env python

import sys
import socket
from itch_message import mold_hdr_struct, add_order_struct

mold_msg_hdr_size = 2


if len(sys.argv) != 2:
    print "Usage: %s PORT" % sys.argv[0]
    sys.exit(1)

port = int(sys.argv[1])

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.bind(('', port))

while True:
    data, addr = s.recvfrom(1024)
    ao_data = data[mold_hdr_struct.size + mold_msg_hdr_size:]
    assert len(ao_data) == add_order_struct.size
    messagetype, stocklocate, trackingnumber, timestamp, orderreferencenumber, buysellindicator, shares, stock, price = add_order_struct.unpack(ao_data)
    print dict(stock=stock, shares=shares, price=price)

