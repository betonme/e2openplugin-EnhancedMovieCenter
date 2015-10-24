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
import math
import os
import random
import re

from collections import defaultdict
from time import time
from datetime import datetime
from threading import Thread

from Components.config import *
from Components.GUIComponent import GUIComponent
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaBlend
from Tools.LoadPixmap import LoadPixmap
from Tools.Directories import fileExists, resolveFilename, SCOPE_CURRENT_SKIN
from skin import parseColor, parseFont, parseSize
from enigma import eListboxPythonMultiContent, eListbox, gFont, RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_HALIGN_CENTER, eServiceReference, eServiceCenter, ePythonMessagePump, loadPNG, getDesktop
from timer import TimerEntry

from . import _
from EMCFileCache import movieFileCache
from EMCMountPoints import mountPoints
from RecordingsControl import RecordingsControl, getRecording
from DelayedFunction import DelayedFunction
from EMCTasker import emcDebugOut
from VlcPluginInterface import VlcPluginInterfaceList, vlcSrv, vlcDir, vlcFil
from VlcPluginInterface import DEFAULT_VIDEO_PID, DEFAULT_AUDIO_PID, ENIGMA_SERVICE_ID
from operator import itemgetter
from CutListSupport import CutList
from MetaSupport import MetaList
from EitSupport import EitList
from PermanentSort import PermanentSort
from E2Bookmarks import E2Bookmarks
from EMCBookmarks import EMCBookmarks
from ServiceSupport import ServiceCenter
from ThreadQueue import ThreadQueue
from EnhancedMovieCenter import imgVti, newPiconRenderer

global imgVti
global newPiconRenderer
if imgVti:
	from enigma import BT_SCALE, BT_FIXRATIO as BT_KEEP_ASPECT_RATIO

if newPiconRenderer:
		from Components.Renderer.Picon import getPiconName
		from enigma import BT_SCALE, BT_KEEP_ASPECT_RATIO

global extAudio, extDvd, extVideo, extPlaylist, extList, extMedia, extBlu
global cmtDir, cmtUp, cmtTrash, cmtLRec, cmtVLC, cmtBME2, cmtBMEMC, virVLC, virAll, virToE, virToD
global vlcSrv, vlcDir, vlcFil
global plyDVB, plyM2TS, plyDVD, plyMP3, plyVLC, plyAll
global sidDVB, sidDVD, sidMP3

# Set definitions

# Media types
extAudio    = frozenset([".ac3", ".dts", ".flac", ".m4a", ".mp2", ".mp3", ".ogg", ".wav", ".wma", ".aac"])
extVideo    = frozenset([".ts", ".trp", ".avi", ".divx", ".f4v", ".flv", ".img", ".ifo", ".iso", ".m2ts", ".m4v", ".mkv", ".mov", ".mp4", ".mpeg", ".mpg", ".mts", ".vob", ".wmv", ".bdmv", ".asf", ".stream"])
extPlaylist = frozenset([".m3u", ".e2pls"])#, ".pls"])
extMedia    = extAudio | extVideo | extPlaylist
extDir      = frozenset([""])
extList     = extMedia | extDir

# Additional file types
extTS       = frozenset([".ts", ".trp"])
extM2ts     = frozenset([".m2ts"])
#extDvd      = frozenset([".iso", ".img", ".ifo"])
extIfo      = frozenset([".ifo"])
extIso      = frozenset([".iso", ".img"])
extDvd      = extIfo | extIso
extVLC      = frozenset([vlcFil])
extBlu      = frozenset([".bdmv"])
# blue disk movie
# mimetype("video/x-bluray") ext (".bdmv")

# Player types
plyDVB      = extTS																										# ServiceDVB
plyM2TS     = extM2ts																									# ServiceM2TS
plyDVD      = extDvd																									# ServiceDVD
plyMP3      = extMedia - plyDVB - plyM2TS - plyDVD - extBlu						# ServiceMP3 GStreamer
plyVLC      = extVLC																									# VLC Plugin
#plyBLU      = extBlu | extIso																				# BludiscPlayer Plugin
plyAll      = plyDVB | plyM2TS | plyDVD | plyMP3 | plyVLC | extBlu


# Type definitions

# Service ID types for E2 service identification
sidDVB      = eServiceReference.idDVB									# eServiceFactoryDVB::id   enum { id = 0x1 };
sidDVD      = 4369 																		# eServiceFactoryDVD::id   enum { id = 0x1111 };
sidMP3      = 4097																		# eServiceFactoryMP3::id   enum { id = 0x1001 };
# For later purpose
sidM2TS     = 3 																			# eServiceFactoryM2TS::id  enum { id = 0x3 };
#TODO
#sidXINE = 4112										# eServiceFactoryXine::id  enum { id = 0x1010 };
#additionalExtensions = "4098:m3u 4098:e2pls 4098:pls"

# Grouped service ids
sidsCuts = frozenset([sidDVB, sidDVD])

# Custom types: Used by EMC internally for sorting and type identification

cmtUp      = "0"
cmtTrash   = "1"
cmtLRec    = "2"
cmtBME2    = "BE2"
cmtBMEMC   = "BEMC"
cmtDir     = "D"
cmtVLC     = "V"

substitutelist = [("."," "), ("_"," "), ("-"," "), ("1080p",""), ("720p",""), ("x264",""), ("h264",""), ("1080i",""), ("AC3","")]

# Grouped custom types
virVLC     = frozenset([cmtVLC, vlcSrv, vlcDir])
virAll     = frozenset([cmtBME2, cmtBMEMC, cmtVLC, cmtLRec, cmtTrash, cmtUp, cmtDir, vlcSrv, vlcDir])
virToE     = frozenset([cmtBME2, cmtBMEMC, cmtVLC, cmtLRec, cmtTrash, cmtUp, vlcSrv, vlcDir])

if config.EMC.directories_ontop.value:
	virToD = virToE
else:
	virToD = virAll


#-------------------------------------------------
# func: readBasicCfgFile( file )
#
# Reads the lines of a file in a list. Empty lines
# or lines beginnig with '#' will be ignored.
#-------------------------------------------------
def readBasicCfgFile(file):
	data = []
	if not os.path.exists(file):
		return data
	f = None
	try:
		f = open(file, "r")
		lines = f.readlines()
		for line in lines:
			line = line.strip()
			if not line:					# no empty lines
				continue
			if line[0:1] == "#":				# no comment lines
				continue
			data.append( line )
	except Exception, e:
		emcDebugOut("[EMC] Exception in readBasicCfgFile: " + str(e))
	finally:
		if f is not None:
			f.close()
	return data

#-------------------------------------------------
# func: getPlayerService(path, name="", ext=None)
#
# Determine the service of a media file
#-------------------------------------------------
def getPlayerService(path, name="", ext=None):
	if ext in plyDVB:
		service = eServiceReference(sidDVB, 0, path)
	elif ext in plyMP3:
		service = eServiceReference(sidMP3, 0, path)
	elif ext in plyDVD:
		service = eServiceReference(sidDVD, 0, path)
		#QUESTION Is the special name handling really necessary
		if service:
			# Copied from dvd player
			if path.endswith("/VIDEO_TS") or path.endswith("/"):
				names = service.toString().rsplit("/",3)
				if names[2].startswith("Disk ") or names[2].startswith("DVD "):
					#TEST name = str(names[1]) + " - " + str(names[2])
					name = names[1] + " - " + names[2]
				else:
					name = names[2]
	elif ext in plyM2TS:
		service = eServiceReference(sidM2TS, 0, path)
	else:
		path = path.replace(":","") # because of VLC player
		#service = eServiceReference("2:0:1:0:0:0:0:0:0:0:" + path)
		service = eServiceReference(ENIGMA_SERVICE_ID, 0, path)
		print "[EMC] service valid=", service.valid()
		service.setData(0, DEFAULT_VIDEO_PID)
		service.setData(1, DEFAULT_AUDIO_PID)
	if name:
		service.setName(name)
	return service

def getMovieNameWithoutExt(moviename=""):
	if config.EMC.movie_show_format.value:
		for rem in extVideo:
			rem = rem.replace("."," ")
			if moviename.endswith(rem):
				moviename = moviename[:-len(rem)]
				break
	return moviename

def getMovieNameWithoutPhrases(moviename=""):
	# Remove phrases which are encapsulated in [*] or (*) from the movietitle
	moviename = re.sub(r'\[.*\]', "", moviename)
	moviename = re.sub(r'\(.*\)', "", moviename)
	moviename = re.sub(r' S\d\dE\d\d .*', "", moviename)
	for (phrase,sub) in substitutelist:
		moviename = moviename.replace(phrase,sub)
	return moviename

def getProgress(service, length=0, last=0, forceRecalc=False, cuts=None):
	# All calculations are done in seconds
	# The progress of a recording isn't correct, because we only get the actual length not the final
	cuts = None
	progress = 0
	#updlen = length
	if last <= 0:
		# Get last position from cut file
		if cuts is None:
			cuts = CutList( service.getPath() )
		last = cuts.getCutListLast()
	# Check for valid position
	if last > 0 or forceRecalc:
		# Valid position
		# Recalc the movie length to calculate the progress status
		if length <= 0:
			if service:
				esc = eServiceCenter.getInstance()
				info = esc and esc.info(service)
				length = info and info.getLength(service) or 0
			if length <= 0:
				if cuts is None:
					cuts = CutList( service.getPath() )
				length = cuts.getCutListLength()
				if length <= 0:
					# Set default file length if is not calculateable
					# 90 minutes = 90 * 60
					length = 5400
					# We only update the entry if we do not use the default value
				#	updlen = 0
				#else:
				#	updlen = length
			#else:
			#	updlen = length
		if length:
			progress = calculateProgress(last, length)
		else:
			# This should never happen, we always have our default length
			progress = 100
			#emcDebugOut("[MC] getProgress(): Last without any length")
	else:
		# No position implies progress is zero
		progress = 0
	return progress, length

def getRecordProgress(path):
	# The progress of all recordings is updated
	# - on show dialog
	# - on reload list / change directory / movie home
	# The progress of one recording is updated
	# - if it will be highlighted the list
	# Note: There is no auto update mechanism of the recording progress
	record = getRecording(path)
	if record:
		begin, end, service = record
		last = time() - begin
		length = end - begin
		return calculateProgress(last, length)
	else:
		return 0

def calculateProgress(last, length):
	progress = 0
	if length:
		# Adjust the watched movie length (98% of movie length)
		# else we will never see the 100%
		adjlength = float(length) / 100.0 * 98.0
		# Calculate progress and round up
		progress = int( math.ceil ( float(last) / float(adjlength) * 100.0 ) )
		# Normalize progress
		if progress < 0: progress = 0
		elif progress > 100: progress = 100
	return progress

def toggleProgressService(service, preparePlayback, forceProgress=-1, first=False):
	if service is None:
		return

	# Cut file handling
	path = service.getPath()

	# Only for compatibilty reasons
	# Should be removed anytime
	cuts  = path +".cuts"
	cutsr = path +".cutsr"
	if os.path.exists(cutsr) and not os.path.exists(cuts):
		# Rename file - to catch all old EMC revisions
		try:
			os.rename(cutsr, cuts)
		except Exception, e:
			emcDebugOut("[CUTS] Exception in toggleProgressService: " + str(e))
	# All calculations are done in seconds
	cuts = CutList( path )
	last = cuts.getCutListLast()
	#length = self.getLengthOfService(service)
	progress, length = getProgress(service, length=0, last=last, forceRecalc=True, cuts=cuts)

	if not preparePlayback:
		if first:
			if progress < 100: forceProgress = 50		# force next state 100
			else: forceProgress = 100 							# force next state 0
		if forceProgress > -1:
			progress = forceProgress

		if progress >= 100:
			# 100% -> 0
			# Don't care about preparePlayback, always reset to 0%
			# Save last marker
			cuts.toggleLastCutList(cuts.CUT_TOGGLE_START)
		elif progress <= 0:
			# 0% -> SAVEDLAST or length
			cuts.toggleLastCutList(cuts.CUT_TOGGLE_RESUME)
		else:
			# 1-99% -> length
			cuts.toggleLastCutList(cuts.CUT_TOGGLE_FINISHED)
	else:
		if progress >= 100 or config.EMC.movie_rewind_finished.value is True and progress >= int(config.EMC.movie_finished_percent.value):
			# 100% -> 0 or
			# Start playback and rewind is set and movie progress > finished -> 0
			# Don't save SavedMarker
			cuts.toggleLastCutList(cuts.CUT_TOGGLE_START_FOR_PLAY)
		else:
			# Delete SavedMarker
			cuts.toggleLastCutList(cuts.CUT_TOGGLE_FOR_PLAY)

	return progress

