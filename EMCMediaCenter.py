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

import os

from Components.config import *
from Components.ActionMap import ActionMap, NumberActionMap, HelpableActionMap
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.ServiceEventTracker import ServiceEventTracker, InfoBarBase
from enigma import eTimer, iPlayableService, iServiceInformation, eServiceReference, iServiceKeys, getDesktop
from Screens.Screen import Screen
from Screens.InfoBarGenerics import *
from Screens.InfoBar import MoviePlayer, InfoBar
from Screens.MessageBox import MessageBox
from Screens.HelpMenu import HelpableScreen
from Components.ServiceEventTracker import ServiceEventTracker, InfoBarBase
from Tools.Directories import fileExists, resolveFilename, SCOPE_LANGUAGE, SCOPE_PLUGINS

from EnhancedMovieCenter import _
from EMCTasker import emcDebugOut
from DelayedFunction import DelayedFunction
from CutListSupport import CutList
from InfoBarSupport import InfoBarSupport

from MovieCenter import serviceIdDVD
global serviceIdDVD

dvdPlayerPlg = "%s%s"%(resolveFilename(SCOPE_PLUGINS), "Extensions/DVDPlayer/plugin.py")


class EMCMediaCenter( CutList, Screen, HelpableScreen, InfoBarSupport ):
	
	ENABLE_RESUME_SUPPORT = True
	ALLOW_SUSPEND = True
	
	def __init__(self, session, playlist, recordings, playall=False):
		
		# Attention because of the borg pattern:
		# The CutList must be initialized very first  
		CutList.__init__(self)
		Screen.__init__(self, session)
		HelpableScreen.__init__(self)
		InfoBarSupport.__init__(self)
		
		# Skin
		self.skinName = "EMCMediaCenter"
		skin = None
		CoolWide = getDesktop(0).size().width()
		if CoolWide == 720:
			skin = "/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/CoolSkin/EMCMediaCenter_720.xml"
		elif CoolWide == 1024:
			skin = "/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/CoolSkin/EMCMediaCenter_1024.xml"
		elif CoolWide == 1280:
			skin = "/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/CoolSkin/EMCMediaCenter_1280.xml"
		if skin:
			Cool = open(skin)
			self.skin = Cool.read()
			Cool.close()
		
		# Events
		self.__event_tracker = ServiceEventTracker(screen=self, eventmap=
			{
		# Disabled for tests
		# If we enable them, the sound will be delayed for about 2 seconds ?
				iPlayableService.evStart: self.__serviceStarted,
				iPlayableService.evStopped: self.__serviceStopped,
				#iPlayableService.evUser: self.__timeUpdated,
				#iPlayableService.evUser+1: self.__statePlay,
				#iPlayableService.evUser+2: self.__statePause,
				iPlayableService.evUser+3: self.__osdFFwdInfoAvail,
				iPlayableService.evUser+4: self.__osdFBwdInfoAvail,
				#iPlayableService.evUser+5: self.__osdStringAvail,
				iPlayableService.evUser+6: self.__osdAudioInfoAvail,
				iPlayableService.evUser+7: self.__osdSubtitleInfoAvail,
				iPlayableService.evUser+8: self.__chapterUpdated,
				iPlayableService.evUser+9: self.__titleUpdated,
				iPlayableService.evUser+11: self.__menuOpened,
				iPlayableService.evUser+12: self.__menuClosed,
				iPlayableService.evUser+13: self.__osdAngleInfoAvail
			})
			
			# Keymap
	#		self["SeekActions"] = HelpableActionMap(self, "InfobarSeekActions", 							-1 higher priority
	#		self["MovieListActions"] = HelpableActionMap(self, "InfobarMovieListActions", 		0
	#		self["ShowHideActions"] = ActionMap( ["InfobarShowHideActions"] ,  								0
	#		self["EPGActions"] = HelpableActionMap(self, "InfobarEPGActions",									0
	#		self["CueSheetActions"] = HelpableActionMap(self, actionmap,											1 lower priority
	#		self["InstantExtensionsActions"] = HelpableActionMap(self, "InfobarExtensions", 	1 lower priority
	#		self["NumberActions"] = NumberActionMap( [ "NumberActions"],											0 Set by EMC to 2 very lower priority 
	#		self["TeletextActions"] = HelpableActionMap(self, "InfobarTeletextActions",				0 Set by EMC to 2 very lower priority 
	#		self["MenuActions"] = HelpableActionMap(self, "InfobarMenuActions",  							0 Set by EMC to 2 very lower priority 
		if config.EMC.movie_exit.value:
			self["actions"] = HelpableActionMap(self, "CoolPlayerActions",
				{
					"leavePlayer":	(self.leavePlayer, 		_("Stop playback")),
					"EMCGreen":	(self.CoolAVSwitch,			_("Format AVSwitch")),
				}) # default priority
		else:
			self["actions"] = HelpableActionMap(self, "CoolPlayerActions2",
				{
					"leavePlayer":	(self.leavePlayer, 		_("Stop playback")),
					"EMCGreen":	(self.CoolAVSwitch,			_("Format AVSwitch")),
				}) # default priority
		
		self["DVDPlayerPlaybackActions"] = HelpableActionMap(self, "EMCDVDPlayerActions",
			{
				"dvdMenu": (self.enterDVDMenu, _("show DVD main menu")),
				#"showInfo": (self.showInfo, _("toggle time, chapter, audio, subtitle info")),
				"nextChapter": (self.nextChapter, _("forward to the next chapter")),
				"prevChapter": (self.prevChapter, _("rewind to the previous chapter")),
				"nextTitle": (self.nextTitle, _("jump forward to the next title")),
				"prevTitle": (self.prevTitle, _("jump back to the previous title")),
				"dvdAudioMenu": (self.enterDVDAudioMenu, _("(show optional DVD audio menu)")),
				"AudioSelection": (self.audioSelection, _("Select audio track")),	# InfoBarAudioSelection
				"nextAudioTrack": (self.nextAudioTrack, _("switch to the next audio track")),
				"nextSubtitleTrack": (self.nextSubtitleTrack, _("switch to the next subtitle language")),
				"nextAngle": (self.nextAngle, _("switch to the next angle")),
			}, 1) # lower priority
		# Only enabled if playing a dvd
		self["DVDPlayerPlaybackActions"].setEnabled(False)
		
		self["DVDMenuActions"] = ActionMap(["WizardActions"],
			{
				"left": self.keyLeft,
				"right": self.keyRight,
				"up": self.keyUp,
				"down": self.keyDown,
				"ok": self.keyOk,
				"back": self.keyBack,
			}, 2) # lower priority
		# Only enabled during DVD Menu
		self["DVDMenuActions"].setEnabled(False)
		
		self["GeneralPlayerPlaybackActions"] = HelpableActionMap(self, "EMCGeneralPlayerActions",
			{
				"showExtensions": (self.showExtensionSelection, _("view extensions...")),	# InfobarExtensions
			}, 2) # lower priority
		
		self["MenuActions"].prio = 2
		self["TeletextActions"].prio = 2
		self["NumberActions"].prio = 2
		
		# DVD Player
		self["audioLabel"] = Label("")
		self["subtitleLabel"] = Label("")
		self["angleLabel"] = Label("")
		self["chapterLabel"] = Label("")
		self["anglePix"] = Pixmap()
		self["anglePix"].hide()
		self.last_audioTuple = None
		self.last_subtitleTuple = None
		self.last_angleTuple = None
		self.totalChapters = 0
		self.currentChapter = 0
		self.totalTitles = 0
		self.currentTitle = 0
		self.in_menu = False
		self.dvdScreen = None
		
		# Further initialization
		self.firstStart = False
		self.stopped = False
		self.closedByDelete = False
		self.playerOpenedList = False
		
		self.playInit(playlist, recordings, playall)
		
		# Dialog Events
		self.onShown.append(self.__onShow)  # Don't use onFirstExecBegin() it will crash
		self.onClose.insert(0, self.__playerClosed)
		self.onClose.append(self.__onClose)

	def CoolAVSwitch(self):
		if config.av.policy_43.value == "pillarbox":
			config.av.policy_43.value = "panscan"
		elif config.av.policy_43.value == "panscan":
			config.av.policy_43.value = "scale"
		else:
			config.av.policy_43.value = "pillarbox"

	def playInit(self, playlist, recordings, playall):
		self.lastservice = self.session.nav.getCurrentlyPlayingServiceReference()
		self.playlist = playlist
		self.playall = playall
		self.playcount = -1
		self.recordings = recordings
		self.firstStart = False
		self.service = None
		self.recordings.setPlayerInstance(self)

	def __onShow(self):
		if self.firstStart:
			# Avoid new playback if the user switches between MovieSelection and MoviePlayer
			return
		self.firstStart = True
		self.evEOF()	# begin playback

	def __playerClosed(self):
		if self.service:
			self.updateCutList( self.service, self.getSeekPlayPosition(), self.getSeekLength() )

	def __onClose(self):
	#def __del__(self): needs stopped, closed, playeropened as globals
		self.session.nav.playService(self.lastservice)
		try:
			from MovieSelection import gMS
			if self.stopped:
				emcDebugOut("[EMCPlayer] Player closed by user")
				if config.EMC.movie_reopen.value:
					DelayedFunction(80, gMS.session.execDialog, gMS)		# doesn't crash Enigma2 subtitle functionality
			elif self.closedByDelete:
				emcDebugOut("[EMCPlayer] closed due to file delete")
				DelayedFunction(80, gMS.session.execDialog, gMS)		# doesn't crash Enigma2 subtitle functionality
			else:
				emcDebugOut("[EMCPlayer] closed due to playlist EOF")
				if self.playerOpenedList or config.EMC.movie_reopenEOF.value: # did the player close while movie list was open?
					DelayedFunction(80, gMS.session.execDialog, gMS)		# doesn't crash Enigma2 subtitle functionality
			self.playerOpenedList = False
		except Exception, e:
			emcDebugOut("[EMCPlayer] __del__ exception:\n" + str(e))

	def evEOF(self, needToClose=False):
		# see if there are more to play
		if self.playall:
			# Play All
			try:
				self.playcount = -1
				self.playlist = [ self.playall.next() ]
			except StopIteration:
				self.playall = None
				self.playlist = []
			
		if (self.playcount + 1) < len(self.playlist):
			self.playcount += 1
			service = self.playlist[self.playcount]
			path = service and service.getPath()
			if os.path.exists(path): # or True: # is vlc
				
				# rename .cutsr to .cuts if user has toggled it
				self.recordings.toggleProgress(service, True)
				self.service = service
				
				if service and service.type == serviceIdDVD:
					# Only import DVDPlayer, if we want to play a DVDPlayer format
					if fileExists(dvdPlayerPlg) or fileExists("%sc"%dvdPlayerPlg):
						try:
							from Plugins.Extensions.DVDPlayer import servicedvd # load c++ part of dvd player plugin
						except:
							pass
						from Plugins.Extensions.DVDPlayer.plugin import DVDOverlay
						if not self.dvdScreen:
							self.dvdScreen = self.session.instantiateDialog(DVDOverlay)
					else:
						self.session.open(MessageBox, _("No DVD-Player found!"), MessageBox.TYPE_ERROR, 10)
						self.leavePlayer(True)
						return
					self["TeletextActions"].setEnabled(False)
					self["DVDPlayerPlaybackActions"].setEnabled(True)
				else:
					if self.dvdScreen:
						self.dvdScreen.close()
						self.dvdScreen = None
					else:
						self.dvdScreen = None
					self["TeletextActions"].setEnabled(True)
					self["DVDPlayerPlaybackActions"].setEnabled(False)
				
				# Is this really necessary 
				# TEST for M2TS Audio problem
				#self.session.nav.stopService() 
				
				# Start playing movie
				self.session.nav.playService(service)
				
				#Temp only
				#self.service = self.session.nav.getCurrentService()
				
				if service and service.type == serviceIdDVD:
					# Seek will cause problems with DVDPlayer!
					# ServiceDVD needs this to start
					subs = self.getServiceInterface("subtitle")
					if subs and self.dvdScreen:
						subs.enableSubtitles(self.dvdScreen.instance, None)
				else:
					# TEST for M2TS Audio problem
					#self.setSeekState(InfoBarSeek.SEEK_STATE_PLAY)
					#TODO Do we need this
					#self.doSeek(0)
					#TODO AutoSelect subtitle for DVD Player is not implemented yet
					DelayedFunction(200, self.setAudioTrack)
					DelayedFunction(400, self.setSubtitleState, True)
			else:
				self.session.open(MessageBox, _("Skipping movie, the file does not exist.\n\n") + service.getPath(), MessageBox.TYPE_ERROR, 10)
				self.evEOF(needToClose)
				
		else:
			if needToClose or config.usage.on_movie_eof.value != "pause":
				self.closedByDelete = needToClose
				self.leavePlayer(False)

	def leavePlayer(self, stopped=True):
		self.setSubtitleState(False)
		self.stopped = stopped
		if self.playerOpenedList and not stopped:	# for some strange reason "not stopped" has to be checked to avoid a bug (???)
			self.recordings.close(None)
		#else:
		if self.dvdScreen:
			self.dvdScreen.close()
		# Possible Problem: Avoid GeneratorExit exception
		#if self.playall:
		#	playall.close()
		self.recordings.setPlayerInstance(None)
		#self.close(self.lastservice)
		self.close()

	def removeFromPlaylist(self, deletedlist):
		callEOF = False
		for x in deletedlist:
			xp = x.getPath().split("/")[-1]
			if xp == self.service.getPath().split("/")[-1]:
				callEOF = True
			for p in self.playlist:
				if xp == p.getPath().split("/")[-1]:
					self.playlist.remove(p)
		if callEOF:
			self.playcount -= 1	# need to go one back since the current was removed
			self.evEOF(True)	# force playback of the next movie or close the player if none left

	def currentlyPlayedMovie(self):
		return self.service

	def movieSelected(self, playlist, playall=False):
		self.playerOpenedList = False
		if playlist is not None and len(playlist) > 0:
			self.playcount = -1
			self.playlist = playlist
			self.playall = playall
			self.evEOF()	# start playback of the first movie

	##############################################################################
	## Audio and Subtitles
	def tryAudioEnable(self, alist, match, tracks):
		index = 0
		for e in alist:
			if e.find(match) >= 0:
				emcDebugOut("[EMCPlayer] audio track match: " + str(e))
				tracks.selectTrack(index)
				return True
			index += 1
		return False

	def setAudioTrack(self):
		try:
			if not config.EMC.autoaudio.value: return
			from Tools.ISO639 import LanguageCodes as langC
			service = self.session.nav.getCurrentService()
			#tracks = service and service.audioTracks()
			tracks = service and self.getServiceInterface("audioTracks")
			nTracks = tracks and tracks.getNumberOfTracks() or 0
			if not nTracks: return
			trackList = []
			for i in xrange(nTracks):
				audioInfo = tracks.getTrackInfo(i)
				lang = audioInfo.getLanguage()
				if langC.has_key(lang):
					lang = langC[lang][0]
				desc = audioInfo.getDescription()
				trackList += [str(lang) + " " + str(desc)]
			for audiolang in [config.EMC.audlang1.value, config.EMC.audlang2.value, config.EMC.audlang3.value]:
				if self.tryAudioEnable(trackList, audiolang, tracks): break
		except Exception, e:
			emcDebugOut("[EMCPlayer] audioTrack exception:\n" + str(e))

	def trySubEnable(self, slist, match):
		for e in slist:
			if match == e[2]:
				emcDebugOut("[EMCPlayer] subtitle match: " + str(e))
				if self.selected_subtitle != e[0]:
					self.subtitles_enabled = False
					self.selected_subtitle = e[0]
					self.subtitles_enabled = True
					return True
		return False
	
	def setSubtitleState(self, enabled):
		try:
			if not config.EMC.autosubs.value or not enabled: return
			from Tools.ISO639 import LanguageCodes as langC
			#s = self.getCurrentServiceSubtitle()
			subs = self.getServiceInterface("subtitle")
			lt = [ (e, (e[0] == 0 and "DVB" or e[0] == 1 and "TXT" or "???")) for e in (subs and subs.getSubtitleList() or []) ]
			l = [ [e[0], e[1], langC.has_key(e[0][4]) and langC[e[0][4]][0] or e[0][4] ] for e in lt ]
			for sublang in [config.EMC.sublang1.value, config.EMC.sublang2.value, config.EMC.sublang3.value]:
				if self.trySubEnable(l, sublang): break
		except Exception, e:
			emcDebugOut("[EMCPlayer] setSubtitleState exception:\n" + str(e))

	##############################################################################
	## DVD Player keys
	def keyLeft(self):
		self.sendKey(iServiceKeys.keyLeft)

	def keyRight(self):
		self.sendKey(iServiceKeys.keyRight)

	def keyUp(self):
		self.sendKey(iServiceKeys.keyUp)

	def keyDown(self):
		self.sendKey(iServiceKeys.keyDown)

	def keyOk(self):
		self.sendKey(iServiceKeys.keyOk)
			
	def keyBack(self):
		self.leavePlayer()

	def nextAudioTrack(self):
		self.sendKey(iServiceKeys.keyUser)

	def nextSubtitleTrack(self):
		self.sendKey(iServiceKeys.keyUser+1)
		if self.dvdScreen:
			# Force show dvd screen
			#self.dvdScreen.hide()
			self.dvdScreen.show()

	def enterDVDAudioMenu(self):
		self.sendKey(iServiceKeys.keyUser+2)

	def nextChapter(self):
		if self.sendKey(iServiceKeys.keyUser+3):
			if config.usage.show_infobar_on_skip.value:
				# InfoBarSeek
				self.showAfterSeek()

	def prevChapter(self):
		if self.sendKey(iServiceKeys.keyUser+4):
			if config.usage.show_infobar_on_skip.value:
				# InfoBarSeek
				self.showAfterSeek()

	def nextTitle(self):
		if self.sendKey(iServiceKeys.keyUser+5):
			if config.usage.show_infobar_on_skip.value:
				# InfoBarSeek
				self.showAfterSeek()

	def prevTitle(self):
		if self.sendKey(iServiceKeys.keyUser+6):
			if config.usage.show_infobar_on_skip.value:
				# InfoBarSeek
				self.showAfterSeek()

	def enterDVDMenu(self):
		self.sendKey(iServiceKeys.keyUser+7)
	
	def nextAngle(self):
		self.sendKey(iServiceKeys.keyUser+8)

	def sendKey(self, key):
		if self.service and self.service.type != serviceIdDVD: return None
		keys = self.getServiceInterface("keys")
		if keys:
			keys.keyPressed(key)
		return keys

	def getServiceInterface(self, iface):
		service = self.session.nav.getCurrentService() # self.service
		if service:
			attr = getattr(service, iface, None)
			if callable(attr):
				return attr()
		return None

	##############################################################################
	## DVD Player specific
	def __serviceStarted(self):
		if self.dvdScreen:
			# Force show dvd screen
			#self.dvdScreen.hide()
			self.dvdScreen.show()
		
	def __serviceStopped(self):
		if self.dvdScreen:
			self.dvdScreen.hide()
		subs = self.getServiceInterface("subtitle")
		if subs and self.session and self.session.current_dialog:
			subs.disableSubtitles(self.session.current_dialog.instance)

	def __osdFFwdInfoAvail(self):
		self.setChapterLabel()

	def __osdFBwdInfoAvail(self):
		self.setChapterLabel()

	def __osdAudioInfoAvail(self):
		info = self.getServiceInterface("info")
		audioTuple = info and info.getInfoObject(iServiceInformation.sUser+6)
		if audioTuple:
			audioString = "%d: %s (%s)" % (audioTuple[0],audioTuple[1],audioTuple[2])
			self["audioLabel"].setText(audioString)
			#if audioTuple != self.last_audioTuple: # and not self.in_menu:
			#	self.doShow()
		self.last_audioTuple = audioTuple

	def __osdSubtitleInfoAvail(self):
		info = self.getServiceInterface("info")
		subtitleTuple = info and info.getInfoObject(iServiceInformation.sUser+7)
		if subtitleTuple:
			subtitleString = ""
			if subtitleTuple[0] is not 0:
				subtitleString = "%d: %s" % (subtitleTuple[0],subtitleTuple[1])
			self["subtitleLabel"].setText(subtitleString)
			#if subtitleTuple != self.last_subtitleTuple: # and not self.in_menu:
			#	self.doShow()
		self.last_subtitleTuple = subtitleTuple

	def __osdAngleInfoAvail(self):
		info = self.getServiceInterface("info")
		angleTuple = info and info.getInfoObject(iServiceInformation.sUser+8)
		if angleTuple:
			angleString = ""
			if angleTuple[1] > 1:
				angleString = "%d / %d" % (angleTuple[0],angleTuple[1])
				self["anglePix"].show()
			else:
				self["anglePix"].hide()
			self["angleLabel"].setText(angleString)
			#if angleTuple != self.last_angleTuple: # and not self.in_menu:
			#	self.doShow()
		self.last_angleTuple = angleTuple

	def __chapterUpdated(self):
		info = self.getServiceInterface("info")
		if info:
			self.currentChapter = info.getInfo(iServiceInformation.sCurrentChapter)
			self.totalChapters = info.getInfo(iServiceInformation.sTotalChapters)
			self.setChapterLabel()

	def __titleUpdated(self):
		info = self.getServiceInterface("info")
		if info:
			self.currentTitle = info.getInfo(iServiceInformation.sCurrentTitle)
			self.totalTitles = info.getInfo(iServiceInformation.sTotalTitles)
			self.setChapterLabel()
			#if not self.in_menu:
			#self.doShow()

	def __menuOpened(self):
		self.hide()
		#if self.dvdScreen:
		#	# Force show dvd screen
		#	self.dvdScreen.hide()
		#	self.dvdScreen.show()
		self.in_menu = True
		if self.has_key("ShowHideActions"):
			self["ShowHideActions"].setEnabled(False)
		if self.has_key("MovieListActions"):
			self["MovieListActions"].setEnabled(False)
		if self.has_key("SeekActions"):
			self["SeekActions"].setEnabled(False)
		if self.has_key("DVDMenuActions"):
			self["DVDMenuActions"].setEnabled(True)

	def __menuClosed(self):
		#if self.dvdScreen:
		#	self.dvdScreen.hide()
		self.show()
		self.in_menu = False
		if self.has_key("DVDMenuActions"):
			self["DVDMenuActions"].setEnabled(False)
		if self.has_key("ShowHideActions"):
			self["ShowHideActions"].setEnabled(True)
		if self.has_key("MovieListActions"):
			self["MovieListActions"].setEnabled(True)
		if self.has_key("SeekActions"):
			self["SeekActions"].setEnabled(True)

	# Not used yet
	#def createSummary(self):
	#	if self.service and self.service.type == serviceIdDVD:
	#		if fileExists(dvdPlayerPlg) or fileExists("%sc"%dvdPlayerPlg):
	#			from Plugins.Extensions.DVDPlayer.plugin import DVDSummary
	#			return DVDSummary

	def setChapterLabel(self):
		chapterLCD = "Menu"
		chapterOSD = "DVD Menu"
		if self.currentTitle > 0:
			chapterLCD = "%s %d" % (_("Chap."), self.currentChapter)
			chapterOSD = "DVD %s %d/%d" % (_("Chapter"), self.currentChapter, self.totalChapters)
			chapterOSD += " (%s %d/%d)" % (_("Title"), self.currentTitle, self.totalTitles)
		self["chapterLabel"].setText(chapterOSD)
		#try:
		#	self.session.summary.updateChapter(chapterLCD)
		#except:
		#	pass

	##############################################################################
	## Implement functions for InfoBarGenerics.py
	# InfoBarShowMovies
	def showMovies(self):
		try:
			self.playerOpenedList = True
			#DelayedFunction(20, self.session.execDialog, self.recordings)
			self.session.execDialog(self.recordings)
		except Exception, e:
			emcDebugOut("[EMCPlayer] showMovies exception:\n" + str(e))

	##############################################################################
	## Override functions from InfoBarGenerics.py
	# InfoBarShowHide
	#def serviceStarted(self):
	#	if not self.in_menu:
	#		if self.dvdScreen:
	#			self.dvdScreen.show()
	#	else:
	#		InfoBarShowHide.serviceStarted(self)

	def doShow(self):
		if self.in_menu:
			pass
			#self.hide()
			#if self.dvdScreen:
			#	# Force show dvd screen
			#	self.dvdScreen.hide()
			#	self.dvdScreen.show()
		else:
			#if self.dvdScreen:
			#	self.dvdScreen.hide()
			InfoBarShowHide.doShow(self)

	# InfoBarCueSheetSupport
	def playLastCB(self, answer):
		if answer == True:
			self.doSeek(self.resume_point)
		# From Merlin2
		elif config.EMC.movie_jump_first_mark.value == True:
			self.jumpToFirstMark()
		if self.service and self.service.type == serviceIdDVD:
			# DVDPlayer Workaround
			self.pauseService()
			self.unPauseService()
		self.showAfterSeek()

	# InfoBarNumberZap
	def keyNumberGlobal(self, number):
		if self.service and self.service.type == serviceIdDVD:
			if fileExists(dvdPlayerPlg) or fileExists("%sc"%dvdPlayerPlg):
				from Plugins.Extensions.DVDPlayer.plugin import ChapterZap
				self.session.openWithCallback(self.numberEntered, ChapterZap, "0")

	def numberEntered(self, retval):
		if retval and retval > 0 and retval != "":
			self.zapToNumber(retval)

	def zapToNumber(self, number):
		if self.service:
			seekable = self.getSeek()
			if seekable:
				seekable.seekChapter(number)

	# InfoBarMenu Key_Menu
	#def mainMenu(self):
	#	self.enterDVDMenu()

	# InfoBarShowHide Key_Ok
	def toggleShow(self):
		if not self.in_menu:
			# Call baseclass function
			InfoBarShowHide.toggleShow(self)

	# InfoBarSeek
#	def showAfterSeek(self):
#		if self.in_menu and self.dvdScreen:
#			self.hideAfterResume()
#			self.dvdScreen.show()
#		else:
#			InfoBarSeek.showAfterSeek(self)

	def doEofInternal(self, playing):
		if self.in_menu:
			self.hide()
		DelayedFunction(1000, self.evEOF)

  ##############################################################################
	## Oozoon image specific
	def up(self):
		self.showMovies()
		
	def down(self):
		self.showMovies()

	##############################################################################
	## LT image specific
	def startCheckLockTimer(self):
		pass
