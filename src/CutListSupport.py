#!/usr/bin/python
# encoding: utf-8
#
# CutListSupport
# Copyright (C) 2011 cmikula, betonme
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

import os
import struct
from bisect import insort

from Components.config import *
from Screens.InfoBarGenerics import InfoBarCueSheetSupport, InfoBarSeek

from EMCTasker import emcDebugOut
from IsoFileSupport import IsoSupport

from RecordingsControl import getRecording

try:
	from Plugins.Extensions.CutlistDownloader.plugin import bestCutlist#
except ImportError as ie:
	hasCutlistDownloader = False
else:
	hasCutlistDownloader = True

# [Cutlist.Workaround] Enable Cutlist-Workaround:
# Creates an Backup of the Cutlist during recording and merge it with the cutlist-File from enigma after recording
DO_CUTLIST_WORKAROUND = True
# Cut File support class
# Description
# http://git.opendreambox.org/?p=enigma2.git;a=blob;f=doc/FILEFORMAT
class CutList():

	# InfoBarCueSheetSupport types
	CUT_TYPE_IN = 0
	CUT_TYPE_OUT = 1
	CUT_TYPE_MARK = 2
	CUT_TYPE_LAST = 3
	# Additional custom EMC specific types
	# Has to be remove before starting a player
	CUT_TYPE_SAVEDLAST = 4
	CUT_TYPE_LENGTH = 5

	# Toggle Types
	CUT_TOGGLE_START = 0
	CUT_TOGGLE_RESUME = 1
	CUT_TOGGLE_FINISHED = 2
	CUT_TOGGLE_START_FOR_PLAY = 3
	CUT_TOGGLE_FOR_PLAY = 4

	# Additional cut_list information
	#		cut_list[x][0] = pts   = long long
	#		cut_list[x][1] = what  = long

	# Constants
	ENABLE_RESUME_SUPPORT = True
	MOVIE_FINISHED = 0xFFFFFFFFFFFFFFFF

	INSORT_SCOPE = 45000  # 0.5 seconds * 90 * 1000

	def __init__(self, path=None):
		# Is already initialized in InfoBar and EMCMediaCenter
		#InfoBarCueSheetSupport.__init__(self)
		#InfoBarSeek.__init__(self)
		#self.service = None
		self.cut_file = None
		self.cut_mtime = 0
		self.cut_list = []
		self.iso = None

		self.__newPath(path)
		self.__readCutFile()
		self.__verifyCutList()

	def __newPath(self, path):
		name = None
		if path:
			#TODO very slow
			if path.endswith(".iso"):
				if not self.iso:
					self.iso = IsoSupport(path)
				name = self.iso and self.iso.getIsoName()
				if name and len(name):
					path = "/home/root/dvd-" + name
			elif os.path.isdir(path):
				path += "/dvd"
			path += ".cuts"
			if self.cut_file != path:
				self.cut_file = path
				self.cut_mtime = 0

	def __ptsToSeconds(self, pts):
		# Cut files are using the presentation time stamp time format
		# pts has a resolution of 90kHz
		return pts / 90 / 1000

	def __secondsToPts(self, seconds):
		return seconds * 90 * 1000

	def __getCuesheet(self):
		service = self.session.nav.getCurrentService()
		if service is None:
			return None
		return service.cueSheet()

	##############################################################################
	## Overwrite Functions

	# InfoBarCueSheetSupport
	def downloadCuesheet(self):
		try:
			service = hasattr(self, "service") and self.service

			# Is there native cuesheet support
			cue = self.__getCuesheet() #InfoBarCueSheetSupport._InfoBarCueSheetSupport__getCuesheet(self)
			if cue is None or (cue and not cue.getCutList()):
				# No native cuesheet support
				if service:
					path = service.getPath()
					self.__newPath(path)
					self.__readCutFile()
			else:
				# Native cuesheet support
				self.cut_list = cue.getCutList()

			#print "CUTSTEST0 ", self.cut_list
			if config.EMC.cutlist_at_download.value:
				if service and hasCutlistDownloader:
					try:
						bestCutlist(service, self.cutlistDownloaded)
					except Exception, e:
						emcDebugOut("[EMC] Plugin CutlistDownloader exception:" + str(e))

			#MAYBE: If the cutlist is empty we can check the EPG NowNext Events
		except Exception, e:
			emcDebugOut("[CUTS] downloadCutList exception:" + str(e))

	def cutlistDownloaded(self, cutlist=[]):
		print "EMC cutlistDownloaded"
		print self.cut_list
		if cutlist:
			for pts, what in cutlist:
				self.__insort(pts, what)
		print self.cut_list

	# InfoBarCueSheetSupport
	def uploadCuesheet(self):
		try:
			# Always check for saving the last marker
			if config.EMC.movie_save_lastplayed.value is True:
				self.__saveOldLast()

			# Is there native cuesheet support
			cue = InfoBarCueSheetSupport._InfoBarCueSheetSupport__getCuesheet(self)

			if cue is None or (cue and not cue.getCutList()):
				# No native cuesheet support
				# Update local cut list, maybe there is a newer one
				#TODO to be tested
				#self.__readCutFile(True)
				if hasattr(self, "service") and self.service:
					path = self.service.getPath()
					self.__newPath(path)
					self.__writeCutFile()
			else:
				# Native cuesheet support
				cue.setCutList(self.cut_list)
		except Exception, e:
			emcDebugOut("[CUTS] uploadCuesheet exception:" + str(e))

	def updateFromCuesheet(self):
		print "Cutlist updateCuesheet"
		try:
			# Use non native cuesheet support
			# [Cutlist.Workaround] merge with Backup-File if exists
			savefileexists = False
			if DO_CUTLIST_WORKAROUND:
				cutspath = self.cut_file + ".save"
				if os.path.exists(cutspath):
					emcDebugOut("[Cutlist.Workaround] Reading from Backup-File")
					savefileexists = True
					self.__readCutFileWithPath(cutspath, True)
				else:
					emcDebugOut("[Cutlist.Workaround] No Backup-File found: ")
			cutspath = self.cut_file
			self.__readCutFileWithPath(cutspath, True)
			self.__writeCutFile()
			if savefileexists:
				emcDebugOut("[Cutlist.Workaround] Delete Backup-File ")
				os.remove(cutspath + '.save')
		except Exception, e:
			emcDebugOut("[CUTS] updateCuesheet exception:" + str(e))

	def setCutList(self, cut_list):
		self.cut_list = cut_list
		self.__writeCutFile()

	##############################################################################
	## Get Functions
	def getCutList(self):
		return self.cut_list

	def getCutListMTime(self):
		return self.cut_mtime

	# Wrapper in seconds
	def getCutListLast(self):
		return self.__ptsToSeconds( self.__getCutListLast() )

	def getCutListLength(self):
		return self.__ptsToSeconds( self.__getCutListLength() )

	def getCutListSavedLast(self):
		return self.__ptsToSeconds( self.__getCutListSavedLast() )

	# Internal from cutlist in pts
	def __getCutListLast(self):
		if self.cut_list:
			for (pts, what) in self.cut_list:
				if what == self.CUT_TYPE_LAST:
					return pts
		return 0

	def __getCutListLength(self):
		if self.cut_list:
			for (pts, what) in self.cut_list:
				if what == self.CUT_TYPE_LENGTH:
					return pts
		return 0

	def __getCutListSavedLast(self):
		if self.cut_list:
			for (pts, what) in self.cut_list:
				if what == self.CUT_TYPE_SAVEDLAST:
					return pts
		return 0

	##############################################################################
	## Modify Functions
	## Use remove and insort to guarantee the cut list is sorted

	# API modification functions
	# Calculate in seconds
	# A modification will always be written immediately
	def toggleLastCutList(self, toggle=0):
		self.__toggleLast( toggle)
		#print "toggleLastCutList " + str(toggle) + " cutlist " + str(self.cut_list)
		self.__writeCutFile()

	def updateCutList(self, play, length):
		# Always check for saving the last marker
		#print "CUTSTEST1 ", self.cut_list
		if config.EMC.movie_save_lastplayed.value is True:
			self.__saveOldLast()
		#print "CUTSTEST2 ", self.cut_list
		self.__removeSavedLast( self.__getCutListSavedLast() )
		#print "CUTSTEST3 ", self.cut_list
		self.__replaceLast( play )
		#print "CUTSTEST4 ", self.cut_list
		self.__replaceLength( length )
		#print "CUTSTEST5 ", self.cut_list
		self.uploadCuesheet()

	def removeMarksCutList(self):
		# All Marks will be removed
		# All others items will stay
		if self.cut_list:
			for cp in self.cut_list[:]:
				if cp[1] == self.CUT_TYPE_MARK:
					self.cut_list.remove(cp)
		self.__writeCutFile()

	# Internal modification functions
	# Calculate in pts
	# Without saving changes
	def __verifyCutList(self):
		if config.EMC.movie_ignore_firstcuts.value is True:
			# Don't care about the first 10 seconds
			if self.cut_list:
				for cp in self.cut_list[:]:
					if cp[0] < self.__secondsToPts(10):
						self.cut_list.remove(cp)

	def __saveOldLast(self):
		# Save the last played as marker
		last = self.__getCutListLast()
		if last > 0:
			self.__insort(last, self.CUT_TYPE_MARK)

	def __toggleLast(self, toggle):
		oldLast = self.__getCutListLast()
		savedLast = self.__getCutListSavedLast()
		self.__removeSavedLast(savedLast)
		newLast = 0
		newSaved = 0

		#if savedLast == oldLast:
		#	print "Cutlist if savedLast == oldLast: " + str(savedLast) + " toggle: " + str(toggle) + " " + str(self.cut_file)

		if toggle == self.CUT_TOGGLE_START:
			newLast = 0
		elif toggle == self.CUT_TOGGLE_RESUME:
			#if savedLast == oldLast: # 0:
			#	newLast = self.MOVIE_FINISHED
			#else:
			newLast = savedLast or self.MOVIE_FINISHED
		elif toggle == self.CUT_TOGGLE_FINISHED:
			newLast = self.MOVIE_FINISHED
		elif toggle == self.CUT_TOGGLE_START_FOR_PLAY:
			newLast = 0
			savedLast = 0
			#oldLast = oldLast
		elif toggle == self.CUT_TOGGLE_FOR_PLAY:
			newLast = oldLast
			savedLast = 0
			oldLast = 0

		newSaved = savedLast or oldLast
		self.__replaceLast(newLast)
		self.__appendSavedLast(newSaved)

	def __insort(self, pts, what):
		if self.cut_list:
			for (clpts, clwhat) in self.cut_list[:]:
				if clwhat == what:
					if clpts-self.INSORT_SCOPE < pts < clpts+self.INSORT_SCOPE:
						# Found a conflicting entry, replace it to avoid doubles and short jumps
						self.cut_list.remove( (clpts, clwhat) )
			insort(self.cut_list, (pts, what))
		else:
			insort(self.cut_list, (pts, what))

	def __appendSavedLast(self, pts):
		if pts > 0 and pts < self.MOVIE_FINISHED:
			self.__insort(pts, self.CUT_TYPE_MARK)
			self.cut_list.append( (pts, self.CUT_TYPE_SAVEDLAST) )

	def __replaceLength(self, pts):
		if self.cut_list:
			for cp in self.cut_list[:]:
				if cp[1] == self.CUT_TYPE_LENGTH:
					self.cut_list.remove(cp)
		if pts > 0:
			self.__insort(pts, self.CUT_TYPE_LENGTH)

	def __replaceLast(self, pts):
		if self.cut_list:
			for cp in self.cut_list[:]:
				if cp[1] == self.CUT_TYPE_LAST:
					self.cut_list.remove(cp)
		if pts > 0:
			self.__insort(pts, self.CUT_TYPE_LAST)

	def __removeSavedLast(self, pts):
		if self.cut_list:
			for cp in self.cut_list[:]:
				if cp[0] == pts:
					if cp[1] == self.CUT_TYPE_SAVEDLAST:
						self.cut_list.remove(cp)

	##############################################################################
	# [Cutlist.Workaround] add Param path in __readCutFile to merge with backup-File
	## File IO Functions
	def __readCutFile(self, update=False):
		self.__readCutFileWithPath(self.cut_file, update)

	def __readCutFileWithPath(self, path, update=False):
		data = ""
		if path and os.path.exists(path):
			mtime = os.path.getmtime(path)
			if self.cut_mtime == mtime:
				# File has not changed
				pass

			else:
				# New path or file has changed
				self.cut_mtime = mtime

				if not update:
					# No update clear all
					self.cut_list = []

				# Read data from file
				# OE1.6 with Pyton 2.6
				#with open(path, 'rb') as f: data = f.read()
				f = None
				try:
					f = open(path, 'rb')
					data = f.read()
				except Exception, e:
					emcDebugOut("[CUTS] Exception in __readCutFile: " + str(e))
				finally:
					if f is not None:
						f.close()

				# Parse and unpack data
				if data:
					pos = 0
					while pos+12 <= len(data):
						# Unpack
						(pts, what) = struct.unpack('>QI', data[pos:pos+12])
						self.__insort(long(pts), what)
						# Next cut_list entry
						pos += 12
		else:
			# No path or no file clear all
			self.cut_list = []

	def __writeCutFile(self):
		data = ""
		path = self.cut_file
		if path:

			# Generate and pack data
			if self.cut_list:
				for (pts, what) in self.cut_list:
					data += struct.pack('>QI', pts, what)

			# Write data to file
			# OE1.6 with Pyton 2.6
			#with open(path, 'wb') as f: f.write(data)
			f = None
			try:
				f = open(path, 'wb')
				if data:
					f.write(data)
			except Exception, e:
				emcDebugOut("[CUTS] Exception in __writeCutFile: " + str(e))
			finally:
				if f is not None:
					f.close()

			# [Cutlist.Workaround]
			# Always make a backup-copy when recording, it will be merged with enigma-cutfile after recording
			if DO_CUTLIST_WORKAROUND:
				recFileName=self.cut_file[:-5]
				record = getRecording(recFileName)
				if record:
					savepath = self.cut_file + ".save"
					fsave = None
					try:
						emcDebugOut("[Cutlist.Workaround] Creating backupfile: " + str(savepath))
						fsave = open(savepath, 'wb')
						if data:
							fsave.write(data)
					except Exception, e:
						emcDebugOut("[Cutlist.Workaround] Exception in __writeCutFile: " + str(e))
					finally:
						if fsave is not None:
							fsave.close()

			# Save file timestamp
			if path and os.path.exists(path):
				self.cut_mtime = os.path.getmtime(path)