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

from __init__ import _
from Components.config import *
from Components.config import config
from Components.Button import Button
from Components.ConfigList import ConfigListScreen
from Components.Language import *
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.Sources.StaticText import StaticText
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Screens.ServiceScan import *
import Screens.Standby
from Tools import Notifications
from enigma import eServiceEvent, eActionMap
import os, struct
import NavigationInstance

from DelayedFunction import DelayedFunction
from EMCTasker import emcTasker, emcDebugOut

EMCVersion = "V2.0.2"
EMCAbout = "\n   Enhanced Movie Center " +EMCVersion+ ".\n\n   Plugin's usage is free.\n\n   and the source is licensed under GPL.\n\n   by .\n\n   Coolman & Swiss-MAD"

def setEPGLanguage(dummy=None):
	if config.EMC.epglang.value:
		emcDebugOut("Setting EPG language: " + str(config.EMC.epglang.value))
		eServiceEvent.setEPGLanguage(config.EMC.epglang.value)
language.addCallback(setEPGLanguage)
DelayedFunction(5000, setEPGLanguage)

def setupKeyResponseValues(dummy=None):
	# currently not working on DM500/DM600, wrong input dev files?
	e1 = os.open("/dev/input/event0", os.O_RDWR)
	e2 = os.open("/dev/input/event0", os.O_RDWR)
	s1 = struct.pack("LLHHl", 0, 0, 0x14, 0x00, int(config.EMC.key_repeat.value))
	s2 = struct.pack("LLHHl", 0, 0, 0x14, 0x01, int(config.EMC.key_period.value))
	size = struct.calcsize("LLHHl")
	os.write(e1, s1)
	os.write(e2, s1)
	os.write(e1, s2)
	os.write(e2, s2)
	os.close(e1)
	os.close(e2)

# Only one trashclean instance is allowed
trashCleanCall = None

def cleanupSetup(dummyparam=None):
	try:
		from MovieSelection import gMS
		global trashCleanCall
		if trashCleanCall is not None:
			if trashCleanCall.exists():
				trashCleanCall.cancel()
		if config.EMC.movie_trashcan_clean.value is True or config.EMC.movie_finished_clean.value is True:
			from time import time
			recordings = NavigationInstance.instance.getRecordings()
			rec_time = NavigationInstance.instance.RecordTimer.getNextRecordingTime()
			cltime = config.EMC.movie_trashcan_ctime.value
			lotime = localtime()
			ltime = lotime[3]*60 + lotime[4]
			ctime = cltime[0]*60 + cltime[1]
			seconds = 60 * (ctime - ltime)
			if recordings or rec_time > 0 and (rec_time - time()) < 600: # no more recordings exist
				DelayedFunction(1800000, cleanupSetup)
				emcDebugOut("recordings exist... so next trashcan cleanup in " + str(seconds/60) + " minutes")
			else:
				if seconds <= 0:
					seconds += 86400	# 24*60*60
				# Recall setup funktion
				trashCleanCall = DelayedFunction(1000*seconds, cleanupSetup)
				# Execute trash cleaning
				DelayedFunction(2000, gMS.purgeExpired)
				emcDebugOut("Next trashcan cleanup in " + str(seconds/60) + " minutes")
	except Exception, e:
		emcDebugOut("[sp] cleanupSetup exception:\n" + str(e))

def EMCStartup(session):
	if not os.path.exists(config.EMC.folder.value):
		emcTasker.shellExecute("mkdir " + config.EMC.folder.value)
	emcDebugOut("+++ EMC "+EMCVersion+" startup")

	if config.EMC.epglang.value:
		eServiceEvent.setEPGLanguage(config.EMC.epglang.value)
	setupKeyResponseValues()
	DelayedFunction(5000, cleanupSetup)

	# Go into standby if the reason for restart was EMC auto-restart
	if os.path.exists(config.EMC.folder.value + "/EMC_standby_flag.tmp"):
		emcDebugOut("+++ Going into Standby mode after auto-restart")
		Notifications.AddNotification(Screens.Standby.Standby)
		emcTasker.shellExecute("rm -f " + config.EMC.folder.value + "/EMC_standby_flag.tmp")

