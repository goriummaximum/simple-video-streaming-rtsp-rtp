from random import randint
import sys, traceback, threading, socket

from VideoStream import VideoStream
from RtpPacket import RtpPacket

class ServerWorker:
	SETUP = 'SETUP'
	PLAY = 'PLAY'
	PAUSE = 'PAUSE'
	TEARDOWN = 'TEARDOWN'
	FORWARD = 'FORWARD'
	BACKWARD = 'BACKWARD'
	DESCRIBE = 'DESCRIBE'
	
	
	INIT = 0
	READY = 1
	PLAYING = 2
	state = INIT
	skipMovie = 0
	backMovie = 0
	flagSkip = 0
	flagBack = 0
	currentFrameNbr = 0


	OK_200 = 0
	FILE_NOT_FOUND_404 = 1
	CON_ERR_500 = 2
	
	clientInfo = {}
	
	def __init__(self, clientInfo):
		self.clientInfo = clientInfo
		
	def run(self):
		threading.Thread(target=self.recvRtspRequest).start()
	
	def recvRtspRequest(self):
		"""Receive RTSP request from the client."""
		connSocket = self.clientInfo['rtspSocket'][0]
		while True:            
			data = connSocket.recv(256)
			if data:
				print("C: " + self.clientInfo['rtspSocket'][1][0] + 
					":" + str(self.clientInfo['rtspSocket'][1][1]) + 
					"\n" + data.decode("utf-8"))
				self.processRtspRequest(data.decode("utf-8"))
	
	def processRtspRequest(self, data):
		"""Process RTSP request sent from the client."""
		# Get the request type
		request = data.split('\n')
		line1 = request[0].split(' ')
		self.requestType = line1[0]
		
		# Get the media file name
		self.filename = line1[1]
		
		# Get the RTSP sequence number 
		seq = request[1].split(' ')
		
		# Process SETUP request
		if self.requestType == self.SETUP:
			if self.state == self.INIT:
				# Update state
				print("\nprocessing SETUP\n")
				
				try:
					self.clientInfo['videoStream'] = VideoStream(self.filename)
					self.state = self.READY
				except IOError:
					self.replyRtsp(self.FILE_NOT_FOUND_404, seq[1])
				
				# Generate a randomized RTSP session ID
				self.clientInfo['session'] = randint(100000, 999999)
				
				# Send RTSP reply
				self.replyRtsp(self.OK_200, seq[1], totalFrameNum= self.clientInfo['videoStream'].totalFrameNum)
				self.clientInfo['totalSendPacketCount'] = 0
				
				# Get the RTP/UDP port from the last line
				self.clientInfo['rtpPort'] = request[2].split(' ')[3]
		
		# Process PLAY request 		
		elif self.requestType == self.PLAY:
			if self.state == self.READY:
				print("\nprocessing PLAY\n")
				self.state = self.PLAYING
				
				# Create a new socket for RTP/UDP
				self.clientInfo["rtpSocket"] = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
				self.replyRtsp(self.OK_200, seq[1])
				
				# Create a new thread and start sending RTP packets
				self.clientInfo['event'] = threading.Event()
				self.clientInfo['worker']= threading.Thread(target=self.sendRtp) 
				self.clientInfo['worker'].start()
		
		# Process PAUSE request
		elif self.requestType == self.PAUSE:
			if self.state == self.PLAYING:
				print("\nprocessing PAUSE\n")
				self.state = self.READY
				
				self.clientInfo['event'].set()
			
				self.replyRtsp(self.OK_200, seq[1])
		
		# Process TEARDOWN request
		elif self.requestType == self.TEARDOWN:
			print("\nprocessing TEARDOWN\n")
			self.state = self.INIT
			self.replyRtsp(self.OK_200, seq[1], totalSendPacketCount=self.clientInfo['totalSendPacketCount'])
			try:
				self.clientInfo['event'].set()
				self.clientInfo['rtpSocket'].close()
			except:
				None

		# Process DESCRIBE request
		elif self.requestType == self.DESCRIBE:
			print("\nprocessing DESCRIBE\n")
			self.replyRtsp(self.OK_200, seq[1])

		# Process FORWARD request
		elif self.requestType == self.FORWARD:
			if self.state == self.PLAYING:
				print("\nprocessing FORWARD\n")
				self.skipMovie = 1
				self.replyRtsp(self.OK_200, seq[1])

		# Process BACKWARD request
		elif self.requestType == self.BACKWARD:
			if self.state == self.PLAYING:
				print("\nprocessing BACKWARD\n")
				self.clientInfo['videoStream'] = VideoStream(self.filename)
				self.backMovie = 1
				self.replyRtsp(self.OK_200, seq[1])
		
			
	def sendRtp(self):
		"""Send RTP packets over UDP."""
		while True:
			self.clientInfo['event'].wait(0.05) 

			# Stop sending if request is PAUSE or TEARDOWN
			if self.clientInfo['event'].isSet():
				break
				
			if self.skipMovie == 1:
				for i in range(1, 50):
					self.clientInfo['videoStream'].nextFrame()
					
				self.skipMovie = 0

			if self.backMovie == 1:
				for i in range(1, self.currentFrameNbr - 50):
					self.clientInfo['videoStream'].nextFrame()
				
				self.backMovie = 0

			self.currentFrameNbr = self.clientInfo['videoStream'].frameNbr()
			data = self.clientInfo['videoStream'].nextFrame()

			if data: 
				frameNumber = self.clientInfo['videoStream'].frameNbr()

				self.clientInfo['totalSendPacketCount'] += 1
				try:
					address = self.clientInfo['rtspSocket'][1][0]
					port = int(self.clientInfo['rtpPort'])
					self.clientInfo['rtpSocket'].sendto(self.makeRtp(data, frameNumber),(address,port))
				except:
					print("Connection Error")
					#print('-'*60)
					#traceback.print_exc(file=sys.stdout)
					#print('-'*60)

	def makeRtp(self, payload, frameNbr):
		"""RTP-packetize the video data."""
		version = 2
		padding = 0
		extension = 0
		cc = 0
		marker = 0
		pt = 26 # MJPEG type
		seqnum = frameNbr
		ssrc = 0 
		
		rtpPacket = RtpPacket()
		
		rtpPacket.encode(version, padding, extension, cc, seqnum, marker, pt, ssrc, payload)
		
		return rtpPacket.getPacket()
		
	def replyRtsp(self, code, seq, totalFrameNum = -1, totalSendPacketCount = -1):
		"""Send RTSP reply to the client."""
		if code == self.OK_200:
			try:
				reply = 'RTSP/1.0 200 OK\nCSeq: ' + seq + '\nSession: ' + str(self.clientInfo['session'])
			except:
				reply = 'RTSP/1.0 200 OK\nCSeq: ' + seq + '\nSession: NA'

			if (self.requestType == self.SETUP):
				reply = reply + '\nTotalFrame: ' + str(totalFrameNum)
			
			elif (self.requestType == self.TEARDOWN):
				reply = reply + '\nTotalSendPacketCount: ' + str(totalSendPacketCount)
			
			elif (self.requestType == self.DESCRIBE):
				reply = reply + '\nFileName: ' + self.filename + '\nStreamType: real-time' + '\nencodingType: MJPEG' + '\nConnectionType: RTP/RTSP1.0'

			connSocket = self.clientInfo['rtspSocket'][0]
			connSocket.send(reply.encode())
			print("S: \n" + reply + "\n----------")
		
		# Error messages
		elif code == self.FILE_NOT_FOUND_404:
			print("404 NOT FOUND")
		elif code == self.CON_ERR_500:
			print("500 CONNECTION ERROR")
