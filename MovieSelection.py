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

from Components.ActionMap import ActionMap, HelpableActionMap
from Components.Button import Button
from Components.config import *
from Components.Label import Label
from Screens.Screen import Screen
from Screens.HelpMenu import HelpableScreen
from Screens.MessageBox import MessageBox
from Screens.ChoiceBox import ChoiceBox
from Screens.LocationBox import MovieLocationBox
from Tools import Notifications
from Tools.BoundFunction import boundFunction
from enigma import getDesktop, eServiceReference
import os
from time import time

from DelayedFunction import DelayedFunction
from EnhancedMovieCenter import _
from EMCTasker import emcTasker, emcDebugOut
from MovieCenter import MovieCenter
from MovieSelectionMenu import MovieMenu
from EMCMediaCenter import EMCMediaCenter
from VlcPluginInterface import VlcPluginInterfaceSel
from CutListSupport import CutList
from DirectoryStack import DirectoryStack
from E2Bookmarks import E2Bookmarks
from ServiceSupport import ServiceEvent

from MovieCenter import extMedia
global extMedia

gMS = None


class SelectionEventInfo:
	def __init__(self):
		#from Components.Sources.ServiceEvent import ServiceEvent
		self["Service"] = ServiceEvent()

	def updateEventInfo(self, service):
		if service is None:
			# Reload is in progress
			self["Service"].newService(None)
		else:
			self["Service"].newService(service)


