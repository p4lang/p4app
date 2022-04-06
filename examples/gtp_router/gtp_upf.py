from scapy.all import sniff


if __name__ == '__main__':
    sniff(iface=sys.argv[1])
