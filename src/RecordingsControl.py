#!/usr/bin/python
# encoding: utf-8
#
# Copyright (C) 2011 by Coolman & Swiss-MAD
#
# In case of reuse of this source code please do not remove this copyright.
#
#	This program is free software: you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation, either version 3 of the License, or
#	(at your option) any later version.
#
#	This program is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.
#
#	For more information on the GNU General Public License see:
#	<http://www.gnu.org/licenses/>.
#

import pickle, os
from collections import defaultdict

from Components.config import config
from RecordTimer import AFTEREVENT
import NavigationInstance

from EMCTasker import emcTasker, emcDebugOut
from DelayedFunction import DelayedFunction

def getRecording(filename):
	try:
		if filename[0] == "/": 			filename = os.path.basename(filename)
		if filename.endswith(".ts"):	filename = filename[:-3]

		for timer in NavigationInstance.instance.RecordTimer.timer_list:
			try: timer.Filename
			except: timer.calculateFilename()
			if filename == os.path.basename(timer.Filename):
				return timer.begin, timer.end, timer.service_ref.ref
	except Exception, e:
		emcDebugOut("[emcRC] getRecording exception:\n" + str(e))
	return None


class NetworkAwareness:
	def __init__(self):
		self.retries = 0
		self.ip = None
		self.initialized = False

	def whatIsMyIP(self):
		if not self.initialized: self.ipLookup()
		return self.ip

	def ipLookup(self):
		os.system("ifconfig | grep Bcast | sed 's;^.*addr:;;' | sed 's: .*::' >/tmp/myip")
		file = open("/tmp/myip")
		myip = file.read()
		file.close()
		self.ip = [ int(a) for a in myip.split(".") ]
		if len(self.ip) != 4:
			self.ip = [0,0,0,0]
		else:
			self.initialized = True
		emcDebugOut( "[spNET] IP = " + str(self.ip).replace(", ", ".")[1:-1] )

spNET = NetworkAwareness()


class RecordEventObserver:
	def __init__(self, callback):
		self.callback = callback

		try:
			NavigationInstance.instance.RecordTimer.on_state_change.append(self.recEvent)
		except Exception, e:
			emcDebugOut("[spRO] Record observer add exception:\n" + str(e))

	def recEvent(self, timer):
		try:
			self.callback(timer)
		except Exception, e:
			emcDebugOut("[spRO] recEvent exception:\n" + str(e))


