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
from Components.Sources.ServiceEvent import ServiceEvent
from Screens.Screen import Screen
from Screens.HelpMenu import HelpableScreen
from Screens.MessageBox import MessageBox
from Screens.ChoiceBox import ChoiceBox
from Tools import Notifications
from enigma import getDesktop
import os

from DelayedFunction import DelayedFunction
from EnhancedMovieCenter import _
from EMCTasker import emcTasker, emcDebugOut
from MovieCenter import MovieCenter
from MovieSelectionMenu import MovieMenu
from EMCMediaCenter import EMCMediaCenter
from RogueFileCheck import RogueFileCheck
from VlcPluginInterface import VlcPluginInterfaceSel
from CutListSupport import CutList

gMS = None


class SelectionEventInfo:
	def __init__(self):
		self["Service"] = ServiceEvent()
		self["FileName"] = Label("")
		self["FileSize"] = Label("")

	def updateEventInfo(self):
		try:
			if self["list"].currentSelIsDirectory() or self["list"].currentSelIsLatest() or self["list"].currentSelIsVlc() or self.getCurrent() is None:
				self.resetEventInfo()
			else:
				service = self.getCurrent()
				if service:
					self["Service"].newService(service)
					self["FileName"].setText(self["list"].getCurrentSelName())
					path = service.getPath()
					if os.path.exists(path):
						self["FileSize"].setText("(%d MB)" %(os.path.getsize(path)/1048576))  # 1048576 = 1024 * 1024
		except Exception, e:
			emcDebugOut("[EMCMS] updateEventInfo exception:\n" + str(e))

	def loadingEventInfo(self, loading=True):
		if loading:
			self.resetEventInfo()

	def resetEventInfo(self):
		self["Service"].newService(None)
		self["FileName"].setText("")
		self["FileSize"].setText("")


class EMCSelection(Screen, HelpableScreen, SelectionEventInfo, VlcPluginInterfaceSel):
	def __init__(self, session):
		Screen.__init__(self, session)
		SelectionEventInfo.__init__(self)
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
		
		self.wasClosed = True
		self.playerInstance = None
		self.lastPlayedMovies = None
		self.multiSelectIdx = None
		self.returnService = None
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
				"EMCOK":		(self.entrySelected,		_("Play selected movie(s)")),
#				"EMCOKL":		(self.unUsed,				"-"),
				"EMCPLAY":		(self.PlayAll,		_("Play ALL")),
				"EMCEXIT":	(self.abort, 				_("Close EMC")),
				"EMCMENU":	(self.openMenu,				_("Open menu")),
				"EMCINFO":	(self.showEventInformation,	_("Show event info")),
				"EMCINFOL":	(self.IMDbSearch,			_("IMDBSearch")),
				"EMCRed":		(self.deleteFile,			_("Delete file or empty dir")),
				"EMCGreen":	(self.toggleSort,			_("Toggle sort mode")),
				"EMCYellow":	(self.moveMovie,			_("Move selected movie(s)")),
				"EMCBlue":	(self.blueFunc,				_("Movie home / Play last (configurable)")),
#				"EMCRedL":	(self.unUsed,				"-"),
#				"EMCGreenL":	(self.unUsed,				"-"),
#				"EMCYellowL":	(self.unUsed,				"-"),
				"EMCBlueL":	(self.openBookmarks,		_("Open bookmarks")),
				"EMCLeft":	(self.pageUp,				_("Move cursor page up")),
				"EMCRight":	(self.pageDown,				_("Move cursor page down")),
				"EMCUp":	(self.moveUp,			_("Move cursor up")),
				"EMCDown":	(self.moveDown,			_("Move cursor down")),
				"EMCUpB":	self.updateAfterKeyPress,
				"EMCDownB": 	self.updateAfterKeyPress,
				"EMCBqtPlus":	(self.moveTop,			_("Move cursor to the top")),
				"EMCBqtMnus":	(self.moveEnd,			_("Move cursor to the end")),
				"EMCArrowR":	(self.CoolForward,		_("Directory forward")),
#				"EMCArrowRL":	(self.unUsed,				"-"),
				"EMCArrowL":	(self.CoolBack,			_("Directory back")),
