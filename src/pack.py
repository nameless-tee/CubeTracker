
class OverreadException(Exception):
	pass

def overreadAssert(value, msg="Overread"):
	if not value:
		raise OverreadException(msg)

def makeSafeRead(read):
	def r2(n, read=read):
		data = read(n)
		if len(data) != n:
			raise OverreadException("Overread")
		return data
	return r2

def toSigned_(bits, n):
	sign = n >> (bits-1)
	mask = (1 << bits) - 1
	return (((-1)^mask) * sign) | (n & mask)

class ConstBytes(object):
	def __init__(self, data, output=None):
		self.data = data
		self.output = output
	def read(self, read):
		assert(read(len(self.data)) == self.data)
		return self.output
	def write(self, write, data):
		write(self.data)

class Bytes(object):
	def __init__(self, length):
		self.length = length
	def read(self, read):
		data = read(self.length)
		assert(len(data) == self.length)
		return data
	def write(self, write, data):
		assert(len(data) == self.length)
		write(data)		

class Array(object):
	def __init__(self, tp, n):
		self.tp = tp
		self.n = n
	def write(self, write, data):
		assert(self.n == len(data))
		for i in data:
			self.tp.write(write, i)
	def read(self, read):
		return tuple(
			self.tp.read(read)
			for i in range(self.n)
		)

class Int(object):
	@staticmethod
	def write(write, n): # shared/tools.cpp #76
		if n < 128 and n > -127:
			write(bytes((n & 0xFF,)))
		else: # Merged the last two cases
			small = n < 0x8000 and n >= -0x8000
			write(
				bytes(
					(0x80 if small else 0x81,)
					+ tuple(
						(n >> (i*8)) & 0xFF
						for i in range(
							2 if small else 4
						)
					)
				)
			)
	@staticmethod
	def read(read):
		c = read(1)[0]
		if c == 0x81 or c == 0x80:
			l = 4 if c == 0x81 else 2
			res = 0
			for i in range(l):
				res |= ord(read(1)) << (i * 8)
			return toSigned_(8*l, res)
		else:
			return toSigned_(8, c)

class Int3(object):
	@staticmethod
	def write(write, n):
		assert(len(n) == 3)
		for i in n:
			Int.write(write, i)
	@staticmethod
	def read(read):
		return tuple(Int.read(read) for i in range(3))

class Int3Scaled(object):
	def __init__(self, scale):
		self.scale = scale
	def write(self, write, n):
		Int3.write(
			write,
			tuple(
				int(i / self.scale+0.5)
				for i in n
			)
		)
	def read(self, read):
		return tuple(
			i * self.scale
			for i in Int3.read(read)
		)

DMF_Scale = 1.0/16.0
DNF_Scale = 1.0/100.0

Int3DMF = Int3Scaled(DMF_Scale)
Int3DNF = Int3Scaled(DNF_Scale)

class UInt(object):
	@staticmethod
	def write(write, n):
		bts = []
		while True:
			if n >= 0x80:
				bts.append((n & 0x7F) | 0x80)
			else:
				bts.append(n)
				break
			n >>= 7
		write(bytes(bts))
	@staticmethod
	def read(read):
		res = 0
		shift = 0
		while True:
			n = read(1)[0]
			res |= (n & 0x7F) << shift
			shift += 7
			if 0 == n & 0x80:
				return res

import struct
float_struct = struct.Struct("<f")

class Float(object):
	@staticmethod
	def write(write, f):
		write(float_struct.pack(f))
	@staticmethod
	def read(read):
		return float_struct.unpack(read(4))[0]

# This is a rather shitty way to encode a string
class ByteString(object):
	@staticmethod
	def write(write, s):
		for c in s:
			assert(c != 0)
			Int.write(write, c)
		Int.write(write, 0)
	@staticmethod
	def read(read):
		buf = []
		while True:
			c = read(1)[0]
			if not (0 < c <= 0xFF):
				break
			buf.append(c)
		return bytes(buf)

# This is a more reasonable way to encode a string
class SubBuffer(object):
	@staticmethod
	def write(write, s):
		UInt.write(write, len(s))
		write(s)
	@staticmethod
	def read(read):
		l = UInt.read(read)
		data = read(l)
		assert(len(data) == l)
		return data

class TypedSubBuffer(object):
	def __init__(self, tp):
		self.tp = tp
	def write(self, write, s):
		data = toBytes(self.tp.write, s)
		SubBuffer.write(write, data)
	def read(self, read):
		data = SubBuffer.read(read)
		return fromBytes(self.tp.read, data)

class Empty(object):
	@staticmethod
	def write(write, data):
		assert(data == None)
	@staticmethod
	def read(read):
		return None

class NamedFields(object):
	def __init__(self, fields):
		self.fields = fields
	def write(self, write, data, ignoreUnused=False):
		assert(len(data) == len(self.fields) or ignoreUnused)
		for name, tp in self.fields:
			tp.write(write, data[name])
	def read(self, read):
		data = dict()
		for name, tp in self.fields:
			data[name] = tp.read(read)
		return data

class Branch(object):
	def __init__(self, branches):
		self.branches = branches
		self.by_name = dict()
		self.by_id = dict()
		i = 0
		for branch in self.branches:
			if len(branch) == 2:
				branch = branch + (i,)
			elif len(branch) == 3:
				pass
			else:
				assert(False)
			self.by_name[branch[0]] = branch
			self.by_id[branch[2]] = branch
			i = branch[2]+1
	def write(self, write, data):
		branch = self.by_name[data[0]]
		Int.write(write, branch[2])
		branch[1].write(write, data[1])
	def read(self, read):
		branch = self.by_id[Int.read(read)]
		return (
			branch[0],
			branch[1].read(read)
		)

def optAttrib(obj, attr, alt=None):
	try:
		return obj.__getattribute__(obj, attr)
	except AttributeError:
		return alt

class PacketHandler(object):
	def __init__(self):
		self.pack_types = dict()
		self.pack_classes = dict()
		self.pack_names = dict()
		self.type_num = 0
	def register(self, tp):
		index = optAttrib(tp, "index")
		if index is not None:
			self.type_num = index
		assert(self.type_num not in self.pack_types)
		self.pack_types[self.type_num] = tp
		self.pack_classes[tp] = self.type_num
		self.pack_names[tp.__name__] = self.type_num
		self.type_num += 1
		return tp
	def read(self, read):
		iD = Int.read(read)
		# ~ assert(iD in self.pack_types)
		if iD in self.pack_types:
			tp = self.pack_types[iD]
			return (tp, tp.packer.read(read))
		else:
			return (None, iD)
	def write(self, write, data):
		tp, data = data
		iD = self.pack_classes[tp]
		Int.write(write, iD)
		tp.packer.write(write, data)

import io

def toBytes(fun, data):
	buf = io.BytesIO()
	fun(buf.write, data)
	buf.seek(0)
	return buf.read()

def fromBytes(fun, s):
	buf = io.BytesIO(s)
	return fun(buf.read)

def testInverse(tp, data, comp = lambda a, b: a == b):
	buf = io.BytesIO()
	tp.write(buf.write, data)
	buf.seek(0)
	res = tp.read(buf.read)
	assert(buf.tell() == buf.getbuffer().nbytes)
	assert(comp(data, res))
