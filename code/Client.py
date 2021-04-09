from tkinter import *
import tkinter.messagebox
from tkinter.ttk import Progressbar
from PIL import Image, ImageTk, ImageFile
import socket, threading, sys, traceback, os

from RtpPacket import RtpPacket

ImageFile.LOAD_TRUNCATED_IMAGES = True

CACHE_FILE_NAME = "cache-"
CACHE_FILE_EXT = ".jpg"

class NetworkStatistics:
	def __init__(self):
		self.lossRate = 0.0
		self.averageDownRate = 0.0
		
	def computeLoss(self, sendingFrameNum, receiveFrameNum):
		self.lossRate = receiveFrameNum / sendingFrameNum

	def exportLogFile(self):
		pass

class Client:
	# Initiation..
	def __init__(self, master, serveraddr, serverport, rtpport, filename):
		self.master = master
		self.master.protocol("WM_DELETE_WINDOW", self.handler)
		self.createWidgets()
		self.serverAddr = serveraddr
		self.serverPort = int(serverport)
		self.rtpPort = int(rtpport)
		self.fileName = filename
		self.cacheFile = ""
		self.rtspSeq = 0
		self.sessionId = 0
		self.requestSent = -1
		self.teardownAcked = 0
		self.connectToServer()
		self.frameNbr = 0
		self.recvRtpPacket = RtpPacket()
		self.networkStat = NetworkStatistics()

		self.INIT = 0
		self.READY = 1
		self.PLAYING = 2
		self.state = self.INIT
	
		self.SETUP = 0
		self.PLAY = 1
		self.PAUSE = 2
		self.TEARDOWN = 3
		
	# THIS GUI IS JUST FOR REFERENCE ONLY, STUDENTS HAVE TO CREATE THEIR OWN GUI 	
	def createWidgets(self):
		"""Build GUI."""
		# Create Setup button
		self.setup = Button(self.master, width=20, padx=3, pady=3)
		self.setup["text"] = "Setup"
		self.setup["command"] = self.setupMovie
		self.setup.grid(row=1, column=0, padx=2, pady=2)
		
		# Create Play button		
		self.start = Button(self.master, width=20, padx=3, pady=3)
		self.start["text"] = "Play"
		self.start["command"] = self.playMovie
		self.start.grid(row=1, column=1, padx=2, pady=2)
		
		# Create Pause button			
		self.pause = Button(self.master, width=20, padx=3, pady=3)
		self.pause["text"] = "Pause"
		self.pause["command"] = self.pauseMovie
		self.pause.grid(row=1, column=2, padx=2, pady=2)
		
		# Create Teardown button
		self.teardown = Button(self.master, width=20, padx=3, pady=3)
		self.teardown["text"] = "Teardown"
		self.teardown["command"] =  self.exitClient
		self.teardown.grid(row=1, column=3, padx=2, pady=2)
		
		# Create a label to display the movie
		self.label = Label(self.master, height=19)
		self.label.grid(row=0, column=0, columnspan=4, sticky=W+E+N+S, padx=5, pady=5)

		# Create a remaining timer
		self.time = Label(self.master, text="Time Left: ", width=8, heigh=2)
		self.time.grid(row=2, column=3, padx=0, pady=0)

		# Create a progress bar
		self.progress = Progressbar(self.master, orient=HORIZONTAL, length=100, mode='determinate')
		self.progress.grid(row=2, column=0, columnspan=1, padx=2, pady=0)
		
		# Create forward button
		self.forward = Button(self.master, width=10, padx=3, pady=3)
		self.forward["text"] = "Forward"
		self.forward["command"] =  self.forwardMovie
		self.forward.grid(row=2, column=1, padx=2, pady=2)

		# Create backward button
		self.backward = Button(self.master, width=10, padx=3, pady=3)
		self.backward["text"] = "Backward"
		self.backward["command"] =  self.backwardMovie
		self.backward.grid(row=2, column=2, padx=2, pady=2)

	def setupMovie(self):
		"""Setup button handler."""
		if (self.state == self.INIT):
			self.state = self.READY
			self.sendRtspRequest(self.SETUP)

			reply = self.recvRtspReply()
			print(reply)

			replyEle = self.parseRtspReply(reply)
			self.sessionId = replyEle[2][1]
			self.totalFrameNum = int(replyEle[3][1])
			self.totalTime = 0.05 * self.totalFrameNum
			self.progress.configure(maximum=self.totalTime)

			rtpWorker = threading.Thread(target=self.openRtpPort) 
			rtpWorker.start()

	def exitClient(self):
		"""Teardown button handler."""
		if (self.state == self.READY or self.state == self.PLAYING):
			self.state = self.INIT
			self.sendRtspRequest(self.TEARDOWN)
			reply = self.recvRtspReply()
			print(reply)
			if (reply.split('\n')[0] == "RTSP/1.0 200 OK"):
				if os.path.exists(self.cacheFile):
					os.remove(self.cacheFile)
				self.rtpSocket_client.close()

	def pauseMovie(self):
		"""Pause button handler."""
		if (self.state == self.PLAYING):
			self.state = self.READY
			self.sendRtspRequest(self.PAUSE)
			reply = self.recvRtspReply()
			print(reply)

	
	def playMovie(self):
		"""Play button handler."""
		if (self.state == self.READY):
			self.state = self.PLAYING
			self.sendRtspRequest(self.PLAY)
			reply = self.recvRtspReply()
			print(reply)

	def forwardMovie(self):
		if (self.state == self.PLAYING or self.state == self.PAUSE):
			print("bruh")

	def backwardMovie(self):
		if (self.state == self.PLAYING or self.state == self.PAUSE):
			print("bruh")
	
	def listenRtp(self):		
		"""Listen for RTP packets and decode."""
		while True:
			data, address = self.rtpSocket_client.recvfrom(16384)

			if (data):
				self.recvRtpPacket.decode(data)
				self.cacheFile = self.writeFrame(self.recvRtpPacket.getPayload())
				self.updateMovie(self.cacheFile)

				currentFrameNbr = self.recvRtpPacket.seqNum()
				current = self.totalTime - 0.05 * currentFrameNbr
				currMin = current / 60
				currSec = current % 60
				
				self.progress['value'] = 0.05 * currentFrameNbr

				if currMin < 10:
					self.time.configure(text="Time Left: 0%d:%d" % (currMin, currSec), width=12, heigh=2)
					if currSec < 10:
						self.time.configure(text="Time Left: 0%d:0%d" % (currMin, currSec), width=12, heigh=2)

				else:
					self.time.configure(text="Time Left: %d:%d" % (currMin, currSec), width=12, heigh=2)
					if currSec < 10:
						self.time.configure(text="Time Left: %d:0%d" % (currMin, currSec), width=12, heigh=2)

				print(self.recvRtpPacket.timestamp())
					
	def writeFrame(self, data):
		"""Write the received frame to a temp image file. Return the image file."""
		cacheFile = CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT
		f = open(cacheFile, "wb")
		f.write(data)
		f.close()

		return cacheFile
	
	def updateMovie(self, imageFile):
		"""Update the image file as video frame in the GUI."""
		frame = ImageTk.PhotoImage(Image.open(imageFile))
		self.label.configure(image=frame, height=300)
		self.label.image = frame
		
	def connectToServer(self):
		"""Connect to the Server. Start a new RTSP/TCP session."""
		self.rtspSocket_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		try:
			self.rtspSocket_client.connect((self.serverAddr, self.serverPort))
		except:
			print("Fail to connect to server")
	
	def sendRtspRequest(self, requestCode):
		"""Send RTSP request to the server."""
		requestCode_list = ["SETUP", "PLAY", "PAUSE", "TEARDOWN"]
		if (requestCode == self.SETUP):
			self.rtspSeq = self.rtspSeq + 1
			requesCodetMsg = requestCode_list[requestCode] + " " + self.fileName + " " + "RTSP/1.0"
			requestSeqMsg = "\n" + "CSeq:" + " " + str(self.rtspSeq)
			requestHeader = "\n" + "Transport" + " " + "RTP/UDP;" + " " + "client_port=" + " " + str(self.rtpPort)
			requestPacket = requesCodetMsg + requestSeqMsg + requestHeader
			self.rtspSocket_client.sendall(bytes(requestPacket, "utf-8"))
	
		elif (requestCode == self.PLAY or requestCode == self.PAUSE or requestCode == self.TEARDOWN):
			self.rtspSeq = self.rtspSeq + 1
			requesCodetMsg = requestCode_list[requestCode] + " " + self.fileName + " " + "RTSP/1.0"
			requestSeqMsg = "\n" + "CSeq:" + " " + str(self.rtspSeq)
			requestSession = "\n" + "Session:" + " " + str(self.sessionId)
			requestPacket = requesCodetMsg + requestSeqMsg + requestSession
			self.rtspSocket_client.sendall(bytes(requestPacket, "utf-8"))
		
	
	def recvRtspReply(self):
		"""Receive RTSP reply from the server."""
		return self.rtspSocket_client.recv(256).decode("utf-8")
	
	def parseRtspReply(self, data):
		"""Parse the RTSP reply from the server."""
		replyLines = data.split('\n')
		replyEle = []
		for line in replyLines:
			replyEle.append(line.split(' '))
		return replyEle

	
	def openRtpPort(self):
		"""Open RTP socket binded to a specified port."""
		while True:
			try:
				self.rtpSocket_client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
				self.rtpSocket_client.bind(('', self.rtpPort))
				self.rtpSocket_client.settimeout(0.5)
				self.listenRtp()
			except Exception as err:
				print(err)
				if (str(err) == "[Errno 9] Bad file descriptor"):
					break

	def handler(self):
		"""Handler on explicitly closing the GUI window."""
		if os.path.exists(self.cacheFile):
			os.remove(self.cacheFile)
		self.rtpSocket_client.close()
		self.rtspSocket_client.close()
		self.master.destroy()
		sys.exit()