#				"EMCArrowLL":	(self.unUsed,				"-"),
				"EMCVIDEOB":	(self.toggleSelectionList,		_("Toggle service selection")),
				"EMCVIDEOL":	(self.resetSelectionList,		_("Remove service selection")),
				"EMCAUDIO":	(self.openMenuPlugins,		_("Available plugins menu")),
#				"EMCAUDIOL":	(self.unUsed,				"-"),
				"EMCMENUL":	(self.openMenuPlugins,		_("Available plugins menu")),
				"EMCTV":		(self.triggerReloadList,			_("Reload movie file list")),
				"EMCTVL":		(self.CoolTimerList,			_("Open Timer List")),
				"EMCRADIO":	(self.toggleProgress,			_("Toggle viewed / not viewed")),
#				"EMCRADIOL":	(self.unUsed,				"-"),
				"EMCTEXT":	(self.multiSelect,			_("Start / end multiselection")),
#				"EMCTEXTL":	(self.unUsed,				"-"),
				"0": self.CoolKey0,
				"7": self.CoolAVSwitch
			}, prio=-1)
			# give them a little more priority to win over baseclass buttons
		self["actions"].csel = self
		#self["actions"].setEnabled(True)
		
		HelpableScreen.__init__(self)
		
		self.currentPathSel = config.EMC.movie_homepath.value
		self.tmpSelList = None
		self.toggle = True
		self.backStack = []
		self.forwardStack = []
		self.onExecBegin.append(self.onDialogShow)

	def CoolAVSwitch(self):
		if config.av.policy_43.value == "pillarbox":
			config.av.policy_43.value = "panscan"
		elif config.av.policy_43.value == "panscan":
			config.av.policy_43.value = "scale"
		else:
			config.av.policy_43.value = "pillarbox"

	def CoolReturn(self):
		if self.returnService:
			self.moveToService(self.returnService)
			self.returnService = None
			self.tmpSelList = None

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
		self.wasClosed = True
		self.close(None)

	def blueFunc(self):
		if config.EMC.movie_bluefunc.value == "Movie home": 
			self.changeDir(config.EMC.movie_homepath.value)
		else: self.playLast()

	def changeDir(self, path, service=None):
		# Isdir check is disabled because of VirtualViews
		#if os.path.isdir(path):
		self.currentPathSel = path
		if service:
			self.reloadList(moveToService=service)
		else:
			self.reloadList(cursorToLatest=True)

	def CoolKey0(self):
		# Movie home
		self.forwardStack = []
		#self.backStack = [] OR append
		self.backStack.append((self.currentPathSel, self["list"].getCurrent()))
		self.changeDir(config.EMC.movie_homepath.value)

	def CoolForward(self):
		if len(self.forwardStack) > 0:
			(path, service) = self.forwardStack.pop()
			self.backStack.append((self.currentPathSel, self["list"].getCurrent()))
			self.changeDir(path, service)

	def CoolBack(self):
		path = None
		service = None
		if len(self.backStack) > 0:
			# History folder
			(path, service) = self.backStack.pop()
		else:
			# Parent folder
			path = os.path.split(self.currentPathSel)[0]
		if path != self.currentPathSel:
			self.forwardStack.append((self.currentPathSel, self["list"].getCurrent()))
			self.changeDir(path, service)
		else:
			# Move cursor to top of the list
			self.moveUp()

	def setNextPathSel(self, nextdir):
		if nextdir == "..":
			# Open parent folder
			if self.currentPathSel != "" and self.currentPathSel != "/":
				# Parent folder
				nextdir = os.path.split(self.currentPathSel)[0]
			else:
				# No way to go folder up
				return
		else:
			# Open folder nextdir
			pass
		self.forwardStack = []
		self.backStack.append((self.currentPathSel, self["list"].getCurrent()))
		self.changeDir(nextdir)

	def getCurrent(self):
		return self["list"].getCurrent()

	def moveUp(self):
		self.cursorDir = -1
		self["list"].instance.moveSelection( self["list"].instance.moveUp )
		self.updateAfterKeyPress(False)

	def moveDown(self):
		self.cursorDir = 1
		self["list"].instance.moveSelection( self["list"].instance.moveDown )
		self.updateAfterKeyPress(False)

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

	def updateAfterKeyPress(self, updinfo=True):
		if self.tmpSelList:
			self.updateCoolCurrent()
		if self.multiSelectIdx:
			self.multiSelect( self.getCurrentIndex() )
		if updinfo:
			self.updateMovieInfo()

	def updateCoolCurrent(self):
		if self.returnService:
			# Service was stored for a pending update,
			# but user wants to move it,
			# so we have to update self.returnService
			if self.tmpSelList:
				self.returnService = self.getNextSelectedService(self.getCurrent(), self.tmpSelList)

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

	#def moveTo(self):
	#	self.updateMovieInfo()

	def openBookmarks(self):
		self.session.openWithCallback(self.openBookmarksCB, MovieMenu, "bookmarks", self["list"], None, self["list"].makeSelectionList(), self.currentPathSel)

	def openBookmarksCB(self, path=None):
		if path is not None:
			path = "bookmark" + path.replace("\n","")
			self.menuCallback(path)

	def menuCallback(self, selection=None):
		if selection is not None:
			if selection == "Play last": self.playLast()
			elif selection == "Movie home": self.changeDir(config.EMC.movie_homepath.value)
			elif selection == "reload": self.reloadList()
			elif selection == "ctrash": self.purgeExpired()
			elif selection == "trash": self.changeDir(config.EMC.movie_trashpath.value)
			elif selection == "delete": self.deleteFile(True)
			elif selection == "rogue": self.rogueFiles()
			elif selection == "cutlistmarker": self.removeCutListMarker()
			elif selection.startswith("bookmark"): self.changeDir(selection[8:])

	def openMenu(self):
		current = self.getCurrent()
		if self["list"].currentSelIsDirectory() or self.browsingVLC(): current = None
		self.session.openWithCallback(self.menuCallback, MovieMenu, "normal", self["list"], current, self["list"].makeSelectionList(), self.currentPathSel)

	def openMenuPlugins(self):
		current = self.getCurrent()
		if not self["list"].currentSelIsDirectory() and not self.browsingVLC():
			self.session.openWithCallback(self.menuCallback, MovieMenu, "plugins", self["list"], current, self["list"].makeSelectionList(), self.currentPathSel)

	def openScriptMenu(self):
		if self.browsingVLC():
			self.session.open(MessageBox, _("No script operation for VLC streams."), MessageBox.TYPE_ERROR)
			return
		try:
			list = []
			paths = ["/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/script/", "/etc/enigma2/EnhancedMovieCenter/"]
			
			for path in paths:
				for e in os.listdir(path):
					if not os.path.isdir(path + e):
						if e.endswith(".sh"):
							list.append([e, path+e])
						elif e.endswith(".py"):
							list.append([e, path+e])
			
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
		DelayedFunction( int(config.EMC.movie_descdelay.value), self.updateTitle )
		if not self.browsingVLC():
			DelayedFunction( int(config.EMC.movie_descdelay.value), self.updateEventInfo )

	def updateTitle(self):
		if self.multiSelectIdx:
			self.setTitle(_("*** Multiselection active ***"))
			return
		lotime = localtime()
		title = "[%02d:%02d] " %(lotime[3],lotime[4])
		if os.path.exists(self.currentPathSel+"/"):
			stat = os.statvfs(self.currentPathSel+"/")
			free = (stat.f_bavail if stat.f_bavail!=0 else stat.f_bfree) * stat.f_bsize / 1024 / 1024
			if free >= 10240:	#unit in Giga bytes if more than 10 GB free
				title = "(%d GB) " %(free/1024)
			else:
				title = "(%d MB) " %(free)
		title += self.currentPathSel + (self.currentPathSel=="")*"/"
		title = title.replace(config.EMC.movie_homepath.value+"/", ".../")
		self.setTitle(title)

	def toggleSort(self):
		if self.browsingVLC(): return
		service = self.getNextSelectedService(self.getCurrent())
		if self["list"].getAlphaSort():
			self["key_green"].text = _("Alpha sort")
			self["list"].setAlphaSort(False)
		else:
			self["key_green"].text = _("Date sort")
			self["list"].setAlphaSort(True)
		self.reloadList(service)

	def toggleSelectionList(self):
		if self.toggle == False:
			self.toggle = True
			return
		if self.toggle:
			if not self["list"].currentSelIsDirectory() and not self.browsingVLC():
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
		try:
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
		except Exception, e:
			emcDebugOut("[EMCMS] toggleProgress exception:\n" + str(e))
	
	def __toggleProgressService(self, service, preparePlayback, forceProgress=-1, first=False):
		try:
			if service is None:
				return
			
			# Cut file handling
			path = service.getPath()
			cuts  = path +".cuts"
			cutsr = path +".cutsr"
			if os.path.exists(cutsr) and not os.path.exists(cuts):
				# Rename file - to catch all old EMC revisions
				os.rename(cutsr, cuts)	
				
			# All calculations are done in seconds
			cuts = CutList( service )
			last = cuts.getCutListLast()
			len = self["list"].getLengthOfService(service)
			progress, len = self["list"].getProgress(service, len=len, last=last, forceRecalc=True, cuts=cuts)
			
			if not preparePlayback:
				if first:
					if progress < 100: forceProgress = 50		# force next state 100
					else: forceProgress = 100 							# force next state 0
				if forceProgress > -1:
					progress = forceProgress
			
			if not preparePlayback:
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
		except Exception, e:
			emcDebugOut("[EMCMS] toggleProgressService exception:\n" + str(e))
			return None
	
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
		evt = self["list"].getCurrentEvent()
		if evt:
			self.session.open(EventViewSimple, evt, ServiceReference(self.getCurrent()))

	def initCursor(self):
		if self.playerInstance is None:	# detect movie player state (None == not open)
			if config.EMC.moviecenter_gotonewest.value:
				self.cursorToLatest()
			else:
				self.updateMovieInfo()
		else:
			if config.EMC.moviecenter_gotonewestp.value:
				self.cursorToLatest()
			else:
				service = self.playerInstance.currentlyPlayedMovie()
				if service is not None:
					self.moveToService(service)
				else:
					self.updateMovieInfo()

	def cursorToLatest(self):
		if config.EMC.moviecenter_reversed.value:
			self.moveToIndex(len(self["list"]())-1)
		else:
			self.moveToIndex(0)

	def onDialogShow(self):
		if self.wasClosed:
			self.wasClosed = False
			#self["actions"].setEnabled(True)
			self["key_red"].text = _("Delete")
			
			if config.EMC.needsreload.value:
				self["list"].setAlphaSort(config.EMC.CoolStartAZ.value)
			
			if self["list"].getAlphaSort():
				self["key_green"].text = _("Date sort")
			else:
				self["key_green"].text = _("Alpha sort")
				
			self["key_yellow"].text = _("Move")
			self["key_blue"].text = _(config.EMC.movie_bluefunc.value)
			
			if config.EMC.needsreload.value:
				config.EMC.needsreload.value = False
				DelayedFunction(50, self.initList)
			elif self.returnService:
				# Move to last played movie
				self.CoolReturn()
			else:
				if config.EMC.movie_reload.value or self["list"].newRecordings or len(self["list"]) == 0:
					DelayedFunction(50, self.initList)
				else:
					self.initCursor()

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
			curSerRef = None
		elif len(self["list"]) == 0:
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

	def removeCutListMarker(self):
		if self.browsingVLC(): return
		current = self.getCurrent()	# make sure there is atleast one entry in the list
		if current is not None:
			selectedlist = self["list"].makeSelectionList()[:]
			for service in selectedlist:
				path = service.getPath()
				ext = os.path.splitext(path)[1].lower()
				cuts = CutList( service )
				cuts.removeMarksCutList()
				self["list"].unselectService(service)
			emcDebugOut("[EMCMS] cut list marker removed permanently")

	def mountpoint(self, path, first=True):
		if first: path = os.path.realpath(path)
		if os.path.ismount(path) or len(path)==0: return path
		return self.mountpoint(os.path.split(path)[0], False)

	def deleteFile(self, permanently=False):
		if self.multiSelectIdx:
			self.multiSelectIdx = None
			self.updateTitle()
		if self.browsingVLC(): return
		self.permanentDel  = permanently or int(config.EMC.movie_trashcan_limit.value) == 0
		self.permanentDel |= self.currentPathSel == config.EMC.movie_trashpath.value
		self.permanentDel |= self.mountpoint(self.currentPathSel) != self.mountpoint(config.EMC.movie_trashpath.value)
		current = self.getCurrent()	# make sure there is atleast one entry in the list
		if current is not None:
			selectedlist = self["list"].makeSelectionList()[:]
			if self["list"].currentSelIsDirectory() and len(selectedlist) == 1 and current==selectedlist[0]:
				# try to delete an empty directory
				if self.delPathSel(self["list"].getCurrentSelDir()):
					self["list"].removeService(selectedlist[0])
			else:
				if self["list"].serviceBusy(selectedlist[0]): return
				if selectedlist and len(selectedlist)>0:
					self.recsToStop = []
					self.remRecsToStop = False
					for service in selectedlist:
						path = service.getPath()
						if self["list"].recControl.isRecording(path):
							self.recsToStop.append(path)
						if self["list"].recControl.isRemoteRecording(path):
							self.remRecsToStop = True
					if len(self.recsToStop)>0:
						self.stopRecordQ()
					else:
						self.deleteMovieQ(selectedlist, self.remRecsToStop)

	def deleteMovieQ(self, selectedlist, remoteRec):
		try:
			self.tmpSelList = selectedlist[:]
			self.delCurrentlyPlaying = False
			rm_add = ""
			if remoteRec:
				rm_add = _(" Deleting remotely recorded and it will display an rec-error dialog on the other DB.") + "\n"
				
			if self.playerInstance is not None:
				nowPlaying = self.playerInstance.currentlyPlayedMovie().getPath().split("/")[-1]
				for s in selectedlist:
					if s.getPath().split("/")[-1] == nowPlaying:
						self.delCurrentlyPlaying = True
						break
					
			entrycount = len(selectedlist)
			delStr = _("Delete") + _(" permanently")*self.permanentDel
			if entrycount == 1:
				service = selectedlist[0]
				#name = "\n" + self["list"].getFileNameOfService(service).replace(".ts","")
				name = os.path.splitext(self["list"].getFileNameOfService(service))[0]
				if not self.delCurrentlyPlaying:
					if config.EMC.movie_trashcan_validation.value or int(config.EMC.movie_trashcan_limit.value) == 0 or self.permanentDel:
						self.session.openWithCallback(self.deleteMovieConfimation, MessageBox, delStr + "?\n" + rm_add + name, MessageBox.TYPE_YESNO)
					else:
						self.deleteMovieConfimation(True)
				else:
					self.session.openWithCallback(self.deleteMovieConfimation, MessageBox, delStr + _(" currently played?") + "\n" + rm_add + name, MessageBox.TYPE_YESNO)
			else:
				if entrycount > 1:
					movienames = ""
					i = 0
					for service in selectedlist:
						if i >= 5 and entrycount > 5:	# show only 5 entries in the file list
							movienames += "..."
							break
						i += 1
						#name = self["list"].getFileNameOfService(service).replace(".ts","")	# TODO: None check
						name = os.path.splitext(self["list"].getFileNameOfService(service))[0]
						if len(name) > 48:
							name = name[:48] + "..."	# limit the name string
						movienames += name + "\n"*(i<entrycount)
					if not self.delCurrentlyPlaying:
						if config.EMC.movie_trashcan_validation.value or int(config.EMC.movie_trashcan_limit.value) == 0 or self.permanentDel:
							self.session.openWithCallback(self.deleteMovieConfimation, MessageBox, delStr + _(" all selected video files?") + "\n" + rm_add + movienames, MessageBox.TYPE_YESNO)
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
			delete = int(config.EMC.movie_trashcan_limit.value)==0 or self.permanentDel
			if os.path.exists(config.EMC.movie_trashpath.value) or delete:
				# if the user doesn't want to keep the movies in the trash, purge immediately
				self.execFileOp(config.EMC.movie_trashpath.value, current, self.tmpSelList, op="delete", purgeTrash=delete)
				for x in self.tmpSelList:
					self.lastPlayedCheck(x)
				self["list"].resetSelection()
			elif not delete:
				self.session.openWithCallback(self.trashcanCreate, MessageBox, _("Delete failed because the trashcan directory does not exist. Attempt to create it now?"), MessageBox.TYPE_YESNO)
			emcDebugOut("[EMCMS] deleteMovie")

	def delPathSel(self, path):
		if path != "..":
			if os.path.islink(path):
				emcTasker.shellExecute("rm -f '" + path + "'")
				return True
			elif os.path.exists(path):
				if len(os.listdir(path))>0:
					self.session.open(MessageBox, _("Directory is not empty."), MessageBox.TYPE_ERROR, 10)
				else:
					emcTasker.shellExecute('rmdir "' + path +'"')
					return True
		else:
			self.session.open(MessageBox, _("Cannot delete the parent directory."), MessageBox.TYPE_ERROR, 10)
		return False

	def rogueFiles(self):
		check = RogueFileCheck(config.EMC.movie_homepath.value, config.EMC.movie_trashpath.value)
		emcTasker.shellExecute( check.getScript(config.EMC.movie_trashpath.value) )
		self.session.open(MessageBox, check.getStatistics(), MessageBox.TYPE_INFO)

	def setPlayerInstance(self, player):
		try:
			self.playerInstance = player
		except Exception, e:
			emcDebugOut("[EMCMS] setPlayerInstance exception:\n" + str(e))

	def openPlayer(self, playlist, playall=False):
		#self["actions"].setEnabled(False)
		# Force update of event info after playing movie 
		self.resetEventInfo()
		# Save service 
		self.returnService = self.getCurrent()
		# force a copy instead of an reference!
		self.lastPlayedMovies = playlist[:]
		playlistcopy = playlist[:]
		# Start Player
		if self.playerInstance is None:
			Notifications.AddNotification(EMCMediaCenter, playlistcopy, self, playall)
		else:
			#DelayedFunction(10, self.playerInstance.movieSelected, playlist, playall)
			self.playerInstance.movieSelected(playlist, playall)
		self.wasClosed = True
		self.close(None)

	def entrySelected(self, playall=False):
		try:
			current = self.getCurrent()
			if current is not None:
				if self["list"].currentSelIsLatest():
					emcDebugOut("[EMCMS] entrySelected currentSelIsLatest")
					entry = "Latest Recordings"
					self.setNextPathSel(entry)
				elif self["list"].currentSelIsDirectory(): # or currentSelIsVlc or currentSelIsVlcDir
					# Open folder and reload movielist
					emcDebugOut("[EMCMS] entrySelected currentSelIsDirectory")
					self.setNextPathSel( self["list"].getCurrentSelDir() )
				elif self["list"].currentSelIsVlc():
					emcDebugOut("[EMCMS] entrySelected currentSelIsVlc")
					entry = self["list"].list[ self["list"].getCurrentIndex() ]
					self.vlcMovieSelected(entry)
				else:
					emcDebugOut("[EMCMS] entrySelected else")
					playlist = self["list"].makeSelectionList()
					if not self["list"].serviceBusy(playlist[0]):
						self.openPlayer(playlist, playall)
					else:
						self.session.open(MessageBox, _("File not available."), MessageBox.TYPE_ERROR, 10)
		except Exception, e:
			emcDebugOut("[EMCMS] entrySelected exception:\n" + str(e))

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
		env += " EMC_TRASH=%s"%config.EMC.movie_trashpath.value
		env += " EMC_TRASH_DAYS=%s"%int(config.EMC.movie_trashcan_limit.value)

		current = self["list"].getCurrentSelPath().replace(" ","\ ")
		if os.path.exists(result[1]):
			if result[1].endswith(".sh"):
				emcTasker.shellExecute("%s; sh %s %s %s" %(env, result[1], self.currentPathSel, current))
			elif result[1].endswith(".py"):
				emcTasker.shellExecute("%s; python %s %s %s" %(env, result[1], self.currentPathSel, current))

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
		if loading:
			self["list"].hide()
			self["wait"].show()
		else:
			self["wait"].hide()
			self["list"].show()
		self.loadingEventInfo(loading)

	def initList(self):
		self.reloadList(initCursor=True)

	def triggerReloadList(self):
		self.reloadList(moveToService=self.getCurrent())

	def reloadList(self, moveToService=None, initCursor=False, cursorToLatest=False):
		self.multiSelectIdx = None
		if config.EMC.moviecenter_loadtext.value:
			self.loading()
		DelayedFunction(5, self.__reloadList, moveToService, initCursor, cursorToLatest)

	def __reloadList(self, moveToService=None, initCursor=False, cursorToLatest=False):
		try:
			if self.currentPathSel is None:
				emcDebugOut("[EMCMS] reloadList: currentPathSel is None")
				return
			path = self.currentPathSel
			if os.path.exists(path) or path.find("Latest Recordings")>-1 or path.find("VLC servers")>-1 or self.browsingVLC():
				emcDebugOut("[EMCMS] __reloadList")
				self["list"].reload(path + "/"*(path != "/"))
			if initCursor:
				self.initCursor()
			elif cursorToLatest:
				self.cursorToLatest()
			else:
				self.moveToService(moveToService)
		except Exception, e:
			emcDebugOut("[EMCMS] reloadList exception:\n" + str(e))
		finally:
			if config.EMC.moviecenter_loadtext.value:
				self.loading(False)

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

	def execFileOp(self, targetPath, current, selectedlist, op="move", purgeTrash=False):
		self.returnService = self.getNextSelectedService(current, selectedlist)
		mvCmd = ""
		rmCmd = ""
		association = []
		for service in selectedlist:
			name = os.path.splitext( self["list"].getFileNameOfService(service) )[0]
			if name is not None:
				if op=="delete":	# target == trashcan
					if purgeTrash or self.currentPathSel == targetPath or self.mountpoint(self.currentPathSel) != self.mountpoint(targetPath):
						# direct delete from the trashcan or network mount (no copy to trashcan from different mountpoint)
						rmCmd += '; rm -f "'+ self.currentPathSel +"/"+ name +'."*'
					else:
						# create a time stamp with touch
						mvCmd += '; touch "'+ self.currentPathSel +"/"+ name +'."*'
						# move movie into the trashcan
						mvCmd += '; mv "'+ self.currentPathSel +"/"+ name +'."* "'+ targetPath +'/"'
					association.append((service, self.delCB))	# put in a callback for this particular movie
					self["list"].highlightService(True, "del", service)
					if config.EMC.movie_hide_del.value:
						self["list"].removeService(service)
				elif op == "move":
					#if self.mountpoint(self.currentPathSel) == self.mountpoint(targetPath):
					#	#self["list"].removeService(service)	# normal direct move
					#	pass
					#else:
					# different self.mountpoint? -> reset user&group
					if self.mountpoint(targetPath) != self.mountpoint(config.EMC.movie_homepath.value):		# CIFS to HDD is ok!
						# need to change file ownership to match target filesystem file creation
						tfile = targetPath + "/owner_test"
						sfile = "\""+ self.currentPathSel +"/"+ name +".\"*"
						mvCmd += "; touch %s;ls -l %s | while read flags i owner group crap;do chown $owner:$group %s;done;rm %s" %(tfile,tfile,sfile,tfile)
					mvCmd += '; mv "'+ self.currentPathSel +"/"+ name +'."* "'+ targetPath +'/"'
					association.append((service, self.moveCB))	# put in a callback for this particular movie
					self["list"].highlightService(True, "move", service)
					if config.EMC.movie_hide_mov.value:
						self["list"].removeService(service)
					self.moveRecCheck(service, targetPath)
				self.lastPlayedCheck(service)
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
					targetPath = self.currentPathSel
					if self["list"].getCurrentSelDir() == "..":
						targetPath = os.path.split(targetPath)[0]
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
					from Screens.LocationBox import LocationBox
					if len(selectedlist)==1 and self["list"].serviceBusy(selectedlist[0]): return
					self.tmpSelList = selectedlist[:]
					self.session.openWithCallback(self.mvDirSelected, LocationBox, windowTitle= _("Select Location"), text = _("Choose directory"),
						filename = "", currDir = self.currentPathSel+"/", minFree = 0)
				except:
					self.session.open(MessageBox, _("How to move files:\nSelect some movies with the VIDEO-button, move the cursor on top of the destination directory and press yellow."), MessageBox.TYPE_ERROR, 10)
			emcDebugOut("[EMCMS] moveMovie")

	def moveRecCheck(self, service, targetPath):
		try:
			path = service.getPath()
			if self["list"].recControl.isRecording(path):
				self["list"].recControl.fixTimerPath(path, path.replace(self.currentPathSel, targetPath))
		except Exception, e:
			emcDebugOut("[EMCMS] moveRecCheck exception:\n" + str(e))

	def mvDirSelected(self, targetPath):
		if targetPath is not None:
			current = self.getCurrent()
			self.execFileOp(targetPath, current, self.tmpSelList)
			self["list"].resetSelection()
			emcDebugOut("[EMCMS] mvDirSelected")

	def trashcanCreate(self, confirmed):
		try:
			os.makedirs(config.EMC.movie_trashpath.value)
			# reload to show the trashcan
			self.reloadList()
		except Exception, e:
			self.session.open(MessageBox, _("Trashcan create failed. Check mounts and permissions."), MessageBox.TYPE_ERROR)
			emcDebugOut("[EMCMS] trashcanCreate exception:\n" + str(e))

	def purgeExpired(self):
		try:
			if os.path.exists(config.EMC.movie_trashpath.value):
				if config.EMC.movie_trashcan_clean.value is True:
					# trashcan cleanup
					purgeCmd = ""
					dirlist = os.listdir(config.EMC.movie_trashpath.value)
					for movie in dirlist:
						fullpath = config.EMC.movie_trashpath.value +"/"+ movie
						currTime = localtime()
						expTime = localtime(os.stat(fullpath).st_mtime + 24*60*60*int(config.EMC.movie_trashcan_limit.value))
						if currTime > expTime:
							print "EMC purge " + str(fullpath)
							#purgeCmd += "; rm -f \"%s\"*" % fullpath.replace(".*","")
							#purgeCmd += "; rm -f \"%s\"*" % os.path.splitext(fullpath)[0]
							purgeCmd += '; rm -f "'+ os.path.splitext(fullpath)[0] +'."*'
					if purgeCmd != "":
						emcTasker.shellExecute(purgeCmd[2:])
						emcDebugOut("[EMCMS] trashcan cleanup activated")
					else:
						emcDebugOut("[EMCMS] trashcan cleanup: nothing to delete...")
				if config.EMC.movie_finished_clean.value is True:
					# movie folder cleanup
					import Screens.Standby
					if Screens.Standby.inStandby:
						mvCmd = ""
						dirlist = os.listdir(config.EMC.movie_homepath.value)
						for movie in dirlist:
							fullpath = config.EMC.movie_homepath.value +"/"+ movie
							if os.path.exists(fullpath):
								currTime = localtime()
								#print "EMC fullpath " + str(fullpath)
								expTime = localtime(os.stat(fullpath).st_mtime + 24*60*60*int(config.EMC.movie_finished_limit.value))
								if currTime > expTime:
									# Check progress
									#print "EMC move " + str(fullpath) + " " + str(movie)
									service = self["list"].getPlayerService(fullpath, movie)
									#print "EMC service " + str(service)
									progress, len = self["list"].getProgress(service, forceRecalc=True)
									#print "EMC progress " + str(progress)
									if progress >= int(config.EMC.movie_finished_percent.value):
										print "EMC progress > finished " + str(fullpath)
										file = os.path.splitext(fullpath)[0]
										# create a time stamp with touch
										mvCmd += '; touch "'+ file +'."*'
										# move movie into the trashcan
										#old mvCmd += "; mv \"%s\"*" % fullpath.replace(".*","") #"'+ targetPath +'/"'
										mvCmd += '; mv "'+ file +'."* "'+ config.EMC.movie_trashpath.value +'/"'
						if mvCmd != "":
							emcTasker.shellExecute(mvCmd[2:])
							emcDebugOut("[EMCMS] finished movie cleanup activated")
						else:
							emcDebugOut("[EMCMS] finished movie cleanup: nothing to move...")
			else:
				emcDebugOut("[EMCMS] trashcan cleanup: no trashcan...")
		except Exception, e:
			emcDebugOut("[EMCMS] purgeExpired exception:\n" + str(e))