def dirInfo(folder, bsize=False):
	#TODO Improve performance
	count = 0
	size = 0
	structlist = ["video_ts", "bdmv"]
	if config.EMC.cfghide_enable.value:
		hideitemlist = readBasicCfgFile("/etc/enigma2/emc-hide.cfg") or []
	else:
		hideitemlist = []
	extCount = extList - extBlu - extIfo
	if os.path.exists(folder):
		#for m in os.listdir(path):
		for (path, dirs, files) in os.walk(folder):
			for dir in dirs:
				if config.EMC.cfghide_enable.value and hideitemlist:
					if dir in hideitemlist or (dir[0:1] == "." and ".*" in hideitemlist):
						dirs.remove(dir)			# hidden dir's subtree won't be explored
				if dir.lower() in structlist:
					count += 1						# add dvd/blustructure movies
					dirs.remove(dir)			# structure's subtree won't be explored
			#count += len(dirs)					# don't count dirs
			for m in files:
				if os.path.splitext(m)[1].lower() in extList:
					count += 1
					if bsize:
						# Only retrieve the file size if it is requested,
						# because it costs a lot of time
						filename = os.path.join(path, m)
						if os.path.exists(filename):
							size += os.path.getsize(filename)
	if size:
		size /= (1024.0 * 1024.0 * 1024.0)
	if folder != cmtTrash:
		movieFileCache.addCountSizeToCache(folder, count, size)
	return count, size

def detectDVDStructure(checkPath):
	if not os.path.isdir(checkPath):
		return None
	elif not config.EMC.scan_linked.value and os.path.islink(checkPath):
		return None
	dvdpath = os.path.join(checkPath, "VIDEO_TS.IFO")
	if fileExists( dvdpath ):
		return dvdpath
	dvdpath = os.path.join(checkPath, "VIDEO_TS/VIDEO_TS.IFO")
	if fileExists( dvdpath ):
		return dvdpath
	dvdpath = os.path.join(checkPath, "DVD/VIDEO_TS/VIDEO_TS.IFO")
	if fileExists( dvdpath ):
		return dvdpath
	return None

def detectMOVStructure(checkPath):
	if not os.path.isdir(checkPath):
		return None
	elif not config.EMC.scan_linked.value and os.path.islink(checkPath):
		return None
	extMovie = extVideo - extBlu
	for ext in extMovie:
		movpath = os.path.join(checkPath, os.path.basename(checkPath)) + ext
		if fileExists( movpath ):
			return movpath
	return None

def detectBLUStructure(checkPath):
	if not os.path.isdir(checkPath):
		return None
	elif not config.EMC.scan_linked.value and os.path.islink(checkPath):
		return None
	blupath = os.path.join(checkPath, "BDMV/index.bdmv")
	if fileExists( blupath ):
		return blupath
	blupath = os.path.join(checkPath, "BRD/BDMV/index.bdmv")
	if fileExists( blupath ):
		return blupath
	return None

def detectBLUISO(checkPath):
	random.seed()
	mountdir = '/tmp/EMCISO' + str(random.getrandbits(16))
	dir, fileext = os.path.splitext(checkPath)
	if fileext =='.iso':
		if not os.path.exists(mountdir):
			os.system('mkdir ' + mountdir)
		else:
			os.system('umount -d -f ' + mountdir)
		os.system('mount -r "' + checkPath + '" ' + mountdir)
		if detectBLUStructure(mountdir):
			os.system('umount -d -f ' + mountdir)
			os.system('rmdir ' + mountdir)
			return True
		os.system('umount -d -f ' + mountdir)
		os.system('rmdir ' + mountdir)
	return False

# muss drinnen bleiben sonst crashed es bei foreColorSelected
def MultiContentEntryProgress(pos = (0, 0), size = (0, 0), percent = None, borderWidth = None, foreColor = None, foreColorSelected = None, backColor = None, backColorSelected = None):
	return (eListboxPythonMultiContent.TYPE_PROGRESS, pos[0], pos[1], size[0], size[1], percent, borderWidth, foreColor, foreColorSelected, backColor, backColorSelected)

THREAD_WORKING = 1
THREAD_FINISHED = 2

class CountSizeWorker(Thread):
	def __init__(self):
		Thread.__init__(self)
		self.__running = False
		self.__messages = ThreadQueue()
		self.__messagePump = ePythonMessagePump()
		self.__list = ThreadQueue()

	def __getMessagePump(self):
		return self.__messagePump
	MessagePump = property(__getMessagePump)

	def __getMessageQueue(self):
		return self.__messages
	Message = property(__getMessageQueue)

	def __getRunning(self):
		return self.__running
	isRunning = property(__getRunning)

	def isListEmpty(self):
		return self.__list.empty()

	def getListLength(self):
		return len(self.__list)

	def Cancel(self):
		self.__running = False

	def add(self, item):
		self.__list.push(item)
		if not self.__running:
			self.__running = True
#			print'[EMC] CountSizeWorker Start'
			self.start()

	def run(self):
		while not self.__list.empty():
			if not self.__running: break

			item = self.__list.pop()
#			print'[EMC] CountSizeWorker processing: ', item
			result = None

			try:
				result = dirInfo(item, bsize=True)
			except Exception, e:
				print('[EMC] CountSizeWorker result exception:', str(e))

				# Exception finish job with error
				result = str(e)

			if result:
				if self.__running:
					self.__messages.push((2, result))
			else:
				self.__messages.push((1, result))

		self.__messagePump.send(0)
		self.__running = False
		Thread.__init__(self)

countsizeworker = CountSizeWorker()

moviecenterdata = None

