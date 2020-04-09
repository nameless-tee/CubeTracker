import socket
import protocol
import pack
import sys
import time
import traceback
import json

if len(sys.argv) != 4:
	sys.stderr.write("Usage: python serverPing.py <sauer/tesser> <host> <port>\n")
	exit(1)

# ~ game = "sauer"
game = sys.argv[1]
payload = None
payloadType = pack.Empty
target = (sys.argv[2], int(sys.argv[3]))

pingType, pongType = (
	i(payloadType) for i in ({
		"tesser" : (protocol.TesserPing, protocol.TesserPong),
		"sauer" : (protocol.SauerPing, protocol.SauerPong),
	})[game]
)


pingDatas = [
	{
		"head" : {
			"type" : "ping",
			"arg" : 1,
			"ext" : None,
		},
		"payload" : payload,
	},
	{
		"head" : {
			"type" : "ext",
			"arg" : -1,
			"ext" : "stats",
		},
		"payload" : payload,
	},
	{
		"head" : {
			"type" : "ext",
			"arg" : 0,
			"ext" : "uptime",
		},
		"payload" : payload,
	},
	{
		"head" : {
			"type" : "ext",
			"arg" : 0,
			"ext" : "teams",
		},
		"payload" : payload,
	},
]



pings = [
	pack.toBytes(pingType.write, i)
	for i in pingDatas
]

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

for ping in pings:
	# ~ print("request", ping)
	sock.sendto(ping, target)
	time.sleep(0.001)

sock.settimeout(.3)
try:
	while True:
		response, addr = sock.recvfrom(1024*8)
		try:
			unpacked = pack.fromBytes(pongType.read, response)
			print(unpacked)
			print(json.dumps(unpacked, indent=4, sort_keys=True))
		except Exception:
			sys.stderr.write(f"Error while parsing response from: {addr}\n")
			sys.stderr.write(f"{repr(response)}\n")
			traceback.print_exc(file=sys.stderr)
except socket.timeout:
	pass
