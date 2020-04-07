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
	("map", pack.ByteString),
	("description", pack.ByteString),
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

class SauerPongTail:
	@staticmethod
	def read(read):
		head = SauerPongHead.read(read)
		if head["paused"] == 7:
			opt = CubePongOpt.read(read)
			head["paused"] = bool(opt["paused"])
			head["speed"] = opt["speed"]
		else:
			head["paused"] = False
			head["speed"] = 100
		foot = CubePongFoot.read(read)
		head.update(foot)
		return head
	@staticmethod
	def write(write, data):
		copy = dict(data.items())
		tmp = data["paused"]
		try:
			if data["speed"] == 100 and not data["paused"]:
				data["paused"] = 5
				SauerPongHead.write(write, copy, ignoreUnused = True)
			else:
				copy["paused"] = 7
				SauerPongHead.write(write, copy, ignoreUnused = True)
				CubePongOpt.write(write, {
					"paused" : 1 if tmp else 0,
					"speed" : data["speed"]
				}, ignoreUnused = True)
		finally:
			data["paused"] = tmp
		CubePongFoot.write(write, data, ignoreUnused = True)
		

SauerExtPlayer = pack.NamedFields((
	("num", pack.Int),
	("ping", pack.Int),
	("name", pack.ByteString),
	("team", pack.ByteString),
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
	("ip", pack.Bytes(3)),
))

# ~ class S

SauerExtHead = pack.NamedFields((
	("ack", pack.ConstBytes(pack.toBytes(pack.Int.write, -1))),
	("version", pack.Int),
))

class SauerExtPlayerIDs(object):
	@classmethod
	def read(self, read):
		safe = pack.makeSafeRead(read)
		ids = []
		while True:
			try:
				ids.append(pack.Int.read(safe))
			except pack.OverreadException:
				break
		return ids

SauerExtStats = pack.NamedFields((
	("head", SauerExtHead),
	("noerror", pack.ConstBytes(pack.toBytes(pack.Int.write, 0))), # EXT_NO_ERROR
	("data",  pack.Branch((
		("ids", SauerExtPlayerIDs, -10), # EXT_PLAYERSTATS_RESP_IDS
		("player", SauerExtPlayer, -11), # EXT_PLAYERSTATS_RESP_STATS
	)))
))

SauerExtTeamsHead = pack.NamedFields((
	("head", SauerExtHead),
	("teammode", pack.Int),
	("mode", pack.Int),
	("remaining", pack.Int),
))

class SauerExtTeamsTeam(object):
	@staticmethod
	def read(read):
		safe = pack.makeSafeRead(read)
		try:
			name = pack.ByteString.read(safe)
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
		pack.ByteString.write(write, data["name"])
		pack.Int.write(write, data["score"])
		if data["bases"] == None:
			pack.Int.write(write, -1)
		else:
			pack.Int.write(write, len(data["bases"]))
			for base in data["bases"]:
				pack.Int.write(write, base)

class SauerExtTeams(object):
	@staticmethod
	def read(read):
		head = SauerExtTeamsHead.read(read)
		head["teammode"] = not head["teammode"]
		teams = []
		if head["teammode"]:
			teams = []
			while (team := SauerExtTeamsTeam.read(read)) != None:
				teams.append(team)
				
		head["teams"] = teams
		return head
	@staticmethod
	def write(write, data):
		SauerExtTeamsHead.write(write, {
			"head" : data["head"],
			"teammode" : 0 if data["teammode"] else 1,
			"mode" : data["mode"],
			"remaining" : data["remaining"],
		})
		for team in data["teams"]:
			SauerExtTeamsTeam.write(write, team)


class SauerPingHead(object):
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



class SauerPong(object):
	extMap = {
		"stats" : SauerExtStats,
		"uptime" : pack.Int,
		"teams" : SauerExtTeams,		
	}
	def __init__(self, payloadType):
		self.pt = payloadType
	def read(self, read):
		head = SauerPingHead.read(read)
		pl = self.pt.read(read)
		if head["type"] == "ping":
			return {
				"head" : head,
				"data" : SauerPongTail.read(read),
				"payload" : pl,
			}
		elif head["type"] == "ext":
			return {
				"head" : head,
				"data" : self.extMap[head["ext"]].read(read),
				"payload" : pl,
			}
		else:
			raise ArgumentError("Invalid ping type")
	def write(self, write, data):
		SauerPingHead.write(write, data["head"])
		self.pt.write(write, data["payload"])
		if data["head"]["type"] == "ping":
			SauerPongTail.write(write, data["data"])
		elif data["head"]["type"] == "ext":
			self.extMap[data["head"]["ext"]].write(write, data["data"])


# ~ class SauerExtStats(object):
	# ~ @staticmethod
	# ~ def read(read):
		

# ~ class SauerExtHead(object):
	# ~ ACK = pack.ConstBytes(pack.toBytes(pack.Int.write, -1))
	# ~ VER = pack.ConstBytes(pack.toBytes(pack.Int.write, 105))
	# ~ @staticmethod
	# ~ def read(read):
		# ~ self.ACK.read(read)
		# ~ self.VER.read(read)