class EnhancedMovieCenterMenu(ConfigListScreen, Screen):
	skin = """
		<screen name="EnhancedMovieCenterMenu" position="center,center" size="620,500" title="EnhancedMovieCenterMenu">
		<widget name="config" position="10,10" size="605,353 " enableWrapAround="1" scrollbarMode="showOnDemand" />
		<eLabel position="0,362" size="620,2" backgroundColor="#999999" zPosition="1" />
		<widget source="help" render="Label" position="10,367" size="605,88" font="Regular;20" foregroundColor="#999999" />
		<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/key-red.png" position="66,455" zPosition="0" size="140,40" transparent="1" alphatest="on" />
		<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/key-green.png" position="412,455" zPosition="0" size="140,40" transparent="1" alphatest="on" />
		<widget name="key_red" position="66,455" zPosition="1" size="140,40" font="Regular;20" valign="center" halign="center" backgroundColor="#9f1313" transparent="1" shadowColor="#000000" shadowOffset="-1,-1" />
		<widget name="key_green" position="412,455" zPosition="1" size="140,40" font="Regular;20" valign="center" halign="center" backgroundColor="#1f771f" transparent="1" shadowColor="#000000" shadowOffset="-1,-1" />
	</screen>"""
	def __init__(self, session):
		Screen.__init__(self, session)
		self.skinName = "EnhancedMovieCenterMenu"
		self.skin = EnhancedMovieCenterMenu.skin
		
		self["actions"] = ActionMap(["ChannelSelectBaseActions", "OkCancelActions", "ColorActions"],
		{
			"ok":			self.keyOK,
			"cancel":		self.keyCancel,
			"red":			self.keyCancel,
			"green": 		self.keySaveNew,
			"nextBouquet":	self.bouquetPlus,
			"prevBouquet":	self.bouquetMinus,
		}, -2) # higher priority
		
		self["key_red"] = Button(_("Cancel"))
		self["key_green"] = Button(_("Save"))
#		self["key_yellow"] = Button(" ")
#		self["key_blue"] = Button(" ")
		self["help"] = StaticText()
		
		self.list = []
		self.EMCConfig = []
		ConfigListScreen.__init__(self, self.list, session = session, on_change = self.changedEntry)
		self.onShown.append(self.onDialogShow)
		self.needsRestartFlag = False
		self.defineConfig()
		self.createConfig()
		def selectionChanged():
			current = self["config"].getCurrent()
			if self["config"].current != current:
				if self["config"].current:
					self["config"].current[1].onDeselect(self.session)
				if current:
					current[1].onSelect(self.session)
				self["config"].current = current
			for x in self["config"].onSelectionChanged:
				x()
		self["config"].selectionChanged = selectionChanged
		self["config"].onSelectionChanged.append(self.updateHelp)


	def defineConfig(self):
		
		separator = "".ljust(250,"-")
		