#TODO RecControl should be a separate global instance
class RecordingsControl:
	def __init__(self, recStateChange):
		self.recStateChange = recStateChange
		self.recObserver = RecordEventObserver(self.recEvent)
		self.recDict = defaultdict(list)
		self.recRemoteList = []
		self.recFile = None
		# if Enigma2 has crashed, we need to recreate the list of the ongoing recordings
		for timer in NavigationInstance.instance.RecordTimer.timer_list:
			self.recEvent(timer)

	def recEvent(self, timer):
		# StateWaiting=0, StatePrepared=1, StateRunning=2, StateEnded=3
		try:
			if timer.justplay: return
			inform = False
			try: timer.Filename
			except: timer.calculateFilename()

			filename = os.path.basename(timer.Filename)
			if timer.state == timer.StatePrepared:	pass
			elif timer.state == timer.StateRunning:	# timer.isRunning()
				if config.EMC.files_cache.value:
					cutfilename = "/" + filename
					realpath = timer.Filename.replace(cutfilename, '')
					ext = ".ts"
					recname = timer.Filename + ext, filename + ext, ext
					from EMCFileCache import movieFileCache
					if movieFileCache.IsPathInCache(realpath):
						movieFileCache.addRecToCacheFileList(realpath, recname)
				if not filename in self.recDict:
					begin = timer.begin
					if timer.autoincrease:
						end = begin
					else:
						end = timer.end
					self.recDict[filename] = (begin, end, timer.service_ref.ref, str(timer))
					inform = True
					emcDebugOut("[emcRC] REC START for: " + filename)
			else: #timer.state == timer.StateEnded:
				if filename in self.recDict:
					del self.recDict[filename]
					inform = True
					emcDebugOut("[emcRC] REC END for: " + filename)
					try:
						if hasattr(timer, "fixMoveCmd"):
							emcTasker.shellExecute(timer.fixMoveCmd)
							emcDebugOut("[emcRC] File had been moved while recording was in progress, moving left over files..")
					except: pass
				if config.EMC.timer_autocln.value:
					DelayedFunction(2000, self.timerCleanup)	# postpone to avoid crash in basic timer delete by user
			if inform:
				if config.EMC.remote_recordings.value:
					self.recFileUpdate()
				self.recStateChange(timer)
		except Exception, e:
			emcDebugOut("[emcRC] recEvent exception:\n" + str(e))

	def timerCleanup(self):
		try:
			NavigationInstance.instance.RecordTimer.cleanup()
		except Exception, e:
			emcDebugOut("[emcRC] timerCleanup exception:\n" + str(e))

	def isRecording(self, filename):
		try:
			if filename[0] == "/": 			filename = os.path.basename(filename)
			if filename.endswith(".ts"):	filename = filename[:-3]
			return filename in self.recDict
		except Exception, e:
			emcDebugOut("[emcRC] isRecording exception:\n" + str(e))
			return False

	def isRemoteRecording(self, filename):
		try:
			if filename[0] == "/": 			filename = os.path.basename(filename)
			if filename.endswith(".ts"):	filename = filename[:-3]
			return filename in self.recRemoteList
		except Exception, e:
			emcDebugOut("[emcRC] isRemoteRecording exception:\n" + str(e))
			return False

	def stopRecording(self, filename):
		try:
			if filename[0] == "/":			filename = os.path.basename(filename)
			if filename.endswith(".ts"):	filename = filename[:-3]
			if filename in self.recDict:
				for timer in NavigationInstance.instance.RecordTimer.timer_list:
					if timer.isRunning() and not timer.justplay and timer.Filename.find(filename)>=0:
						if timer.repeated: return False
						timer.afterEvent = AFTEREVENT.NONE
						NavigationInstance.instance.RecordTimer.removeEntry(timer)
						emcDebugOut("[emcRC] REC STOP for: " + filename)
						return True
			else:
				emcDebugOut("[emcRC] OOPS stop REC for nonexistent: " + filename)
		except Exception, e:
			emcDebugOut("[emcRC] stopRecording exception:\n" + str(e))
		return False

	def isCutting(self, filename):
		try:
			if filename.endswith("_.ts"):
				if not os.path.exists(filename[:-2]+"eit"):
					return True
			return False
		except Exception, e:
			emcDebugOut("[emcRC] isCutting exception:\n" + str(e))
			return False

	def fixTimerPath(self, old, new):
		try:
			if old.endswith(".ts"):	old = old[:-3]
			if new.endswith(".ts"):	new = new[:-3]
			for timer in NavigationInstance.instance.RecordTimer.timer_list:
				if timer.isRunning() and not timer.justplay and timer.Filename == old:
					timer.dirname = os.path.dirname(new) + "/"
					timer.fixMoveCmd = 'mv "'+ timer.Filename +'."* "'+ timer.dirname +'"'
					timer.Filename = new
					emcDebugOut("[emcRC] fixed path: " + new)
					break

		except Exception, e:
			emcDebugOut("[emcRC] fixTimerPath exception:\n" + str(e))

	def remoteInit(self, ip):
		try:
			if not os.path.exists(config.EMC.folder.value):
				emcTasker.shellExecute("mkdir " + config.EMC.folder.value)
			if ip is not None:
				rec = "/db_%s.rec" %str(ip).replace(", ", ".")[1:-1]
				self.recFile = os.path.join(config.EMC.folder.value, rec)
		except Exception, e:
			emcDebugOut("[emcRC] remoteInit exception:\n" + str(e))

	def recFileUpdate(self):
		recf = None
		try:
			if self.recFile is None: self.remoteInit( spNET.whatIsMyIP() )
			if self.recFile is None: return	# was not able to get IP
			recf = open(self.recFile, "wb")
			pickle.dump(self.recDict.keys(), recf)
		except Exception, e:
			emcDebugOut("[emcRC] recFileUpdate exception:\n" + str(e))
		finally:
			if recf is not None:
				recf.close()

	def recFilesRead(self):
		if self.recFile is None: self.recFileUpdate()
		if self.recFile is None: return
		self.recRemoteList = []
		recf = None
		try:
			if config.EMC.folder.value and os.path.exists(config.EMC.folder.value):
				for x in os.listdir(config.EMC.folder.value):
					path = os.path.join(config.EMC.folder.value, x)
					if x.endswith(".rec") and path != self.recFile:
						recf = open( path, "rb" )
						self.recRemoteList += pickle.load(recf)
		except Exception, e:
			emcDebugOut("[emcRC] recFilesRead exception:\n" + str(e))
		finally:
			if recf is not None:
				recf.close()