class EMCSelection(Screen, HelpableScreen, SelectionEventInfo, VlcPluginInterfaceSel, DirectoryStack, E2Bookmarks):
	def __init__(self, session):
		Screen.__init__(self, session)
		SelectionEventInfo.__init__(self)
		VlcPluginInterfaceSel.__init__(self)
		DirectoryStack.__init__(self)
		self.avPolicy43 = config.av.policy_43.value
		
		self.skinName = "EMCSelection"
		skin = None
		CoolWide = getDesktop(0).size().width()
		if CoolWide == 720:
			skin = "/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/CoolSkin/EMCSelection_720.xml"
		elif CoolWide == 1024:
			skin = "/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/CoolSkin/EMCSelection_1024.xml"
		elif CoolWide == 1280:
			skin = "/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/CoolSkin/EMCSelection_1280.xml"
		if skin:
			Cool = open(skin)
			self.skin = Cool.read()
			Cool.close()
		
		self.playerInstance = None
		self.lastPlayedMovies = None
		self.multiSelectIdx = None
		self.returnService = None
		self.callUpdate = None
		self.cursorDir = 0
		self["wait"] = Label(_("Reading directory..."))
		self["wait"].hide()
		self["list"] = MovieCenter()
		self["key_red"] = Button()
		self["key_green"] = Button()
		self["key_yellow"] = Button()
		self["key_blue"] = Button()
		global gMS
		gMS = self
		self["actions"] = HelpableActionMap(self, "PluginMovieSelectionActions",
			{
				"EMCOK":			(self.entrySelected,		_("Play selected movie(s)")),
#				"EMCOKL":			(self.unUsed,				"-"),
				"EMCPLAY":		(self.PlayAll,		_("Play ALL")),
				"EMCEXIT":		(self.abort, 				_("Close EMC")),
				"EMCMENU":		(self.openMenu,				_("Open menu")),
				"EMCINFO":		(self.showEventInformation,	_("Show event info")),
				"EMCINFOL":		(self.IMDbSearch,			_("IMDBSearch")),
				"EMCRed":			(self.deleteFile,			_("Delete file or empty dir")),
				"EMCGreen":		(self.toggleSort,			_("Toggle sort mode")),
				"EMCYellow":	(self.moveMovie,			_("Move selected movie(s)")),
				"EMCBlue":		(self.blueFunc,				_("Movie home / Play last (configurable)")),
#				"EMCRedL":		(self.unUsed,				"-"),
#				"EMCGreenL":	(self.unUsed,				"-"),
#				"EMCYellowL":	(self.unUsed,				"-"),
				"EMCBlueL":		(self.openBookmark,		_("Open E2 bookmarks")),
				"EMCLeft":		(self.pageUp,				_("Move cursor page up")),
				"EMCRight":		(self.pageDown,				_("Move cursor page down")),
				"EMCUp":			(self.moveUp,			_("Move cursor up")),
				"EMCDown":		(self.moveDown,			_("Move cursor down")),
				"EMCBqtPlus":	(self.moveTop,			_("Move cursor to the top")),
				"EMCBqtMnus":	(self.moveEnd,			_("Move cursor to the end")),
				"EMCArrowNext":	(self.CoolForward,		_("Directory forward")),
#				"EMCArrowNextL":	(self.unUsed,				"-"),
				"EMCArrowPrevious":	(self.CoolBack,			_("Directory back")),
#				"EMCArrowPreviousL":	(self.directoryUp,				_("Directory up")),
				"EMCVIDEOB":	(self.toggleSelectionList,		_("Toggle service selection")),
				"EMCVIDEOL":	(self.resetSelectionList,		_("Remove service selection")),
				"EMCAUDIO":		(self.openMenuPlugins,		_("Available plugins menu")),
#				"EMCAUDIOL":	(self.unUsed,				"-"),
				"EMCMENUL":		(self.openMenuPlugins,		_("Available plugins menu")),
				"EMCTV":			(self.triggerReloadList,			_("Reload movie file list")),
				"EMCTVL":			(self.CoolTimerList,			_("Open Timer List")),
				"EMCRADIO":		(self.toggleProgress,			_("Toggle viewed / not viewed")),
#				"EMCRADIOL":	(self.unUsed,				"-"),
				"EMCTEXT":		(self.multiSelect,			_("Start / end multiselection")),
#				"EMCTEXTL":		(self.unUsed,				"-"),
				"0":		(self.CoolKey0,					"-"),
				"4":		(self.CoolAVSwitch,			"-"),
				"7":		(self.CoolTVGuide,			"-"),
				"8":		(self.CoolEasyGuide,		"-"),
				"9":		(self.CoolSingleGuide,	"-"),
			}, prio=-1)
			# give them a little more priority to win over baseclass buttons
		self["actions"].csel = self
		
		HelpableScreen.__init__(self)
		
		self.currentPath = config.EMC.movie_homepath.value
		self.tmpSelList = None
		self.toggle = True
		
		self.onShow.append(self.onDialogShow)
		self.onHide.append(self.onDialogHide)

	def CoolAVSwitch(self):
		if config.av.policy_43.value == "pillarbox":
			config.av.policy_43.value = "panscan"
		elif config.av.policy_43.value == "panscan":
			config.av.policy_43.value = "scale"
		else:
			config.av.policy_43.value = "pillarbox"

	def CoolTVGuide(self):
		try:
			from Plugins.Extensions.CoolTVGuide.plugin import main
			main(self.session)
		except: return

	def CoolEasyGuide(self):
		try:
			from Plugins.Extensions.CoolTVGuide.CoolEasyGuide import CEGmain
			CEGmain(self.session)
		except: return

	def CoolSingleGuide(self):
		try:
			from Plugins.Extensions.CoolTVGuide.CoolSingleGuide import CSGmain
			CSGmain(self.session)
		except: return

	def CoolTimerList(self):
		from Screens.TimerEdit import TimerEditList
		self.session.open(TimerEditList)

	def abort(self):
		if config.EMC.CoolStartHome.value:
			self.changeDir(config.EMC.movie_homepath.value)
		if self.playerInstance is not None:
			self.playerInstance.movieSelected(None)
		else:
			config.av.policy_43.value = self.avPolicy43
		self.close(None)

	def blueFunc(self):
		if config.EMC.movie_bluefunc.value == "MH":
			self.returnService = None
			self["list"].alphaSort = config.EMC.CoolStartAZ.value
			self["list"].returnSort = None
			self.changeDir(config.EMC.movie_homepath.value)
		elif config.EMC.movie_bluefunc.value == "PL":
			self.playLast()

	def changeDir(self, path, service=None):
		path = os.path.normpath(path)
		self.returnService = service
		#TODOret if self.returnService: print "EMC ret chnSer " +str(self.returnService.toString())
		self.reloadList(path)

	def CoolKey0(self):
		# Movie home
		self.setStackNextDirectory( self.currentPath, self["list"].getCurrent() )
		self.changeDir(config.EMC.movie_homepath.value)

	def CoolForward(self):
		path, service = self.goForward( self.currentPath, self["list"].getCurrent() )
		if path and service:
			# Actually we are in a history folder - go forward
			self.changeDir(path, service)
		else:
			# No entry on stack
			# Move cursor to top of the list
			self.moveTop()

	def CoolBack(self):
		path, service = self.goBackward( self.currentPath, self["list"].getCurrent() )
		if path and service:
			# History folder is available - go back 
			self.changeDir(path, service)
		else:
			self.directoryUp()

	def directoryUp(self):
		path = None
		service = None
		if self.currentPath != "" and self.currentPath != "/":
			# Open parent folder
			self.setNextPath()
		else:
			# No entry on stack
			# Move cursor to top of the list
			self.moveTop()

	def setNextPath(self, nextdir = None, service = None):
		if nextdir == ".." or nextdir is None or nextdir.endswith(".."):
			if self.currentPath != "" and self.currentPath != "/":
				# Open Parent folder
				service = self["list"].getPlayerService(self.currentPath)
				nextdir = os.path.dirname(self.currentPath)
			else:
				# No way to go folder up
				return
		else:
			# Open folder nextdir and select given or first entry
			pass
		
		self.setStackNextDirectory( self.currentPath, self["list"].getCurrent() )
		self.changeDir(nextdir, service)

	def getCurrent(self):
		return self["list"].getCurrent()

	def moveUp(self):
		self.cursorDir = -1
		self["list"].instance.moveSelection( self["list"].instance.moveUp )
		self.updateAfterKeyPress()

	def moveDown(self):
		self.cursorDir = 1
		self["list"].instance.moveSelection( self["list"].instance.moveDown )
		self.updateAfterKeyPress()

	def pageUp(self):
		self.cursorDir = 0
		self["list"].instance.moveSelection( self["list"].instance.pageUp )
		self.updateAfterKeyPress()

	def pageDown(self):
		self.cursorDir = 0
		self["list"].instance.moveSelection( self["list"].instance.pageDown )
		self.updateAfterKeyPress()

	def moveTop(self):
		self["list"].instance.moveSelection( self["list"].instance.moveTop )
		self.updateAfterKeyPress()

	def moveEnd(self):
		self["list"].instance.moveSelection( self["list"].instance.moveEnd )
		self.updateAfterKeyPress()

	def updateAfterKeyPress(self):
		if self.returnService:
			# Service was stored for a pending update,
			# but user wants to move, copy, delete it,
			# so we have to update returnService
			if self.tmpSelList:
				self.returnService = self.getNextSelectedService(self.getCurrent(), self.tmpSelList)
				#TODOret if self.returnService: print "EMC ret updSer " +str(self.returnService.toString())
		if self.multiSelectIdx:
			self.multiSelect( self.getCurrentIndex() )
		self.updateMovieInfo()

	def multiSelect(self, index=-1):
		if self.browsingVLC(): return
		
		if index == -1:
			# User pressed the multiselect key
			if self.multiSelectIdx is None:
				# User starts multiselect
				index = self.getCurrentIndex()
				# Start new list with first selected item index
				self.multiSelectIdx = [index]
				# Toggle the first selected item
				self["list"].toggleSelection( index=index )
			else:
				# User stops multiselect
				# All items are already toggled
				self.multiSelectIdx = None
			self.updateTitle()
		else:	
			if self.multiSelectIdx:
				# Multiselect active
				firstIndex = self.multiSelectIdx[0]
				lastIndex = self.multiSelectIdx[-1]
				# Calculate step : selection and range step +1/-1 -> indicates the direction
				selStep = 1 - 2 * ( firstIndex > lastIndex)  # >=
				rngStep = 1 - 2 * ( lastIndex > index )
				if selStep == rngStep or firstIndex == lastIndex:
					start = lastIndex + rngStep
					end = index + rngStep
				elif index not in self.multiSelectIdx:
					start = lastIndex
					end = index + rngStep
				else:
					start = lastIndex
					end = index
				# Range from last selected to cursor position (both are included)
				for i in xrange(start, end, rngStep):
					if self.multiSelectIdx[0] == i:
						# Never untoggle the first index
						continue  # pass
					elif i not in self.multiSelectIdx:
						# Append index
						self.multiSelectIdx.append(i)
						# Toggle
						self["list"].toggleSelection( index=i )
					else:
						# Untoggle
						self["list"].toggleSelection( index=i )
						# Remove index
						self.multiSelectIdx.remove(i)
			else:
				emcDebugOut("[EMCMS] multiSelect Not active")

	def openBookmark(self):
		self.session.openWithCallback(self.openBookmarkCB, MovieLocationBox, text = _("Open E2 Bookmark path"), dir = str(self.currentPath)+"/")

	def openBookmarkCB(self, path=None):
		if path is not None:
			self.changeDir(path)

	def menuCallback(self, selection=None, parameter=None):
		if selection is not None:
			if selection == "Play last": self.playLast()
			elif selection == "Movie home": self.changeDir(config.EMC.movie_homepath.value)
			elif selection == "reload": self.reloadList()
			elif selection == "plugin": self.onDialogShow()
			elif selection == "setup": self.onDialogShow()
			elif selection == "ctrash": self.purgeExpired()
			elif selection == "trash": self.changeDir(config.EMC.movie_trashcan_path.value)
			elif selection == "delete": self.deleteFile(True)
			elif selection == "cutlistmarker": self.removeCutListMarker()
			elif selection == "obookmark": self.openBookmark()
			elif selection == "rbookmark": self.removeBookmark(parameter)
			elif selection == "dirup": self.directoryUp()
			elif selection == "oscripts": self.openScriptMenu()

	def openMenu(self):
		current = self.getCurrent()
		#if not self["list"].currentSelIsPlayable(): current = None
		self.session.openWithCallback(self.menuCallback, MovieMenu, "normal", self["list"], current, self["list"].makeSelectionList(), self.currentPath)

	def openMenuPlugins(self):
		current = self.getCurrent()
		if self["list"].currentSelIsPlayable():
			self.session.openWithCallback(self.menuCallback, MovieMenu, "plugins", self["list"], current, self["list"].makeSelectionList(), self.currentPath)

	def openScriptMenu(self):
		#TODO actually not used and not working
		if self.browsingVLC():
			self.session.open(MessageBox, _("No script operation for VLC streams."), MessageBox.TYPE_ERROR)
			return
		try:
			list = []
			paths = ["/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/script/", "/etc/enigma2/EnhancedMovieCenter/"]
			
			for path in paths:
				for e in os.listdir(path):
					pathe = os.path.join(path, e)
					if not os.path.isdir(pathe):
						if e.endswith(".sh"):
							list.append([e, pathe])
						elif e.endswith(".py"):
							list.append([e, pathe])
			
			if len(list) == 0:
				self.session.open(MessageBox, paths[0]+"\n   or" + paths[1]+"\n" + _("Does not contain any scripts."), MessageBox.TYPE_ERROR)
				return
			
			dlg = self.session.openWithCallback(self.scriptCB, ChoiceBox, " ", list)
			dlg.setTitle(_("Choose script"))
			dlg["list"].move(0,30)
		
		except Exception, e:
			emcDebugOut("[EMCMS] openScriptMenu exception:\n" + str(e))

	def unUsed(self):
		self.session.open(MessageBox, _("No functionality set..."), MessageBox.TYPE_INFO)

	def updateMovieInfo(self):
		if self.callUpdate is not None:
			if self.callUpdate.exists():
				self.callUpdate.cancel()
		self.callUpdate = DelayedFunction( int(config.EMC.movie_descdelay.value), self.updateMovieInfoDelayed )

	def updateMovieInfoDelayed(self):
		self.updateTitle()
		self.updateEventInfo(self.getCurrent())

	def updateTitle(self):
		if self.multiSelectIdx:
			self.setTitle(_("*** Multiselection active ***"))
			return
		lotime = localtime()
		title = "[%02d:%02d] " %(lotime[3],lotime[4])
		if os.path.exists(self.currentPath):
			stat = os.statvfs(self.currentPath)
			free = (stat.f_bavail if stat.f_bavail!=0 else stat.f_bfree) * stat.f_bsize / 1024 / 1024
			if free >= 10240:	#unit in Giga bytes if more than 10 GB free
				title = "(%d GB) " %(free/1024)
			else:
				title = "(%d MB) " %(free)
		title += self.currentPath or "/" #TEST + (self.currentPath == "")*"/"
		title = title.replace(config.EMC.movie_homepath.value, "...")
		self.setTitle(title)

	def toggleSort(self):
		if self.browsingVLC(): return
		service = self.getNextSelectedService(self.getCurrent())
		self.returnService = service
		self["list"].setSorting( not self["list"].getSorting()[0] )
		self.initButtons()
		self.initCursor()
		self.updateMovieInfo()

	def toggleSelectionList(self):
		if self.toggle == False:
			self.toggle = True
			return
		if self.toggle:
			if self["list"].currentSelIsPlayable():
				self["list"].toggleSelection()
			# Move cursor
			if config.EMC.moviecenter_selmove.value != "o":
				if self.cursorDir == -1 and config.EMC.moviecenter_selmove.value == "b":
					self.moveToIndex( max(self.getCurrentIndex()-1, 0) )
				else:
					self.moveToIndex( min(self.getCurrentIndex()+1, len(self["list"])-1) )

	def resetSelectionList(self):
		if self.multiSelectIdx:
			self.multiSelectIdx = None
			self.updateTitle()
		self.toggle = False
		selectedlist = self["list"].makeSelectionList()[:]
		if selectedlist:
			for service in selectedlist:
				self["list"].toggleSelection(service)

	def toggleProgress(self, service=None, preparePlayback=False):
		if self.multiSelectIdx:
			self.multiSelectIdx = None
			self.updateTitle()
		if service is None:
			first = False
			forceProgress = -1
			current = self.getCurrent()
			if current is not None:
				# Force copy of selectedlist
				selectedlist = self["list"].makeSelectionList()[:]
				if len(selectedlist)>1 and not preparePlayback:
					first = True
				for sel in selectedlist:
					progress = self.__toggleProgressService(sel, preparePlayback, forceProgress, first)
					first = False
					if not preparePlayback:
						forceProgress = progress
		else:
			self.__toggleProgressService(service, preparePlayback)
	
	def __toggleProgressService(self, service, preparePlayback, forceProgress=-1, first=False):
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
			os.rename(cutsr, cuts)	
			
		# All calculations are done in seconds
		cuts = CutList( path )
		last = cuts.getCutListLast()
		length = self["list"].getLengthOfService(service)
		progress = self["list"].getProgress(service, length=length, last=last, forceRecalc=True, cuts=cuts)
		
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
		
		# Update movielist entry
		self["list"].invalidateService(service)
		return progress
	
	def IMDbSearch(self):
		name = ''
		if (self["list"].getCurrentSelName()):
			name = (self["list"].getCurrentSelName())
		try:
			from Plugins.Extensions.IMDb.plugin import IMDB
		except ImportError:
			IMDB = None
		if IMDB is not None:
			self.session.open(IMDB, name, False)

	def showEventInformation(self):
		from Screens.EventView import EventViewSimple
		from ServiceReference import ServiceReference
		
		# Get our customized event
		evt = self["list"].getCurrentEvent()
		if evt:
			self.session.open(EventViewSimple, evt, ServiceReference(self.getCurrent()))

	def initCursor(self, ifunknown=True):
		if self.returnService:
			# Move to next or last selected entry
			self.moveToService(self.returnService)
			#TODOret if self.returnService: print "EMC ret retSer " +str(self.returnService.toString())
			#self.tmpSelList = None
		
		elif self.playerInstance:
			# Get current service from movie player
			service = self.playerInstance.currentlyPlayedMovie()
			if service is not None:
				self.moveToService(service)
		
		elif ifunknown:
			# Select first entry
			#TODOret print "EMC ret initCursor movetop correct ????"
			self.moveTop()
		
		self.returnService = None
		self.updateMovieInfo()

	def onDialogShow(self):
		self.initButtons()
		
		if config.EMC.movie_reload.value \
			or config.EMC.needsreload.value \
			or len(self["list"]) == 0:
			config.EMC.needsreload.value = False
			DelayedFunction(50, self.initList)
		
		else:
			# Refresh is done automatically
			#self["list"].refreshList()
			self.initCursor(False)
		
		self.updateMovieInfo()

	def onDialogHide(self):
		self.returnService = self.getCurrent() #self.getNextSelectedService(self.getCurrent(), self.tmpSelList)

	def getCurrentIndex(self):
		return self["list"].getCurrentIndex()

	def moveToIndex(self, index):
		self.multiSelectIdx = None
		self["list"].moveToIndex(index)
		self.updateMovieInfo()
	
	def moveToService(self, service):
		self.multiSelectIdx = None
		self["list"].moveToService(service)
		self.updateMovieInfo()

	def getNextSelectedService(self, current, selectedlist=None):
		curSerRef = None
		if current is None:
			tserRef = None
		elif not self["list"]:
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
			last_idx = len(self["list"]) - 1
			len_sel = len(selectedlist)
			first_sel_idx = last_idx
			last_sel_idx = 0
			
			# Get first and last selected item indexes
			for sel in selectedlist:
				idx = self["list"].getIndexOfService(sel)
				if idx < 0: idx = 0
				if idx < first_sel_idx: first_sel_idx = idx
				if idx > last_sel_idx:  last_sel_idx = idx
			
			# Calculate previous and next item indexes
			prev_idx = first_sel_idx - 1
			next_idx = last_sel_idx + 1
			len_fitola = last_sel_idx - first_sel_idx + 1
			
			# Check if there is a not selected item between the first and last selected item
			if len_fitola > len_sel:
				for entry in self["list"].list[first_sel_idx:last_sel_idx]:
					if entry[0] not in selectedlist:
						# Return first entry which is not in selectedlist
						curSerRef = entry[0]
						break
			# Check if next calculated item index is within the movie list
			elif next_idx <= last_idx:
				# Select item behind selectedlist
				curSerRef = self["list"].getServiceOfIndex(next_idx)
			# Check if previous calculated item index is within the movie list
			elif prev_idx >= 0:
				# Select item before selectedlist
				curSerRef = self["list"].getServiceOfIndex(prev_idx)
			else:
				# The whole list must be selected
				# First and last item is selected
				# Recheck and find first not selected item
				for entry in self["list"].list:
					if entry[0] not in selectedlist:
						# Return first entry which is not in selectedlist
						curSerRef = entry[0]
						break
		return curSerRef

	#TODO
	# Move all file operation functions to a separate class

	def removeCutListMarker(self):
		if self.browsingVLC(): return
		current = self.getCurrent()	# make sure there is atleast one entry in the list
		if current is not None:
			selectedlist = self["list"].makeSelectionList()[:]
			for service in selectedlist:
				cuts = CutList( service.getPath() )
				cuts.removeMarksCutList()
				self["list"].unselectService(service)
			emcDebugOut("[EMCMS] cut list marker removed permanently")

	def mountpoint(self, path, first=True):
		if first: path = os.path.realpath(path)
		if os.path.ismount(path) or len(path)==0: return path
		return self.mountpoint(os.path.dirname(path), False)

	def deleteFile(self, permanently=False):
		if self.multiSelectIdx:
			self.multiSelectIdx = None
			self.updateTitle()
		if self.browsingVLC(): return
		self.permanentDel  = permanently or not config.EMC.movie_trashcan_enable.value
		self.permanentDel |= self.currentPath == config.EMC.movie_trashcan_path.value
		self.permanentDel |= self.mountpoint(self.currentPath) != self.mountpoint(config.EMC.movie_trashcan_path.value)
		current = self.getCurrent()	# make sure there is atleast one entry in the list
		if current is not None:
			selectedlist = self["list"].makeSelectionList()[:]
			if self["list"].currentSelIsDirectory() and len(selectedlist) == 1 and current==selectedlist[0]:
				if not config.EMC.movie_trashcan_enable.value or config.EMC.movie_delete_validation.value or self.permanentDel:
					path = current.getPath()
					if os.path.islink(path):
						msg = _("Do you really want to remove your link\n%s?") % (path)
					else:
						msg = _("Do you really want to remove your directory\n%s?") % (path)
					self.session.openWithCallback(
							boundFunction(self.delPathSelConfirmed, current),
							MessageBox,
							msg )
				else:
					self.delPathSelConfirmed(current, True)
			elif self["list"].currentSelIsBookmark() and len(selectedlist) == 1 and current==selectedlist[0]:
				# Delete a single bookmark
				self.removeBookmark(current)
			else:
				if self["list"].serviceBusy(selectedlist[0]): return
				if selectedlist and len(selectedlist)>0:
					self.recsToStop = []
					self.remRecsToStop = False
					for service in selectedlist:
						path = service.getPath()
						if self["list"].recControl.isRecording(path):
							self.recsToStop.append(path)
						if config.EMC.remote_recordings.value and self["list"].recControl.isRemoteRecording(path):
							self.remRecsToStop = True
					if len(self.recsToStop)>0:
						self.stopRecordQ()
					else:
						self.deleteMovieQ(selectedlist, self.remRecsToStop)

	def removeBookmark(self, service):
		if service:
			path = service.getPath()
			if self.isE2Bookmark(path):
				if config.EMC.movie_delete_validation.value:
					self.session.openWithCallback(
							boundFunction(self.removeBookmarkConfirmed, service),
							MessageBox,
							_("Do you really want to remove your bookmark\n%s?") % (path) )
				else:
					self.removeBookmarkConfirmed(service, True)

	def removeBookmarkConfirmed(self, service, confirm):
		if confirm and service and config.movielist and config.movielist.videodirs:
			path = service.getPath()
			if self.removeE2Bookmark(path):
				# If service is not in list, don't care about it.
				self["list"].removeService(service)

	def deleteMovieQ(self, selectedlist, remoteRec):
		try:
			self.tmpSelList = selectedlist[:]
			self.delCurrentlyPlaying = False
			rm_add = ""
			if remoteRec:
				rm_add = _(" Deleting remotely recorded and it will display an rec-error dialog on the other DB.") + "\n"
				
			if self.playerInstance is not None:
				if self.playerInstance.currentlyPlayedMovie() in selectedlist:
					self.delCurrentlyPlaying = True
			entrycount = len(selectedlist)
			delStr = _("Delete") + _(" permanently")*self.permanentDel
			if entrycount == 1:
				service = selectedlist[0]
				name = self["list"].getNameOfService(service)
				if not self.delCurrentlyPlaying:
					if not config.EMC.movie_trashcan_enable.value or config.EMC.movie_delete_validation.value or self.permanentDel:
						self.session.openWithCallback(
								self.deleteMovieConfimation,
								MessageBox,
								delStr + "?\n" + rm_add + name,
								MessageBox.TYPE_YESNO )
					else:
						self.deleteMovieConfimation(True)
				else:
					self.session.openWithCallback(
							self.deleteMovieConfimation,
							MessageBox,
							delStr + _(" currently played?") + "\n" + rm_add + name,
							MessageBox.TYPE_YESNO )
			else:
				if entrycount > 1:
					movienames = ""
					i = 0
					for service in selectedlist:
						if i >= 5 and entrycount > 5:	# show only 5 entries in the file list
							movienames += "..."
							break
						i += 1
						name = self["list"].getNameOfService(service)
						if len(name) > 48:
							name = name[:48] + "..."	# limit the name string
						movienames += name + "\n"*(i<entrycount)
					if not self.delCurrentlyPlaying:
						if not config.EMC.movie_trashcan_enable.value or config.EMC.movie_delete_validation.value or self.permanentDel:
							self.session.openWithCallback(
									self.deleteMovieConfimation,
									MessageBox,
									delStr + _(" all selected video files?") + "\n" + rm_add + movienames,
									MessageBox.TYPE_YESNO )
						else:
							self.deleteMovieConfimation(True)
					else:
						self.session.openWithCallback(self.deleteMovieConfimation, MessageBox, delStr + _(" all selected video files? The currently playing movie is also one of the selections and its playback will be stopped.") + "\n" + rm_add + movienames, MessageBox.TYPE_YESNO)
		except Exception, e:
			self.session.open(MessageBox, _("Delete error:\n") + str(e), MessageBox.TYPE_ERROR)
			emcDebugOut("[EMCMS] deleteMovieQ exception:\n" + str(e))

	def deleteMovieConfimation(self, confirmed):
		current = self.getCurrent()
		if confirmed and self.tmpSelList is not None and len(self.tmpSelList)>0:
			if self.delCurrentlyPlaying:
				if self.playerInstance is not None:
					self.playerInstance.removeFromPlaylist(self.tmpSelList)
			delete = not config.EMC.movie_trashcan_enable.value or self.permanentDel
			if os.path.exists(config.EMC.movie_trashcan_path.value) or delete:
				# if the user doesn't want to keep the movies in the trash, purge immediately
				self.execFileOp(config.EMC.movie_trashcan_path.value, current, self.tmpSelList, op="delete", purgeTrash=delete)
				for x in self.tmpSelList:
					self.lastPlayedCheck(x)
				self["list"].resetSelection()
			elif not delete:
				self.session.openWithCallback(self.trashcanCreate, MessageBox, _("Delete failed because the trashcan directory does not exist. Attempt to create it now?"), MessageBox.TYPE_YESNO)
			emcDebugOut("[EMCMS] deleteMovie")

	def delPathSelConfirmed(self, service, confirm):
		if confirm and service:
			path = service.getPath()
			if path != "..":
				if os.path.islink(path):
					emcTasker.shellExecute("rm -f '" + path + "'")
					self["list"].removeService(service)
				elif os.path.exists(path):
					if len(os.listdir(path))>0:
						self.session.open(MessageBox, _("Directory is not empty."), MessageBox.TYPE_ERROR, 10)
					else:
						emcTasker.shellExecute('rmdir "' + path +'"')
						self["list"].removeService(service)
			else:
				self.session.open(MessageBox, _("Cannot delete the parent directory."), MessageBox.TYPE_ERROR, 10)

	def setPlayerInstance(self, player):
		try:
			self.playerInstance = player
		except Exception, e:
			emcDebugOut("[EMCMS] setPlayerInstance exception:\n" + str(e))

	def openPlayer(self, playlist, playall=False):
		# Force update of event info after playing movie 
		self.updateEventInfo(None)
		
		# force a copy instead of an reference!
		self.lastPlayedMovies = playlist[:]
		playlistcopy = playlist[:]
		# Start Player
		if self.playerInstance is None:
			Notifications.AddNotification(EMCMediaCenter, playlistcopy, self, playall)
		else:
			#DelayedFunction(10, self.playerInstance.movieSelected, playlist, playall)
			self.playerInstance.movieSelected(playlist, playall)
		self.close(None)

	def entrySelected(self, playall=False):
		current = self.getCurrent()
		if current is not None:
			# Save service 
			self.returnService = self.getCurrent() #self.getNextSelectedService(self.getCurrent(), self.tmpSelList)
			
			# Think about MovieSelection should only know about directories and files
			# All other things should be in the MovieCenter
			if self["list"].currentSelIsVirtual():
				# Open folder and reload movielist
				self.setNextPath( self["list"].getCurrentSelDir() )
			elif self.browsingVLC():
				# TODO full integration of the VLC Player
				entry = self["list"].list[ self["list"].getCurrentIndex() ]
				self.vlcMovieSelected(entry)
			else:
				playlist = self["list"].makeSelectionList()
				if not self["list"].serviceBusy(playlist[0]):
					self.openPlayer(playlist, playall)
				else:
					self.session.open(MessageBox, _("File not available."), MessageBox.TYPE_ERROR, 10)

	def playLast(self):
		if self.multiSelectIdx:
			self.multiSelectIdx = None
			self.updateTitle()
		if self.lastPlayedMovies is None:
			self.session.open(MessageBox, _("Last played movie/playlist not available..."), MessageBox.TYPE_ERROR, 10)
		else:
			self.openPlayer(self.lastPlayedMovies)

	def PlayAll(self):
		if self.multiSelectIdx:
			self.multiSelectIdx = None
			self.updateTitle()
		playlist = [self.getCurrent()] 
		playall = self["list"].getNextService()
		self.openPlayer(playlist, playall)

	def scriptCB(self, result=None):
		if result is None: return
		
		env = "export EMC_OUTDIR=%s"%config.EMC.folder.value
		env += " EMC_HOME=%s"%config.EMC.movie_homepath.value
		env += " EMC_PATH_LIMIT=%s"%config.EMC.movie_pathlimit.value
		env += " EMC_TRASH=%s"%config.EMC.movie_trashcan_path.value
		env += " EMC_TRASH_DAYS=%s"%int(config.EMC.movie_trashcan_limit.value)
		
		if self["list"].currentSelIsPlayable() or self["list"].currentSelIsDirectory():
			current = self["list"].getCurrentSelDir() + (self["list"].currentSelIsDirectory()) * "/"
			current = current.replace(" ","\ ")
			if os.path.exists(result[1]):
				if result[1].endswith(".sh"):
					emcTasker.shellExecute("%s; sh %s %s %s" %(env, result[1], self.currentPath, current))
				elif result[1].endswith(".py"):
					emcTasker.shellExecute("%s; python %s %s %s" %(env, result[1], self.currentPath, current))

	def stopRecordConfirmation(self, confirmed):
		if not confirmed: return
		# send as a list?
		stoppedAll=True
		for e in self.recsToStop:
			stoppedAll = stoppedAll and self["list"].recControl.stopRecording(e)
		if not stoppedAll:
			self.session.open(MessageBox, _("Not stopping any repeating timers. Modify them with the timer editor."), MessageBox.TYPE_INFO, 10)

	def stopRecordQ(self):
		try:
			filenames = ""
			for e in self.recsToStop:
				filenames += "\n" + e.split("/")[-1][:-3]
			self.session.openWithCallback(self.stopRecordConfirmation, MessageBox, _("Stop ongoing recording?\n") + filenames, MessageBox.TYPE_YESNO)
		except Exception, e:
			emcDebugOut("[EMCMS] stopRecordQ exception:\n" + str(e))

	def lastPlayedCheck(self, service):
		try:
			if self.lastPlayedMovies is not None:
				if service in self.lastPlayedMovies:
					self.lastPlayedMovies.remove(service)
				if len(self.lastPlayedMovies) == 0:
					self.lastPlayedMovies = None
		except Exception, e:
			emcDebugOut("[EMCMS] lastPlayedCheck exception:\n" + str(e))

	def loading(self, loading=True):
		self.updateEventInfo(None)
		if loading:
			self["list"].hide()
			self["wait"].show()
		else:
			self["wait"].hide()
			self["list"].show()

	def initButtons(self):
		# Initialize buttons
		self["key_red"].text = _("Delete")
		#TODO get color from MovieCenter
		sort, perm = self["list"].getSorting()
		green = ""
		if sort:
			green = _("Alpha sort")
		else:
			green = _("Date sort")
		if perm == True:
			green += _(" (P)")
		self["key_green"].text = green
		self["key_yellow"].text = _("Move")
		self["key_blue"].text = _(config.EMC.movie_bluefunc.description[config.EMC.movie_bluefunc.value])

	def initList(self):
		# Initialize list
		self.reloadList()

	def triggerReloadList(self):
		#IDEA:
		# Short TV refresh list - reloads only progress
		# Long TV reload  list - finds new movies 
		self.returnService = self.getNextSelectedService(self.getCurrent(), self.tmpSelList)
		#TODOret if self.returnService: print "EMC ret triSer " +str(self.returnService.toString())
		self.reloadList()

	def reloadList(self, path=None):
		self.multiSelectIdx = None
		if config.EMC.moviecenter_loadtext.value:
			self.loading()
		DelayedFunction(20, self.__reloadList, path)

	def __reloadList(self, path):
		if path is None:
			path = self.currentPath
		
		# The try here is a nice idea, but it costs us a lot of time
		# Maybe it should be implemented with a timer
		
		#TIME t = time()
		
		#try:
		
		if self["list"].reload(path):
			self.currentPath = path
			self.initButtons()
			self.initCursor()
		
		#except Exception, e:
		#	#MAYBE: Display MessageBox
		#	emcDebugOut("[EMCMS] reloadList exception:\n" + str(e))
		#finally:
		
		if config.EMC.moviecenter_loadtext.value:
			self.loading(False)
		
		#TIME print "EMC After reload " + str(time() - t)
		
		self.updateMovieInfo()

	def moveCB(self, service):
		self["list"].highlightService(False, "move", service)	# remove the highlight
		if not config.EMC.movie_hide_mov.value:
			self["list"].removeService(service)
		self.updateMovieInfo()

	def delCB(self, service):
		self["list"].highlightService(False, "del", service)	# remove the highlight
		if not config.EMC.movie_hide_del.value:
			self["list"].removeService(service)
		self.updateMovieInfo()