#         _config list entry                                
#         _                                                 , config variable                     
#         _                                                 ,                                     , function called on save
#         _                                                 ,                                     ,                       , function called if user has pressed OK
#         _                                                 ,                                     ,                       ,                       , usage setup level from E2
#         _                                                 ,                                     ,                       ,                       ,   0: simple+
#         _                                                 ,                                     ,                       ,                       ,   1: intermediate+
#         _                                                 ,                                     ,                       ,                       ,   2: expert+
#         _                                                 ,                                     ,                       ,                       ,       , depends on relative parent entries
#         _                                                 ,                                     ,                       ,                       ,       ,   parent config value must be true
#         _                                                 ,                                     ,                       ,                       ,       ,   a selection value "" is False 
#         _                                                 ,                                     ,                       ,                       ,       ,           , _context sensitive help text
		self.EMCConfig = [	
			(  _("About")                                         , config.EMC.about                    , None                  , self.showInfo         , 0     , []        , _("Opens the About dialog box.") ),
			
			(  _("Start EMC with")                                , config.EMC.movie_launch             , self.launchListSet    , None                  , 0     , []        , _("Set a direct key to open EMC.") ),
			(  _("Show plugin config in extensions menu")         , config.EMC.extmenu_plugin           , self.needsRestart     , None                  , 0     , []        , _("Show or hide the EMC Config in the extensions menu.\n(The extension menu are normaly reach with the [blue] key.") ),
			(  _("Show EMC in extensions menu")                   , config.EMC.extmenu_list             , self.needsRestart     , None                  , 0     , []        , _("Show or hide the EMC Pluginstart in the extensions menu.\n(The extension menu are normaly reach with the [blue] key.") ),
			
			(  _("Disable EMC")                                   , config.EMC.ml_disable               , self.needsRestart     , None                  , 1     , []        , _("Disable the EMC (MovieList) completly, but some special function like [Timerlist cleanup],[Trashcan clean] or [Auto restart] works in the background.") ),
			
			(  _("Movie home at start")                           , config.EMC.CoolStartHome            , None                  , None                  , 0     , []        , _("EMC start always in the \"Movie home\" directory.\n(In the next row you can set the \"Movie home\" directory).") ),
			(  _("Movie home home path")                          , config.EMC.movie_homepath           , self.validatePath     , self.openLocationBox  , 0     , []        , _("Set your \"Movie home\" path.") ),
			
			(  _("EMC path access limit")                         , config.EMC.movie_pathlimit          , self.validatePath     , self.openLocationBox  , 1     , []        , _("Limit your access path out from your \"Movie home\".\n(With the [<] and [>] buttons (next to the No.0 key) you can still go higher than this limit.") ),
			
			(  _("Trashcan path")                                 , config.EMC.movie_trashpath          , self.validatePath     , self.openLocationBox  , 0     , []        , _("Set your trashcan path.\n(There will move the recordings when you press [delete] and the trashcan is activated.") ),
			(  _("Hide trashcan directory")                       , config.EMC.movie_trashcan_hide      , None                  , None                  , 0     , []        , _("When is activated you dont see the trashcan directory in EMC.\n(You can however reach the trashcan over the EMC [MENU])") ),
			(  _("Delete validation")                             , config.EMC.movie_trashcan_validation, None                  , None                  , 0     , []        , _("When is activated and trashcan is using, EMC never will ask for a delete validation.") ),
			
			(  _("Enable daily trashcan cleanup")                 , config.EMC.movie_trashcan_clean     , self.trashCleanupSetup, None                  , 0     , []        , _("EMC delete old files in your trashcan, when reach the age that you set in the next row.") ),
			(  _("Daily cleanup time")                            , config.EMC.movie_trashcan_ctime     , self.trashCleanupSetup, None                  , 0     , [-1]      , _("Time when EMC delete all files in trashcan that had reach the remaining time.") ),
			(  _("How many days files may remain in trashcan")    , config.EMC.movie_trashcan_limit     , self.trashCleanupSetup, None                  , 0     , [-2]      , _("Set how many days files may remain in trashcan before EMC delete them permanently.\n(When set to [0] the files will delete directly).") ),
			(  _("Move finished movies in trashcan")              , config.EMC.movie_finished_clean     , self.trashCleanupSetup, None                  , 2     , [-3]      , _("Move all finished (watched) recordings from \"Movie home\" to the trashcan that had reach the remaining time you have set in the next setup row.") ),
			(  _("Age of finished movies in movie folder (days)") , config.EMC.movie_finished_limit     , self.trashCleanupSetup, None                  , 2     , [-4,-1]   , _("Set how many days finished (watched) recordings may remain in your \"Movie home\".") ),
			
			(  _("Show Latest Recordings directory")              , config.EMC.latest_recordings        , None                  , None                  , 0     , []        , _("Display a virtual folder in your \"Movie home\" that list the latest recordings. Also from the subdirectories in your \"Movie home\".\n(Only one page)") ),
			(  _("Show VLC directory")                            , config.EMC.vlc                      , None                  , None                  , 0     , []        , _("Show or hide the the VLC directory when is installed the VlcPlayerExtended Plugin.") ),
			(  _("Show E2 Bookmarks in movielist")                , config.EMC.bookmarks_e2             , None                  , None                  , 0     , []        , _("Display virtual folders in your \"Movie home\" with your Enigma2 Bookmarks.") ),
			(  _("Show EMC Bookmarks in movielist")               , config.EMC.bookmarks_emc            , None                  , None                  , 0     , []        , _("Display virtual folders in your \"Movie home\" with your EMC Bookmarks.") ),
			
			(  separator                                          , config.EMC.about                    , None                  , None                  , 1     , []        , _("HELP_separator_hide&performance") ),			
			(  _("Hide selected entries in movielist")            , config.EMC.cfghide_enable           , None                  , None                  , 1     , []        , _("HELP_cfghide_enable") ),
			(  _("Scan for DVD structures")                       , config.EMC.check_dvdstruct          , None                  , None                  , 1     , []        , _("HELP_Scan for DVD structures") ),
			(  _("No structure scan in selected folders")         , config.EMC.cfgnoscan_enable         , None                  , None                  , 1     , []        , _("HELP_cfgnoscan_enable") ),
			(  _("No structure scan in linked folders")           , config.EMC.noscan_linked            , None                  , None                  , 1     , []        , _("HELP_noscan_linked") ),
			
			(  separator                                          , config.EMC.about                    , None                  , None                  , 0     , []        , _("") ),			
			(  _("Sort file A to Z at startup")                   , config.EMC.CoolStartAZ              , None                  , None                  , 0     , []        , _("HELP_Sort file A to Z at startup") ),
			(  _("File order reverse")                            , config.EMC.moviecenter_reversed     , None                  , None                  , 0     , []        , _("HELP_File order reverse") ),
			(  _("EMC open with cursor on newest (TV mode)")      , config.EMC.moviecenter_gotonewest   , None                  , None                  , 0     , []        , _("") ),
			(  _("EMC open with cursor on newest (player)")       , config.EMC.moviecenter_gotonewestp  , None                  , None                  , 0     , []        , _("") ),
			(  _("Cursor predictive move after selection")        , config.EMC.moviecenter_selmove      , None                  , None                  , 0     , []        , _("HELP_Cursor predictive move after selection") ),
			
			(  _("Listbox is skin able")                          , config.EMC.skin_able                , None                  , None                  , 0     , []        , _("HELP_Listbox is skin able") ),
			
			(  _("Try to load titles from .meta files")           , config.EMC.movie_metaload           , None                  , None                  , 0     , []        , _("HELP_Try to load titles from .meta files") ),
			(  _("Show Movie Format")                             , config.EMC.movie_show_format        , None                  , None                  , 0     , []        , _("HELP_Show Movie Format") ),
			(  _("Show Cut-Nr if exist")                          , config.EMC.movie_show_cutnr         , None                  , None                  , 0     , []        , _("HELP_Show Cut-Nr if exist") ),
			(  _("Show date")                                     , config.EMC.movie_date               , None                  , None                  , 0     , []        , _("HELP_Show date") ),
			
			(  _("Show movie icons")                              , config.EMC.movie_icons              , None                  , None                  , 0     , []        , _("") ),
			(  _("Show movie progress")                           , config.EMC.movie_progress           , None                  , None                  , 0     , []        , _("") ),
			(  _("Short watching percent")                        , config.EMC.movie_watching_percent   , None                  , None                  , 0     , [-1]      , _("") ),
			(  _("Finished watching percent")                     , config.EMC.movie_finished_percent   , None                  , None                  , 0     , [-2]      , _("") ),
			(  _("Show icon indication for non-watched")          , config.EMC.movie_mark               , None                  , None                  , 0     , [-3]      , _("") ),
			
			(  _("No resume below 10 seconds")                    , config.EMC.movie_ignore_firstcuts   , None                  , None                  , 1     , []        , _("") ),
			(  _("Jump to first mark when playing movie")         , config.EMC.movie_jump_first_mark    , None                  , None                  , 1     , []        , _("") ),
			(  _("Rewind finished movies before playing")         , config.EMC.movie_rewind_finished    , None                  , None                  , 1     , []        , _("") ),
			(  _("Always save last played progress as marker")    , config.EMC.movie_save_lastplayed    , None                  , None                  , 1     , []        , _("") ),
			
			(  _("Display directory reading text")                , config.EMC.moviecenter_loadtext     , None                  , None                  , 1     , []        , _("") ),
			(  _("EMC always reload after open")                  , config.EMC.movie_reload             , None                  , None                  , 1     , []        , _("") ),
			(  _("EMC re-open list after STOP-press")             , config.EMC.movie_reopen             , None                  , None                  , 1     , []        , _("") ),
			(  _("EMC re-open list after Movie end")              , config.EMC.movie_reopenEOF          , None                  , None                  , 1     , []        , _("") ),
			
			(  _("Leave Movie with Exit")                         , config.EMC.movie_exit               , None                  , None                  , 0     , []        , _("") ),
			(  _("Blue button function")                          , config.EMC.movie_bluefunc           , None                  , None                  , 0     , []        , _("") ),
			
			(  _("Hide movies being moved")                       , config.EMC.movie_hide_mov           , None                  , None                  , 1     , []        , _("") ),
			(  _("Hide movies being deleted")                     , config.EMC.movie_hide_del           , None                  , None                  , 1     , []        , _("") ),
			
			(  _("Automatic timers list cleaning")                , config.EMC.timer_autocln            , None                  , None                  , 1     , []        , _("") ),
			
			(  _("Enigma daily auto-restart")                     , config.EMC.enigmarestart            , self.autoRestartInfo  , self.autoRestartInfo  , 1     , []        , _("") ),
			(  _("Enigma auto-restart window begin")              , config.EMC.enigmarestart_begin      , self.autoRestartInfo  , self.autoRestartInfo  , 1     , [-1]      , _("") ),
			(  _("Enigma auto-restart window end")                , config.EMC.enigmarestart_end        , self.autoRestartInfo  , self.autoRestartInfo  , 1     , [-2]      , _("") ),
			(  _("Force standby after auto-restart")              , config.EMC.enigmarestart_stby       , None                  , None                  , 1     , [-3]      , _("") ),
			
			(  separator                                          , config.EMC.about                    , None                  , None                  , 1     , []        , _("") ),			
			(  _("Preferred EPG language")                        , config.EMC.epglang                  , setEPGLanguage        , None                  , 1     , []        , _("") ),
			(  _("Enable playback auto-subtitling")               , config.EMC.autosubs                 , None                  , None                  , 1     , []        , _("") ),
			(  _("Primary playback subtitle language")            , config.EMC.sublang1                 , None                  , None                  , 1     , [-1]      , _("") ),
			(  _("Secondary playback subtitle language")          , config.EMC.sublang2                 , None                  , None                  , 1     , [-2]      , _("") ),
			(  _("Tertiary playback subtitle language")           , config.EMC.sublang3                 , None                  , None                  , 1     , [-3]      , _("") ),
			(  _("Enable playback auto-language selection")       , config.EMC.autoaudio                , None                  , None                  , 1     , []        , _("") ),
			(  _("Primary playback audio language")               , config.EMC.audlang1                 , None                  , None                  , 1     , [-1]      , _("") ),
			(  _("Secondary playback audio language")             , config.EMC.audlang2                 , None                  , None                  , 1     , [-2]      , _("") ),
			(  _("Tertiary playback audio language")              , config.EMC.audlang3                 , None                  , None                  , 1     , [-3]      , _("") ),
			
			(  separator                                          , config.EMC.about                    , None                  , None                  , 2     , []        , _("") ),			
			(  _("EMC output directory")                          , config.EMC.folder                   , self.validatePath     , self.openLocationBox  , 2     , []        , _("") ),
			(  _("Enable EMC debug output")                       , config.EMC.debug                    , self.dbgChange        , None                  , 2     , []        , _("") ),
			(  _("Debug output file name")                        , config.EMC.debugfile                , None                  , None                  , 2     , []        , _("") ),
			(  _("Description field update delay")                , config.EMC.movie_descdelay          , None                  , None                  , 2     , []        , _("") ),
			(  _("Key period value (50-900)")                     , config.EMC.key_period               , setupKeyResponseValues, None                  , 2     , []        , _("") ),
			(  _("Key repeat value (250-900)")                    , config.EMC.key_repeat               , setupKeyResponseValues, None                  , 2     , []        , _("") )
		]
		
		#TODO Later
		#(  _("Show if a movie is currently cutting"), config.EMC.check_movie_cutting
		
	def createConfig(self):
		try:
			list = []
			for i, conf in enumerate( self.EMCConfig ):
				# 0 entry text
				# 1 variable
				# 2 validation
				# 3 pressed ok
				# 4 setup level
				# 5 parent entries
				# 6 help text
				# Config item must be valid for current usage setup level
				if config.usage.setup_level.index >= conf[4]:
					# Parent entries must be true
					for parent in conf[5]:
						if not self.EMCConfig[i+parent][1].value:
							break
					else:
						# loop fell through without a break
						list.append( getConfigListEntry( conf[0], conf[1], conf[2], conf[3], conf[4], conf[5], conf[6] ) )
