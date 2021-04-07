import sys
from time import time
HEADER_SIZE = 12

class RtpPacket:	
	header = bytearray(HEADER_SIZE)
	
	def __init__(self):
		pass
		
	def encode(self, version, padding, extension, cc, seqnum, marker, pt, ssrc, payload):
		"""Encode the RTP packet with header fields and payload."""
		self.payload = payload
		timestamp = int(time())
		header = bytearray(HEADER_SIZE)

		header[0] = version << 6 | padding << 5 | extension << 4 | cc
		header[1] = marker << 7 | pt
		header[2] = (seqnum >> 8) & 0xFF
		header[3] = seqnum & 0xFF
		
		k = 24
		for i in range(4, 8):
			header[i] = (timestamp >> k) & 0xFF
			k = k - 8
		
		k = 24
		for i in range(8, 12):
			header[i] = (ssrc >> k) & 0xFF
			k = k - 8
		
	def decode(self, byteStream):
		"""Decode the RTP packet."""
		self.header = bytearray(byteStream[:HEADER_SIZE])
		self.payload = byteStream[HEADER_SIZE:]
	
	def version(self):
		"""Return RTP version."""
		return int(self.header[0] >> 6)
	
	def seqNum(self):
		"""Return sequence (frame) number."""
		seqNum = self.header[2] << 8 | self.header[3]
		return int(seqNum)
	
	def timestamp(self):
		"""Return timestamp."""
		timestamp = self.header[4] << 24 | self.header[5] << 16 | self.header[6] << 8 | self.header[7]
		return int(timestamp)
	
	def payloadType(self):
		"""Return payload type."""
		pt = self.header[1] & 127
		return int(pt)
	
	def getPayload(self):
		"""Return payload."""
		return self.payload
		
	def getPacket(self):
		"""Return RTP packet."""
		return self.header + self.payload