class MovieCenterData(VlcPluginInterfaceList, PermanentSort, E2Bookmarks, EMCBookmarks):

	def __init__(self):
		VlcPluginInterfaceList.__init__(self)
		PermanentSort.__init__(self)

		self.currentPath = config.EMC.movie_homepath.value

		self.list = []
		from Plugins.Extensions.EnhancedMovieCenter.plugin import sort_modes
		self.actualSort = sort_modes.get( config.EMC.moviecenter_sort.value )[1]
		self.returnSort = None
		self.selectionList = None

		self.recControl = RecordingsControl(self.recStateChange)

		self.currentSelectionCount = 0
		self.highlightsMov = []
		self.highlightsDel = []
		self.highlightsCpy = []
		self.hideitemlist = readBasicCfgFile("/etc/enigma2/emc-hide.cfg") or []
		self.nostructscan = readBasicCfgFile("/etc/enigma2/emc-noscan.cfg") or []
		self.topdirlist = readBasicCfgFile("/etc/enigma2/emc-topdir.cfg") or []

	def getList(self):
		return self.list

	def getListEntry(self, index):
		return self.list[index]

	def getTypeOfIndex(self, index):
		return self.list[index][7]

	def getSorting(self):
		# Return the actual sorting mode
		return self.actualSort

	def resetSorting(self):
		from Plugins.Extensions.EnhancedMovieCenter.plugin import sort_modes
		self.actualSort = sort_modes.get( config.EMC.moviecenter_sort.value )[1]

	def isEqualPermanentSort(self):
		isperm = False
		perm = self.getPermanentSort(self.currentPath)
		if perm is not None:
			isperm = self.actualSort == perm
		# Return if the current sorting mode is set as / equal the permanent one
		return isperm

	def doListSort(self, sortlist):
		# This will find all unsortable items
		# But is not as fast as the second implementation
		# If [2] = date = None then it is a directory or special folder entry
		# tmplist = [i for i in sortlist if i[7] in virAll]
		if config.EMC.directories_ontop.value:
			virToD = virToE
		else:
			virToD = virAll
		if config.EMC.cfgtopdir_enable.value:
			topdirlist = self.topdirlist
			tmplist = [i for i in sortlist if i[7] in virToD or i[3] in topdirlist]
		else:
			tmplist = [i for i in sortlist if i[7] in virToD]
		# Extract list items to be sorted
		sortlist = [i for i in sortlist if i not in tmplist]
		# Always sort via extension and sorttitle and never reversed
		tmplist.sort( key=lambda x: (x[7],x[1]) )

		# Sort list, same algorithm for both implementations
		# Using itemgetter is slightly faster but not as flexible
		#  from operator import itemgetter: (key=itemgetter(x))
		#  Then the list has to be flat
		#   no sub tuples are possible
		#   no negotiation is possible
		# Faster if separate? sortlist.reverse()
		# Tuple: (service, sorttitle, date, title, path, selectionnumber, length, ext, cutnr, sorteventtitle, eventtitle, piconpath, sortyear, sortmonth, sortday, sorthour, sortmin)
		mode, order = self.actualSort
		if mode is None:
			mode = self.actualSort[0]
		if order is None:
			order = self.actualSort[1]

		movie_metaload = config.EMC.movie_metaload.value
		if mode == "D":	# Date sort
			if not order:
				if movie_metaload:
					sortlist.sort( key=lambda x: (-x[12],-x[13],-x[14],-x[15],-x[16],x[1],x[9],-x[8]) )
				else:
					sortlist.sort( key=lambda x: (-x[12],-x[13],-x[14],-x[15],-x[16],x[1],-x[8]) )
			else:
				if movie_metaload:
					sortlist.sort( key=lambda x: (x[12],x[13],x[14],x[15],x[16], x[1], x[9], x[8]), reverse=True )
				else:
					sortlist.sort( key=lambda x: (x[12],x[13],x[14],x[15],x[16], x[1], x[8]), reverse=True )

		elif mode == "A":	# Alpha sort
			if not order:
				sortlist.sort( key=lambda x: (x[1],x[12],x[13],x[14],x[15],x[16],x[8]) )
			else:
				sortlist.sort( key=lambda x: (x[1],-x[12],-x[13],-x[14],-x[15],-x[16],-x[8]) )

		elif mode == "ADN":	# Alpha sort with new date, newest first
			if not order:
				sortlist.sort( key=lambda x: (x[1],-x[12],-x[13],-x[14],-x[15],-x[16],x[8]) )
			else:
				sortlist.sort( key=lambda x: (x[1],x[12],x[13],x[14],x[15],x[16],-x[8]) )

		elif mode == "AM":	# Alpha sort with meta
			if not order:
				sortlist.sort( key=lambda x: (x[1],x[9],x[12],x[13],x[14],x[15],x[16],x[8]) )
			else:
				sortlist.sort( key=lambda x: (x[1],x[9],-x[12],-x[13],-x[14],-x[15],-x[16],-x[8]) )

		elif mode == "AMDN":	# Alpha sort with meta and new date, newest first
			if not order:
				sortlist.sort( key=lambda x: (x[1],x[9],-x[12],-x[13],-x[14],-x[15],-x[16],x[8]) )
			else:
				sortlist.sort( key=lambda x: (x[1],x[9],x[12],x[13],x[14],x[15],x[16],-x[8]) )

		elif mode == "P":	# Progress
			if not order:
				sortlist.sort( key=lambda x: ( getProgress(x[0], x[6]) ) ) #,x[2],x[8]) )
			else:
				sortlist.sort( key=lambda x: ( getProgress(x[0], x[6]) ) ) # ,x[2],-x[8]) )

		# Combine lists
		if order:
			#TODO TEST later with green button solution
			sortlist.reverse()
		#	tmplist += sortlist
		#	return tmplist.reverse()
		#else:
		return tmplist + sortlist

	def updateLength(self, service, length):
		# Update entry in list... so next time we don't need to recalc
		idx = self.getIndexOfService(service)
		if idx >= 0:
			x = self.list[idx]
			if x[6] != length:
				l = list(x)
				l[6] = length
				self.list[idx] = tuple(l)

	def serviceBusy(self, service):
		return service in self.highlightsMov or service in self.highlightsDel or service in self.highlightsCpy

	def serviceMoving(self, service):
		return service and service in self.highlightsMov

	def serviceDeleting(self, service):
		return service and service in self.highlightsDel

	def serviceCopying(self, service):
		return service and service in self.highlightsCpy

	def __len__(self):
		return len(self.list)

	def resetSelection(self):
		self.selectionList = None
		self.currentSelectionCount = 0

	def getFilePathOfService(self, service):
		if service:
			for entry in self.list:
				if entry[0] == service:
					return entry[4]
		return ""

	def getNameOfService(self, service):
		if service:
			for entry in self.list:
				if entry[0] == service:
					return entry[3]
		return ""

	def getLengthOfService(self, service):
		if service:
			for entry in self.list:
				if entry[0] == service:
					return entry[6]
		return 0

	def getIndexOfService(self, service):
		if service:
			idx = 0
			for entry in self.list:
				if entry[0] == service:
					return idx
				idx += 1
		return -1

	def getServiceOfIndex(self, index):
		return self.list[index] and self.list[index][0]

	def createDirListRecursive(self, path, useCache = True):
		dirstack, subdirlist, subfilelist, filelist = [], [], [], []

		dappend = dirstack.append
		fextend = filelist.extend
		pathreal = os.path.realpath
		pathislink = os.path.islink
		pathsplitext = os.path.splitext

		# walk through entire tree below current path. Might take a bit long on huge disks...
		dirstack.append( path )

		# Search files through all given paths
		for directory in dirstack:

			# Avoid trashcan subdirectories
			if directory.find( config.EMC.movie_trashcan_path.value ) == -1:

				# Get entries
				subdirlist, subfilelist = self.createDirList(directory, useCache)

				# Found new directories to search within, use only their path
				for d, name, ext in subdirlist:
					# Resolve symbolic links and get the real path
					d = pathreal( d )

					# Avoid duplicate directories and ignore links
					if d not in dirstack and not pathislink( d ):
						dappend( d )

				# Store the media files
				fextend( subfilelist )

		del dappend
		del fextend
		del pathreal
		del pathislink
		del pathsplitext
		# We don't want any folders
		return [], filelist

	def __createDirList(self, path):
		subdirlist, filelist = [], []
		dvdStruct = None
		pathname, ext = "", ""

		# Improve performance and avoid dots
		movie_trashpath = config.EMC.movie_trashcan_enable.value and os.path.realpath(config.EMC.movie_trashcan_path.value)
		check_dvdstruct = config.EMC.check_dvdstruct.value \
							and not (config.EMC.cfgscan_suppress.value and path in self.nostructscan)
		check_moviestruct = config.EMC.check_moviestruct.value \
							and not (config.EMC.cfgscan_suppress.value and path in self.nostructscan)
		check_blustruct = config.EMC.check_blustruct.value \
							and not (config.EMC.cfgscan_suppress.value and path in self.nostructscan)

		hideitemlist = config.EMC.cfghide_enable.value and self.hideitemlist

		localExtList = extList - extBlu

		dappend = subdirlist.append
		fappend = filelist.append
		splitext = os.path.splitext
		pathjoin = os.path.join
		pathisfile = os.path.isfile
		pathisdir = os.path.isdir
		pathislink = os.path.islink

		if os.path.exists(path):

			# Get directory listing
			#TEST later performance listdir vs walk
			#for file in os.listdir(path):
			for root, dirs, files in os.walk(path):

				for file in files:

					# This will decrease the function execution time massively
					ext = splitext(file)[1].lower()

					if ext not in localExtList:
						continue

					if hideitemlist:
						if file in hideitemlist or (file[0:1] == "." and ".*" in hideitemlist):
							continue

					pathname = pathjoin(path, file)

					# Filter dead links
					if pathisfile(pathname):

						# Symlink media file
						if pathislink(pathname) and not config.EMC.symlinks_show.value:
							continue

						# Media file found
						fappend( (pathname, file, ext) )

				for dir in dirs:

					if hideitemlist:
						if dir in hideitemlist or (dir[0:1] == "." and ".*" in hideitemlist):
							continue

					pathname = pathjoin(path, dir)

					# Filter dead links
					if pathisdir(pathname):
						if check_dvdstruct:
							dvdStruct = detectDVDStructure(pathname)
							if dvdStruct:
								# DVD Structure found
								pathname = os.path.dirname(dvdStruct)
								ext = splitext(dvdStruct)[1].lower()
								fappend( (pathname, dir, ext) )
								continue
						if check_moviestruct:
							movStruct = detectMOVStructure(pathname)
							if movStruct:
								# Movie Structure found
								ext = splitext(movStruct)[1].lower()
								fappend( (movStruct, dir, ext) )
								continue
						if check_blustruct:
							bluStruct = detectBLUStructure(pathname)
							if bluStruct:
								# Bluray Structure found
								pathname = os.path.dirname(bluStruct)
								ext = splitext(bluStruct)[1].lower()
								fappend( (pathname, dir, ext) )
								continue
						if config.EMC.directories_show.value:
							if not movie_trashpath or os.path.realpath(pathname).find( movie_trashpath ) == -1:
								# Symlink folder found
								if pathislink(pathname) and not config.EMC.symlinks_show.value:
									continue
								# Folder found
								dappend( (pathname, dir, cmtDir) )
				# We only want the topdir
				break

		del dappend
		del fappend
		del splitext
		del pathjoin
		del pathisfile
		del pathisdir
		del pathislink
		return subdirlist, filelist

	def reloadDirList(self, path):
		return self.createDirList(path, False)

	def createDirList(self, path, useCache = True):
		subdirlist, filelist = [], []
		if useCache and movieFileCache.IsPathInCache(path):
			subdirlist, filelist = movieFileCache.getCacheForPath(path)
		else:
			subdirlist, filelist = self.__createDirList(path)
			movieFileCache.addPathToCache(path, subdirlist, filelist, self)
		return subdirlist, filelist

	def createLatestRecordingsList(self):
		# Make currentPath more flexible
		#MAYBE: What about using current folder for latest recording lookup?
		dirstack, subdirlist, filelist, subfilelist, newfilelist = [], [], [], [], []

		dappend = dirstack.append
		fextend = filelist.extend
		nfextend = newfilelist.extend
		pathreal = os.path.realpath
		pathislink = os.path.islink
		pathsplitext = os.path.splitext

		# walk through entire tree below movie home. Might take a bit long on huge disks...
		# think about breaking at 2nd level,
		# but include folders used in timers, auto timers and bookmarks
		dirstack.append( config.EMC.movie_homepath.value )

		# Search files through all given paths
		for directory in dirstack:

			# first we check entrys in "emc-noscan.cfg",
			# to load the list faster and dont wakeup any devices
			if not self.checkNoScanPath(directory):

				# Avoid trashcan subdirectories
				if directory.find( config.EMC.movie_trashcan_path.value ) == -1:

					# Get entries
					subdirlist, subfilelist = self.createDirList(directory, False)

					# Found new directories to search within, use only their path
					for d, name, ext in subdirlist:
						# Resolve symbolic links and get the real path
						d = pathreal( d )

						# Avoid duplicate directories and ignore links
						if d not in dirstack and not pathislink( d ):
							dappend( d )

					# Store the media files
					fextend( [ (p,f,e) for p,f,e in subfilelist if e in extTS ] )

		val = int(config.EMC.latest_recordings_limit.value)
		if val != -1:
			if imgVti:			# is needed for vti, "val" is 1-365 in days
				val = val * 86400
			for path, name, ext in filelist:
				fdate = self.checkDate(path)
				nowDate = time()         # time from now in seconds, 86400 is one day
				if fdate >= nowDate - val:
					nfextend( [ (path, name, ext) ] )

		del dappend
		del fextend
		del nfextend
		del pathreal
		del pathislink
		del pathsplitext

		# Sorting is done through our default sorting algorithm
		if val != -1:
			return newfilelist
		else:
			return filelist

	def checkNoScanPath(self, path):
		check = False
		if config.EMC.latest_recordings_noscan.value or config.EMC.dir_info_usenoscan.value:
			device = mountPoints.getMountPointDeviceCached(path)
			for line in self.nostructscan:
				if (line in path) or (line in device):
					check = True
					break
		return check

	def checkDate(self, path, dirDate=False):
		date = 0
		year, month, day, hour, min = "", "", "", "", ""
		try:
			if path and os.path.exists(path):
				getdate = os.stat(path)
				if dirDate:
					from time import strftime, localtime
					year = strftime('%Y', localtime(getdate[8]))
					month = strftime('%m', localtime(getdate[8]))
					day = strftime('%d', localtime(getdate[8]))
					hour = strftime('%H', localtime(getdate[8]))
					min = strftime('%M', localtime(getdate[8]))
				else:
					date = getdate[8]
		except Exception, e:
			emcDebugOut("[EMC] Exception in checkDate: " + str(e))
		if dirDate:
			return year, month, day, hour, min
		else:
			return date

	def createFileInfo(self, pathname):
		# Create info for new record
		p = os.path.basename(pathname)
		ext = os.path.splitext(p)[1].lower()
		return [ (pathname, p, ext) ]

	def createCustomList(self, currentPath, trashcan=True, extend=True):
		customlist = []
		path, name = "", ""
		append = customlist.append
		pathjoin = os.path.join
		pathreal = os.path.realpath

		currentPath = pathreal(currentPath)

		if currentPath != "" and currentPath != pathreal(config.EMC.movie_pathlimit.value):
			append( (	pathjoin(currentPath, ".."),
								"..",
								cmtUp) )

		if extend:
			# Insert these entries always at last
			if currentPath == pathreal(config.EMC.movie_homepath.value):
				if trashcan and config.EMC.movie_trashcan_enable.value and config.EMC.movie_trashcan_show.value:
					append( (	config.EMC.movie_trashcan_path.value,
										_(os.path.basename(config.EMC.movie_trashcan_path.value)) or _("trashcan"),
										cmtTrash) )

				if config.EMC.latest_recordings.value:
					append( (	pathjoin(currentPath, "Latest Recordings"),
										_("Latest Recordings"),
										cmtLRec) )

				if config.EMC.vlc.value and os.path.exists("/usr/lib/enigma2/python/Plugins/Extensions/VlcPlayer"):
					append( (	pathjoin(currentPath, "VLC servers"),
										"VLC servers",
										cmtVLC) )

				if config.EMC.bookmarks.value == "Both" or config.EMC.bookmarks.value == "E2":
					bookmarks = self.getE2Bookmarks()
					if bookmarks:
						for bookmark in bookmarks:
							append( (	bookmark,
												os.path.basename(bookmark) or bookmark,
												cmtBME2 ) )

				if config.EMC.bookmarks.value == "Both" or config.EMC.bookmarks.value == "EMC":
					bookmarks = self.getEMCBookmarks()
					if bookmarks:
						for bookmark in bookmarks:
							append( (	bookmark,
												os.path.basename(bookmark),
												cmtBMEMC ) )

		del append
		del pathjoin
		return customlist

	def reloadInternal(self, currentPath, simulate=False, recursive=False):
		#TODO add parameter reset list sort
		emcDebugOut("[EMC] LOAD PATH:\n" + str(currentPath))
		customlist, subdirlist, filelist, tmplist = [], [], [], []
		resetlist = True
		nextSort = None

		if config.EMC.remote_recordings.value:
			# get a list of current remote recordings
			self.recControl.recFilesRead()

		# Create listings
		if os.path.isdir(currentPath):
			# Found directory

			# Read subdirectories and filenames
			if not recursive:
				subdirlist, filelist = self.createDirList(currentPath, True)
			else:
				subdirlist, filelist = self.createDirListRecursive(currentPath, True)

			if not simulate:
				customlist = self.createCustomList(currentPath)

		elif os.path.isfile(currentPath):
			# Found file

			filelist = self.createFileInfo(currentPath)
			resetlist = False
			currentPath = None

		else:
			# Found virtual directory

			if currentPath.endswith("VLC servers"):
				emcDebugOut("[EMC] VLC Server")
				subdirlist = self.createVlcServerList(currentPath)
				customlist = self.createCustomList(currentPath, extend=False)

			elif currentPath.find("VLC servers")>-1:
				emcDebugOut("[EMC] VLC Files")
				subdirlist, filelist = self.createVlcFileList(currentPath)

			elif currentPath.endswith("Latest Recordings"):
				emcDebugOut("[EMC] Latest Recordings")
				filelist = self.createLatestRecordingsList()
				customlist = self.createCustomList(currentPath, extend=False)
				# Set date descending as next sort mode
				nextSort = ("D",False)

			else:
				# No changes done
				return False

		# Local variables
		movie_hide_mov = config.EMC.movie_hide_mov.value
		movie_hide_del = config.EMC.movie_hide_del.value
		movie_show_cutnr = config.EMC.movie_show_cutnr.value
		movie_show_format = config.EMC.movie_show_format.value
		title_replace_special_chars = config.EMC.replace_specialchars.value

		# Avoid dots
		append = tmplist.append
		pathexists = os.path.exists
		pathsplitext = os.path.splitext

		service = None
		title, sorttitle = "", ""
		date = datetime.fromtimestamp(0)
		cutnr = ""
		metastring, eitstring = "", ""
		sorteventtitle, eventtitle = "", ""
		piconpath = ""
		sortyear, sortmonth, sortday, sorthour, sortmin = "", "", "", "", ""

		# Add custom entries and sub directories to the list
		customlist += subdirlist
		if customlist is not None:
			for path, filename, ext in customlist:
				sorttitle = ""
				title = filename

				# Replace special chars with spaces
				if title_replace_special_chars:
					title = title.replace("_"," ")
					title = title.replace("."," ")

				# Very bad but there can be both encodings
				# E2 recordings are always in utf8
				# User files can be in cp1252
				#TODO Is there no other way?
				try:
					title.decode('utf-8')
				except UnicodeDecodeError:
					try:
						title = title.decode("cp1252").encode("utf-8")
					except UnicodeDecodeError:
						title = title.decode("iso-8859-1").encode("utf-8")

				service = getPlayerService(path, title)

				sorttitle = title.lower()

				if date is None:
					date = datetime.fromtimestamp(0)

				# we get now the real date for folders
				# so we can sort this, if they are in the list, not at top
				if path.endswith("Latest Recordings") or path.endswith("VLC servers"):
					pass
				else:
					if title not in self.topdirlist:
						newDate = None
						if config.EMC.files_cache.value:
							newDate = movieFileCache.getDateInfoFromCacheForPath(path)
						if newDate is None:
							newDate = newDate or self.checkDate(path, True)
						sortyear = newDate[0]
						sortmonth = newDate[1]
						sortday = newDate[2]
						sorthour = newDate[3]
						sortmin = newDate[4]
				append((service, sorttitle, date, title, path, 0, 0, ext, 0, sorteventtitle, eventtitle, piconpath, int(sortyear or 0), int(sortmonth or 0), int(sortday or 0), int(sorthour or 0), int(sortmin or 0)))

		# Add file entries to the list
		if filelist is not None:
			#TODO extract the function to retrieve the correct title
			movie_metaload = config.EMC.movie_metaload.value
			movie_eitload = config.EMC.movie_eitload.value
			for path, filename, ext in filelist:
				# Filename, Title, Date, Sortingkeys handling
				# First we extract as much as possible informations from the filename
				service = None
				title, date, cutnr = "", "", ""
				length = 0
				#TODO metalength, eitlength and priority handling
				metastring, eitstring = "", ""
				#metadate, eitdate = "", ""
				sorttitle = ""
				#sortdate = ""
				#sortkeyalpha, sortkeydate = "", ""
				sorteventtitle = ""
				eventtitle = ""
				piconpath = ""
				sortyear, sortmonth, sortday, sorthour, sortmin = "", "", "", "", ""
				isExtHDDSleeping = mountPoints.isExtHDDSleeping(str(currentPath),self)

				# Remove extension
				if not ext:
					# Avoid splitext it is very slow compared to a slice
					title, ext = pathsplitext(filename)
				else:
					#TODO Should not be necessary
					# If there is an ext filename is already the shortname without the extension
					#title = filename[:-len(ext)]
					title = pathsplitext(filename)[0]

				# Get cut number
				if title[-4:-3] == "_" and title[-3:].isdigit():
					cutnr = title[-3:]
					title = title[:-4]

				# Replace special chars with spaces
				if title_replace_special_chars:
					title = title.replace("_"," ")
					title = title.replace("."," ")

				# Derived from RecordTimer
				# This is everywhere so test it first
				if title[0:8].isdigit():
					if not title[8:9].isdigit() and title[9:13].isdigit():
						# Default: filename = YYYYMMDD TIME - service_name
						date = title[0:13]									# "YYYYMMDD TIME - " -> "YYYYMMDD TIME"
						title = title[16:]									# skips "YYYYMMDD TIME - "

						# Standard: filename = YYYYMMDD TIME - service_name - name
						# Long Composition: filename = YYYYMMDD TIME - service_name - name - description
						# Standard: filename = YYYYMMDD TIME - service_name - name
						# Skip service_name, extract name
						split = title.find(" - ")
						if split > 0: title = title[3+split:]

					elif title[8:11] == " - ":
						# Short Composition: filename = YYYYMMDD - name
						date = title[0:8] + " 2000"			# "YYYYMMDD" + " " + DUMMY_TIME
						title = title[11:]									# skips "YYYYMMDD - "

					if date:
						dtime = int(date[9:13] or 2000)
						date = int(date[0:8] or 0)
						try:
							date = datetime(date/10000, date%10000/100, date%100, dtime/100, dtime%100)
						except ValueError, e:
							date = datetime.fromtimestamp(0)

				# If the user wants it, extract information from the meta and eit files
				# But it is very slow

				if movie_metaload and not isExtHDDSleeping:
					# read title from META
					meta = MetaList(path)
					if meta:
						metastring = meta.getMetaName()
						eventtitle = meta.getMetaTitle()
						if not eventtitle and config.EMC.movie_metaload_all.value:
							eventtitle = meta.getMetaDescription()
						if not date:
							date = meta.getMetaDate()
						# Improve performance and avoid calculation of movie length
						length = meta.getMetaLength()

				if not metastring and movie_eitload and not isExtHDDSleeping:
						# read title from EIT
						eit = EitList(path)
						if eit:
							eitstring = eit.getEitName()
							if not date:
								date = eit.getEitDate()
							if not length:
								length = eit.getEitLengthInSeconds()
				# get piconpath
				if config.EMC.movie_picons.value and not isExtHDDSleeping:
					meta = MetaList(path)
					metaref = meta.getMetaServiceReference()
					if config.EMC.movie_picons_path_own.value:
						pos = metaref.rfind(':')
						if pos != -1:
							metaref = metaref[:pos].rstrip(':').replace(':', '_')
					# now we need to check if picon-file exists
					if newPiconRenderer:
						if config.EMC.movie_picons_path_own.value:
							picon = config.EMC.movie_picons_path.value + "/" + metaref + '.png'
						else:
							picon = getPiconName(metaref)
					else:
						picon = config.EMC.movie_picons_path.value + "/" + metaref + '.png'
					if fileExists(picon):
						piconpath = picon

				# Priority and fallback handling

				# Set title priority here
				# Fallback is the filename
				title = metastring or eitstring or title or filename

				# Very bad but there can be both encodings
				# E2 recordings are always in utf8
				# User files can be in cp1252
				#TODO Is there no other way?
				try:
					title.decode('utf-8')
				except UnicodeDecodeError:
					try:
						title = title.decode("cp1252").encode("utf-8")
					except UnicodeDecodeError:
						title = title.decode("iso-8859-1").encode("utf-8")

				# Set date priority here
				# Fallback get date from filesystem, but it is very slow
				if config.EMC.files_cache.value and not date:
					date = movieFileCache.getDateInfoFromCacheForPath(path)
					if date is not None:
						date = datetime.fromtimestamp(date)
				if not date:
					date = pathexists(path) and datetime.fromtimestamp( self.checkDate(path) ) or None
				if date is None:
					date = datetime.fromtimestamp(0)

				# Create sortkeys
				#if not sortdate: sortdate = date and date.strftime( "%Y%m%d %H%M" ) or ""
				sorttitle = title.lower()
				sorteventtitle = eventtitle.lower()
				#sortkeyalpha = sorttitle + ("%03d") % int(cutnr or 0) + sortdate
				#sortkeydate = sortdate + sorttitle + ("%03d") % ( 999 - int(cutnr or 0) )

				# combine information regarding the emc config
				if movie_show_cutnr:
					title += " "+cutnr

				if movie_show_format:
					title += " "+ext[1:]

				# Get player service and set formatted title
				service = getPlayerService(path, title, ext)

				# Bad workaround to get all information into our Service Source
				service.date = date
				# get a better date to sort with other values
				try:
					sdate = str(date)
					sdate = sdate.split(' ', -1)
					if len(sdate) >= 1:
						stime = sdate[1].split(':', -1)
						sorthour = stime[0]
						sortmin = stime[1]
					sdate = sdate[0].split('-', -1)
					sortyear = sdate[0]
					sortmonth = sdate[1]
					sortday = sdate[2]
				except Exception, e:
					emcDebugOut("[EMC] Exception in get new date-sort values: " + str(e) + "\n" + "trying with this date: " + str(date))

				# Check config settings
				#TODO These checks should be done earlier but there we don't have the service yet
				if (movie_hide_mov and self.serviceMoving(service)) \
					or (movie_hide_del and self.serviceDeleting(service)):
					continue
				append((service, sorttitle, date, title, path, 0, length, ext, int(cutnr or 0), sorteventtitle, eventtitle, piconpath, int(sortyear or 0), int(sortmonth or 0), int(sortday or 0), int(sorthour or 0), int(sortmin or 0)))

		# Cleanup before continue
		del append
		del pathexists
		del pathsplitext

		if not simulate:
			# If we are here, there is no way back
			self.currentSelectionCount = 0
			self.selectionList = None

			if currentPath is not None:
				self.currentPath = currentPath

				# Lookup for a permanent sorting mode
				perm = self.getPermanentSort(currentPath)
				if perm:
					# Backup the actual sorting mode
					if self.returnSort is None:
						self.returnSort = self.actualSort
					self.actualSort = perm

				elif self.returnSort:
					# Restore sorting mode
					self.actualSort = self.returnSort
					self.returnSort = None

				if nextSort:
					# Backup the actual sorting mode
					if self.returnSort is None:
						self.returnSort = self.actualSort
					# Set new sorting mode
					self.actualSort = nextSort

			if resetlist:
				self.list = []
			else:
				tmplist = self.list + tmplist

			self.list = self.doListSort( tmplist )
			return self.list

		else:
			# Simulate only
			return self.doListSort( tmplist )

	def globalReload(self, arg):
		try:
			global moviecenter
			if moviecenter:
				moviecenter.reload( arg )
		except: pass

	def globalRefresh(self):
		try:
			global moviecenter
			if moviecenter:
				moviecenter.refreshList()
		except: pass

	def recStateChange(self, timer):
		if timer:
			path = os.path.dirname(timer.Filename)
			if os.path.realpath(path) == os.path.realpath(self.currentPath):
				# EMC shows the directory which contains the recording
				filename = timer.Filename + ".ts"
				if timer.state == TimerEntry.StateRunning:
					if not self.list:
						# Empty list it will be better to reload it complete
						# Maybe EMC was never started before
						emcDebugOut("[MC] Timer started - full reload")
						DelayedFunction(3000, self.globalReload, self.currentPath)
					else:
						# We have to add the new recording
						emcDebugOut("[MC] Timer started - add recording")
						# Timer filname is without extension
						DelayedFunction(3000, self.globalReload, filename)
				elif timer.state == TimerEntry.StateEnded:
					#MAYBE Just refresh the ended record
					# But it is fast enough
					emcDebugOut("[MC] Timer ended")
					DelayedFunction(3000, self.globalRefresh)
					# [Cutlist.Workaround] Initiate the Merge
					DelayedFunction(3000, self.mergeCutListAfterRecording, filename)

	def mergeCutListAfterRecording(self, path):
		emcDebugOut("[Cutlist.Workaround] MovieCenter.mergeCutListAfterRecording: " + str(path))
		cuts = CutList( path )
		cuts.updateFromCuesheet()

	def getNextService(self, service):
		#IDEA: Optionally loop over all
		#TODO calculate the correct title
		idx = self.getIndexOfService(service)
		if self.list[idx][7] in extMedia:
			# Cursor marks a movie
			length = len(self.list)
			for i in xrange(length):
				entry = self.list[ (i+idx)%length ]
				if entry and entry[7] in plyAll:
					# Entry is no directory
					service = entry[0]
					if not self.serviceBusy(service):
						yield service
		elif self.list[idx][7] == cmtDir:
			# Cursor marks a directory
			#IDEA: Optionally play also the following movielist items (folders and movies)
			path = self.list[idx][4]
			# Don't play movies from the trash folder or ".."
			if os.path.realpath(path) != os.path.realpath(config.EMC.movie_trashcan_path.value) and path != "..":
				#TODO Reuse the reload and createdirlist function
					# Then the files are sorted and played in their correct order
					# So we don't have the whole dir and file recognition handling twice
					# Simulate reload:	tmplist = self.reload(path, True)
				for root, dirs, files in os.walk(path): #,False):
					if dirs:
						for dir in dirs:
							pathname = os.path.join(root, dir)
							dvdStruct = detectDVDStructure( pathname )
							if dvdStruct:
								pathname = os.path.dirname(dvdStruct)
								ext = os.path.splitext(dvdStruct)[1].lower()
								service = getPlayerService(pathname, dir, ext)
								if not self.serviceBusy(service):
									yield service
					if files:
						for name in files:
							ext = os.path.splitext(name)[1].lower()
							if ext in extMedia:
								pathname = os.path.join(root, name)
								#TODO get formatted Name
								service = getPlayerService(pathname, name, ext)
								if not self.serviceBusy(service):
									yield service

	def getRandomService(self, service):
		#IDEA: Optionally loop over all
		#TODO calculate the correct title
		idx = self.getIndexOfService(service)
		if self.list[idx][7] in extMedia:
			# Cursor marks a movie
			length = len(self.list)
			shuffle = range(length)
			random.shuffle( shuffle )
			for i in shuffle:
				entry = self.list[i]
				if entry and entry[7] in plyAll:
					# Entry is no directory
					service = entry[0]
					if not self.serviceBusy(service):
						yield service
		elif self.list[idx][7] == cmtDir:
			# Cursor marks a directory
			#IDEA: Optionally play also the following movielist items (folders and movies)
			path = self.list[idx][4]
			# Don't play movies from the trash folder or ".."
			if os.path.realpath(path) != os.path.realpath(config.EMC.movie_trashcan_path.value) and path != "..":
				#IDEA Is there a way to reuse the reload or createdirlist function
					#TODO Then the files are sorted and played in their correct order
					# So we don't have the whole dir and file recognition handling twice
					# Simulate reload:	tmplist = self.reload(path, True)
				entries = []
				for root, dirs, files in os.walk(path):
					for dir in dirs:
						entries.append( os.path.join(root, dir) )
					for file in files:
						entries.append( os.path.join(root, file) )

				if entries:
					length = len(entries)
					shuffle = range(length)
					random.shuffle( shuffle )
					for i in shuffle:
						entry = entries[i]
						pathname = os.path.join(root, entry)
						ext = os.path.splitext(pathname)[1]
						if ext in plyAll:
							# Entry is playable
							service = getPlayerService(pathname, entry, ext)
							if not self.serviceBusy(service):
								yield service

						elif os.path.isdir(pathname):
							dvdStruct = detectDVDStructure( pathname )
							if dvdStruct:
								path = os.path.dirname(dvdStruct)
								ext = os.path.splitext(dvdStruct)[1].lower()
								service = getPlayerService(path, entry, ext)
								if not self.serviceBusy(service):
									yield service

	def removeServiceInternal(self, service):
		if service:
			for l in self.list[:]:
				if l[0] == service:
					self.list.remove(l)
					break
			return self.doListSort(self.list)

	def removeServiceOfTypeInternal(self, service, type):
		if service:
			for l in self.list[:]:
				if l[0] == service and l[7] == type:
					self.list.remove(l)
					break
			return self.doListSort(self.list)

	def setSortingModeInternal(self, mode, order):
		self.returnSort = None

		if mode is None:
			mode = self.actualSort[0]
		if order is None:
			order = self.actualSort[1]

		self.actualSort = (mode, order)

		self.list = self.doListSort(self.list)
		return self.list

	def toggleSelectionInternal(self, entry, index, overrideNum, invalidateFunction=None):
		if self.selectionList == None:
			self.selectionList = []
		newselnum = entry[5]	# init with old selection number
		if overrideNum == None:
			if self.serviceBusy(entry[0]): return	# no toggle if file being operated on
			# basic selection toggle
			if newselnum == 0:
				# was not selected
				self.currentSelectionCount += 1
				newselnum = self.currentSelectionCount
				self.selectionList.append(entry[0]) # append service
			else:
				# was selected, reset selection number and decrease all that had been selected after this
				newselnum = 0
				self.currentSelectionCount -= 1
				count = 0
				if entry is not None:
					if entry[0] in self.selectionList:
						self.selectionList.remove(entry[0]) # remove service
				for i in self.list:
					if i[5] > entry[5]:
						l = list(i)
						l[5] = i[5]-1
						self.list[count] = tuple(l)
						invalidateFunction and invalidateFunction(count) # force redraw
					count += 1
		else:
			newselnum = overrideNum * (newselnum == 0)
		l = list(entry)
		l[5] = newselnum
		self.list[index] = tuple(l)
		invalidateFunction and invalidateFunction(index) # force redraw of the modified item

	def highlightServiceInternal(self, enable, mode, service):
		if enable:
			if mode == "move":
				self.highlightsMov.append(service)
			elif mode == "del":
				self.highlightsDel.append(service)
			elif mode == "copy":
				self.highlightsCpy.append(service)
		elif service:
			# Reset the length to force progress recalculation
			self.updateLength(service, 0)
			if mode == "move":
				if service in self.highlightsMov:
					self.highlightsMov.remove(service)
			elif mode == "del":
				if service in self.highlightsDel:
					self.highlightsDel.remove(service)
			elif mode == "copy":
				if service in self.highlightsCpy:
					self.highlightsCpy.remove(service)


