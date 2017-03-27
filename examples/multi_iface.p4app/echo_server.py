import socket, sys

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(('', int(sys.argv[1])))

while True:
    try:
        data, addr = sock.recvfrom(1024)
    except KeyboardInterrupt:
        sock.close()
        break
    print addr, data
    sock.sendto(data, addr)
