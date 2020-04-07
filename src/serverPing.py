import socket
import protocol
import pack
import sys
import time

target = (sys.argv[1], int(sys.argv[2]))
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

pl = b"" #b"\x01Hallo"
# ~ sock.sendto(b"\xff\xff"+pl, target)
# ~ sock.sendto(b"\x00\x01"+pack.toBytes(pack.Int.write, -1)+b"HelloThisIsNotGoodHelloThisIsNotGoodHelloThisIsNotGoodHelloThisIsNotGood"[:29], target)

# ~ data = b"\x00\x01"+pack.toBytes(pack.Int.write, -1)
data = b"\x01"

print("request", data)

sock.sendto(data, target)

sock.settimeout(.3)
try:
	while True:
		res = sock.recvfrom(1024*8)[0][len(pl):]
		print(repr(res))
		
		for i in range(100000):
			unpacked = pack.fromBytes(protocol.SauerPong(pack.Empty).read, res)
			# ~ print(unpacked)
			packed = pack.toBytes(protocol.SauerPong(pack.Empty).write, unpacked)
			# ~ print(packed)
		t = time.time() - t
except socket.timeout:
	pass
# ~ print(pack.fromBytes(protocol.SauerPongTail.read, res))
