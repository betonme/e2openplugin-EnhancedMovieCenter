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

from Components.config import *
from Components.GUIComponent import GUIComponent
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaTest, MultiContentEntryProgress
from Tools.LoadPixmap import LoadPixmap
from Tools.Directories import fileExists

from skin import parseColor, parseFont, parseSize
from enigma import eListboxPythonMultiContent, eListbox, gFont, RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_HALIGN_CENTER, eServiceReference, eServiceCenter

from RecordingsControl import RecordingsControl
from DelayedFunction import DelayedFunction
from EMCTasker import emcDebugOut
from EnhancedMovieCenter import _
from VlcPluginInterface import VlcPluginInterfaceList
from operator import itemgetter
from CutListSupport import CutList
from MetaSupport import MetaList


# Media types
audioExt = frozenset([".ac3", ".dts", ".flac", ".m4a", ".mp2", ".mp3", ".ogg", ".wav"])
videoExt = frozenset([".ts", ".avi", ".divx", ".f4v", ".flv", ".img", ".iso", ".m2ts", ".m4v", ".mkv", ".mov", ".mp4", ".mpeg", ".mpg", ".mts", ".vob"])
mediaExt = audioExt | videoExt

# Additional file types
tsExt    = frozenset([".ts"])
m2tsExt  = frozenset([".m2ts"])
dvdExt   = frozenset([".iso", ".img", ".ifo"])

# Player types
playerDVB  = tsExt																											# ServiceDVB
playerM2TS = m2tsExt																										# ServiceM2TS
playerDVD  = dvdExt																											# ServiceDVD
playerMP3  = audioExt | videoExt - playerDVB - playerM2TS - playerDVD		# ServiceMP3 GStreamer

serviceIdDVB = eServiceReference.idDVB	# eServiceFactoryDVB::id   enum { id = 0x1 }; 
serviceIdDVD = 4369 										# eServiceFactoryDVD::id   enum { id = 0x1111 };
serviceIdMP3 = 4097											# eServiceFactoryM2TS::id  enum { id = 0x1001 };
# For later purpose
serviceIdM2TS = 3 											# eServiceFactoryM2TS::id  enum { id = 0x3 };
#TODO
#serviceIdXINE = 4112										# eServiceFactoryXine::id  enum { id = 0x1010 };

serviceIdsCuts = frozenset([serviceIdDVB, serviceIdDVD])


