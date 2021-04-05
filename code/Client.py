from tkinter import *
import tkinter.messagebox
from PIL import Image, ImageTk
import socket, threading, sys, traceback, os

from RtpPacket import RtpPacket

CACHE_FILE_NAME = "cache-"
CACHE_FILE_EXT = ".jpg"

class Client:
	INIT = 0
	READY = 1
	PLAYING = 2
	state = INIT
	
	SETUP = 0
	PLAY = 1
	PAUSE = 2
	TEARDOWN = 3
	
	# Initiation..
	def __init__(self, master, serveraddr, serverport, rtpport, filename):
		self.master = master
		self.master.protocol("WM_DELETE_WINDOW", self.handler)
		self.createWidgets()
		self.serverAddr = serveraddr
		self.serverPort = int(serverport)
		self.rtpPort = int(rtpport)
		self.fileName = filename
		self.rtspSeq = 0
		self.sessionId = 0
		self.requestSent = -1
		self.teardownAcked = 0
		self.connectToServer()
		self.frameNbr = 0
		
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
	
	def setupMovie(self):
		"""Setup button handler."""
		self.sendRtspRequest(self.SETUP)
		reply = self.recvRtspReply()
		self.sessionId = self.parseRtspReply(reply)
		self.openRtpPort()

		print(self.sessionId)

	def exitClient(self):
		"""Teardown button handler."""
		self.sendRtspRequest(self.TEARDOWN)
		reply = self.recvRtspReply()

		print(reply)

	def pauseMovie(self):
		"""Pause button handler."""
		self.sendRtspRequest(self.PAUSE)
		reply = self.recvRtspReply()

		print(reply)
	
	def playMovie(self):
		"""Play button handler."""
		self.sendRtspRequest(self.PLAY)
		reply = self.recvRtspReply()

		print(reply)
	
	def listenRtp(self):		
		"""Listen for RTP packets."""
		#TODO
					
	def writeFrame(self, data):
		"""Write the received frame to a temp image file. Return the image file."""
	#TODO
	
	def updateMovie(self, imageFile):
		"""Update the image file as video frame in the GUI."""
	#TODO
		
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
		replayLines = data.split('\n')
		return int(replayLines[2].split(' ')[1])

	
	def openRtpPort(self):
		"""Open RTP socket binded to a specified port."""
		self.rtpSocket_client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		self.rtpSocket_client.settimeout(0.5)

	def handler(self):
		"""Handler on explicitly closing the GUI window."""
		self.master.destroy()