def loadPix(name):
	plugindir = '/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/'
	if fileExists(resolveFilename(SCOPE_CURRENT_SKIN, 'emc/'+name)):
		pic = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, 'emc/'+name))
	else:
		pic = LoadPixmap(cached=True, path=plugindir+name)
	return pic


moviecenter = None

class MovieCenter(GUIComponent):

	def __getattr__(self, name):
		global moviecenterdata
		if moviecenterdata is None:
			moviecenterdata = MovieCenterData()
		return getattr(moviecenterdata, name)

	#def __setattr__(self, name, value):
	#	global moviecenterdata
	#	if moviecenterdata is None:
	#		moviecenterdata = MovieCenterData()
	#	setattr(moviecenterdata, name, value)

	def __init__(self):
		GUIComponent.__init__(self)

		global moviecenter
		moviecenter = self

		screenwidth = getDesktop(0).size().width()
		if screenwidth and screenwidth == 1920:
			self.fullhd = True
		else:
			self.fullhd = False

		self.startWorker = False

		self.serviceHandler = ServiceCenter.getInstance()

		self.CoolFont = parseFont("Regular;20", ((1,1),(1,1)))
		self.CoolSelectFont = parseFont("Regular;20", ((1,1),(1,1)))
		self.CoolDateFont = parseFont("Regular;20", ((1,1),(1,1)))

		#IDEA self.CoolIconPos
		self.CoolMoviePos = 100
		self.CoolMovieHPos = 0
		self.CoolMovieSize = 490
		self.CoolFolderSize = 550
		self.CoolTitleColor = 0
		self.CoolDatePos = -1
		self.CoolDateHPos = 0
		self.CoolDateWidth = 110
		self.CoolDateColor = 0
		self.CoolHighlightColor = 0
		self.CoolProgressPos = -1
		self.CoolProgressHPos = 0
		self.CoolBarPos = -1
		self.CoolBarHPos = 8
		self.CoolIconHPos = 2
		# we have now reached a point, where we need a
		# general change in buildMovieCenterEntry for that
		# for example:
		# we can make now all values like that
		# so it gives more possibilities for skinners, but needs real changes then !
		# self.CoolIconPos = parsePosition("5,2", ((1,1),(1,1)))
		# self.CoolIconSize = parseSize("24,24", ((1,1),(1,1)))
		self.CoolIconPos = 5
		self.CoolIconSize = parseSize("24,24", ((1,1),(1,1)))

		self.CoolSelNumTxtWidth = 26

		self.CoolBarSize = parseSize("55,10", ((1,1),(1,1)))
		self.CoolBarSizeSa = parseSize("55,10", ((1,1),(1,1)))

		self.CoolMoviePiconPos = -1
		self.CoolMoviePiconSize = -1
		self.CoolPiconPos = -1
		self.CoolPiconHPos = -1
		self.CoolPiconWidth = -1
		self.CoolPiconHeight = -1
		self.CoolCSWidth = 110
		self.CoolDirInfoWidth = -1

		self.DefaultColor = 0xFFFFFF
		self.TitleColor = 0xFFFFFF
		self.DateColor = 0xFFFFFF
		self.BackColor = None
		self.BackColorSel = 0x000000
		self.FrontColorSel = 0xFFFFFF
		self.UnwatchedColor = 0xFFFFFF
		self.WatchingColor = 0x3486F4
		self.FinishedColor = 0x46D93A
		self.RecordingColor = 0x9F1313
		#IDEA self.CutColor

		self.l = eListboxPythonMultiContent()
		self.l.setFont(0, gFont("Regular", 22))
		self.l.setFont(1, self.CoolFont)
		self.l.setFont(2, gFont("Regular", 20))
		self.l.setFont(3, self.CoolSelectFont)
		self.l.setFont(4, self.CoolDateFont)
		self.l.setBuildFunc(self.buildMovieCenterEntry)
		self.l.setItemHeight(28)

		self.pic_back            = loadPix('back.png')
		self.pic_directory       = loadPix('dir.png')
		self.pic_directory_locked= loadPix('dir_locked.png')
		self.pic_directory_search= loadPix('dir_search.png')
		self.pic_movie_default   = loadPix('movie_default.png')
		self.pic_movie_unwatched = loadPix('movie_unwatched.png')
		self.pic_movie_watching  = loadPix('movie_watching.png')
		self.pic_movie_finished  = loadPix('movie_finished.png')
		self.pic_movie_rec       = loadPix('movie_rec.png')
		self.pic_movie_recrem    = loadPix('movie_recrem.png')
		self.pic_movie_cut       = loadPix('movie_cut.png')
		self.pic_e2bookmark      = loadPix('e2bookmark.png')
		self.pic_emcbookmark     = loadPix('emcbookmark.png')
		self.pic_trashcan        = loadPix('trashcan.png')
		self.pic_trashcan_full   = loadPix('trashcan_full.png')
		self.pic_mp3             = loadPix('music.png')
		self.pic_dvd_default     = loadPix('dvd_default.png')
		self.pic_dvd_watching    = loadPix('dvd_watching.png')
		self.pic_dvd_finished    = loadPix('dvd_finished.png')
		self.pic_brd_default     = loadPix('brd_default.png')
		# TODO: Progress.value for blue structure
		#self.pic_brd_watching    = loadPix('brd_watching.png')
		#self.pic_brd_finished    = loadPix('brd_finished.png')
		self.pic_playlist        = loadPix('playlist.png')
		self.pic_vlc             = loadPix('vlc.png')
		self.pic_vlc_dir         = loadPix('vlcdir.png')
		self.pic_link            = loadPix('link.png')
		self.pic_latest          = loadPix('virtual.png')
		self.pic_col_dir         = loadPix('coldir.png')

		self.onSelectionChanged = []

		self.l.setList( self.getList() )

	def applySkin(self, desktop, parent):
		attribs = []
		if self.skinAttributes is not None:
			for (attrib, value) in self.skinAttributes:
				if attrib == "CoolFont":
					self.CoolFont = parseFont(value, ((1,1),(1,1)))
					self.l.setFont(1, self.CoolFont)
				elif attrib == "CoolSelectFont":
					self.CoolSelectFont = parseFont(value, ((1,1),(1,1)))
					self.l.setFont(3, self.CoolSelectFont)
				elif attrib == "CoolDateFont":
					self.CoolDateFont = parseFont(value, ((1,1),(1,1)))
					self.l.setFont(4, self.CoolDateFont)
				elif attrib == "CoolDirPos":
					pass

				elif attrib == "CoolMoviePos":
					self.CoolMoviePos = int(value)
				elif attrib == "CoolMovieHPos":
					self.CoolMovieHPos = int(value)
				elif attrib == "CoolMovieSize":
					self.CoolMovieSize = int(value)
				elif attrib == "CoolMoviePiconPos":
					self.CoolMoviePiconPos = int(value)
				elif attrib == "CoolMoviePiconSize":
					self.CoolMoviePiconSize = int(value)
				elif attrib == "CoolIconHPos":
					self.CoolIconHPos = int(value)
				elif attrib == "CoolIconPos":
					self.CoolIconPos = int(value)
				elif attrib == "CoolIconSize":
					self.CoolIconSize = parseSize(value, ((1,1),(1,1)))

				elif attrib == "CoolFolderSize":
					self.CoolFolderSize = int(value)
				elif attrib == "CoolTitleColor":
					self.CoolTitleColor = int(value)
				elif attrib == "CoolDatePos":
					self.CoolDatePos = int(value)
				elif attrib == "CoolDateHPos":
					self.CoolDateHPos = int(value)
				elif attrib == "CoolDateWidth":
					self.CoolDateWidth = int(value)
				elif attrib == "CoolDateColor":
					self.CoolDateColor = int(value)
				elif attrib == "CoolHighlightColor":
					self.CoolHighlightColor = int(value)
				elif attrib == "CoolTimePos":
					pass

				elif attrib == "CoolDirInfoWidth":
					self.CoolDirInfoWidth = int(value)
				elif attrib == "CoolSelNumTxtWidth":
					self.CoolSelNumTxtWidth = int(value)
				elif attrib == "CoolProgressPos":
					self.CoolProgressPos = int(value)
				elif attrib == "CoolProgressHPos":
					self.CoolProgressHPos = int(value)
				elif attrib == "CoolBarPos":
					self.CoolBarPos = int(value)
				elif attrib == "CoolBarHPos":
					self.CoolBarHPos = int(value)
				elif attrib == "CoolBarSize":
					self.CoolBarSize = parseSize(value, ((1,1),(1,1)))
				elif attrib == "CoolBarSizeSa":
					self.CoolBarSizeSa = parseSize(value, ((1,1),(1,1)))
				elif attrib == "CoolPiconPos":
					self.CoolPiconPos = int(value)
				elif attrib == "CoolPiconHPos":
					self.CoolPiconHPos = int(value)
				elif attrib == "CoolPiconWidth":
					self.CoolPiconWidth = int(value)
				elif attrib == "CoolPiconHeight":
					self.CoolPiconHeight = int(value)
				elif attrib == "DefaultColor":
					self.DefaultColor = parseColor(value).argb()
				elif attrib == "BackColor":
					self.BackColor = parseColor(value).argb()
				elif attrib == "BackColorSel":
					self.BackColorSel = parseColor(value).argb()
				elif attrib == "FrontColorSel":
					self.FrontColorSel = parseColor(value).argb()
				elif attrib == "UnwatchedColor":
					self.UnwatchedColor = parseColor(value).argb()
				elif attrib == "WatchingColor":
					self.WatchingColor = parseColor(value).argb()
				elif attrib == "FinishedColor":
					self.FinishedColor = parseColor(value).argb()
				elif attrib == "RecordingColor":
					self.RecordingColor = parseColor(value).argb()
				else:
					attribs.append((attrib, value))
		self.skinAttributes = attribs
		return GUIComponent.applySkin(self, desktop, parent)

	def selectionChanged(self):
		for f in self.onSelectionChanged:
			try:
				f()
			except Exception, e:
				emcDebugOut("[MC] External observer exception: \n" + str(e))

	def buildMovieCenterEntry(self, service, sorttitle, date, title, path, selnum, length, ext, cutnr, sorteventtitle, eventtitle, piconpath, *args):
		#TODO remove before release
		try:
			offset = 0
			progressWidth = 55
			globalHeight = 80
			progress = 0
			pixmap = None
			color = None
			datetext = ""

			res = [ None ]
			append = res.append

			isLink = None
			if config.EMC.files_cache.value:
				isLink = movieFileCache.getLinkInfoFromCacheForPath(path)
			if isLink is None:
				isLink = os.path.islink(path)
			isExtHDDSleeping = mountPoints.isExtHDDSleeping(path,self)
			#usedFont = int(config.EMC.skin_able.value)
			if int(config.EMC.skin_able.value):
				usedFont = 1
				usedDateFont = 4
			else:
				usedFont = 0
				usedDateFont = 2

			#TODOret print "EMC ret bldSer " +str(service.toString())

			if ext in plyAll:
				colortitle = None
				colordate = None
				colorhighlight = None
				selnumtxt = None

				bluiso = False
				checkIso = config.EMC.check_blustruct_iso.value
				if checkIso:
					if ext in extIso:
						if detectBLUISO(service.getPath()):
							bluiso = True

				# Playable files
				latest = date and (datetime.today()-date).days < 1

				# Check for recording only if date is within the last day
				if latest and self.recControl.isRecording(path):
					datetext = "-- REC --"
					pixmap = self.pic_movie_rec
					color = self.RecordingColor
					# Recordings status shows always the progress of the recording,
					# Never the progress of the cut list marker to avoid misunderstandings
					progress = service and getRecordProgress(path) or 0

				elif latest and config.EMC.remote_recordings.value and self.recControl.isRemoteRecording(path):
					datetext = "-- rec --"
					pixmap = self.pic_movie_recrem
					color = self.RecordingColor

				#IDEA elif config.EMC.check_movie_cutting.value:
				elif self.recControl.isCutting(path):
					datetext = "-- CUT --"
					pixmap = self.pic_movie_cut
					color = self.RecordingColor

				elif ext in plyVLC:
					datetext = "   VLC   "
					pixmap = self.pic_vlc
					color = self.DefaultColor

				else:
					# Media file
					if config.EMC.movie_date_format.value:
						datetext = date.strftime( config.EMC.movie_date_format.value )

					if config.EMC.movie_progress.value and not isExtHDDSleeping:
						# Calculate progress and state
						progress, updlen = getProgress(service, length) or 0
						if updlen:
							self.updateLength(service, updlen)
						movieUnwatched = config.EMC.movie_progress.value and	progress < int(config.EMC.movie_watching_percent.value)
						movieWatching  = config.EMC.movie_progress.value and	progress >= int(config.EMC.movie_watching_percent.value) and progress < int(config.EMC.movie_finished_percent.value)
						movieFinished  = config.EMC.movie_progress.value and	progress >= int(config.EMC.movie_finished_percent.value)
					else:
						progress = 0
						movieUnwatched = False
						movieWatching = False
						movieFinished = False

					# Icon
					if config.EMC.movie_icons.value:
						# video
						if ext in extVideo and ext not in extDvd and ext not in extBlu:
							if movieUnwatched:
								if config.EMC.mark_latest_files.value and latest:
									pixmap = self.pic_latest
								else:
									pixmap = self.pic_movie_unwatched
							elif movieWatching:
								pixmap = self.pic_movie_watching
							elif movieFinished:
								pixmap = self.pic_movie_finished
							else:
								pixmap = self.pic_movie_default
						# audio
						elif ext in extAudio:
							pixmap = self.pic_mp3
						# dvd iso/structure
						elif ext in extDvd and not bluiso:
							if movieWatching:
								pixmap = self.pic_dvd_watching
							elif movieFinished:
								pixmap = self.pic_dvd_finished
							else:
								pixmap = self.pic_dvd_default
						# blue iso/structure
						elif ext in extBlu or bluiso:
							pixmap = self.pic_brd_default
							# TODO: Progress.value for blue iso/structure
							#if movieWatching:
							#	pixmap = self.pic_brd_watching
							#elif movieFinished:
							#	pixmap = self.pic_brd_finished
							#else:
							#	pixmap = self.pic_brd_default

						# playlists
						elif ext in extPlaylist:
							pixmap = self.pic_playlist
						# all others
						else:
							pixmap = self.pic_movie_default

					# Color
					if movieUnwatched:
						color = self.UnwatchedColor
					elif movieWatching:
						color = self.WatchingColor
					elif movieFinished:
						color = self.FinishedColor
					else:
						color = self.DefaultColor

				colortitle = color
				colordate = color
				#colorhighlight = color
				if color == self.WatchingColor or color == self.FinishedColor or color == self.RecordingColor:
					colorhighlight = color
				else:
					colorhighlight = self.FrontColorSel

				# Get entry selection number
				if service in self.highlightsMov: selnumtxt = "-->"
				elif service in self.highlightsDel: selnumtxt = "X"
				elif service in self.highlightsCpy: selnumtxt = "+"
				elif selnum > 0: selnumtxt = "%02d" % selnum

				if selnumtxt is None:
					if config.EMC.movie_icons.value:
						# hide symlink arrow
						if isLink and config.EMC.link_icons.value:
							selPic = self.pic_link
						else:
							selPic = pixmap
						if not config.EMC.skin_able.value:
							append(MultiContentEntryPixmapAlphaBlend(pos=(5,2), size=(24,24), png=selPic, **{}))
							offset = 35
						else:
							append(MultiContentEntryPixmapAlphaBlend(pos=(self.CoolIconPos,self.CoolIconHPos), size=(self.CoolIconSize.width(),self.CoolIconSize.height()), png=selPic, **{}))
							offset = self.CoolIconPos + self.CoolIconSize.width() + 5
					else:
						offset = 5
				else:
					if not config.EMC.skin_able.value:
						append(MultiContentEntryText(pos=(5, 2), size=(self.CoolSelNumTxtWidth, globalHeight), font=3, flags=RT_HALIGN_LEFT, text=selnumtxt))
						offset += 5 + self.CoolSelNumTxtWidth + 4
					else:
						append(MultiContentEntryText(pos=(self.CoolIconPos, self.CoolIconHPos), size=(self.CoolSelNumTxtWidth, globalHeight), font=3, flags=RT_HALIGN_LEFT, text=selnumtxt))
						offset += 5 + self.CoolSelNumTxtWidth + 4

				movie_metaload = config.EMC.movie_metaload.value
				if not config.EMC.skin_able.value:

					# TODO: Progress.value for blue structure
					if not ext in extBlu and not bluiso:
						if config.EMC.movie_progress.value == "PB":
							append(MultiContentEntryProgress(pos=(offset, self.CoolBarHPos), size = (self.CoolBarSize.width(), self.CoolBarSize.height()), percent = progress, borderWidth = 1, foreColor = color, foreColorSelected=color, backColor = self.BackColor, backColorSelected = None))
							offset += self.CoolBarSize.width() + 10

						elif config.EMC.movie_progress.value == "P":
							append(MultiContentEntryText(pos=(offset, 0), size=(progressWidth, globalHeight), font=usedFont, flags=RT_HALIGN_CENTER, text="%d%%" % (progress), color = color, color_sel = colorhighlight, backcolor = self.BackColor, backcolor_sel = self.BackColorSel))
							offset += progressWidth + 5

					if config.EMC.movie_date_format.value:
						if config.EMC.movie_date_format.value == "%d.%m.%Y %H:%M":
							self.CoolDateWidth = 160
						elif config.EMC.movie_date_format.value == "%Y/%m/%d %H:%M":
							self.CoolDateWidth = 162
						else:
							self.CoolDateWidth = 110
						append(MultiContentEntryText(pos=(self.l.getItemSize().width() - self.CoolDateWidth, 0), size=(self.CoolDateWidth, globalHeight), font=usedDateFont, color = colordate, color_sel = colorhighlight, backcolor = self.BackColor, backcolor_sel = self.BackColorSel, flags=RT_HALIGN_CENTER, text=datetext))

					# Media files left side not skin_able
					if movie_metaload:
						if eventtitle != "":
							title = title + " - " + eventtitle

					# Picons only for .ts-files
					textX = offset
					textY = 0
					textSizeY = globalHeight
					if ext in extTS:
						if config.EMC.movie_picons.value:
							piconPos = config.EMC.movie_picons_pos.value
							if piconpath:
								picon = loadPNG(piconpath)
								piconH = self.l.getItemSize().height() - 6
								piconW = piconH * 2 - 5
								piconY = 2
								if piconPos == "nr":
									if config.EMC.movie_date_format.value != "":
										piconX = self.l.getItemSize().width() - self.CoolDateWidth - piconW - 5
										textSizeX = self.l.getItemSize().width() - textX - self.CoolDateWidth - piconW - 15
									else:
										piconX = self.l.getItemSize().width() - piconW - 5
										textSizeX = self.l.getItemSize().width() - textX - 15 - piconW
								else:
									if config.EMC.movie_date_format.value != "":
										piconX = offset
										textX += piconW + 5
										textSizeX = self.l.getItemSize().width() - textX - self.CoolDateWidth - 10
									else:
										piconX = offset
										textX += piconW + 5
										textSizeX = self.l.getItemSize().width() - textX - 5
								# Special way for vti-images, directly over "eListboxPythonMultiContent", they have no "flags=..", only "options=.."
								if newPiconRenderer or imgVti:
									append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, piconX, piconY, piconW, piconH, picon, None, None, BT_SCALE | BT_KEEP_ASPECT_RATIO))
								else:
									append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, piconX, piconY, piconW, piconH, picon, None, None))

								append(MultiContentEntryText(pos=(textX, textY), size=(textSizeX, textSizeY), font=usedFont, flags=RT_HALIGN_LEFT, text=title, color = colortitle, color_sel = colorhighlight, backcolor = self.BackColor, backcolor_sel = self.BackColorSel))
							else:
								if piconPos == "nr":
									if config.EMC.movie_date_format.value != "":
										textSizeX = self.l.getItemSize().width() - textX - self.CoolDateWidth - 10
									else:
										textSizeX = self.l.getItemSize().width() - textX - 5
								else:
									if config.EMC.movie_date_format.value != "":
										textSizeX = self.l.getItemSize().width() - textX - self.CoolDateWidth - 10
									else:
										textSizeX = self.l.getItemSize().width() - textX - 5
								append(MultiContentEntryText(pos=(textX, textY), size=(textSizeX, textSizeY), font=usedFont, flags=RT_HALIGN_LEFT, text=title, color = colortitle, color_sel = colorhighlight, backcolor = self.BackColor, backcolor_sel = self.BackColorSel))
						else:
							if config.EMC.movie_date_format.value != "":
								textSizeX = self.l.getItemSize().width() - textX - self.CoolDateWidth - 10
							else:
								textSizeX = self.l.getItemSize().width() - textX - 5
							append(MultiContentEntryText(pos=(textX, textY), size=(textSizeX, textSizeY), font=usedFont, flags=RT_HALIGN_LEFT, text=title, color = colortitle, color_sel = colorhighlight, backcolor = self.BackColor, backcolor_sel = self.BackColorSel))
					else:
						if config.EMC.movie_date_format.value != "":
							textSizeX = self.l.getItemSize().width() - textX - self.CoolDateWidth - 10
						else:
							textSizeX = self.l.getItemSize().width() - textX - 5
						append(MultiContentEntryText(pos=(textX, textY), size=(textSizeX, textSizeY), font=usedFont, flags=RT_HALIGN_LEFT, text=title, color = colortitle, color_sel = colorhighlight, backcolor = self.BackColor, backcolor_sel = self.BackColorSel))

				else:
					# Skin can overwrite show column date, progress and progressbar
					# Show Icon always depends on EMC config

					# Skin color overwrite handling
					if self.CoolTitleColor == 0:
						colortitle = self.TitleColor
					if self.CoolDateColor == 0:
						colordate = self.DateColor
					if self.CoolHighlightColor == 0:
						colorhighlight = self.FrontColorSel

					# If no date format is specified, the date column is switched off
					#print "EMC skinable date " + str(config.EMC.movie_date_format.value)
					if config.EMC.movie_date_format.value:
						CoolDatePos = self.CoolDatePos
					else:
						CoolDatePos = -1

					#If show movie progress is off, the progress columns are switched off
					#print "EMC skinable prog " + str(config.EMC.movie_progress.value)
					if config.EMC.movie_progress.value == "PB":
						CoolBarPos = self.CoolBarPos
					else:
						CoolBarPos = -1
					if config.EMC.movie_progress.value == "P":
						CoolProgressPos = self.CoolProgressPos
					else:
						CoolProgressPos = -1

					# TODO: Progress.value for blue structure
					if ext in extBlu or bluiso:
						CoolProgressPos = -1
						CoolBarPos = -1

					if CoolBarPos != -1:
						if config.EMC.movie_icons.value:
							append(MultiContentEntryProgress(pos=(CoolBarPos, self.CoolBarHPos -2), size = (self.CoolBarSizeSa.width(), self.CoolBarSizeSa.height()), percent = progress, borderWidth = 1, foreColor = color, foreColorSelected=color, backColor = self.BackColor, backColorSelected = None))
						else:
							if self.CoolBarPos < self.CoolMoviePos:
								iconsub = self.CoolIconSize.width()
							else:
								iconsub = 0
							append(MultiContentEntryProgress(pos=(CoolBarPos - iconsub, self.CoolBarHPos -2), size = (self.CoolBarSizeSa.width(), self.CoolBarSizeSa.height()), percent = progress, borderWidth = 1, foreColor = color, foreColorSelected=color, backColor = self.BackColor, backColorSelected = None))
					if CoolProgressPos != -1:
						if config.EMC.movie_icons.value:
							append(MultiContentEntryText(pos=(CoolProgressPos, self.CoolProgressHPos), size=(progressWidth, globalHeight), font=usedFont, flags=RT_HALIGN_LEFT, text="%d%%" % (progress), color = colortitle, color_sel = colorhighlight))
						else:
							if self.CoolProgressPos < self.CoolMoviePos:
								iconsub = self.CoolIconSize.width()
							else:
								iconsub = 0
							append(MultiContentEntryText(pos=(CoolProgressPos - iconsub, self.CoolProgressHPos), size=(progressWidth, globalHeight), font=usedFont, flags=RT_HALIGN_LEFT, text="%d%%" % (progress), color = colortitle, color_sel = colorhighlight))
					if CoolDatePos != -1:
						append(MultiContentEntryText(pos=(CoolDatePos, self.CoolDateHPos), size=(self.CoolDateWidth, globalHeight), font=usedDateFont, text=datetext, color = colordate, color_sel = colorhighlight, flags=RT_HALIGN_CENTER))

					# Media files left side
					if movie_metaload:
						if eventtitle != "":
							title = title + " - " + eventtitle

					# show picons only, if we have piconpath
					if config.EMC.movie_picons.value:
						if piconpath:
							CoolPiconPos = self.CoolPiconPos
							CoolMoviePiconPos = self.CoolMoviePiconPos
						else:
							CoolPiconPos = -1
							CoolMoviePiconPos = -1
					else:
						CoolPiconPos = -1
						CoolMoviePiconPos = -1

					progressval = config.EMC.movie_progress.value
					if ext in extTS:
						if CoolPiconPos != -1 and CoolMoviePiconPos != -1:
							picon = loadPNG(piconpath)
							if self.CoolPiconHeight == -1:
								self.CoolPiconHeight = self.l.getItemSize().height() - 6
							if self.CoolPiconHPos == -1:
								self.CoolPiconHPos = 2
							if self.CoolPiconWidth == -1:
								self.CoolPiconWidth = 110
							# Special way for vti-images, directly over "eListboxPythonMultiContent", they have no "flags=..", only "options=.."
							if newPiconRenderer or imgVti:
								progresssub = 0
								numsub = 0
								if config.EMC.movie_icons.value:
									if progressval == "MC" or progressval == "":
										if self.CoolBarPos < CoolPiconPos:
											progresssub = self.CoolBarSizeSa.width() + 5
								else:
									if selnumtxt is None:
										numsub = self.CoolIconSize.width()
									if progressval == "MC" or progressval == "":
										if self.CoolBarPos < CoolPiconPos:
											progresssub = self.CoolBarSizeSa.width()
								append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, CoolPiconPos - numsub - progresssub, self.CoolPiconHPos, self.CoolPiconWidth, self.CoolPiconHeight, picon, None, None, BT_SCALE | BT_KEEP_ASPECT_RATIO))
							else:
								progresssub = 0
								numsub = 0
								if config.EMC.movie_icons.value:
									if progressval == "MC" or progressval == "":
										if self.CoolBarPos < CoolPiconPos:
											progresssub = self.CoolBarSizeSa.width() + 5
								else:
									if selnumtxt is None:
										numsub = self.CoolIconSize.width()
									if progressval == "MC" or progressval == "":
										if self.CoolBarPos < CoolPiconPos:
											progresssub = self.CoolBarSizeSa.width()
								append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, CoolPiconPos - numsub - progresssub, self.CoolPiconHPos, self.CoolPiconWidth, self.CoolPiconHeight, picon, None, None))

							progresssub = 0
							progressadd = 0
							numsub = 0
							if config.EMC.movie_icons.value:
								if progressval == "MC" or progressval == "":
									progressadd = self.CoolBarSizeSa.width()
									if self.CoolBarPos < self.CoolMoviePiconPos:
										progresssub = self.CoolBarSizeSa.width() + 5
							else:
								if selnumtxt is None:
									numsub = self.CoolIconSize.width()
								if progressval == "MC" or progressval == "":
									progressadd = self.CoolBarSizeSa.width()
									if self.CoolBarPos < self.CoolMoviePiconPos:
										progresssub = self.CoolBarSizeSa.width()
							append(MultiContentEntryText(pos=(self.CoolMoviePiconPos - numsub - progresssub, 0), size=(self.CoolMoviePiconSize + numsub + progressadd, globalHeight), font=usedFont, flags=RT_HALIGN_LEFT, text=title, color = colortitle, color_sel = colorhighlight))
						else:
							progresssub = 0
							progressadd = 0
							numsub = 0
							if config.EMC.movie_icons.value:
								if progressval == "MC" or progressval == "":
									progressadd = self.CoolBarSizeSa.width()
									if self.CoolBarPos < self.CoolMoviePos:
										progresssub = self.CoolBarSizeSa.width() + 10
							else:
								if selnumtxt is None:
									numsub = self.CoolIconSize.width()
								if progressval == "MC" or progressval == "":
									progressadd = self.CoolBarSizeSa.width()
									if self.CoolBarPos <= self.CoolMoviePos:
										progresssub = self.CoolBarSizeSa.width()
							append(MultiContentEntryText(pos=(self.CoolMoviePos - numsub - progresssub, 0), size=(self.CoolMovieSize + numsub + progressadd, globalHeight), font=usedFont, flags=RT_HALIGN_LEFT, text=title, color = colortitle, color_sel = colorhighlight))
					else:
						progresssub = 0
						progressadd = 0
						numsub = 0
						if config.EMC.movie_icons.value:
							if progressval == "MC" or progressval == "":
								progressadd = self.CoolBarSizeSa.width()
								if self.CoolBarPos < self.CoolMoviePos:
									progresssub = self.CoolBarSizeSa.width() + 10
						else:
							if selnumtxt is None:
								numsub = self.CoolIconSize.width()
							if progressval == "MC" or progressval == "":
								progressadd = self.CoolBarSizeSa.width()
								if self.CoolBarPos < self.CoolMoviePos:
									progresssub = self.CoolBarSizeSa.width()
						append(MultiContentEntryText(pos=(self.CoolMoviePos - numsub - progresssub, 0), size=(self.CoolMovieSize + numsub + progressadd, globalHeight), font=usedFont, flags=RT_HALIGN_LEFT, text=title, color = colortitle, color_sel = colorhighlight))

			else:
				# Directory and vlc directories

				#TODO Is there any way to combine it for both files and directories?
				#TODO Color not used yet for folders color = self.DefaultColor
				#TODO config.EMC.movie_icons.value not used here // try: line ~1827
				#TODO Skin config.EMC.skin_able.value not used here
				#TODO config.EMC.movie_date_format.value not used here

				if ext == cmtVLC:
					pixmap = self.pic_vlc
					datepic = None
					if config.EMC.directories_info.value == "D":
						datetext = _("VLC")

				elif ext == vlcSrv:
					pixmap = self.pic_vlc
					datepic = None
					if config.EMC.directories_info.value == "D":
						datetext = _("VLC-Server")

				elif ext == vlcDir:
					pixmap = self.pic_vlc_dir
					datepic = None
					if config.EMC.directories_info.value == "D":
						datetext = _("VLC-Dir")

				elif ext == cmtLRec:
					pixmap = self.pic_latest
					datepic = None
					if config.EMC.directories_info.value == "D":
						datetext = _("Latest")

				elif ext == cmtUp:
					pixmap = self.pic_back
					datepic = None
					if config.EMC.directories_info.value == "D":
						datetext = _("Up")

				elif ext == cmtBME2:
					pixmap = self.pic_e2bookmark
					datepic = None
					if config.EMC.directories_info.value == "D":
						datetext = _("Bookmark")

				elif ext == cmtBMEMC:
					pixmap = self.pic_emcbookmark
					datepic = None
					if config.EMC.directories_info.value == "D":
						datetext = _("Bookmark")

				elif ext == cmtTrash:
					if config.EMC.movie_trashcan_enable.value and config.EMC.movie_trashcan_info.value:
						#TODO Improve performance
						count = 0
						if config.EMC.movie_trashcan_info.value == "C":
							count, size = dirInfo(path)
							datetext = " ( %d ) " % (count)
						elif config.EMC.movie_trashcan_info.value == "CS":
							count, size = dirInfo(path, bsize=True)
							datetext = " (%d / %.0f GB) " % (count, size)
						elif config.EMC.movie_trashcan_info.value == "S":
							count, size = dirInfo(path, bsize=True)
							if size >= 100:
								datetext = " ( %.2f TB ) " % (size/1024.0)
							else:
								datetext = " ( %.2f GB ) " % (size)
						else:
							# Should never happen
							datetext = _("Trashcan")
						if count:
							# Trashcan contains garbage
							pixmap = self.pic_trashcan_full
						else:
							# Trashcan is empty
							pixmap = self.pic_trashcan
						self.CoolCSWidth = 110
					else:
						pixmap = self.pic_trashcan
						if config.EMC.directories_info.value == "D":
							datetext = _("Trashcan")

				elif ext == cmtDir:
					if not isExtHDDSleeping:
						if os.path.isfile(path + "/dir.lock"):
							pixmap = self.pic_directory_locked
						else:
							pixmap = self.pic_directory
					else:
						pixmap = self.pic_directory

					if config.EMC.directories_ontop.value and title not in self.topdirlist:
						pixmap = self.pic_col_dir

					# Directory and symlink-direcory info.value
					getValues = movieFileCache.getCountSizeFromCache(path)
					if config.EMC.directories_info.value:
						if config.EMC.directories_info.value == "C":
							count = 0
							if getValues is not None:
								count, size = getValues
								if self.startWorker:
									self.addCountsizeworker(path)
								datetext = " ( %d ) " % (count)
							else:
								self.addCountsizeworker(path)
								datetext = ""
								datepic = self.pic_directory_search
						elif config.EMC.directories_info.value == "CS":
							count, size = 0, 0
							if getValues is not None:
								count, size = getValues
								if self.startWorker:
									self.addCountsizeworker(path)
								if size >= 1000:
									size /= 1024.0
									datetext = " (%d / %.0f TB) " % (count, size)
								else:
									datetext = " (%d / %.0f GB) " % (count, size)
								# TODO: make this easier, but hold it on the right side
								self.CoolCSWidth = 110
								if size or count >=99:
									if size >= 99 and count <=99:
										self.CoolCSWidth = 125
									elif size <= 99 and count >= 99:
										if count >= 999:
											if size <= 10:
												self.CoolCSWidth = 135
											else:
												self.CoolCSWidth = 145
										elif count >= 9999:
											if size <= 10:
												self.CoolCSWidth = 140
											else:
												self.CoolCSWidth = 160
										else:
											self.CoolCSWidth = 125
									elif size >= 99 and count >= 99:
										if count >= 999:
											self.CoolCSWidth = 145
										elif count >= 9999:
											self.CoolCSWidth = 160
										else:
											self.CoolCSWidth = 140
							else:
								self.addCountsizeworker(path)
								datetext = ""
								datepic = self.pic_directory_search
						elif config.EMC.directories_info.value == "S":
							size = 0
							if getValues is not None:
								count, size = getValues
								if self.startWorker:
									self.addCountsizeworker(path)
								if size >= 100:
									datetext = " ( %.2f TB ) " % (size/1024.0)
								else:
									datetext = " ( %.2f GB ) " % (size)
							else:
								self.addCountsizeworker(path)
								datetext = ""
								datepic = self.pic_directory_search
						elif config.EMC.directories_info.value == "D":
							if config.EMC.directories_size_skin.value:
								if getValues is not None:
									if self.startWorker:
										self.addCountsizeworker(path)
								else:
									self.addCountsizeworker(path)
							datetext = _("Directory")
							if isLink:
								datetext = _("Link")
							if config.EMC.directories_ontop.value and title not in self.topdirlist:
								datetext = _("Collection")
						else:
							# Should never happen
							pixmap = self.pic_directory
							datetext = _("Directory")

					else: # config.EMC.directories_info.value == ""
						if config.EMC.directories_size_skin.value:
							if getValues is not None:
								if self.startWorker:
									self.addCountsizeworker(path)
							else:
								self.addCountsizeworker(path)
				else:
					# Should never happen
					pixmap = self.pic_directory
					datetext = _("UNKNOWN")

				# Is there any way to combine it for both files and directories?
				# it is, but not with this hole code
				if config.EMC.movie_icons.value:
					# hide symlink arrow
					if isLink and config.EMC.link_icons.value:
						dirPic = self.pic_link
					else:
						dirPic = pixmap
					if not config.EMC.skin_able.value:
						append(MultiContentEntryPixmapAlphaBlend(pos=(5,2), size=(24,24), png=dirPic, **{}))
					else:
						append(MultiContentEntryPixmapAlphaBlend(pos=(self.CoolIconPos,self.CoolIconHPos), size=(self.CoolIconSize.width(),self.CoolIconSize.height()), png=dirPic, **{}))

				# Directory left side
				if not config.EMC.skin_able.value:
					dirTitleSize = (self.CoolFolderSize, globalHeight)   # this is not realy mutable ?!
					if config.EMC.movie_icons.value:
						dirTitlePos = (35, 2)
					else:
						dirTitlePos = (5, 2)
				else:
					if config.EMC.movie_icons.value:
						dirTitlePos = (self.CoolIconPos + self.CoolIconSize.width() + 5, self.CoolIconHPos)
						dirTitleSize = (self.CoolFolderSize, globalHeight)
					else:
						dirTitlePos = (5, self.CoolIconHPos)
						dirTitleSize = (self.CoolFolderSize + self.CoolIconSize.width(), globalHeight)
				append(MultiContentEntryText(pos=dirTitlePos, size=dirTitleSize, font=usedFont, flags=RT_HALIGN_LEFT, text=title))

				# TODO: Directory left side - skin able
				#append(MultiContentEntryText(pos=(self.CoolMoviePos, 0), size=(self.CoolFolderSize, globalHeight), font=usedFont, flags=RT_HALIGN_LEFT, text=title))

				# Directory right side
				val = config.EMC.directories_info.value
				if val == "C" or val == "CS" or val == "S":
					if self.fullhd:
						if not config.EMC.skin_able.value:
							CoolCSWidth = int(self.CoolCSWidth * 1.5)
						else:
							if self.CoolDirInfoWidth != -1:
								CoolCSWidth = self.CoolDirInfoWidth
							else:
								CoolCSWidth = int(self.CoolCSWidth * 1.5)
					else:
						if not config.EMC.skin_able.value:
							CoolCSWidth = self.CoolCSWidth
						else:
							if self.CoolDirInfoWidth != -1:
								CoolCSWidth = self.CoolDirInfoWidth
							else:
								CoolCSWidth = self.CoolCSWidth
					if config.EMC.count_size_position.value == "1":
						halign = RT_HALIGN_RIGHT
					else:
						halign = RT_HALIGN_CENTER
					if datetext != "":
						append(MultiContentEntryText(pos=(self.l.getItemSize().width() - CoolCSWidth - 5, self.CoolMovieHPos), size=(CoolCSWidth, globalHeight), font=usedDateFont, flags=halign, text=datetext))
					else:
						useIcon = config.EMC.count_size_default_icon.value
						if useIcon:
							if datepic is not None:
								append(MultiContentEntryPixmapAlphaBlend(pos=(self.l.getItemSize().width() - self.CoolDateWidth /2, self.CoolMovieHPos), size=(CoolCSWidth, globalHeight), png=self.pic_directory_search, **{}))
						else:
							if datepic is not None:
								count = config.EMC.count_default_text.value
								countsize = config.EMC.count_size_default_text.value
								size = config.EMC.size_default_text.value
								if val == "C":
									datetext = count
								elif val == "CS":
									datetext = countsize
								elif val == "S":
									datetext = size
							append(MultiContentEntryText(pos=(self.l.getItemSize().width() - self.CoolDateWidth, self.CoolMovieHPos), size=(self.CoolDateWidth, globalHeight), font=usedDateFont, flags=halign, text=datetext))
				else:
					append(MultiContentEntryText(pos=(self.l.getItemSize().width() - self.CoolDateWidth, self.CoolMovieHPos), size=(self.CoolDateWidth, globalHeight), font=usedDateFont, flags=RT_HALIGN_CENTER, text=datetext))
			del append
			return res
		except Exception, e:
			emcDebugOut("[EMCMS] build exception:\n" + str(e))

	def addCountsizeworker(self,path):
		if config.EMC.dir_info_usenoscan.value:
			if self.checkNoScanPath(self.currentPath): #always scan sub-dirs of active no-scan dir
				countsizeworker.add(path)
			elif not self.checkNoScanPath(path):
				countsizeworker.add(path)
		else:
			countsizeworker.add(path)

	def getCurrent(self):
		l = self.l.getCurrentSelection()
		return l and l[0]

	def getCurrentIndex(self):
		return self.instance.getCurrentIndex()

	def getCurrentEvent(self):
		l = self.l.getCurrentSelection()
		if l and l[0]:
			info = self.serviceHandler.info(l[0])
			return info and info.getEvent(l[0])

	def getCurrentE2Event(self):
		l = self.l.getCurrentSelection()
		if l and l[0]:
			service = l[0]
			esc = eServiceCenter.getInstance()
			info = esc and esc.info(service)
			return info and info.getEvent(l[0])

	GUI_WIDGET = eListbox

	def postWidgetCreate(self, instance):
		instance.setWrapAround(True)
		instance.setContent(self.l)
		try:
			self.selectionChanged_conn = instance.selectionChanged.connect(self.selectionChanged)
		except:
			instance.selectionChanged.get().append(self.selectionChanged)

	def preWidgetRemove(self, instance):
		instance.setContent(None)
		self.selectionChanged_conn = None

	def removeService(self, service):
		if service:
			list = self.removeServiceInternal(service)
			self.l.setList( list )

	def removeServiceOfType(self, service, type):
		if service:
			list = self.removeServiceOfTypeInternal(service, type)
			self.l.setList( list )

	def __len__(self):
		return len(self.getList())

	def makeSelectionList(self, currentIfEmpty=True):
		selList = []
		if self.currentSelectionCount == 0 and currentIfEmpty:
			# if no selections made, select the current cursor position
			single = self.l.getCurrentSelection()
			if single:
				selList.append(single[0])
		else:
			selList = self.selectionList
		return selList

	def unselectService(self, service):
		if service:
			if self.selectionList:
				if service in self.selectionList:
					# Service is in selection - unselect it
					self.toggleSelection(service)
				else:
					self.invalidateService(service)
			else:
				self.invalidateService(service)

	def invalidateCurrent(self):
		self.l.invalidateEntry(self.getCurrentIndex())

	def invalidateService(self, service):
		idx = self.getIndexOfService(service)
		if idx < 0: return
		self.l.invalidateEntry( idx ) # force redraw of the item

	def refreshList(self, worker=False):
		# Just invalidate the whole list to force rebuild the entries
		# Updates the progress of all entries
		#IDEA Extend the list and mark the recordings
		# so we don't have to go through the whole list
		#TEST Performance for recordings only updating
		#     Separate function for updating recordings only
		#     Check for recording only if date is within the last day
		#for entry in self.list:
		#	if self.recControl.isRecording(entry[4]):
		#		self.invalidateService(entry[0])
		self.startWorker = worker
		self.l.invalidate()

	def reload(self, currentPath, simulate=False, recursive=False):
		list = self.reloadInternal(currentPath, simulate, recursive)
		self.l.setList( list )
		return list

	def moveUp(self):
		self.startWorker = False
		self.instance.moveSelection(self.instance.moveUp)

	def moveDown(self):
		self.startWorker = False
		self.instance.moveSelection(self.instance.moveDown)

	def pageUp(self):
		self.startWorker = False
		self.instance.moveSelection(self.instance.pageUp)

	def pageDown(self):
		self.startWorker = False
		self.instance.moveSelection(self.instance.pageDown)

	def moveTop(self):
		self.startWorker = False
		self.instance.moveSelection(self.instance.moveTop)

	def moveEnd(self):
		self.startWorker = False
		self.instance.moveSelection(self.instance.moveEnd)

	def moveToIndex(self, index):
		self.instance.moveSelectionTo(index)

	def moveToService(self, service):
		if service:
			index = self.getIndexOfService(service)
			if index:
				self.instance.moveSelectionTo(index)

	def currentSelIsPlayable(self):
		try:	return self.getTypeOfIndex(self.getCurrentIndex()) in extMedia
		except:	return False

	def currentSelIsDirectory(self):
		try:	return self.getTypeOfIndex(self.getCurrentIndex()) == cmtDir
		except:	return False

	def currentSelIsVirtual(self):
		try:	return self.getTypeOfIndex(self.getCurrentIndex()) in virAll
		except:	return False

	def currentSelIsE2Bookmark(self):
		try:	return self.getTypeOfIndex(self.getCurrentIndex()) == cmtBME2
		except:	return False

	def currentSelIsEMCBookmark(self):
		try:	return self.getTypeOfIndex(self.getCurrentIndex()) == cmtBMEMC
		except:	return False

	def indexIsDirectory(self, index):
		try:	return self.getTypeOfIndex(index) == cmtDir
		except:	return False

	def indexIsPlayable(self, index):
		try:	return self.getTypeOfIndex(index) in extMedia
		except:	return False

	def getCurrentSelDir(self):
		self.startWorker = True
		try: return self.getListEntry(self.getCurrentIndex())[4]
		except: return False

	def getCurrentSelName(self):
		try: return self.getListEntry(self.getCurrentIndex())[3]
		except: return "none"

	def highlightService(self, enable, mode, service):
		if enable:
			self.unselectService(service)
			self.highlightServiceInternal(enable, mode, service)
		elif service:
			self.highlightServiceInternal(enable, mode, service)

	def toggleSelection(self, service=None, index=-1, overrideNum=None):
		entry = None
		if service is None:
			if index == -1:
				if self.l.getCurrentSelection() is None: return
				index = self.getCurrentIndex()
			entry = self.list[index]
		else:
			index = 0
			for e in self.list:
				if e[0] == service:
					entry = e
					break
				index += 1
		if entry is None: return

		# We have entry, index, overrideNum
		if not self.indexIsPlayable(index): return
		self.toggleSelectionInternal(entry, index, overrideNum, self.l.invalidateEntry)

	def toggleSortingMode(self):
		from Plugins.Extensions.EnhancedMovieCenter.plugin import sort_modes
		#sorts = list( set( [sort for sort, desc in sort_choices] ) )
		sorts = [ v[1] for v in sort_modes.values() ]
		#print sorts
		# Toggle the mode
		mode, order = self.actualSort
		# Get all sorting modes as a list of unique ids
		modes = list( set( [m for m, o in sorts] ) )
		#print modes
		if mode in modes:
			# Get next sorting mode
			idx = modes.index(mode)
			mode = modes[ (idx+1) % len(modes) ]
		else:
			# Fallback
			mode = modes[ 0 ]
		self.setSortingMode(mode, order)

	def toggleSortingOrder(self):
		mode, order = self.actualSort
		self.setSortingMode(mode, not order)

	def setSortingMode(self, mode=None, order=None):
		list = self.setSortingModeInternal(mode, order)
		self.l.setList( list )

	def toggleProgress(self, service):
		if service is None:
			first = False
			forceProgress = -1
			current = self.getCurrent()
			if current is not None:
				# Force copy of selectedlist
				selectedlist = self.makeSelectionList()[:]
				if len(selectedlist)>1:
					first = True
				for service in selectedlist:
					progress = toggleProgressService(service, False, forceProgress, first)
					self.invalidateService(service)
					#DelayedFunction(1000, self.invalidateService, service)
					first = False
					#if not preparePlayback:
					forceProgress = progress
		else:
			toggleProgressService(service, preparePlayback)
			self.invalidateService(service)
			#DelayedFunction(1000, self.invalidateService, service)

	def getNextSelectedService(self, current, selectedlist=None):
		curSerRef = None
		if current is None:
			curSerRef = None
		elif not self.list:
			# Selectedlist is empty
			curSerRef = None
		elif selectedlist is None:
			# Selectedlist is empty
			curSerRef = current
		elif current is not None and current not in selectedlist:
			# Current is not within the selectedlist
			curSerRef = current
		else:
			# Current is within the selectedlist
			last_idx = len(self.list) - 1
			len_sel = len(selectedlist)
			first_sel_idx = last_idx
			last_sel_idx = 0

			# Get first and last selected item indexes
			for sel in selectedlist:
				idx = self.getIndexOfService(sel)
				if idx < 0: idx = 0
				if idx < first_sel_idx: first_sel_idx = idx
				if idx > last_sel_idx:  last_sel_idx = idx

			# Calculate previous and next item indexes
			prev_idx = first_sel_idx - 1
			next_idx = last_sel_idx + 1
			len_fitola = last_sel_idx - first_sel_idx + 1

			# Check if there is a not selected item between the first and last selected item
			if len_fitola > len_sel:
				for entry in self.list[first_sel_idx:last_sel_idx]:
					if entry[0] not in selectedlist:
						# Return first entry which is not in selectedlist
						curSerRef = entry[0]
						break
			# Check if next calculated item index is within the movie list
			elif next_idx <= last_idx:
				# Select item behind selectedlist
				curSerRef = self.getServiceOfIndex(next_idx)
			# Check if previous calculated item index is within the movie list
			elif prev_idx >= 0:
				# Select item before selectedlist
				curSerRef = self.getServiceOfIndex(prev_idx)
			else:
				# The whole list must be selected
				# First and last item is selected
				# Recheck and find first not selected item
				for entry in self.list:
					if entry[0] not in selectedlist:
						# Return first entry which is not in selectedlist
						curSerRef = entry[0]
						break
		return curSerRef