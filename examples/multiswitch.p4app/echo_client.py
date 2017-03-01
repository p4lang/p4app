import socket, sys

srv_addr = (sys.argv[1], int(sys.argv[2]))

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.sendto(sys.argv[3], srv_addr)

data, addr = sock.recvfrom(1024)
print "received:", data
