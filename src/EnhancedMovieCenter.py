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

from . import _
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
from Screens.LocationBox import LocationBox
from Screens.MessageBox import MessageBox
from Screens.ServiceScan import *
import Screens.Standby
from Tools import Notifications
from enigma import eServiceEvent, eActionMap, eTimer, getDesktop
import os, struct
import NavigationInstance

from itertools import cycle

try:
	from Plugins.Extensions.CutlistDownloader.plugin import bestCutlist#
except ImportError as ie:
	hasCutlistDownloader = False
else:
	hasCutlistDownloader = True

# lets see if mutagen is installed
try:
	from mutagen.mp3 import MP3
except ImportError as ie:
	hasMutagen = False
else:
	hasMutagen = True

try:
	from enigma import eMediaDatabase
	isDreamOS = True
except:
	isDreamOS = False

from DelayedFunction import DelayedFunction
from EMCTasker import emcTasker, emcDebugOut

sz_w = getDesktop(0).size().width()

EMCAbout = "\n  Enhanced Movie Center " +EMCVersion+ "\n\n  (C) 2012 by\n  Coolman, Betonme, einfall, Jojojoxx, mr.scotty & Swiss-MAD \n\n  If you like this plugin and you want to support it,\n  or if just want to say ''thanks'',\n  please donate via PayPal. \n\n  Thanks a lot ! \n\n  PayPal: enhancedmoviecenter@gmail.com"

# Check if image is vti or dream, is needed for build entrys in MovieCenter with picons
global imgVti
global newPiconRenderer
imgVti = False
newPiconRenderer = False

def checkImg():
	global imgVti
	global newPiconRenderer
	check = False
	try:
		from boxbranding import getImageDistro
		distro = getImageDistro()
		imgVti = 'vti' in distro.lower()
		check = True
	except:
		try:
			from enigma import BT_FIXRATIO
			imgVti = True
			check = True
		except Exception, e:
			print "[EMC] checkImg is not Vti", e
	if check:
		if imgVti:
			print "[EMC] checkImg is Vti"
		else:
			print "[EMC] checkImg is not Vti"
	try:
		from Components.Renderer.Picon import getPiconName
		newPiconRenderer = True
	except Exception, e:
		print "[EMC] checkImg is not newPiconRenderer", e
	else:
		print "[EMC] checkImg is newPiconRenderer"


def setEPGLanguage(dummyself=None, dummy=None):
	if config.EMC.epglang.value:
		emcDebugOut("Setting EPG language: " + str(config.EMC.epglang.value))
		eServiceEvent.setEPGLanguage(config.EMC.epglang.value)
language.addCallback(setEPGLanguage)
DelayedFunction(5000, setEPGLanguage)


def setupKeyResponseValues(dummyself=None, dummy=None):
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

def cleanupSetup(dummy=None):
	try:
		global trashCleanCall
		if trashCleanCall is not None:
			if trashCleanCall.exists():
				trashCleanCall.cancel()
		if config.EMC.movie_trashcan_enable.value and config.EMC.movie_trashcan_clean.value or config.EMC.movie_finished_clean.value:
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
				from MovieSelection import purgeExpired
				DelayedFunction(2000, purgeExpired)
				emcDebugOut("Next trashcan cleanup in " + str(seconds/60) + " minutes")
	except Exception, e:
		emcDebugOut("[sp] cleanupSetup exception:\n" + str(e))


def EMCStartup(session):
	emcDebugOut("+++ EMC "+EMCVersion+" startup")

	if config.EMC.epglang.value:
		eServiceEvent.setEPGLanguage(config.EMC.epglang.value)

	setupKeyResponseValues()
	DelayedFunction(5000, cleanupSetup)

	# Check the image to use global for various images
	checkImg()

	# Go into standby if the reason for restart was EMC auto-restart
	if config.EMC.restart.value != "":
		if not os.path.exists(config.EMC.folder.value):
			emcTasker.shellExecute("mkdir " + config.EMC.folder.value)
		flag = os.path.join(config.EMC.folder.value, "EMC_standby_flag.tmp")
		if os.path.exists(flag):
			emcDebugOut("+++ Going into Standby mode after auto-restart")
			Notifications.AddNotification(Screens.Standby.Standby)
			emcTasker.shellExecute("rm -f " + flag)

# lets see if mutagen is available
def checkMutagen():
	if hasMutagen:
		return False
	try:
		import commands
		try:
			result = commands.getoutput('opkg list|grep mutagen')
		except:
			result = commands.getoutput('apt-cache search mutagen')
		if result.startswith('python-mutagen'):
			return True
		else:
			return False
	except Exception, e:
		print "[EMC] checkMutagen Exception:", e

# Predefined settings:
#  Index 0: Custom should always be the first one:           User edited vlues in the config
#  Index 1: Default should always be the second one:         Default values stored within the ConfigElement
#  Index x: All other entries are specified via the config:  Values are defined in the emc config
#                                                                   Be careful, You have to specify a valid value
#                                                                   None stands for not specified, will be ignored
#														Name (Button),		Column,	ID (Title)
predefined_settings = {	_("Custom") : ( None, "" ),
						_("Default") : ( None, "D" ),
						_("Performance") : ( 7, "P" ),
						_("Information") : ( 8, "I" )
						}

def get_predefined_columns():
	return [ v[0] for k,v in predefined_settings.iteritems() if v[0] is not None ]

def get_predefined_nameid(column):
	for k,v in predefined_settings.iteritems():
		if v[0] == column:
			return k, v[1]

def get_predefined_value(key):
	if key in predefined_settings:
		return predefined_settings[key]
	else:
		return predefined_settings[ next_predefined_settings() ]

def next_predefined_settings(key=""):
	if key not in predefined_settings:
		key = _("Custom")
	pdvcycle = cycle(predefined_settings.items())
	for k, v in pdvcycle:
		if k == key:
			k, v = pdvcycle.next()
			if v[0] is None:
				key = k
			else:
				return k