class MovieCenter(GUIComponent, VlcPluginInterfaceList):
	instance = None
	
	def __init__(self):
		MovieCenter.instance = self
		self.list = []
		GUIComponent.__init__(self)
		self.loadPath = config.EMC.movie_homepath.value + "/"
		self.serviceHandler = eServiceCenter.getInstance()
		
		self.CoolFont = parseFont("Regular;20", ((1,1),(1,1)))
		self.CoolSelectFont = parseFont("Regular;20", ((1,1),(1,1)))
		self.CoolDateFont = parseFont("Regular;20", ((1,1),(1,1)))
				
		self.CoolMoviePos = 100
		self.CoolMovieSize = 490
		self.CoolFolderSize = 550
		self.CoolDatePos = -1
		self.CoolDateWidth = 110
		self.CoolDateColor = 0
		self.CoolProgressPos = -1
		self.CoolBarPos = -1
		self.CoolBarHPos = 8
		
		self.CoolBarSize = parseSize("55,10", ((1,1),(1,1)))
		self.CoolBarSizeSa = parseSize("55,10", ((1,1),(1,1)))
		
		self.DateColor = 0xFFFFFF
		self.DefaultColor = 0xFFFFFF
		self.BackColor = None
		self.BackColorSel = 0x000000
		self.UnwatchedColor = 0xFFFFFF
		self.WatchingColor = 0x3486F4
		self.FinishedColor = 0x46D93A
		self.RecordingColor = 0x9F1313

		self.l = eListboxPythonMultiContent()
		self.l.setFont(0, gFont("Regular", 22))
		self.l.setFont(1, self.CoolFont)
		self.l.setFont(2, gFont("Regular", 20))
		self.l.setFont(3, self.CoolSelectFont)
		self.l.setFont(4, self.CoolDateFont)
		self.l.setBuildFunc(self.buildMovieCenterEntry)
		self.l.setItemHeight(28)
		self.currentSelectionCount = 0		
				
		self.alphaSort = config.EMC.CoolStartAZ.value
		self.newRecordings = False
		self.selectionList = None
		self.recControl = RecordingsControl(self.recStateChange)
		self.highlightsMov = []
		self.highlightsDel = []
		
		self.backPic         = LoadPixmap(cached=True, path='/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/back.png')
		self.dirPic          = LoadPixmap(cached=True, path='/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/dir.png')
		self.movie_default   = LoadPixmap(cached=True, path='/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/movie_default.png')
		self.movie_unwatched = LoadPixmap(cached=True, path='/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/movie_unwatched.png')
		self.movie_watching  = LoadPixmap(cached=True, path='/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/movie_watching.png')
		self.movie_finished  = LoadPixmap(cached=True, path='/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/movie_finished.png')
		self.movie_rec       = LoadPixmap(cached=True, path='/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/movie_rec.png')
		self.movie_recrem    = LoadPixmap(cached=True, path='/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/movie_recrem.png')
		self.mp3Pic          = LoadPixmap(cached=True, path='/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/music.png')
		self.dvd_default     = LoadPixmap(cached=True, path='/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/dvd_default.png')
		self.dvd_watching    = LoadPixmap(cached=True, path='/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/dvd_watching.png')
		self.dvd_finished    = LoadPixmap(cached=True, path='/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/dvd_finished.png')
		self.vlcPic          = LoadPixmap(cached=True, path='/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/vlc.png')
		self.vlcdPic         = LoadPixmap(cached=True, path='/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/vlcdir.png')
		self.link            = LoadPixmap(cached=True, path='/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/link.png')
		self.virtualPic      = LoadPixmap(cached=True, path='/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/virtual.png')
		self.onSelectionChanged = []

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
				elif attrib == "CoolMovieSize":
					self.CoolMovieSize = int(value)
				elif attrib == "CoolFolderSize":
					self.CoolFolderSize = int(value)
				elif attrib == "CoolDatePos":
					self.CoolDatePos = int(value)
				elif attrib == "CoolDateWidth":
					self.CoolDateWidth = int(value)
				elif attrib == "CoolDateColor":
					self.CoolDateColor = int(value)
				elif attrib == "CoolTimePos":
					pass
				
				elif attrib == "CoolProgressPos":
					self.CoolProgressPos = int(value)
				elif attrib == "CoolBarPos":
					self.CoolBarPos = int(value)
				elif attrib == "CoolBarHPos":
					self.CoolBarHPos = int(value)
				elif attrib == "CoolBarSize":
					self.CoolBarSize = parseSize(value, ((1,1),(1,1)))
				elif attrib == "CoolBarSizeSa":
					self.CoolBarSizeSa = parseSize(value, ((1,1),(1,1)))
				elif attrib == "DefaultColor":
					self.DefaultColor = parseColor(value).argb()
				elif attrib == "BackColor":
					self.BackColor = parseColor(value).argb()
				elif attrib == "BackColorSel":
					self.BackColorSel = parseColor(value).argb()
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

	def setAlphaSort(self, trueOrFalse):
		self.alphaSort = trueOrFalse

	def getAlphaSort(self):
		return self.alphaSort

	def recStateChange(self, recList):
		try:
			if self.loadPath:
				DelayedFunction(3000, self.reload, self.loadPath)
		except Exception, e:
			emcDebugOut("[MC] recStateChange exception:\n" + str(e))

	def getFileInfo(self, ext, progress):
		pixmap = None
		color = None
		
		# Progress State
		movieUnwatched = config.EMC.movie_mark.value and	progress < int(config.EMC.movie_watching_percent.value)
		movieWatching  = config.EMC.movie_mark.value and	progress >= int(config.EMC.movie_watching_percent.value) and progress < int(config.EMC.movie_finished_percent.value)
		movieFinished  = config.EMC.movie_mark.value and	progress >= int(config.EMC.movie_finished_percent.value)
		
		# Color
		if movieUnwatched:
			color = self.UnwatchedColor
		elif movieWatching:
			color = self.WatchingColor
		elif movieFinished:
			color = self.FinishedColor
		else:
			color = self.DefaultColor
		
		# Icon
		global audioExt, dvdExt, videoExt
		# audio
		if ext in audioExt:
			pixmap = self.mp3Pic
		# dvd iso or structure
		elif ext in dvdExt: # or ext == "":  #Workaround for DVD folder
			if movieWatching:
				pixmap = self.dvd_watching
			elif movieFinished:
				pixmap = self.dvd_finished
			else:
				pixmap = self.dvd_default
		# video
		elif ext in videoExt:
			if movieUnwatched:
				pixmap = self.movie_unwatched
			elif movieWatching:
				pixmap = self.movie_watching
			elif movieFinished:
				pixmap = self.movie_finished
			else:
				pixmap = self.movie_default
		# all others
		else:
			pixmap = self.movie_default

		return pixmap, color

	def getProgress(self, service, len=0, last=0, forceRecalc=False, cuts=None):
		# All calculations are done in seconds
		try:
			cuts = None
			progress = 0
			updlen = len
			if last <= 0:
				# Get last position from cut file
				if cuts is None:
					cuts = CutList( service )
				last = cuts.getCutListLast()
			# Check for valid position
			if last > 0 or forceRecalc:
				# Valid position
				# Recalc the movie length to calculate the progress status
				if len <= 0: 
					if service:
						len = self.getLengthFromServiceHandler(service)
					#emcDebugOut("[MC] Service len:" + str(len))
					if len <= 0: 
						if cuts is None:
							cuts = CutList( service )
						len = cuts.getCutListLength()
						#emcDebugOut("[MC] Cuts length:" + str(len))
						if len <= 0: 
							# Set default file len if is not calculateable
							# 90 minutes = 90 * 60
							len = 5400
							# We only update the entry if we do not use the default value
							updlen = 0
							#emcDebugOut("[MC] getProgress No length: " + str(service.getPath()))
						else:
							updlen = len
					else:
						updlen = len
					if updlen:
						# Update entry in list... so next time we don't need to recalc
						idx = self.getIndexOfService(service)
						if idx >= 0:
							x = self.list[idx]
							self.list[idx] = (x[0], x[1], x[2], x[3], x[4], x[5], updlen, x[7])
				if len:
					# Adjust the watched movie length (99% of movie length) 
					# else we will never see the 100%
					adjlength = len / 100.0 * 98.0
					# Calculate progress and round up
					progress = int( math.ceil ( float(last) / float(adjlength) * 100.0 ) )
					# Normalize progress
					if progress < 0: progress = 0
					elif progress > 100: progress = 100
				else:
					# This should never happen, we always have our default length
					#emcDebugOut("[MC] getProgress(): Last without any length")
					progress = 100
			else:
				# No position implies progress is zero
				progress = 0
			return progress, len
		except Exception, e:
			emcDebugOut("[MC] getProgress() Exception: " + str(e))
			return 0, 0

	def buildMovieCenterEntry(self, service, sortkey, datesort, moviestring, filename, selnum, len, ext):
		try:
			path = self.loadPath + filename
			isLink = os.path.islink(path)
			globalHeight = 40
			usedFont = 0
			if config.EMC.skin_able.value:
				usedFont = 1
			
			# Directory and vlc entries
			if datesort is None:
				res = [ None ]
				if sortkey=="VLCd" or filename=="VLC servers":
					pmap = self.vlcdPic
					CoolPath=_("< VLC >")
				elif filename=="Latest Recordings":
					pmap = self.virtualPic
					CoolPath=_("< Latest >")
				else:
					pmap = self.dirPic
					CoolPath=_("Directory")
				if filename=="..": 
					pmap = self.backPic
				res.append(MultiContentEntryPixmapAlphaTest(pos=(5,2), size=(24,24), png=pmap, **{}))
				if isLink:
					res.append(MultiContentEntryPixmapAlphaTest(pos=(7,13), size=(9,10), png=self.link, **{}))
					CoolPath=_("< Link >")
				# Directory left side
				res.append(MultiContentEntryText(pos=(30, 0), size=(self.CoolFolderSize, globalHeight), font=usedFont, flags=RT_HALIGN_LEFT, text=filename))
				# Directory right side
				res.append(MultiContentEntryText(pos=(self.l.getItemSize().width() - self.CoolDateWidth, 0), size=(self.CoolDateWidth, globalHeight), font=2, flags=RT_HALIGN_CENTER, text=CoolPath))
				return res
			
			# File entries
			progress, len = self.getProgress(service, len)
			pixmap, color = self.getFileInfo(ext, progress)

			date = ""
			if datesort == "VLCs":
				date, pixmap = "VLC", self.vlcPic
			else:
				date = datesort[6:8] + "." + datesort[4:6] + "." + datesort[0:4]
				
			selnumtxt = None
			if selnum == 9999: selnumtxt = "-->"
			elif selnum == 9998: selnumtxt = "X"
			elif selnum > 0: selnumtxt = "%02d" % selnum
			if service in self.highlightsMov: selnumtxt = "-->"
			elif service in self.highlightsDel: selnumtxt = "X"
				
			if self.recControl.isRecording(path):
				date, pixmap, color = "-- REC --", self.movie_rec, self.RecordingColor
			elif self.recControl.isRemoteRecording(path):
				date, pixmap, color = "-- rec --", self.movie_recrem, self.RecordingColor
			elif self.recControl.isCutting(path):
				date, pixmap, color = "-- CUT --", self.movie_rec, self.RecordingColor
			res = [ None ]
				
			offset = 0
			progressWidth = 55
			if config.EMC.movie_icons.value and selnumtxt is None:
				res.append(MultiContentEntryPixmapAlphaTest(pos=(5,2), size=(24,24), png=pixmap, **{}))
				if isLink:
					res.append(MultiContentEntryPixmapAlphaTest(pos=(7,13), size=(9,10), png=self.link, **{}))
				offset = 35
			if selnumtxt is not None:
				res.append(MultiContentEntryText(pos=(5, 0), size=(26, globalHeight), font=3, flags=RT_HALIGN_LEFT, text=selnumtxt))
				offset += 35
				
			if config.EMC.skin_able.value:
				if self.CoolBarPos != -1:
					res.append(MultiContentEntryProgress(pos=(self.CoolBarPos, self.CoolBarHPos -2), size = (self.CoolBarSizeSa.width(), self.CoolBarSizeSa.height()), percent = progress, borderWidth = 1, foreColor = color, backColor = color))
				if self.CoolProgressPos != -1:
					res.append(MultiContentEntryText(pos=(self.CoolProgressPos, 0), size=(progressWidth, globalHeight), font=usedFont, flags=RT_HALIGN_LEFT, text="%d%%" % (progress)))
				if self.CoolDatePos != -1:
					if date != "-- REC --" and date != "-- rec --" and date != "-- CUT --":
						if self.CoolDateColor == 0:
							color = self.DateColor
					res.append(MultiContentEntryText(pos=(self.CoolDatePos, 2), size=(self.CoolDateWidth, globalHeight), font=4, text=date, color = color, color_sel = color, flags=RT_HALIGN_CENTER))
					
				res.append(MultiContentEntryText(pos=(self.CoolMoviePos, 0), size=(self.CoolMovieSize, globalHeight), font=usedFont, flags=RT_HALIGN_LEFT, text=moviestring))
				return res
				
			if config.EMC.movie_progress.value != "Off":
				if config.EMC.movie_progress.value == "PB":
					res.append(MultiContentEntryProgress(pos=(offset, self.CoolBarHPos), size = (self.CoolBarSize.width(), self.CoolBarSize.height()), percent = progress, borderWidth = 1, backColorSelected = None, foreColor = color, backColor = color))
					offset += self.CoolBarSize.width() + 10
				else:
					res.append(MultiContentEntryText(pos=(offset, 0), size=(progressWidth, globalHeight), font=usedFont, flags=RT_HALIGN_CENTER, text="%d%%" % (progress), color = color, color_sel = color, backcolor = self.BackColor, backcolor_sel = self.BackColorSel))
					offset += progressWidth + 5
				
			if config.EMC.movie_date.value:
				if date != "-- REC --" and date != "-- rec --" and date != "-- CUT --":
					if self.CoolDateColor == 0:
						color = self.DateColor
				# Datum
				res.append(MultiContentEntryText(pos=(self.l.getItemSize().width() - self.CoolDateWidth, 0), size=(self.CoolDateWidth, globalHeight), font=4, color = color, color_sel = color, backcolor = self.BackColor, backcolor_sel = self.BackColorSel, flags=RT_HALIGN_CENTER, text=date))
			res.append(MultiContentEntryText(pos=(offset, 0), size=(self.l.getItemSize().width() - offset - self.CoolDateWidth -5, globalHeight), font=usedFont, flags=RT_HALIGN_LEFT, text=moviestring))
				
			return res
		except Exception, e:
			emcDebugOut("[MC] buildMovieCenterEntry exception:\n" + str(e))
			return [ None ]

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

	GUI_WIDGET = eListbox

	def postWidgetCreate(self, instance):
		instance.setWrapAround(True)
		instance.setContent(self.l)
		instance.selectionChanged.get().append(self.selectionChanged)

	def removeService(self, service):
		if service:
			for l in self.list[:]:
				if l[0] == service:
					self.list.remove(l)
			self.l.setList(self.list)

	def serviceBusy(self, service):
		return service in self.highlightsMov or service in self.highlightsDel

	def serviceMoving(self, service):
		return service and service in self.highlightsMov

	def serviceDeleting(self, service):
		return service and service in self.highlightsDel

	def highlightService(self, enable, mode, service):
		if enable:
			if mode == "move":
				self.highlightsMov.append(service)
				self.toggleSelection(service, overrideNum=9999)
			elif mode == "del":
				self.highlightsDel.append(service)
				self.toggleSelection(service, overrideNum=9998)
		else:
			if mode == "move":
				self.highlightsMov.remove(service)
			elif mode == "del":
				self.highlightsDel.remove(service)

	def __len__(self):
		return len(self.list)

	def makeSelectionList(self):
		selList = []
		if self.currentSelectionCount == 0:
			# if no selections made, select the current cursor position
			single = self.l.getCurrentSelection()
			if single:
				selList.append(single[0])
		else:
			selList = self.selectionList
		return selList

	def resetSelection(self):
		self.selectionList = None
		self.currentSelectionCount = 0

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

	def toggleSelection(self, service=None, index=-1, overrideNum=None):
		try:
			x = None
			if service is None:
				if index == -1:
					if self.l.getCurrentSelection() is None: return
					index = self.getCurrentIndex()
				x = self.list[index]
			else:
				index = 0
				for e in self.list:
					if e[0] == service:
						x = e
						break
					index += 1
			if x is None: return
			
			# We have x=service, index, overrideNum
			if self.indexIsDirectory(index): return
			if self.selectionList == None:
				self.selectionList = []
			newselnum = x[5]	# init with old selection number
			if overrideNum == None:
				if self.serviceBusy(x[0]): return	# no toggle if file being operated on
				# basic selection toggle
				if newselnum == 0:
					# was not selected
					self.currentSelectionCount += 1
					newselnum = self.currentSelectionCount
					self.selectionList.append(x[0]) # append service
				else:
					# was selected, reset selection number and decrease all that had been selected after this
					newselnum = 0
					self.currentSelectionCount -= 1
					count = 0
					if x is not None:
						self.selectionList.remove(x[0]) # remove service
					for i in self.list:
						if i[5] > x[5]:
							self.list[count] = (i[0], i[1], i[2], i[3], i[4], i[5]-1, i[6], i[7])
							self.l.invalidateEntry(count) # force redraw
						count += 1
			else:
				newselnum = overrideNum * (newselnum == 0)
			self.list[index] = (x[0], x[1], x[2], x[3], x[4], newselnum, x[6], x[7])
			self.l.invalidateEntry(index) # force redraw of the modified item
		except Exception, e:
			emcDebugOut("[MC] buildMovieCenterEntry exception:\n" + str(e))

	def getLengthFromServiceHandler(self, service):
		# Get the movie length in seconds
		if service:
			info = self.serviceHandler.info(service)
			if info:
				return info.getLength(service)
			else:
				return 0
		else:
			return 0

	def getFileNameOfService(self, service):
		if service:
			for entry in self.list:
				if entry[0] == service:
					return entry[4]
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
	
	def invalidateCurrent(self):
		self.l.invalidateEntry(self.getCurrentIndex())

	def invalidateService(self, service):
		idx = self.getIndexOfService(service)
		if idx < 0: return
		self.l.invalidateEntry( idx ) # force redraw of the item

	def detectDVDStructure(self, loadPath):
		#TODO use a list
		if not os.path.isdir(loadPath):
			return None
		elif fileExists(loadPath + "/VIDEO_TS.IFO"):
			return loadPath + "/VIDEO_TS.IFO"
		elif fileExists(loadPath + "/VIDEO_TS/VIDEO_TS.IFO"):
			return loadPath + "/VIDEO_TS/VIDEO_TS.IFO"
		return None
	
	def reloadLatestRecordings(self):
		try:
			loadpath = config.EMC.movie_homepath.value + "/"
			emcDebugOut("[MC] reloadLatestRecordings, loadpath: " + loadpath)
			trashcan = False
			subdirlist = []
			filelist = []
			templist = []
			
			# walk through entire tree below movie home. Might take a bit long und huge disks... 
			# think about doing a manual recursive search via listdir() and stop at 2nd level, 
			# but include folders used in timers, auto timers and bookmarks
			for root, dirs, files in os.walk(loadpath):
				for p in files:
					pathname = os.path.join(root, p)
					if os.path.isfile(pathname):
						ext = os.path.splitext(p)[1].lower()
						global mediaExt
						if ext in mediaExt:
							fileDateTime = localtime(os.path.getmtime(pathname))
							date = strftime("%Y%m%d%H%M", fileDateTime)
							templist.append( (pathname, p, ext, date) )
							
			templist.sort(key=lambda x: x[3].lower(), reverse=True)
			count = 0
			for item in templist:
				count = count + 1
				filelist.append(item)
				if count > 12:
					break

			subdirlist.insert(0, ("..", ".."))
			return subdirlist, filelist
		except Exception, e:
			emcDebugOut("[MC] reloadLatestRecordings exception:\n" + str(e))

	def createDirlist(self, loadPath):
		try:
			trashcan = False
			subdirlist = []
			filelist = []
			dirlist = os.listdir(loadPath)	# only need to deal with spaces when executing in shell
			# add sub directories to the list
			if dirlist:
				for p in dirlist:
					pathname = os.path.join(loadPath, p)
					dvdStruct = self.detectDVDStructure(pathname)
					if os.path.isdir(pathname) and dvdStruct is None:
						# Path found
						if pathname == config.EMC.movie_trashpath.value:
							trashcan = True
							continue
						subdirlist.append( (pathname, p) )
					else:
						if dvdStruct:
							# DVD Structure found
							pathname = os.path.dirname(dvdStruct)
							ext = os.path.splitext(dvdStruct)[1].lower()
							fileDateTime = localtime(os.path.getmtime(dvdStruct))
							date = strftime("%Y%m%d%H%M", fileDateTime)
							filelist.append( (pathname, p, ext, date) )
						else:
							# Look for media files
							if os.path.isfile(pathname):
								ext = os.path.splitext(p)[1].lower()
								global mediaExt
								if ext in mediaExt:
									fileDateTime = localtime(os.path.getmtime(pathname))
									date = strftime("%Y%m%d%H%M", fileDateTime)
									filelist.append( (pathname, p, ext, date) )
				subdirlist.sort(key=lambda x: x[0].lower())
			# Insert these entries always at last
			if loadPath[:-1] == config.EMC.movie_homepath.value:
				# Insert a virtual directory 'Latest Recordings
				#TODO add config option
				subdirlist.insert(0, ("Latest Recordings", "Latest Recordings"))
				if os.path.exists("/usr/lib/enigma2/python/Plugins/Extensions/VlcPlayer") and not config.EMC.movie_vlc_hide.value:
					subdirlist.insert(0, ("VLC servers", "VLC servers"))
				if trashcan and not config.EMC.movie_trashcan_hide.value:
					subdirlist.insert(0, (config.EMC.movie_trashpath.value, os.path.basename(config.EMC.movie_trashpath.value)))
			if loadPath != "/" and loadPath[:-1] != config.EMC.movie_pathlimit.value:
				subdirlist.insert(0, ("..", ".."))
			return subdirlist, filelist
		except Exception, e:
			emcDebugOut("[MC] createDirlist exception:\n" + str(e))

	def reload(self, loadPath):
		try:
			self.currentSelectionCount = 0
			if not loadPath.endswith("/"): loadPath += "/"
			self.loadPath = loadPath
			self.selectionList = None
			self.list = []
			self.newRecordings = False
			self.recControl.recFilesRead()	# get a list of current remote recordings
			
			emcDebugOut("[MC] LOAD PATH:\n" + loadPath)
			if loadPath.endswith("VLC servers/"):
				emcDebugOut("[MC] VLC Server")
				self.reloadVlcServers()
				return
			elif loadPath.find("VLC servers/")>-1:
				emcDebugOut("[MC] VLC Files")
				self.reloadVlcFilelist()
				return

			if loadPath.endswith("Latest Recordings/"):
				# Read latest recordings
				emcDebugOut("[MC] Latest Recordings")
				subdirlist, filelist = self.reloadLatestRecordings()
			else:
				# Read subdirectories and filenames
				subdirlist, filelist = self.createDirlist(loadPath)
			
			# add sub directories to the list
			if subdirlist is not None:
				for path, name in subdirlist:
					self.list.append((eServiceReference("2:0:1:0:0:0:0:0:0:0:" + path), None, None, None, name, 0, 0, ""))
			
			tmplist = []
			if filelist is not None:
				for path, filename, ext, date in filelist:
					service = self.getPlayerService(path, filename, ext)
					moviestring = ""
					len = 0
		# > meta load
					if config.EMC.CoolMovieNr.value is False:
						if config.EMC.movie_metaload.value:
							meta = MetaList(service)
							moviestring = meta.getMetaName()
							len = meta.getMetaLength()
							if config.EMC.CoolFormat.value:
								if moviestring != "":
									moviestring += ext
		# < meta load
					if filename[0:8].isdigit() and filename[9:13].isdigit() and not filename[8:1].isdigit():
						date = filename[0:8] + filename[9:13]
						if moviestring == "":
							moviestring = filename[16:]	# skips "YYYYMMDD TIME - "
							chlMarker = moviestring.find("_-_")
							if chlMarker > 0: moviestring = moviestring[3+chlMarker:]
							else:
								chlMarker = moviestring.find(" - ")
								if chlMarker > 0: moviestring = moviestring[3+chlMarker:]
					elif filename[0:2].isdigit() and filename[3:5].isdigit() and not filename[2:3].isdigit():
						if moviestring == "":
							moviestring = filename[11:]	# skips "YYYYMMDD TIME - "
							chlMarker = moviestring.find("_-_")
							if chlMarker > 0: moviestring = moviestring[3+chlMarker:]
							else:
								chlMarker = moviestring.find(" - ")
								if chlMarker > 0: moviestring = moviestring[3+chlMarker:]
					elif filename[0:8].isdigit() and filename[8:11] == " - " or filename[0:8].isdigit() and filename[8:11] == "_-_":
					
						date = filename[0:8] + "3333"
						if moviestring == "":
							moviestring = filename[11:]
					else:
						if moviestring == "":
							moviestring = filename[0:]
					
					sortkey = moviestring.lower() + date
					if not (self.serviceMoving(service) and config.EMC.movie_hide_mov.value):
						if not (self.serviceDeleting(service) and config.EMC.movie_hide_del.value):
							if not config.EMC.CoolFormat.value:
								if moviestring.lower().endswith(ext):
									moviestring = os.path.splitext(moviestring)[0]
							tmplist.append((service, sortkey, date, moviestring, filename, 0, len, ext))
			if self.alphaSort:
				tmplist.sort(key=lambda x: x[1], reverse=config.EMC.moviecenter_reversed.value)
			else:
				tmplist.sort(key=lambda x: x[2], reverse=not config.EMC.moviecenter_reversed.value)
			# Combine folders and files
			self.list.extend( tmplist )
			# Assign list to listbox
			self.l.setList(self.list)
			#self.resetSelection()
		except Exception, e:
			emcDebugOut("[MC] reload exception:\n" + str(e))

	def getNextService(self):
		if not self.currentSelIsDirectory():
			# Cusror marks a movie
			idx = self.getCurrentIndex()
			length = len(self.list)
			for i in xrange(length):
				entry = self.list[(i+idx)%length]
				if entry:
					if entry[2]: 
						# Entry is no directory
						yield entry[0]
		else:
			# Cursor marks a directory
			service = self.getCurrent()
			if service:
				path = service.getPath()
				# Don't play movies from the trash folder or ".."
				if path != config.EMC.movie_trashpath.value and not self.getCurrentSelName() == "..":
					for root, dirs, files in os.walk(path): #,False):
						if dirs:
							for dir in dirs:
								path = os.path.join(root, dir)
								dvdStruct = self.detectDVDStructure( path )
								if dvdStruct:
									path = os.path.dirname(dvdStruct)
									ext = os.path.splitext(dvdStruct)[1].lower()
									yield self.getPlayerService(path, dir, ext)
						if files:
							for name in files:
								global mediaExt
								ext = os.path.splitext(name)[1].lower()
								if ext in mediaExt:
									path = os.path.join(root, name)
									ext = os.path.splitext(name)[1].lower()
									yield self.getPlayerService(path, name, ext)

	def getPlayerService(self, path, name, ext=None):
		if not name:
			print "EMC TODO Not tested yet"
			name = os.path.basename(path) 
		if not ext:
			ext = os.path.splitext(path)[1].lower()
		global playerDVB, playerDVD, serviceIdDVB, serviceIdDVD, serviceIdMP3 #, playerMP3
		if ext in playerDVB:
			service = eServiceReference(serviceIdDVB, 0, path)
		elif ext in playerDVD:
			service = eServiceReference(serviceIdDVD, 0, path)
			if service:
				if service.toString().endswith("/VIDEO_TS") or service.toString().endswith("/"):
					names = service.toString().rsplit("/",3)
					if names[2].startswith("Disk ") or names[2].startswith("DVD "):
						name = str(names[1]) + " - " + str(names[2])
					else:
						name = names[2]
					service.setName(str(name))
		elif ext in playerM2TS:
			service = eServiceReference(serviceIdM2TS, 0, path)
		else: # elif ext in playerMP3 
			service = eServiceReference(serviceIdMP3, 0, path)
		return service

	def currentSelIsLatest(self):
		try:	return self.list[self.getCurrentIndex()][4].startswith("Latest Recordings")
		except:	return False

	def currentSelIsDirectory(self):
		try:	return self.list[self.getCurrentIndex()][2] is None #or self.currentSelIsVlcDir()
		except:	return False

	def indexIsDirectory(self, index):
		try:	return self.list[index][2] is None #or self.currentSelIsVlcDir()
		except:	return False

	def getCurrentSelDir(self):
		service = self.getCurrent()
		return service and service.getPath()

	def getCurrentSelName(self):
		try: return self.list[self.getCurrentIndex()][3]
		except: return "none"

	def getCurrentSelPath(self):
		return self.loadPath + self.list[self.getCurrentIndex()][4] + (self.list[self.getCurrentIndex()][2] is None) * "/"

	def moveToIndex(self, index):
		self.instance.moveSelectionTo(index)

	def moveToService(self, service):
		found = 0
		if service:
			count = 0
			for x in self.list:
				if x[0] == service:
					found = count
				count += 1
		self.instance.moveSelectionTo(found)
