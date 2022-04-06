import sys

from scapy.contrib.gtp import GTPHeader
from scapy.layers.inet import IP, UDP
from scapy.layers.l2 import Ether
from scapy.sendrecv import srp1


if __name__ == '__main__':

    gtp = Ether() / \
        IP(dst=sys.argv[1]) / \
        UDP(sport=sys.argv[2], dport=sys.argv[2]) / \
        GTPHeader(teid=2)

    srp1(gtp, iface=sys.argv[3])
