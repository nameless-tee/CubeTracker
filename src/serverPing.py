import socket
import protocol
import pack

SimpleInfoHead = pack.NamedFields((
	("version", pack.Int),
	("numClients", pack.Int),
	("maxClients", pack.Int),
	("paused", pack.Int),
	("mode", pack.Int),
	("timelimit", pack.Int),
	("masterMode", pack.Int),
))

SimpleInfoOpt = pack.NamedFields((
	("paused", pack.Int),
	("speed", pack.Int),
))

SimpleInfoFoot = pack.NamedFields((
	("map", pack.ByteString),
	("description", pack.ByteString),
))

class SimpleInfo:
	@staticmethod
	def read(read):
		head = SimpleInfoHead.read(read)
		if head["paused"] == 5:
			tmp = SimpleInfoOpt.read(read)
			head["paused"] = tmp["paused"]
			head["speed"] = tmp["speed"]
		else:
			head["paused"] = 0
			head["speed"] = 100
		foot = SimpleInfoFoot.read(read)
		for k, v in foot.items():
			head[k] = v
		return head

target = ("127.0.0.1", 42000)
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
pl = b"\x01Hallo"
sock.sendto(b"\xff\xff"+pl, target)
sock.settimeout(10)
res = sock.recvfrom(1024*8)[0][len(pl):]
print(repr(res))
print(pack.fromBytes(SimpleInfo.read, res))
