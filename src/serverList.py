import protocol
import pack
import socket
import re
import time
import traceback

def getServerListRaw():
	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	sock.connect(protocol.SAUER_MASTER_ADDR)
	sock.settimeout(5)
	sock.send(b"list\n")
	data = []
	while new := sock.recv(1024):
		data.append(new)
	return b"".join(data)

def isIP(buf):
	buf = buf.split(b".")
	if len(buf) != 4:
		return False
	try:
		for i in buf:
			if not (0 <= int(i) <= 255):
				return False
	except ValueError:
		return False
	return True

def isPort(buf):
	try:
		# Must be smaller than 65535 because ping uses n+1
		if not (1 <= int(buf) < 65535):
			return False
	except ValueError:
		return False
	return True

def isServerEntry(tpl):
	if len(tpl) != 3:
		return False
	if tpl[0] != b"addserver":
		return False
	if not isIP(tpl[1]):
		return False
	if not isPort(tpl[2]):
		return False
	return True

def getServerList():
	lst = getServerListRaw()
	print(lst)
	lst = (i.split(b" ") for i in lst.split(b"\n"))
	lst = [(j[1], int(j[2])) for j in lst if isServerEntry(j)]
	return lst

def showPings(sock, timeout):
	try:
		t = time.time()
		while (left := time.time() - t + timeout) > 0:
			sock.settimeout(left)
			data, sender = sock.recvfrom(2048)
			print(data, sender)
			try:
				print(pack.fromBytes(
					protocol.SauerPong(pack.Empty).read,
					data
				))
			except Exception as ex:
				traceback.print_exc()
	except socket.timeout:
		pass

def makePing(i = 1):
	return pack.toBytes(protocol.SauerPingHead.write, {
		"type" : "ping",
		"arg" : i,
		"ext" : None,
	})

emptyPing = protocol.SauerPing(pack.Empty)

def showPingAll():
	lst = getServerList()
	sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	for i, addr in enumerate(lst):
		# ~ ping = makePing(i+1)
		ping = pack.toBytes(emptyPing.write, {
			"head" : {
				"type" : "ext",
				"arg" : -1,
				"ext" : "stats",
			},
			"payload" : None,
		})
		sock.sendto(ping, (addr[0], addr[1]+1))
		showPings(sock, 0.01)
	showPings(sock, 5)

if __name__ == "__main__":
	showPingAll()

# ~ print(makePing())

# ~ print(getServerList())
	