#Think about: All file operations should be separate or in MovieCenter.py 

	def execFileOp(self, targetPath, current, selectedlist, op="move", purgeTrash=False):
		self.returnService = self.getNextSelectedService(current, selectedlist)
		mvCmd = ""
		rmCmd = ""
		association = []
		for service in selectedlist:
			path = os.path.splitext( self["list"].getFilePathOfService(service) )[0]
			if path is not None:
				if op=="delete":	# target == trashcan
					if purgeTrash or self.currentPath == targetPath or self.mountpoint(self.currentPath) != self.mountpoint(targetPath):
						# direct delete from the trashcan or network mount (no copy to trashcan from different mountpoint)
						rmCmd += '; rm -f "'+ path +'."*'
					else:
						# create a time stamp with touch
						mvCmd += '; touch "'+ path +'."*'
						# move movie into the trashcan
						mvCmd += '; mv "'+ path +'."* "'+ targetPath +'/"'
					association.append((service, self.delCB))	# put in a callback for this particular movie
					self["list"].highlightService(True, "del", service)
					if config.EMC.movie_hide_del.value:
						self["list"].removeService(service)
				elif op == "move":
					#if self.mountpoint(self.currentPath) == self.mountpoint(targetPath):
					#	#self["list"].removeService(service)	# normal direct move
					#	pass
					#else:
					# different self.mountpoint? -> reset user&group
					if self.mountpoint(targetPath) != self.mountpoint(config.EMC.movie_homepath.value):		# CIFS to HDD is ok!
						# need to change file ownership to match target filesystem file creation
						tfile = targetPath + "/owner_test"
						sfile = "\""+ path +".\"*"
						mvCmd += "; touch %s;ls -l %s | while read flags i owner group crap;do chown $owner:$group %s;done;rm %s" %(tfile,tfile,sfile,tfile)
					mvCmd += '; mv "'+ path +'."* "'+ targetPath +'/"'
					association.append((service, self.moveCB))	# put in a callback for this particular movie
					self["list"].highlightService(True, "move", service)
					if config.EMC.movie_hide_mov.value:
						self["list"].removeService(service)
					self.moveRecCheck(service, targetPath)
				self.lastPlayedCheck(service)
		self["list"].resetSelection()
		if (mvCmd + rmCmd) != "":
			emcTasker.shellExecute((mvCmd + rmCmd)[2:], association)	# first move, then delete if expiration limit is 0

	def moveMovie(self):
		if self.multiSelectIdx:
			self.multiSelectIdx = None
			self.updateTitle()
		if self.browsingVLC() or self["list"].getCurrentSelDir() == "VLC servers": return
		current = self.getCurrent()
		if current is not None:
			selectedlist = self["list"].makeSelectionList()
			dialog = False
			if self["list"].currentSelIsDirectory():
				if current != selectedlist[0]:	# first selection != cursor pos?
					targetPath = self.currentPath
					if self["list"].getCurrentSelDir() == "..":
						targetPath = os.path.dirname(targetPath)
					else:
						#targetPath += "/" + self["list"].getCurrentSelDir()
						targetPath = self["list"].getCurrentSelDir()
					self.tmpSelList = selectedlist[:]
					self.execFileOp(targetPath, current, self.tmpSelList)
					self["list"].resetSelection()
				else:
					if len(selectedlist) == 1:
						self.session.open(MessageBox, _("How to move files:\nSelect some movies with the VIDEO-button, move the cursor on top of the destination directory and press yellow."), MessageBox.TYPE_ERROR, 10)
					else:
						dialog = True
			else:
				dialog = True
			if dialog:
				try:
					from Screens.LocationBox import MovieLocationBox
					if len(selectedlist)==1 and self["list"].serviceBusy(selectedlist[0]): return
					self.tmpSelList = selectedlist[:]
					self.session.openWithCallback(self.mvDirSelected, MovieLocationBox, text = _("Choose directory"), dir = str(self.currentPath)+"/", minFree = 0)
				except:
					self.session.open(MessageBox, _("How to move files:\nSelect some movies with the VIDEO-button, move the cursor on top of the destination directory and press yellow."), MessageBox.TYPE_ERROR, 10)
			emcDebugOut("[EMCMS] moveMovie")

	def moveRecCheck(self, service, targetPath):
		try:
			path = service.getPath()
			if self["list"].recControl.isRecording(path):
				self["list"].recControl.fixTimerPath(path, path.replace(self.currentPath, targetPath))
		except Exception, e:
			emcDebugOut("[EMCMS] moveRecCheck exception:\n" + str(e))

	def mvDirSelected(self, targetPath):
		if targetPath is not None:
			current = self.getCurrent()
			self.execFileOp(targetPath, current, self.tmpSelList)
			emcDebugOut("[EMCMS] mvDirSelected")

	def trashcanCreate(self, confirmed):
		try:
			os.makedirs(config.EMC.movie_trashcan_path.value)
			if self.currentPath == os.path.dirname(config.EMC.movie_trashcan_path.value):
				# reload to show the trashcan only if the current path will contain the trashcan
				self.reloadList()
		except Exception, e:
			self.session.open(MessageBox, _("Trashcan create failed. Check mounts and permissions."), MessageBox.TYPE_ERROR)
			emcDebugOut("[EMCMS] trashcanCreate exception:\n" + str(e))

	# Move all trashcan operations to a separate class
	def purgeExpired(self):
		try:
			movie_trashpath = config.EMC.movie_trashcan_path.value
			movie_homepath = config.EMC.movie_homepath.value
			if os.path.exists(movie_trashpath):
				if config.EMC.movie_trashcan_clean.value is True:
					# Trashcan cleanup
					purgeCmd = ""
					#TODO No subdirectory handling
					dirlist = os.listdir(movie_trashpath)
					for movie in dirlist:
						# Only check media files
						ext = os.path.splitext(movie)[1]
						if ext in extMedia:
							fullpath = os.path.join(movie_trashpath, movie)
							currTime = localtime()
							if os.path.exists(fullpath):
								expTime = localtime(os.stat(fullpath).st_mtime + 24*60*60*int(config.EMC.movie_trashcan_limit.value))
								if currTime > expTime:
									purgeCmd += '; rm -f "'+ os.path.splitext(fullpath)[0] +'."*'
					if purgeCmd != "":
						emcTasker.shellExecute(purgeCmd[2:])
						emcDebugOut("[EMCMS] trashcan cleanup activated")
					else:
						emcDebugOut("[EMCMS] trashcan cleanup: nothing to delete...")
				if config.EMC.movie_finished_clean.value is True:
					#TODO very slow
					# Movie folder cleanup
					# Start only if dreambox is in standby
					# No subdirectory handling
					import Screens.Standby
					if Screens.Standby.inStandby:
						mvCmd = ""
						dirlist = os.listdir(movie_homepath)
						for movie in dirlist:
							# Only check media files
							ext = os.path.splitext(movie)[1]
							if ext in extMedia:
								fullpath = os.path.join(movie_homepath, movie)
								if os.path.exists(fullpath):
									currTime = localtime()
									expTime = localtime(os.stat(fullpath).st_mtime + 24*60*60*int(config.EMC.movie_finished_limit.value))
									if currTime > expTime:
										# Check progress
										service = self["list"].getPlayerService(fullpath, movie, ext)
										progress = self["list"].getProgress(service, forceRecalc=True)
										if progress >= int(config.EMC.movie_finished_percent.value):
											# cut file extension
											fullpath = os.path.splitext(fullpath)[0]
											# create a time stamp with touch for all corresponding files
											mvCmd += '; touch "'+ fullpath +'."*'
											# move movie into the trashcan
											mvCmd += '; mv "'+ fullpath +'."* "'+ movie_trashpath +'"'
						if mvCmd != "":
							emcTasker.shellExecute(mvCmd[2:])
							emcDebugOut("[EMCMS] finished movie cleanup activated")
						else:
							emcDebugOut("[EMCMS] finished movie cleanup: nothing to move...")
			else:
				emcDebugOut("[EMCMS] trashcan cleanup: no trashcan...")
		except Exception, e:
			emcDebugOut("[EMCMS] purgeExpired exception:\n" + str(e))