#			try:
#				list.append( getConfigListEntry( _("Enable component video in A/V Settings"), config.av.yuvenabled, self.needsRestart, None, 2, [], _("") ) )
#			except: pass
			self.list = list
			self["config"].setList(self.list)
		except Exception, e:
			emcDebugOut("[EMCMS] create config exception:\n" + str(e))

	def onDialogShow(self):
		self.setTitle("Enhanced Movie Center "+ EMCVersion + " (Setup)")

	def changedEntry(self):
		self.createConfig()

	def updateHelp(self):
		cur = self["config"].getCurrent()
		self["help"].text = cur and cur[6] or ""

	def autoRestartInfo(self, dummy=None):
		emcTasker.ShowAutoRestartInfo()

	def bouquetPlus(self):
		self["config"].instance.moveSelection(self["config"].instance.pageUp)

	def bouquetMinus(self):
		self["config"].instance.moveSelection(self["config"].instance.pageDown)

	def dbgChange(self, value):
		if value == True:
			pass
		else:
			emcTasker.shellExecute("rm -f " + config.EMC.folder.value + config.EMC.debugfile.value)

	def dirSelected(self, res):
		if res is not None:
			if res[-1:] == "/":
				res = res[:-1]
			#self.list[self["config"].getCurrentIndex()][1].value = res
			self["config"].getCurrent()[1].value = res

	def keyOK(self):
		try:
			#self.list[self["config"].getCurrentIndex()][3]()
			self["config"].getCurrent()[3]()
		except: pass

	def keySaveNew(self):
		config.EMC.needsreload.value = True
		for entry in self.list:
			if entry[1].isChanged():
				entry[1].save()
				if entry[2] is not None:
					entry[2](entry[1].value)	# execute value changed -function
		if self.needsRestartFlag:
			self.session.open(MessageBox, _("Some settings changes require GUI restart to take effect."), MessageBox.TYPE_INFO, 10)
		self.keySave()
		self.close()

	def launchListSet(self, value):
		if value is not None:
			self.needsRestart()

	def needsRestart(self, dummy=None):
		self.needsRestartFlag = True

	def openLocationBox(self):
		try:
			#path = self.list[ self["config"].getCurrentIndex() ][1].value + "/"
			path = self["config"].getCurrent()[1].value + "/"
			from Screens.LocationBox import MovieLocationBox
			self.session.openWithCallback(self.dirSelected, MovieLocationBox, text = _("Choose directory"), dir = path, minFree = 100)
		except: pass

	def showRestart(self):
		emcTasker.ShowAutoRestartInfo()

	def showInfo(self):
		self.session.open(MessageBox, EMCAbout, MessageBox.TYPE_INFO)

	def validatePath(self, value):
		if not os.path.exists(str(value)):
			self.session.open(MessageBox, _("Given path %s does not exist. Please change." % str(value)), MessageBox.TYPE_ERROR)

	def trashCleanupSetup(self, value):
		cleanupSetup()
	