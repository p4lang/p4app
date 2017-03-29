import socket, sys

msg = sys.argv[1]

addrs = zip(sys.argv[2::2], map(int, sys.argv[3::2]))

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.settimeout(2)

for srv_addr in addrs:
    sock.sendto(msg, srv_addr)

    data, addr = sock.recvfrom(1024)
    print "received:", data
