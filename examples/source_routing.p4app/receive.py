#!/usr/bin/python

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

from scapy.all import sniff, sendp
from scapy.all import Packet
from scapy.all import ShortField, IntField, LongField, BitField

import sys
import struct

def handle_pkt(pkt):
    pkt = str(pkt)
    if len(pkt) < 12: return
    preamble = pkt[:8]
    preamble_exp = "\x00" * 8
    if preamble != preamble_exp: return
    num_valid = struct.unpack("<L", pkt[8:12])[0]
    if num_valid != 0:
        print "received incorrect packet"
    msg = pkt[12:]
    print msg
    sys.stdout.flush()

def main():
    sniff(iface = "eth0",
          prn = lambda x: handle_pkt(x))

if __name__ == '__main__':
    main()
