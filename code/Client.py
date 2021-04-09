from tkinter import *
import tkinter.messagebox
from tkinter.ttk import Progressbar
from PIL import Image, ImageTk, ImageFile
import socket, threading, sys, traceback, os
from time import time
from datetime import datetime

from RtpPacket import RtpPacket

ImageFile.LOAD_TRUNCATED_IMAGES = True

CACHE_FILE_NAME = "cache-"
CACHE_FILE_EXT = ".jpg"

class NetworkStatistics:
	"""Initiate a new sesstion stat for a every new session"""
	def __init__(self):
		self.lossRate = 0.0
		self.receivedPacketCount = 0
		self.totalADR = 0
		self.ADR = 0
		self.startDate = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
		self.startTime = time()

	def computeLoss(self, sendingFrameNum, receiveFrameNum):
		try:
			self.lossRate = ((sendingFrameNum - receiveFrameNum) / sendingFrameNum) * 100
		except:
			None

	def computeADR(self):
		try:
			self.ADR = self.totalADR / self.receivedPacketCount
		except:
			None

	def exportLogFile(self, sessionId):
		writeList = [
					"Session ID: " + str(sessionId),
					"\n" + self.startDate + " - " + datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
					"\nSession time: " + str(round(time() - self.startTime, 1)) + " (s)",
					"\nPacket loss rate: " + str(round(self.lossRate, 1)) + " (%)",
					"\nAverage downloading rate: " + str(round(self.ADR, 1)) + " (Bps)"
				]

		fileName = "log-" + str(sessionId) + ".txt"
		logFile = open(fileName, "w")
		logFile.writelines(writeList)
		logFile.close()

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

		self.INIT = 0
		self.READY = 1
		self.PLAYING = 2
		self.state = self.INIT
	
		self.SETUP = 'SETUP'
		self.PLAY = 'PLAY'
		self.PAUSE = 'PAUSE'
		self.TEARDOWN = 'TEARDOWN'
		self.DESCRIBE = 'DESCRIBE'
		

	def describeWindow(self, sessionId, fileName, streamType, encodingType, connectionType):
		window = Toplevel()
		window.title('Session Info')
		label = Label(window, text="Session ID: " + sessionId)
		label.pack(fill='x', padx=50, pady=5)
		label1 = Label(window, text="File name: " + fileName)
		label1.pack(fill='x', padx=50, pady=5)
		label2 = Label(window, text="Stream type: !" + streamType)
		label2.pack(fill='x', padx=50, pady=5)
		label3 = Label(window, text="Encoding type: !" + encodingType)
		label3.pack(fill='x', padx=50, pady=5)
		label4 = Label(window, text="Connection type: !" + connectionType)
		label4.pack(fill='x', padx=50, pady=5)

		closeButton = Button(window, text="Close", command=window.destroy)
		closeButton.pack(fill='x')

	def createWidgets(self):
		"""Build GUI."""
		# Create Setup button
		self.setup = Button(self.master, width=20, padx=3, pady=3)
		self.setup["text"] = "Setup"
		self.setup["command"] = self.setupMovie
		self.setup.grid(row=2, column=0, padx=2, pady=2)
		
		# Create Play button		
		self.start = Button(self.master, width=20, padx=3, pady=3)
		self.start["text"] = "Play"
		self.start["command"] = self.playMovie
		self.start.grid(row=2, column=1, padx=2, pady=2)
		
		# Create Pause button			
		self.pause = Button(self.master, width=20, padx=3, pady=3)
		self.pause["text"] = "Pause"
		self.pause["command"] = self.pauseMovie
		self.pause.grid(row=2, column=2, padx=2, pady=2)
		
		# Create Teardown button
		self.teardown = Button(self.master, width=20, padx=3, pady=3)
		self.teardown["text"] = "Teardown"
		self.teardown["command"] =  self.exitClient
		self.teardown.grid(row=2, column=3, padx=2, pady=2)

		# Create a label to display the movie
		self.label = Label(self.master, height=19)
		self.label.grid(row=1, column=0, columnspan=4, sticky=W+E+N+S, padx=5, pady=5)

		# Create a remaining timer
		self.time = Label(self.master, text="Time Left: ", width=8, heigh=2)
		self.time.grid(row=3, column=3, padx=0, pady=0)

		# Create a progress bar
		self.progress = Progressbar(self.master, orient=HORIZONTAL, length=100, mode='determinate')
		self.progress.grid(row=3, column=0, columnspan=1, padx=2, pady=0)
		
		# Create forward button
		self.forward = Button(self.master, width=10, padx=3, pady=3)
		self.forward["text"] = "Forward"
		self.forward["command"] =  self.forwardMovie
		self.forward.grid(row=3, column=1, padx=2, pady=2)

		# Create backward button
		self.backward = Button(self.master, width=10, padx=3, pady=3)
		self.backward["text"] = "Backward"
		self.backward["command"] =  self.backwardMovie
		self.backward.grid(row=3, column=2, padx=2, pady=2)

		#Create Descibe button
		self.describe = Button(self.master, width=10, padx=3, pady=3)
		self.describe["text"] = "Describe"
		self.describe["command"] = self.describeSession
		self.describe.grid(row=0, column=0, padx=2, pady=2)	
	
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
			self.networkStat = NetworkStatistics()

	def exitClient(self):
		"""Teardown button handler."""
		if (self.state == self.READY or self.state == self.PLAYING):
			self.state = self.INIT
			self.sendRtspRequest(self.TEARDOWN)
			reply = self.recvRtspReply()
			
			replyEle = self.parseRtspReply(reply)
			totalSendPacketCount = int(replyEle[3][1])

			print(reply)
			if (reply.split('\n')[0] == "RTSP/1.0 200 OK"):
				if os.path.exists(self.cacheFile):
					os.remove(self.cacheFile)
				self.rtpSocket_client.close()
				self.networkStat.computeLoss(totalSendPacketCount, self.networkStat.receivedPacketCount)
				self.networkStat.computeADR()
				self.networkStat.exportLogFile(self.sessionId)

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
	
	def describeSession(self):
		"""Describe button handler."""
		self.sendRtspRequest(self.DESCRIBE)
		reply = self.recvRtspReply()
		print(reply)
		replyEle = self.parseRtspReply(reply)
		self.describeWindow(replyEle[2][1], replyEle[3][1], replyEle[4][1], replyEle[5][1], replyEle[6][1])

	def listenRtp(self):		
		"""Listen for RTP packets and decode."""
		while True:
			startTime = time()
			data, address = self.rtpSocket_client.recvfrom(16384)
			endTime = time()

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

				self.networkStat.receivedPacketCount += 1
				self.networkStat.totalADR += (sys.getsizeof(data) / (endTime - startTime))
					
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
		self.rtspSeq = self.rtspSeq + 1
		requestCodetMsg = requestCode + " " + self.fileName + " " + "RTSP/1.0"
		requestSeqMsg = "\n" + "CSeq:" + " " + str(self.rtspSeq)

		if (requestCode == self.SETUP):
			requestHeader = "\n" + "Transport" + " " + "RTP/UDP;" + " " + "client_port=" + " " + str(self.rtpPort)
			requestPacket = requestCodetMsg + requestSeqMsg + requestHeader
			self.rtspSocket_client.sendall(bytes(requestPacket, "utf-8"))
	
		elif (requestCode == self.PLAY or requestCode == self.PAUSE or requestCode == self.TEARDOWN or requestCode == self.DESCRIBE):
			requestSession = "\n" + "Session:" + " " + str(self.sessionId)
			requestPacket = requestCodetMsg + requestSeqMsg + requestSession
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
		if (self.state != self.INIT):
			self.sendRtspRequest(self.TEARDOWN)
			reply = self.recvRtspReply()
			
			replyEle = self.parseRtspReply(reply)
			totalSendPacketCount = int(replyEle[3][1])

			if (reply.split('\n')[0] == "RTSP/1.0 200 OK"):
				self.networkStat.computeLoss(totalSendPacketCount, self.networkStat.receivedPacketCount)
				self.networkStat.computeADR()
				self.networkStat.exportLogFile(self.sessionId)
			
		if os.path.exists(self.cacheFile):
			os.remove(self.cacheFile)
		try:
			self.rtpSocket_client.close()
			self.rtspSocket_client.close()
		except:
			None
		self.master.destroy()
		sys.exit()
