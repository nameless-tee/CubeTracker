import pack

SAUER_MASTER_ADDR = ("master.sauerbraten.org", 28787)

TesserPongHead = pack.NamedFields((
	("version", pack.Int),
	("numClients", pack.Int),
	("maxClients", pack.Int),
	("paused", pack.Int),
	("mode", pack.Int),
	("remaining", pack.Int),
	("masterMode", pack.Int),
))

SauerPongHead = pack.NamedFields((
	("numClients", pack.Int),
	("paused", pack.Int),
	("version", pack.Int),
	("mode", pack.Int),
	("remaining", pack.Int),
	("maxClients", pack.Int),
	("masterMode", pack.Int),
))

CubePongOpt = pack.NamedFields((
	("paused", pack.Int),
	("speed", pack.Int),
))

CubePongFoot = pack.NamedFields((
	("map", pack.EncodedString),
	("description", pack.EncodedString),
))

class TesserPongTail:
	@staticmethod
	def read(read):
		head = TesserPongHead.read(read)
		if head["paused"] == 5:
			opt = CubePongOpt.read(read)
			head["paused"] = opt["paused"]
			head["speed"] = opt["speed"]
		else:
			head["paused"] = 0
			head["speed"] = 100
		foot = CubePongFoot.read(read)
		head.update(foot)
		return head

class GenericPongTail:
	def __init__(self, headType, pauseIndicators):
		self.headType = headType
		self.pauseIndicators = pauseIndicators
	def read(self, read):
		head = self.headType.read(read)
		if head["paused"] == self.pauseIndicators[0]:
			opt = CubePongOpt.read(read)
			head["paused"] = bool(opt["paused"])
			head["speed"] = opt["speed"]
		else:
			assert(head["paused"] == self.pauseIndicators[1])
			head["paused"] = False
			head["speed"] = 100
		foot = CubePongFoot.read(read)
		head.update(foot)
		return head
	def write(self, write, data):
		copy = dict(data.items())
		tmp = data["paused"]
		try:
			if data["speed"] == 100 and not data["paused"]:
				data["paused"] = self.pauseIndicators[1]
				self.headType.write(write, copy, ignoreUnused = True)
			else:
				copy["paused"] = self.pauseIndicators[0]
				self.headType.write(write, copy, ignoreUnused = True)
				CubePongOpt.write(write, {
					"paused" : 1 if tmp else 0,
					"speed" : data["speed"]
				}, ignoreUnused = True)
		finally:
			data["paused"] = tmp
		CubePongFoot.write(write, data, ignoreUnused = True)

SauerPongTail = GenericPongTail(SauerPongHead, (7, 5))
TesserPongTail = GenericPongTail(TesserPongHead, (5, 3))

class IP(object):
	@staticmethod
	def read(read):
		ip = read(3)
		assert(len(ip) == 3)
		return (ip[0] << 16) | (ip[1] << 8) | ip[2]
	def write(write, ip):
		assert(ip >> 24 == 0)
		write(
			(ip >> 16),
			(ip >> 8) & 0xFF,
			(ip >> 0) & 0xFF,
		)

CubeExtPlayer = pack.NamedFields((
	("num", pack.Int),
	("ping", pack.Int),
	("name", pack.EncodedString),
	("team", pack.EncodedString),
	("frags", pack.Int),
	("flags", pack.Int),
	("deaths", pack.Int),
	("teamkills", pack.Int),
	("damage", pack.Int),
	("health", pack.Int),
	("armour", pack.Int),
	("weapon", pack.Int),
	("priviledge", pack.Int),
	("state", pack.Int),
	("ip", IP),
))

CubeExtHead = pack.NamedFields((
	("ack", pack.ConstBytes(pack.toBytes(pack.Int.write, -1))),
	("version", pack.Int),
))

class CubeExtPlayerIDs(object):
	@staticmethod
	def read(read):
		safe = pack.makeSafeRead(read)
		ids = []
		while True:
			try:
				ids.append(pack.Int.read(safe))
			except pack.OverreadException:
				break
		return ids
	@staticmethod
	def write(write, data):
		for i in data:
			pack.Int.write(write, data[i])
		

CubeExtStats = pack.NamedFields((
	("head", CubeExtHead),
	("noerror", pack.ConstBytes(pack.toBytes(pack.Int.write, 0))), # EXT_NO_ERROR
	("data",  pack.Branch((
		("ids", CubeExtPlayerIDs, -10), # EXT_PLAYERSTATS_RESP_IDS
		("player", CubeExtPlayer, -11), # EXT_PLAYERSTATS_RESP_STATS
	)))
))

CubeExtUptime = pack.NamedFields((
	("head", CubeExtHead),
	("uptime", pack.Int),
))