class EnhancedMovieCenterMenu(ConfigListScreen, Screen):
	if sz_w == 1920:
		skin = """
		<screen name="EnhancedMovieCenterMenu" position="center,170" size="1200,820" title="EnhancedMovieCenterMenu">
		<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img_fhd/red.png" position="10,5" size="300,70" alphatest="blend"/>
        <ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img_fhd/green.png" position="310,5" size="300,70" alphatest="blend"/>
        <ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img_fhd/blue.png" position="610,5" size="300,70" alphatest="blend"/>
        <widget backgroundColor="#9f1313" font="Regular;30" halign="center" name="key_red" position="10,5" foregroundColor="white" shadowColor="black" shadowOffset="-2,-2" size="300,70" transparent="1" valign="center" zPosition="1" />
        <widget backgroundColor="#1f771f" font="Regular;30" halign="center" name="key_green" position="310,5" foregroundColor="white" shadowColor="black" shadowOffset="-2,-2" size="300,70" transparent="1" valign="center" zPosition="1" />
        <widget backgroundColor="#18188b" font="Regular;30" halign="center" name="key_blue" position="610,5" foregroundColor="white" shadowColor="black" shadowOffset="-2,-2" size="300,70" transparent="1" valign="center" zPosition="1" />
        <widget font="Regular;34" halign="right" position="1050,25" render="Label" size="120,40" source="global.CurrentTime">
            <convert type="ClockToText">Default</convert>
        </widget>
        <eLabel backgroundColor="grey" position="10,80" size="1180,1" />
        <widget enableWrapAround="1" name="config" itemHeight="45" position="10,90" scrollbarMode="showOnDemand" size="1180,540" />
        <eLabel backgroundColor="grey" position="10,650" size="1180,1" />
        <widget font="Regular;32" halign="center" position="10,655" render="Label" size="1180,145" source="help" valign="center" />
	</screen>"""
	else:
		skin = """
		<screen name="EnhancedMovieCenterMenu" position="center,120" size="820,520" title="EnhancedMovieCenterMenu">
		<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/red.png" position="10,5" size="200,40" alphatest="blend"/>
		<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/green.png" position="210,5" size="200,40" alphatest="blend"/>
		<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/blue.png" position="410,5" size="200,40" alphatest="blend"/>
		<widget name="key_red" position="10,5" size="200,40" zPosition="1" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-2,-2" />
		<widget name="key_green" position="210,5" size="200,40" zPosition="1" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-2,-2" />
		<widget name="key_blue" position="410,5" size="200,40" zPosition="1" font="Regular;20" halign="center" valign="center" backgroundColor="#18188b" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-2,-2" />
		<widget source="global.CurrentTime" render="Label" position="740,14" size="70,24" font="Regular;22" halign="right">
			<convert type="ClockToText">Default</convert>
		</widget>
        <eLabel position="10,50" size="800,1" backgroundColor="grey" />
		<widget name="config" itemHeight="30" position="10,55" size="800,360" enableWrapAround="1" scrollbarMode="showOnDemand" />
		<eLabel position="10,420" size="800,1" backgroundColor="grey" />
		<widget source="help" valign="center" render="Label" position="10,423" size="800,95" font="Regular;20" halign="center" />
	</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		self.skinName = "EnhancedMovieCenterMenu"
		self.skin = EnhancedMovieCenterMenu.skin
		self.screenTitle = "Enhanced Movie Center "+ EMCVersion + " (Setup)"

		self["actions"] = ActionMap(["SetupActions", "OkCancelActions", "EMCConfigActions"],
		{
			"ok":		self.keyOK,
			"cancel":	self.keyCancel,
			"red":		self.keyCancel,
			"green": 	self.keySaveNew,
			"blueshort": 	self.loadPredefinedSettings,
			"bluelong":	self.loadDefaultSettings,
			"nextBouquet":	self.bouquetPlus,
			"prevBouquet":	self.bouquetMinus,
		}, -2) # higher priority

		self["key_red"] = Button(_("Cancel"))
		self["key_green"] = Button(_("Save"))
#		self["key_yellow"] = Button(" ")
		self["key_blue"] = Button()
		self["help"] = StaticText()

		# Key short / long pressed detection
		self.keylong = False

		self.list = []
		self.EMCConfig = []
		ConfigListScreen.__init__(self, self.list, session = session, on_change = self.changedEntry)
		self.needsRestartFlag = False
		self.defineConfig()
		self.createConfig()

		self.reloadTimer = eTimer()
		try:
			self.reloadTimer_conn = self.reloadTimer.timeout.connect(self.createConfig)
		except:
			self.reloadTimer.callback.append(self.createConfig)

		# Override selectionChanged because our config tuples have a size bigger than 2
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

		#Todo Remove if there is another solution, maybe thinkabout xml
		config.EMC.movie_finished_clean.addNotifier(self.changedEntry, initial_call = False, immediate_feedback = True)

		self.onShow.append(self.onDialogShow)

	def defineConfig(self):

		separator = "".ljust(250,"-")

#         _config list entry
#         _                                                 , config element
#         _                                                 ,                                     , function called on save
#         _                                                 ,                                     ,                       , function called if user has pressed OK
#         _                                                 ,                                     ,                       ,                       , usage setup level from E2
#         _                                                 ,                                     ,                       ,                       ,   0: simple+
#         _                                                 ,                                     ,                       ,                       ,   1: intermediate+
#         _                                                 ,                                     ,                       ,                       ,   2: expert+
#         _                                                 ,                                     ,                       ,                       ,       , depends on relative parent entries
#         _                                                 ,                                     ,                       ,                       ,       ,   parent config value must be true
#         _                                                 ,                                     ,                       ,                       ,       ,   a selection value "" is False
#         _                                                 ,                                     ,                       ,                       ,       ,             , _context sensitive help text
#         _                                                 ,                                     ,                       ,                       ,       ,             ,                                                          , performance value
#         _                                                 ,                                     ,                       ,                       ,       ,             ,                                                          ,                   , information value
#         _ 0                                               , 1                                   , 2                     , 3                     , 4     , 5           , 6                                                        , 7                 , 8
		self.EMCConfig = [
			(  _("About")                                         , config.EMC.about                    , None                  , self.showInfo         , 0     , []          , _("HELP_About")                                          , None              , None ),

			(  _("Disable EMC")                                   , config.EMC.ml_disable               , self.needsRestart     , None                  , 1     , []          , _("HELP_Disable EMC")                                    , None              , None ),

			(  _("Start EMC with")                                , config.EMC.movie_launch             , self.launchListSet    , None                  , 0     , []          , _("HELP_Start EMC with")                                 , None              , None ),
			(  _("Show plugin config in extensions menu")         , config.EMC.extmenu_plugin           , self.needsRestart     , None                  , 0     , []          , _("HELP_Show plugin config in extensions menu")          , None              , None ),
			(  _("Show EMC in extensions menu")                   , config.EMC.extmenu_list             , self.needsRestart     , None                  , 0     , []          , _("HELP_Show EMC in extensions menu")                    , None              , None ),

			(  separator                                          , config.EMC.about                    , None                  , None                  , 0     , []          , _("HELP_Key assignment Separator")                       , None              , None ),
			(  _("Bouquet buttons behaviour")                     , config.EMC.bqt_keys                 , None                  , None                  , 0     , []          , _("HELP_Bouquet buttons behaviour")                      , None              , None ),
			(  _("List entries to skip")                          , config.EMC.list_skip_size           , None                  , None                  , 0     , [-1]        , _("HELP_List entries to skip")                           , None              , None ),
			(  _("Red button function")                           , config.EMC.movie_redfunc            , None                  , None                  , 0     , []          , _("HELP_Red button function")                            , None              , None ),
			(  _("Long Red button function")                      , config.EMC.movie_longredfunc        , None                  , None                  , 0     , []          , _("HELP_Long Red button function")                       , None              , None ),
			#(  _("Green button function")                         , config.EMC.movie_greenfunc          , None                  , None                  , 0     , []          , _("HELP_Green button function")                          , None              , None ),
			#(  _("Long Green button function")                    , config.EMC.movie_longgreenfunc      , None                  , None                  , 0     , []          , _("HELP_Long Green button function")                     , None              , None ),
			(  _("Yellow button function")                        , config.EMC.movie_yellowfunc         , None                  , None                  , 0     , []          , _("HELP_Yellow button function")                         , None              , None ),
			(  _("Long Yellow button function")                   , config.EMC.movie_longyellowfunc     , None                  , None                  , 0     , []          , _("HELP_Long Yellow button function")                    , None              , None ),
			(  _("Blue button function")                          , config.EMC.movie_bluefunc           , None                  , None                  , 0     , []          , _("HELP_Blue button function")                           , None              , None ),
			(  _("Long Blue button function")                     , config.EMC.movie_longbluefunc       , None                  , None                  , 0     , []          , _("HELP_Long Blue button function")                      , None              , None ),

			(  separator                                          , config.EMC.about                    , None                  , None                  , 0     , []          , _(" ")                                                    , None              , None ),
			(  _("daily auto-start")                              , config.EMC.restart                  , self.autoRestartInfo  , self.autoRestartInfo  , 1     , []          , _("HELP_Daily auto-start")                               , None              , None ),
			(  _("auto-start window begin")                       , config.EMC.restart_begin            , None                  , None                  , 1     , [-1]        , _("HELP_auto-start window begin")                        , None              , None ),
			(  _("auto-start window end")                         , config.EMC.restart_end              , None                  , None                  , 1     , [-2]        , _("HELP_auto-start window end")                          , None              , None ),
			(  _("Force standby after auto-restart")              , config.EMC.restart_stby             , None                  , None                  , 1     , [-3]        , _("HELP_Force standby after auto-start")                 , None              , None ),
			(  _("LongInfo Button")                               , config.EMC.InfoLong                 , None                  , None                  , 0     , []          , _("HELP_LongInfo Button")                                , None              , None ),

			(  separator                                          , config.EMC.about                    , None                  , None                  , 0     , []          , _(" ")                                                    , None              , None ),
			(  _("Movie home at start")                           , config.EMC.CoolStartHome            , None                  , None                  , 0     , []          , _("HELP_Movie home at start")                            , "false"            , None ),
			(  _("Default sort mode")                             , config.EMC.moviecenter_sort         , None                  , None                  , 0     , []          , _("HELP_Sort mode at startup")                           , None              , None ),

			(  _("Movie home home path")                          , config.EMC.movie_homepath           , self.validatePath     , self.openLocationBox  , 0     , []          , _("HELP_Movie home home path")                           , None              , None ),
			(  _("EMC path access limit")                         , config.EMC.movie_pathlimit          , self.validatePath     , self.openLocationBox  , 1     , []          , _("HELP_EMC path access limit")                          , None              , None ),

			(  _("Cursor predictive move after selection")        , config.EMC.moviecenter_selmove      , None                  , None                  , 0     , []          , _("HELP_Cursor predictive move after selection")         , None              , None ),

			(  separator                                          , config.EMC.about                    , None                  , None                  , 0     , []          , _(" ")                                                   , None              , None ),
			(  _("Show symlinks")                                 , config.EMC.symlinks_show            , None                  , None                  , 0     , []          , _("HELP_Show symlinks")                                  , None              , True ),
#			(  _("Show symlinkdirectories_information")           , config.EMC.symlinkdir_info          , None                  , None                  , 0     , [-1]        , _("HELP_Show symlink_directories_information")           , False             , True ),
			(  _("Show directories")                              , config.EMC.directories_show         , None                  , None                  , 0     , []          , _("HELP_Show directories")                               , None              , True ),
			(  _("Show directories within movielist")             , config.EMC.directories_ontop        , None                  , None                  , 0     , [-1]        , _("HELP_Show directories within movielist")              , False             , True ),
			(  _("Configured directories at the top of movielist"), config.EMC.cfgtopdir_enable         , None                  , None                  , 0     , [-2,-1]     , _("HELP_Configure in etc\enigma2\emc-topdir.cfg")        , False             , True ),
			(  _("Show directories information")                  , config.EMC.directories_info         , None                  , None                  , 0     , [-3]        , _("HELP_Show directories information")                   , ""                , "CS" ),
			(  _("Text shown for initially unknown file count")   , config.EMC.count_default_text       , None                  , None                  , 0     , [-4,-1]     , _("HELP_Text shown for initially unknown file count")    , None              , None ),
			(  _("Text shown for initially unknown count and size"), config.EMC.count_size_default_text , None                  , None                  , 0     , [-5,-2]     , _("HELP_Text shown for initially unknown count and size"), None              , None ),
			(  _("Text shown for initially unknown directory size"), config.EMC.size_default_text       , None                  , None                  , 0     , [-6,-3]     , _("HELP_Text shown for initially unknown directory size"), None              , None ),
			(  _("Icon shown for initially unknown count / size") , config.EMC.count_size_default_icon  , None                  , None                  , 0     , [-7,-4]     , _("HELP_Icon shown for initially unknown count / size")  , None              , None ),
# below of date alignment moved (now also for alignment from trashcan information) 			(  _("Horizontal alignment for count / size")         , config.EMC.count_size_position      , None                  , None                  , 0     , [-8,-5]     , _("HELP_Horizontal alignment for count / size")          , None              , None ),
			(  _("Show directory size in skin")                   , config.EMC.directories_size_skin    , None                  , None                  , 0     , []          , _("HELP_Show directory size in skin")                    , None              , None ),

			(  _("Show Latest Recordings directory")              , config.EMC.latest_recordings        , None                  , None                  , 0     , []          , _("HELP_Show Latest Recordings directory")               , None              , True ),
			(  _("Latest Recordings directory limit")             , config.EMC.latest_recordings_limit  , None                  , None                  , 0     , [-1]        , _("HELP_Latest Recordings directory limit")              , None              , True ),
			(  _("Latest Recordings directory use emc-noscan.cfg"), config.EMC.latest_recordings_noscan , None                  , None                  , 0     , [-2]        , _("HELP_Latest Recordings directory use emc-noscan.cfg") , None              , True ),
			(  _("Show VLC directory")                            , config.EMC.vlc                      , None                  , None                  , 0     , []          , _("HELP_Show VLC directory")                             , None              , True ),
			(  _("Show Bookmarks in movielist")                   , config.EMC.bookmarks                , None                  , None                  , 0     , []          , _("HELP_Show Bookmarks in movielist")                    , "No"              , "Both" ),
			(  _("Use cache for files and directories")           , config.EMC.files_cache              , None                  , None                  , 0     , []          , _("HELP_Use cache for files and directories")            , True              , None ),
			(  _("Minimum file cache limit (0=cache everything)") , config.EMC.min_file_cache_limit     , None                  , None                  , 0     , [-1]        , _("HELP_Minimum file cache limit")                       , None              , False ),
			(  _("Show experimental options")                     , config.EMC.show_experimental_options, None                  , None                  , 0     , []          , _("HELP_Show experimental options")                      , None              , False ),
			(  _("Don't auto scan size of dirs from emc-noscan.cfg") , config.EMC.dir_info_usenoscan    , None                  , None                  , 0     , [-1]        , _("HELP_Don't auto scan size of dirs from emc-noscan.cfg"), None             , False ),
			(  _("Limit file operations in dirs from emc-noscan.cfg") , config.EMC.limit_fileops_noscan , None                  , None                  , 0     , [-2]        , _("HELP_Limit file operations in dirs from emc-noscan.cfg"), None            , False ),
			(  _("After file OPs only re-scan affected dirs")     , config.EMC.rescan_only_affected_dirs, None                  , None                  , 0     , [-3]        , _("HELP_After file OPs only re-scan affected dirs")      , None              , False ),
			(  _("Wake device when entering dir from emc-noscan.cfg"), config.EMC.noscan_wake_on_entry  , None                  , None                  , 0     , [-4]        , _("HELP_Wake device when entering dir from emc-noscan.cfg"), None            , False ),
			(  _("Check for dead links"),                           config.EMC.check_dead_links         , None                  , None                  , 0     , [-5]        , _("HELP_Check for dead links")                           , None              , None ),


			(  separator                                          , config.EMC.about                    , None                  , None                  , 1     , []          , _("HELP_separator_hide&performance")                     , None              , None ),
			(  _("Hide configured entries")                       , config.EMC.cfghide_enable           , None                  , None                  , 1     , []          , _("HELP_cfghide_enable")                                 , True              , True ),
			(  _("Scan for DVD structures")                       , config.EMC.check_dvdstruct          , None                  , None                  , 1     , []          , _("HELP_Scan for DVD structures")                       , False             , True ),
			(  _("Scan for movie structures")                     , config.EMC.check_moviestruct        , None                  , None                  , 1     , []          , _("HELP_Scan for movie structures")                     , False             , True ),
			(  _("Scan for bluray structures")                    , config.EMC.check_blustruct          , None                  , None                  , 1     , []          , _("HELP_Scan for bluray structures")                    , False             , True ),
			(  _("Scan for bluray structures in .iso")            , config.EMC.check_blustruct_iso      , None                  , None                  , 0     , []          , _("HELP_Scan for bluray structures in .iso")             , False             , True ),
			(  _("Suppress scan in selected folders")             , config.EMC.cfgscan_suppress         , None                  , None                  , 1     , []          , _("HELP_cfgscan_suppress")                               , True              , True ),
			(  _("Scan linked folders")                           , config.EMC.scan_linked              , None                  , None                  , 1     , []          , _("HELP_scan_linked")                                    , False             , True ),

			(  separator                                          , config.EMC.about                    , None                  , None                  , 0     , []          , _(" ")                                                    , None              , None ),
			(  _("Try to load titles from .meta files")           , config.EMC.movie_metaload           , None                  , None                  , 0     , []          , _("HELP_Try to load titles from .meta files")            , False             , True ),
			(  _("Load all for non showing titles from .meta files"), config.EMC.movie_metaload_all     , None                  , None                  , 0     , [-1]        , _("HELP_Load all for non showing titles from .meta files"), None             , True ),
			(  _("Try to load titles from .eit files")            , config.EMC.movie_eitload            , None                  , None                  , 0     , []          , _("HELP_Try to load titles from .eit files")             , False             , True ),
			(  _("Replace special chars in title")                , config.EMC.replace_specialchars     , None                  , None                  , 2     , []          , _("HELP_Replace special chars in title")                 , False             , None ),
			(  _("Show Movie Format")                             , config.EMC.movie_show_format        , None                  , None                  , 0     , []          , _("HELP_Show Movie Format")                              , False             , True ),
			(  _("Show Cut-Nr if exist")                          , config.EMC.movie_show_cutnr         , None                  , None                  , 0     , []          , _("HELP_Show Cut-Nr if exist")                           , False             , True ),
			(  _("Resolve links and show real path")              , config.EMC.movie_real_path          , None                  , None                  , 0     , []          , _("HELP_Resolve links and show real path")               , False             , True ),
			(  _("Show Path if no extended description available"), config.EMC.show_path_extdescr       , None                  , None                  , 0     , []          , _("HELP_Show Path if no extended description available") , False             , True ),

			(  separator                                          , config.EMC.about                    , None                  , None                  , 0     , []          , _(" ")                                                    , None              , None ),
			(  _("Listbox is skin able")                          , config.EMC.skin_able                , None                  , None                  , 0     , []          , _("HELP_Listbox is skin able")                           , None              , None ),

			(  _("Date format")                                   , config.EMC.movie_date_format        , None                  , None                  , 0     , []          , _("HELP_Date format")                                    , None              , None ),
			(  _("Horizontal alignment for date")                 , config.EMC.movie_date_position      , None                  , None                  , 0     , []          , _("HELP_Horizontal alignment for date")                  , None              , None ),
			(  _("Horizontal alignment for count / size")         , config.EMC.count_size_position      , None                  , None                  , 0     , []          , _("HELP_Horizontal alignment for count / size")          , None              , None ),

			(  _("Show movie icons")                              , config.EMC.movie_icons              , None                  , None                  , 0     , []          , _("HELP_Show movie icons")                               , False             , True ),
			(  _("Show link arrow")                               , config.EMC.link_icons               , None                  , None                  , 0     , [-1]        , _("HELP_Show link arrow")                                , False             , True ),

			(  _("Show movie picons")                             , config.EMC.movie_picons             , None                  , None                  , 0     , []          , _("HELP_Show movie picons")                              , None              , None ),
			# TODO: this entry only for "List is not skin able"
			(  _("Position movie picons")                         , config.EMC.movie_picons_pos         , None                  , None                  , 0     , [-1]        , _("HELP_Position movie picons")                          , None              , None ),
			(  _("Own Path to movie picons")                      , config.EMC.movie_picons_path_own    , None                  , None                  , 0     , [-2]        , _("HELP_Own Path to movie picons")                       , None              , None ),
			(  _("Path to movie picons")                          , config.EMC.movie_picons_path        , None                  , self.openLocationBox  , 0     , [-3,-1]     , _("HELP_Path to movie picons")                           , None              , None ),

			(  _("Show movie progress")                           , config.EMC.movie_progress           , None                  , None                  , 0     , []          , _("HELP_Show movie progress")                            , ""                , "PB" ),
			(  _("Short watching percent")                        , config.EMC.movie_watching_percent   , None                  , None                  , 0     , [-1]        , _("HELP_Short watching percent")                         , None              , None ),
			(  _("Finished watching percent")                     , config.EMC.movie_finished_percent   , None                  , None                  , 0     , [-2]        , _("HELP_Finished watching percent")                      , None              , None ),
			(  _("Mark new recordings with a star")               , config.EMC.mark_latest_files        , None                  , None                  , 0     , []          , _("HELP_Mark new recordings with a star")                , False             , True ),
			(  _("Show Cover")                                    , config.EMC.movie_cover              , None                  , None                  , 0     , []          , _("HELP_Show Cover")                                     , False             , None ),
			(  _("Cover delay in ms")                             , config.EMC.movie_cover_delay        , None                  , None                  , 0     , [-1]        , _("HELP_Cover delay in ms")                              , 1000              , None ),
			(  _("Cover background")                              , config.EMC.movie_cover_background   , None                  , None                  , 0     , [-2]        , _("HELP_Cover background")                               , None              , None ),
			(  _("Show fallback cover")                           , config.EMC.movie_cover_fallback     , None                  , None                  , 0     , []          , _("HELP_Fallback Cover")                                 , None              , None ),
			#(  _("Toggle Cover Button")                           , config.EMC.toggle_cover_button      , None                  , None                  , 0     , [-3]        , _("HELP_Use Toggle Cover Button")                        , False             , None ),
			(  _("Show movie preview")                            , config.EMC.movie_preview            , None                  , None                  , 0     , []          , _("HELP_Show movie preview")                             , False             , None ),
			(  _("Movie preview delay in ms")                     , config.EMC.movie_preview_delay      , None                  , None                  , 0     , [-1]        , _("HELP_Movie preview delay in ms")                      , 3000              , None ),
			(  _("Start movie preview before last position")      , config.EMC.movie_preview_offset     , None                  , None                  , 0     , [-2]        , _("HELP_Movie preview offset in seconds")                , None              , None ),
			(  _("Hide mini TV")                                  , config.EMC.hide_miniTV              , None                  , None                  , 0     , []          , _("HELP_hide_miniTV")                                    , "never"           , "never" ),
		]
		if not isDreamOS:
			self.EMCConfig.append(
			(  _("Method of hiding mini TV")                      , config.EMC.hide_miniTV_method       , None                  , None                  , 0     , []          , _("HELP_hide_miniTV_method")                             , "stopService"     , "stopService" ),
		)
		self.EMCConfig.extend(
		[
			(  separator                                          , config.EMC.about                    , None                  , None                  , 0     , []          , _(" ")                                                    , None              , None ),
			(  _("No resume below 10 seconds")                    , config.EMC.movie_ignore_firstcuts   , None                  , None                  , 1     , []          , _("HELP_No resume below 10 seconds")                     , None              , None ),
			(  _("Jump to first mark when playing movie")         , config.EMC.movie_jump_first_mark    , None                  , None                  , 1     , []          , _("HELP_Jump to first mark when playing movie")          , None              , None ),
			(  _("Rewind finished movies before playing")         , config.EMC.movie_rewind_finished    , None                  , None                  , 1     , []          , _("HELP_Rewind finished movies before playing")          , None              , None ),
			(  _("Always save last played progress as marker")    , config.EMC.movie_save_lastplayed    , None                  , None                  , 1     , []          , _("HELP_Always save last played progress as marker")     , None              , None ),
			(  _("Zap to channel after record EOF")               , config.EMC.record_eof_zap           , None                  , None                  , 1     , []          , _("HELP_Zap to channel after record EOF")                , None              , None ),
			(  _("Show real length of running records")           , config.EMC.record_show_real_length  , None                  , None                  , 1     , []          , _("HELP_Show real length of running records")            , None              , True ),
		]
		)
		if hasCutlistDownloader:
			self.EMCConfig.append(
			(  _("Download cutlist from Cutlist.at")              , config.EMC.cutlist_at_download      , None                  , None                  , 1     , []          , _("HELP_Download cutlist from Cutlist.at")               , False             , True ),
		)
		self.EMCConfig.extend(
		[
			(  separator                                          , config.EMC.about                    , None                  , None                  , 0     , []          , _("HELP_separator_Trashcan settings")                    , None              , None ),
			(  _("Trashcan enable")                               , config.EMC.movie_trashcan_enable    , None                  , self.openLocationBox  , 0     , []          , _("HELP_Trashcan enable")                                , None              , None ),
			(  _("Trashcan path")                                 , config.EMC.movie_trashcan_path      , self.validatePath     , self.openLocationBox  , 0     , [-1]        , _("HELP_Trashcan path")                                  , None              , None ),
			(  _("Show trashcan directory")                       , config.EMC.movie_trashcan_show      , None                  , None                  , 0     , [-2]        , _("HELP_Show trashcan directory")                        , None              , True ),
			(  _("Show trashcan information")                     , config.EMC.movie_trashcan_info      , None                  , None                  , 0     , [-3,-1]     , _("HELP_Dynamic trashcan")                               , ""                , "CS" ),
			(  _("Delete validation")                             , config.EMC.movie_delete_validation  , None                  , None                  , 0     , [-4]        , _("HELP_Delete validation")                              , None              , None ),

			(  _("Enable daily trashcan cleanup")                 , config.EMC.movie_trashcan_clean     , self.trashCleanupSetup, None                  , 0     , [-5]        , _("HELP_Enable daily trashcan cleanup")                  , None              , None ),
			(  _("Daily cleanup time")                            , config.EMC.movie_trashcan_ctime     , None                  , None                  , 0     , [-6,-1]     , _("HELP_Daily cleanup time")                             , None              , None ),
			(  _("How many days files may remain in trashcan")    , config.EMC.movie_trashcan_limit     , None                  , None                  , 0     , [-7,-2]     , _("HELP_How many days files may remain in trashcan")     , None              , None ),
			(  _("Move finished movies in trashcan")              , config.EMC.movie_finished_clean     , None                  , None                  , 2     , [-8,-3]     , _("HELP_Move finished movies in trashcan")               , None              , None ),
			(  _("Age of finished movies in movie folder (days)") , config.EMC.movie_finished_limit     , None                  , None                  , 2     , [-9,-4,-1]  , _("HELP_Age of finished movies in movie folder (days)")  , None              , None ),

			(  separator                                          , config.EMC.about                    , None                  , None                  , 0     , []          , _(" ")                                                    , None              , None ),
			(  _("Display directory reading text")                , config.EMC.moviecenter_loadtext     , None                  , None                  , 1     , []          , _("HELP_Display directory reading text")                 , None              , None ),
			(  _("EMC always reload after open")                  , config.EMC.movie_reload             , None                  , None                  , 1     , []          , _("HELP_EMC always reload after open")                   , False             , None ),
			(  _("EMC re-open list after STOP-press")             , config.EMC.movie_reopen             , None                  , None                  , 1     , []          , _("HELP_EMC re-open list after STOP-press")              , None              , None ),
			(  _("EMC re-open list after Movie end")              , config.EMC.movie_reopenEOF          , None                  , None                  , 1     , []          , _("HELP_EMC re-open list after Movie end")               , None              , None ),

			(  _("Leave Movie with Exit")                         , config.EMC.movie_exit               , None                  , None                  , 0     , []          , _("HELP_Leave Movie with Exit")                          , None              , None ),

			(  _("Hide movies being moved")                       , config.EMC.movie_hide_mov           , None                  , None                  , 1     , []          , _("HELP_Hide movies being moved")                        , None              , None ),
			(  _("Hide movies being deleted")                     , config.EMC.movie_hide_del           , None                  , None                  , 1     , []          , _("HELP_Hide movies being deleted")                      , None              , None ),

			(  _("Enable remote recordings")                      , config.EMC.remote_recordings        , None                  , None                  , 1     , []          , _("HELP_Enable remote recordings")                       , False             , None ),
			(  _("Automatic timers list cleaning")                , config.EMC.timer_autocln            , None                  , None                  , 1     , []          , _("HELP_Automatic timers list cleaning")                 , None              , None ),

			(  separator                                          , config.EMC.about                    , None                  , None                  , 1     , []          , _("HELP_Language Separator")                             , None              , None ),
			(  _("Preferred EPG language")                        , config.EMC.epglang                  , setEPGLanguage        , None                  , 1     , []          , _("HELP_Preferred EPG language")                         , None              , None ),
			(  _("Extra support for language")                    , config.EMC.langsupp                 , None                  , None                  , 1     , []          , _("HELP_Extra support for selected language")            , None              , None ),
			(  _("Enable playback auto-subtitling")               , config.EMC.autosubs                 , None                  , None                  , 1     , []          , _("HELP_Enable playback auto-subtitling")                , None              , None ),
			(  _("Primary playback subtitle language")            , config.EMC.sublang1                 , None                  , None                  , 1     , [-1]        , _("HELP_Primary playback subtitle language")             , None              , None ),
			(  _("Secondary playback subtitle language")          , config.EMC.sublang2                 , None                  , None                  , 1     , [-2]        , _("HELP_Secondary playback subtitle language")           , None              , None ),
			(  _("Tertiary playback subtitle language")           , config.EMC.sublang3                 , None                  , None                  , 1     , [-3]        , _("HELP_Tertiary playback subtitle language")            , None              , None ),
			(  _("Enable playback auto-language selection")       , config.EMC.autoaudio                , None                  , None                  , 1     , []          , _("HELP_Enable playback auto-language selection")        , None              , None ),
			(  _("Enable playback AC3-track first")               , config.EMC.autoaudio_ac3            , None                  , None                  , 1     , [-1]        , _("HELP_Enable playback AC3-track first")                , None              , None ),
			(  _("Primary playback audio language")               , config.EMC.audlang1                 , None                  , None                  , 1     , [-2]        , _("HELP_Primary playback audio language")                , None              , None ),
			(  _("Secondary playback audio language")             , config.EMC.audlang2                 , None                  , None                  , 1     , [-3]        , _("HELP_Secondary playback audio language")              , None              , None ),
			(  _("Tertiary playback audio language")              , config.EMC.audlang3                 , None                  , None                  , 1     , [-4]        , _("HELP_Tertiary playback audio language")               , None              , None ),

			(  separator                                          , config.EMC.about                    , None                  , None                  , 2     , []          , _("HELP_Advanced options separator")                     , None              , None ),
			(  _("Description field update delay")                , config.EMC.movie_descdelay          , None                  , None                  , 2     , []          , _("HELP_Description field update delay")                 , None              , None ),
			(  _("Key period value (50-900)")                     , config.EMC.key_period               , setupKeyResponseValues, None                  , 2     , []          , _("HELP_Key period value (50-900)")                      , None              , None ),
			(  _("Key repeat value (250-900)")                    , config.EMC.key_repeat               , setupKeyResponseValues, None                  , 2     , []          , _("HELP_Key repeat value (250-900)")                     , None              , None ),

			(  separator                                          , config.EMC.about                    , None                  , None                  , 0     , []          , _("HELP_Advanced options separator")                     , None              , None ),
			(  _("Show message if file added to playlist")        , config.EMC.playlist_message         , None                  , None                  , 0     , []          , _("HELP_Show message if file added to playlist")         , None              , None ),

			(  separator                                          , config.EMC.about                    , None                  , None                  , 0     , []          , _("HELP_Advanced Skin options separator")                , None              , None ),
			(  _("Use original EMC-skin (needs reopen)")          , config.EMC.use_orig_skin            , None                  , None                  , 0     , []          , _("HELP_Use original EMC-skin (needs reopen)")           , None              , None ),


			(  separator                                          , config.EMC.about                    , None                  , None                  , 0     , []          , _("HELP_Advanced audio metadata options separator")      , None              , None ),
		]
		)
		if checkMutagen() and not hasMutagen:
			self.EMCConfig.extend(
		[
			(  _("Download Mutagen-package for audio metadata")   , config.EMC.mutagen_download         , self.downloadMutagen  , None                  , 0     , []          , _("HELP_Download Mutagen-package for audio metadata")    , None              , None ),
		]
		)
		if hasMutagen:
			self.EMCConfig.extend(
		[
			(  _("Show audio metadata (needs skin-changes)")      , config.EMC.mutagen_show             , None                  , None                  , 0     , []          , _("HELP_Show audio metadata (needs skin-changes)")       , None              , None ),
		]
		)
		self.EMCConfig.extend(
		[
			(  _("Upgrade/Download Mutagen v1.28(experimental)")  , config.EMC.mutagen_download_128     , self.getNewMutagen    , None                  , 0     , []          , _("HELP_Upgrade/Download Mutagen v1.28(experimental)")   , None              , None ),

			(  separator                                          , config.EMC.about                    , None                  , None                  , 2     , []          , _("HELP_Advanced options separator")                     , None              , None ),
			(  _("Enable EMC debug output")                       , config.EMC.debug                    , self.dbgChange        , None                  , 2     , []          , _("HELP_Enable EMC debug output")                        , False             , None ),
			(  _("EMC output directory")                          , config.EMC.folder                   , self.validatePath     , self.openLocationBox  , 2     , [-1]        , _("HELP_EMC output directory")                           , None              , None ),
			(  _("Debug output file name")                        , config.EMC.debugfile                , self.validatePath     , None                  , 2     , [-2]        , _("HELP_Debug output file name")                         , None              , None ),
		]
		)

	def getNewMutagen(self, element):
		if element.value == True:
			try:
				from twisted.web.client import downloadPage
				tmppath = "/tmp/mutagen-1.28.tar.gz"
				url = "https://bitbucket.org/lazka/mutagen/downloads/mutagen-1.28.tar.gz"
				downloadPage(url, tmppath).addCallback(self.mutagenDlDone).addErrback(self.mutagenDlError)
			except Exception, e:
				print('[EMC] getNewMutagen exception failure: ', str(e))

	def mutagenDlDone(self, data):
		from Tools.Directories import fileExists
		if fileExists("/tmp/mutagen-1.28.tar.gz"):
			cmd = []
			cmd.append( 'tar -xzf /tmp/mutagen-1.28.tar.gz mutagen-1.28/mutagen -C /tmp' )
			cmd.append( 'rm /tmp/mutagen-1.28.tar.gz' )
			if not os.path.exists("/usr/lib/python2.7/site-packages/mutagen"):
				cmd.append( 'mkdir /usr/lib/python2.7/site-packages/mutagen' )
			cmd.append( 'cp -r /tmp/mutagen-1.28/mutagen /usr/lib/python2.7/site-packages' )
			cmd.append( 'rm -r /tmp/mutagen-1.28' )
			emcTasker.shellExecute(cmd, None, False)
			print "[EMC] mutagenDlDone data:", data

	def mutagenDlError(self, error):
		print "[EMC] mutagenDlError ERROR:", error

	def downloadMutagen(self, element):
		if element.value == True:
			cmd = "opkg install python-mutagen"
			cmd2 = "apt-get install python-mutagen"
			from Screens.Console import Console
			try:
				self.session.open(Console, _("Install Mutagen-package"), [cmd])
			except:
				self.session.open(Console, _("Install Mutagen-package"), [cmd2])

	def createConfig(self):
		list = []
		pds = get_predefined_columns()
		pdname = ""
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
					# Loop fell through without a break
					list.append( getConfigListEntry( conf[0], conf[1], conf[2], conf[3], conf[4], conf[5], conf[6] ) ) # not needed conf[7], conf[8]
					# Check for predefined config match
					for i,pd in enumerate(pds[:]):
						if conf[pd] is not None:
							#print conf[1].value, conf[pd]
							if conf[1].value != conf[pd]:
								# Settings are not equal: Delete it, because we don't have to test the rest of the config elements
								pds.remove(pd)
								continue
#			try:
#				list.append( getConfigListEntry( _("Enable component video in A/V Settings"), config.av.yuvenabled, self.needsRestart, None, 2, [], _("") ) )
#			except: pass
		self.list = list
		self["config"].setList(self.list)
		if pds:
			pdname, id = get_predefined_nameid( pds[0] )
			self.setTitle( self.screenTitle + " <" + id + ">")
		else:
			self.setTitle( self.screenTitle)
		self["key_blue"].setText( next_predefined_settings( pdname ) )

	def loadPredefinedSettings(self):
		#WORKAROUND E2 doesn't send dedicated short or long pressed key events
		if self.keylong:
			self.keylong = False
		# Load next predefined values, Button text indicates already the next values
		column, id = get_predefined_value( self["key_blue"].getText() )
		# Refresh is done implizit on change
		for conf in self.EMCConfig:
			#print conf
			# None values will be ignored
			if conf[column] is not None:
				#print conf[1].value, conf[column]
				conf[1].value = conf[column]
		self.createConfig()

	def loadDefaultSettings(self):
		self.keylong = True
		self.session.openWithCallback(self.loadDefaultSettingsCB, MessageBox, _("Load default settings will overwrite all settings, really load them?"), MessageBox.TYPE_YESNO)

	def loadDefaultSettingsCB(self, result):
		if result:
			# Refresh is done implizit on change
			for conf in self.EMCConfig:
				conf[1].value = conf[1].default
			self.createConfig()

	def onDialogShow(self):
		#self.setTitle( self.screenTitle )
		#self.createConfig()
		pass

	# Overwrite Screen close function
	def close(self):
#		self.session.openWithCallback(self.closed, MessageBox, EMCAbout, MessageBox.TYPE_INFO)
		Screen.close(self)

	def closed(self, dummy=None):
		# Call baseclass function
		Screen.close(self)

	def changedEntry(self, addNotifierDummy=None):
		if self.reloadTimer.isActive():
			self.reloadTimer.stop()
		self.reloadTimer.start(50, True)

	def updateHelp(self):
		cur = self["config"].getCurrent()
		self["help"].text = cur and cur[6] or ""

	def autoRestartInfo(self, dummy=None):
		emcTasker.ShowAutoRestartInfo()

	def bouquetPlus(self):
		self["config"].instance.moveSelection(self["config"].instance.pageUp)

	def bouquetMinus(self):
		self["config"].instance.moveSelection(self["config"].instance.pageDown)

	def dbgChange(self, element):
		if element.value == True:
			pass
		else:
			emcTasker.shellExecute("rm -f " + os.path.join(config.EMC.folder.value, config.EMC.debugfile.value))

	def dirSelected(self, res):
		if res is not None:
			res = os.path.normpath( res )
			self["config"].getCurrent()[1].value = res

	def keyOK(self):
		try:
			current = self["config"].getCurrent()
			current and current[3]( current[1] )
		except: pass

	def keySaveNew(self):
		config.EMC.needsreload.value = True

		if isinstance(config.EMC.movie_finished_clean.notifiers, dict):
			if hasattr( config.EMC.movie_finished_clean, "clearNotifiers" ):
				config.EMC.movie_finished_clean.clearNotifiers()
			else:
				config.EMC.movie_finished_clean.notifiers = { }
		elif isinstance(config.EMC.movie_finished_clean.notifiers, list):
			if hasattr( config.EMC.movie_finished_clean, "clearNotifiers" ):
				config.EMC.movie_finished_clean.clearNotifiers()
			else:
				config.EMC.movie_finished_clean.notifiers = [ ]

		for i, entry in enumerate( self.list ):
			if entry[1].isChanged():
				if entry[2] is not None:
					# execute value changed -function
					if entry[2](entry[1]) is not None:
						# Stop exiting, user has to correct the config
						config.EMC.movie_finished_clean.addNotifier(self.changedEntry, initial_call = False, immediate_feedback = True)
						return
				# Check parent entries
				for parent in entry[5]:
					if self.list[i+parent][2] is not None:
						# execute parent value changed -function
						if self.list[i+parent][2](self.EMCConfig[i+parent][1]) is not None:
							# Stop exiting, user has to correct the config
							config.EMC.movie_finished_clean.addNotifier(self.changedEntry, initial_call = False, immediate_feedback = True)
							return
				entry[1].save()
		if self.needsRestartFlag:
			self.session.open(MessageBox, _("Some settings changes require GUI restart to take effect."), MessageBox.TYPE_INFO, 10)
		self.close()

	def cancelConfirm(self, result):
		if not result:
			return

		if isinstance(config.EMC.movie_finished_clean.notifiers, dict):
			config.EMC.movie_finished_clean.notifiers = { }
		elif isinstance(config.EMC.movie_finished_clean.notifiers, list):
			config.EMC.movie_finished_clean.notifiers = [ ]

		for x in self["config"].list:
			x[1].cancel()
		self.close()

	def keyCancel(self):
		if self["config"].isChanged():
			self.session.openWithCallback(self.cancelConfirm, MessageBox, _("Really close without saving settings?"))
		else:
			self.close()

	def launchListSet(self, element):
		if element is not None:
			self.needsRestart()

	def needsRestart(self, dummy=None):
		self.needsRestartFlag = True

	def openLocationBox(self, element):
		try:
			if element:
				path = os.path.normpath( element.value )
				self.session.openWithCallback(
					self.dirSelected,
					LocationBox,
						windowTitle = _("Select Location"),
						text = _("Choose directory"),
						currDir = str(path)+"/",
						bookmarks = config.movielist.videodirs,
						autoAdd = False,
						editDir = True,
						inhibitDirs = ["/bin", "/boot", "/dev", "/etc", "/lib", "/proc", "/sbin", "/sys", "/var"],
						minFree = 100 )
		except: pass

	def showRestart(self):
		emcTasker.ShowAutoRestartInfo()

	def showInfo(self, dummy=None):
		self.session.open(MessageBox, EMCAbout, MessageBox.TYPE_INFO)

	def validatePath(self, element):
		element.value = os.path.normpath( element.value )
		if not os.path.exists(element.value):
			self.session.open(MessageBox, _("Given path %s does not exist. Please change." % str(element.value)), MessageBox.TYPE_ERROR)
			return False

	def trashCleanupSetup(self, dummy=None):
		if not os.path.exists(config.EMC.movie_trashcan_path.value):
			try:
				os.makedirs(config.EMC.movie_trashcan_path.value)
			except Exception, e:
				self.session.open(MessageBox, _("Trashcan create failed. Check mounts and permissions."), MessageBox.TYPE_ERROR)
				emcDebugOut("[EMCMS] trashcanCreate exception:\n" + str(e))
		cleanupSetup()