CubeExtTeamsHead = pack.NamedFields((
	("head", CubeExtHead),
	("teammode", pack.Int),
	("mode", pack.Int),
	("remaining", pack.Int),
))

class CubeExtTeamsTeam(object):
	@staticmethod
	def read(read):
		safe = pack.makeSafeRead(read)
		try:
			name = pack.EncodedString.read(safe)
		except pack.OverreadException:
			return None
		score = pack.Int.read(read)
		numBases = pack.Int.read(read)
		if numBases < 0:
			bases = None
		else:
			bases = []
			for i in range(numBases):
				bases.append(pack.Int.read(read))		
		return {
			"name" : name,
			"score" : score,
			"bases" : bases,
		}
	@staticmethod
	def write(write, data):
		pack.EncodedString.write(write, data["name"])
		pack.Int.write(write, data["score"])
		if data["bases"] == None:
			pack.Int.write(write, -1)
		else:
			pack.Int.write(write, len(data["bases"]))
			for base in data["bases"]:
				pack.Int.write(write, base)

class CubeExtTeams(object):
	@staticmethod
	def read(read):
		head = CubeExtTeamsHead.read(read)
		head["teammode"] = not head["teammode"]
		teams = []
		if head["teammode"]:
			teams = []
			while (team := CubeExtTeamsTeam.read(read)) != None:
				teams.append(team)
				
		head["teams"] = teams
		return head
	@staticmethod
	def write(write, data):
		CubeExtTeamsHead.write(write, {
			"head" : data["head"],
			"teammode" : 0 if data["teammode"] else 1,
			"mode" : data["mode"],
			"remaining" : data["remaining"],
		})
		for team in data["teams"]:
			CubeExtTeamsTeam.write(write, team)


class CubePingHead(object):
	extTypes = ["uptime", "stats", "teams"]
	extIDs = dict((tp, i) for i, tp in enumerate(extTypes))
	# ~ def __init__(self, payloadType):
		# ~ self.pt = payloadType
	@classmethod
	def write(self, write, data):
		if data["type"] == "ping":
			assert(data["arg"] != 0)
			pack.Int.write(write, data["arg"])
			# ~ self.pt.write(write, data["payload"])
		elif data["type"] == "ext":
			pack.Int.write(write, 0)
			pack.Int.write(write, self.extIDs[data["ext"]])
			# Write client num
			if data["ext"] == "stats":
				pack.Int.write(write, data["arg"])
			# ~ pack.pt.write(write, data["payload"])
	@classmethod
	def read(self, read):
		arg = pack.Int.read(read)
		if arg == 0: # Ext info
			ext = self.extTypes[pack.Int.read(read)]
			arg = 0
			if ext == "stats":
				arg = pack.Int.read(read)
			return {
				"type" : "ext",
				"arg" : arg,
				"ext" : ext,
				# ~ "payload" : self.pt.read(read)
			}
		else: # Ping
			return {
				"type" : "ping",
				"arg" : arg,
				"ext" : None,
				# ~ "payload" : self.pt.read(read),
			}

class SauerPing(pack.NamedFields):
	def __init__(self, payloadType):
		super().__init__((
			("head", CubePingHead),
			("payload", payloadType),
		))

class TesserPing(SauerPing):
	def __init__(self, payloadType):
		super().__init__(payloadType)
	def write(self, write, data):
		write(b"\xff\xff")
		super().write(write, data)
	def read(self, read):
		assert(read(2) == b"\xff\xff")
		return super().read(read)

class GenericPong(object):
		extMap = {
			"stats" : CubeExtStats,
			"uptime" : CubeExtUptime,
			"teams" : CubeExtTeams,		
		}
		def __init__(self, payloadType):
			self.pt = payloadType
		def read(self, read):
			head = CubePingHead.read(read)
			# ~ print("head", head)
			pl = self.pt.read(read)
			if head["type"] == "ping":
				return {
					"head" : head,
					"payload" : pl,
					"data" : self.tailType.read(read),
				}
			elif head["type"] == "ext":
				return {
					"head" : head,
					"payload" : pl,
					"data" : self.extMap[head["ext"]].read(read),
				}
			else:
				raise ArgumentError("Invalid ping type")
		def write(self, write, data):
			CubePingHead.write(write, data["head"])
			self.pt.write(write, data["payload"])
			if data["head"]["type"] == "ping":
				self.tailType.write(write, data["data"])
			elif data["head"]["type"] == "ext":
				self.extMap[data["head"]["ext"]].write(write, data["data"])

class SauerPong(GenericPong):
	tailType = SauerPongTail

class TesserPong(GenericPong):
	tailType = TesserPongTail


