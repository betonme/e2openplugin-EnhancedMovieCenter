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
from time import time
#from thread import start_new_thread
from threading import Thread
from random import shuffle

from Components.ActionMap import ActionMap, HelpableActionMap
from Components.Button import Button
from Components.config import *
from Components.Label import Label
from Components.ServiceEventTracker import ServiceEventTracker
from Screens.Screen import Screen
from Screens.ParentalControlSetup import ProtectedScreen
from Screens.HelpMenu import HelpableScreen
from Screens.MessageBox import MessageBox
from Screens.ChoiceBox import ChoiceBox
from Screens.LocationBox import LocationBox
from Screens.EventView import EventViewSimple
from Tools import Notifications
from Tools.Notifications import AddPopup
from Tools.BoundFunction import boundFunction
from Tools.Directories import fileExists
from enigma import getDesktop, eServiceReference, eTimer, iPlayableService, eServiceCenter, gPixmapPtr

# Movie preview
from Components.VideoWindow import VideoWindow

# Cover
from Components.AVSwitch import AVSwitch
from Components.Pixmap import Pixmap
from enigma import ePicLoad, getDesktop
#from Tools.LoadPixmap import LoadPixmap

# EMC internal
from EMCFileCache import movieFileCache
from DelayedFunction import DelayedFunction
from EnhancedMovieCenter import _
from EMCTasker import emcTasker, emcDebugOut
from MovieCenter import MovieCenter, getPlayerService, getProgress, detectBLUStructure, detectBLUISO
from MovieSelectionMenu import MovieMenu
from EMCMediaCenter import EMCMediaCenter
from VlcPluginInterface import VlcPluginInterfaceSel
from CutListSupport import CutList
from DirectoryStack import DirectoryStack
from E2Bookmarks import E2Bookmarks
from EMCBookmarks import EMCBookmarks
from ServiceSupport import ServiceCenter
from EMCCoverSearch import EMCImdbScan
from MovieRetitle import MovieRetitle
from Components.Sources.EMCServiceEvent import EMCServiceEvent
from MovieInfo import DownloadMovieInfo, MovieInfoTMDb
from EMCPlayList import emcplaylist, EMCPlaylistScreen

#from MetaSupport import MetaList
from MetaSupport import getInfoFile

from MovieCenter import extList, extVideo, extMedia, extDir, plyAll, plyDVD, cmtBME2, cmtBMEMC, cmtDir, plyDVB, extPlaylist
from MovieCenter import getMovieNameWithoutExt, getMovieNameWithoutPhrases

global extList, extVideo, extMedia, extDir, plyAll, plyDVD, cmtBME2, cmtBMEMC, cmtDir, plyDVB, extPlaylist


# Get Count and Size-values at start to CacheList
def startCountSizeCache():
	try:
		movie_homepath = os.path.join(config.EMC.movie_homepath.value)
		global moviecenterdata
		from MovieCenter import MovieCenterData, moviecenterdata
		if moviecenterdata is None:
			moviecenterdata = MovieCenterData()
		moviecenterdata.createStartCountSizeList(movie_homepath)
	except Exception, e:
		emcDebugOut("[EMC] startCountSizeCache get failed !!!\n" + str(e))

# Move all trashcan operations to a separate file / class
def purgeExpired(emptyTrash=False):
	try:
		movie_trashpath = config.EMC.movie_trashcan_path.value
		movie_homepath = os.path.realpath(config.EMC.movie_homepath.value)

		# Avoid cleaning the movie home folder
		for root, dirs, files in os.walk(movie_trashpath):
			if os.path.realpath(root) in movie_homepath:
				AddPopup(
					_("EMC: Skipping Trashcan Cleanup\nMovie Home Path is equal to or a subfolder of the Trashcan"),
					MessageBox.TYPE_INFO,
					0,
					"EMC_TRASHCAN_CLEANUP_SKIPPED_ID"
				)
				return

		if os.path.exists(movie_trashpath):
			movieFileCache.delPathFromCache(movie_trashpath)
			if config.EMC.movie_trashcan_clean.value is True or emptyTrash:
				# Trashcan cleanup
				purgeCmd = ""
				currTime = localtime()
				for root, dirs, files in os.walk(movie_trashpath):
					for movie in files:
						# Only check media files
						ext = os.path.splitext(movie)[1].lower()
						if ext in extMedia:
							fullpath = os.path.join(root, movie)
							if os.path.exists(fullpath):
								if emptyTrash or currTime > localtime(os.stat(fullpath).st_mtime + 24*60*60*int(config.EMC.movie_trashcan_limit.value)):
									#purgeCmd += '; rm -f "'+ os.path.splitext(fullpath)[0] +'."*'

									#TEST_E2DELETE
									service = getPlayerService(fullpath, movie, ext)
									serviceHandler = eServiceCenter.getInstance()
									offline = serviceHandler.offlineOperations(service)
									result = False
									if offline is not None:
										# really delete!
										if not offline.deleteFromDisk(0):
											result = True
									#Workaround: Avoids trashcan failure if trashcan contains *.m2ts or *.iso files
									if ext == '.m2ts' or ext == '.iso':
										result = True
									if result == False:
										AddPopup(
											_("EMC Trashcan Cleanup failed!"),
											MessageBox.TYPE_ERROR,
											0,
											"EMC_TRASHCAN_CLEANUP_FAILED_ID"
										)
										return
									else:
										path = os.path.splitext(fullpath)[0].replace("'","\'")
										purgeCmd += '; rm -f "'+ path +'."*'
									#TEST_E2DELETE

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
					currTime = localtime()
					for root, dirs, files in os.walk(movie_homepath):
						if root.startswith(movie_trashpath):
							# Don't handle the trashcan and its subfolders
							continue
						for movie in files:

							# Only check media files
							ext = os.path.splitext(movie)[1].lower()
							if ext in extMedia:
								fullpath = os.path.join(root, movie)
								fullpathcuts = fullpath + ".cuts"
								if os.path.exists(fullpathcuts):
									if currTime > localtime(os.stat(fullpathcuts).st_mtime + 24*60*60*int(config.EMC.movie_finished_limit.value)):
										# Check progress
										service = getPlayerService(fullpath, movie, ext)
										progress, length = getProgress(service, forceRecalc=True)
										if progress >= int(config.EMC.movie_finished_percent.value):
											# cut file extension
											fullpath = os.path.splitext(fullpath)[0].replace("'","\'")
											# create a time stamp with touch for all corresponding files
											mvCmd += '; touch "'+ fullpath +'."*'
											# move movie into the trashcan
											mvCmd += '; mv "'+ fullpath +'."* "'+ movie_trashpath +'"'
					if mvCmd != "":
						association = []
						#Not necessary anymore - Is done always on show
						#association.append((reloadList))	# Force list reload after cleaning
						emcTasker.shellExecute(mvCmd[2:], association)
						emcDebugOut("[EMCMS] finished movie cleanup activated")
					else:
						emcDebugOut("[EMCMS] finished movie cleanup: nothing to move...")
		else:
			emcDebugOut("[EMCMS] trashcan cleanup: no trashcan...")
	except Exception, e:
		emcDebugOut("[EMCMS] purgeExpired exception:\n" + str(e))


class SelectionEventInfo:
	def __init__(self):
		self["Service"] = EMCServiceEvent(ServiceCenter.getInstance())
		# Movie preview
		desktopSize = getDesktop(0).size()
		self["Video"] = VideoWindow(decoder = 0, fb_width=desktopSize.width(), fb_height=desktopSize.height())
		# Movie Cover
		self["Cover"] = Pixmap()
		self["CoverBg"] = Pixmap()
		self["CoverBg"].hide()

	def initPig(self):
		if not (config.EMC.movie_cover.value or config.EMC.movie_preview.value):
			#print "EMC: InitPig"
			self["Cover"].hide()
			self["CoverBg"].hide()
			self["Video"].show()
			if self.lastservice:
				self.session.nav.playService(self.lastservice)
				self.lastservice = None
		else:
			if config.EMC.movie_cover.value:
				#print "EMC: InitPig C"
				self["Video"].hide()
				self["Cover"].instance.setPixmap(gPixmapPtr())
				self["Cover"].hide()
				self["CoverBg"].hide()
			if config.EMC.movie_preview.value:
				#print "EMC: InitPig P"
				self["Cover"].hide()
				self["CoverBg"].hide()
				self["Video"].hide()

	def updateEventInfo(self, service):
		self["Service"].newService(service)

	def showCover(self, service=None):
		if service:
			path = service.getPath()
			jpgpath = ""
			exts = [".jpg", ".png", "_md.jpg", "_md.png"]
			jpgpath = getInfoFile(path, exts)[1]
			print "EMC jpgpath", jpgpath

			#if path.endswith("/.."):
				#jpgpath = "/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/cover_tr.png"

			if config.EMC.movie_cover_fallback.value and not os.path.exists(jpgpath):
				no_poster = "no_poster.png"
				jpgpath = "/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/" + no_poster

			#TODO avoid os.path.exists double check
			if jpgpath and os.path.exists(jpgpath):
				sc = AVSwitch().getFramebufferScale()
				size = self["Cover"].instance.size()
				self.picload = ePicLoad()
				try:
					self.picload_conn = self.picload.PictureData.connect(self.showCoverCallback)
				except:
					self.picload.PictureData.get().append(self.showCoverCallback)
				if self.picload:
					self.picload.setPara((size.width(), size.height(), sc[0], sc[1], False, 1, config.EMC.movie_cover_background.value))
					if self.picload.startDecode(jpgpath) != 0:
						del self.picload
			else:
				self["Cover"].hide()
				self["CoverBg"].hide()
		else:
			self["Cover"].hide()
#			self["CoverBg"].hide()				#Hide VideoPicture when scrolling movielist

	def showCoverCallback_org(self, picInfo=None):
		if self.picload and picInfo:
			ptr = self.picload.getData()
			if ptr != None:
				self["Cover"].instance.setPixmap(ptr)
				self["Cover"].show()
				self["CoverBg"].show()
			del self.picload

	def showCoverCallback(self, picInfo=None):
		if self.picload and picInfo:
			ptr = self.picload.getData()
			if ptr != None:
				self["Cover"].instance.setPixmap(ptr)
				if config.EMC.movie_cover.value:
					if self.cover:
						self["Cover"].show()
						self["CoverBg"].show()
			del self.picload

	# Movie preview
	def showPreview(self, service=None):
		#print "EMC: showPreview"
		lastserviceref = self.session.nav.getCurrentlyPlayingServiceReference()
		if service:
			# TODO can we reuse the EMCMediaCenter for the video preview
			ext = os.path.splitext(service.getPath())[1].lower()
			if ext in plyAll:
				#self.session.nav.stopService()
				#cue.setCutListEnable(2) #not tested

				# Workaround for not working E2 cue.setCutListEnable not working :-(
				#cutspath = service.getPath() + ".cuts"
				#if os.path.exists(cutspath):
				#	os.chmod(cutspath, 555)
				#	print "EMC set chmod read only"

				# Start preview
				self.session.nav.playService(service)
				# Get service, seek and cuesheet
				s = self.session.nav.getCurrentService()
				seekable = s and s.seek()
				cue = s and s.cueSheet()
				if cue and seekable:
					# Avoid cutlist overwrite
					cue.setCutListEnable(0)
					#cue.setCutListEnable(2)
					#cue.setCutListEnable(3)
					#print "EMC cue.setCutListEnable(0)"
					#self.downloadCuesheet() #not tested

					# Adapted from jumpToFirstMark
					jumpto = None
					# EMC enhancement: increase recording margin to make sure we get the correct mark
					#margin = config.recording.margin_before.value*60*90000 *2 or 20*60*90000
					#middle = (long(seekable.getLength()[1]) or 90*60*90000) / 2
					# Search first mark
					for (pts, what) in cue.getCutList():
						if what == 3: #CUT_TYPE_LAST:
							if pts != None:
								# Start preview x seconds before last position
								jumpto = int(pts) - ( int(config.EMC.movie_preview_offset.value) * 90000 )
								break
					if jumpto is not None and jumpto > 0:
						# Jump to first mark
						seekable.seekTo(jumpto)
				ref = self.session.nav.getCurrentlyPlayingServiceReference()
				ext = ref and os.path.splitext(ref.getPath())[1].lower()
				if ext in plyDVD:
					#subs = getattr(s, "subtitle", None)
					#if callable(subs):
					#	#self.dvdScreen = self.session.instantiateDialog(DVDOverlay)
					#	#subs.enableSubtitles(self.dvdScreen.instance, None)
					#	subs.enableSubtitles(None, None)
					DelayedFunction(50, boundFunction(self.dvdPlayerWorkaround))
				self["Video"].show()
				#try: show preview although cover is on
				if self.cover:
					self["Cover"].hide()
					self["CoverBg"].hide()
					self.toggleCover()
			else:
				# Start LiveTV
				if self.lastservice:
					self.session.nav.playService(self.lastservice)
					#print "EMC: showPreview show"
					self["Video"].show()

		# If livetv is shown - don't stop it
		elif lastserviceref and self.lastservice and lastserviceref != self.lastservice:
			# Stop a previously played preview

			#TEST Do not stop preview on cursor move
			#self.session.nav.stopService()
			print "EMC: showPreview hide"
			#self["Video"].hide()

	def dvdPlayerWorkaround(self):
		from Screens.InfoBar import InfoBar
		infobar = InfoBar and InfoBar.instance
		if infobar:
			infobar.pauseService()
			infobar.unPauseService()


class EMCSelection(Screen, HelpableScreen, SelectionEventInfo, VlcPluginInterfaceSel, DirectoryStack, E2Bookmarks, EMCBookmarks, ProtectedScreen):

	# Define static member variables
	def attrgetter(attr, default=None):
		def get_any(self):
			return getattr(EMCSelection, attr, default)
		return get_any
	def attrsetter(attr):
		def set_any(self, value):
			setattr(EMCSelection, attr, value)
		return set_any

	returnService = property( fget=attrgetter('_returnService'), fset=attrsetter('_returnService'))
	currentPath   = property( fget=attrgetter('_currentPath', config.EMC.movie_homepath.value), fset=attrsetter('_currentPath'))
	lastPlayed    = property( fget=attrgetter('_lastPlayed'), fset=attrsetter('_lastPlayed'))

	def __init__(self, session, returnService=None, playerInstance=None):
		Screen.__init__(self, session)
		if config.ParentalControl.configured.value:
			ProtectedScreen.__init__(self)
		SelectionEventInfo.__init__(self)
		VlcPluginInterfaceSel.__init__(self)
		DirectoryStack.__init__(self)

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

		self.playerInstance = playerInstance
		self.multiSelectIdx = None
		if returnService:
			self.returnService = returnService
			self.currentPath = os.path.dirname(returnService.getPath())
		self.lastservice = None
		self.cursorDir = 0

		self["wait"] = Label(_("Reading directory..."))
		self["wait"].hide()
		self["list"] = MovieCenter()

		self["key_red"] = Button()
		self["key_green"] = Button()
		self["key_yellow"] = Button()
		self["key_blue"] = Button()

		if config.EMC.movie_cover.value:
			self.cover = True
		else:
			self.cover = False

		helptext = self.initButtons()

		self["actions"] = HelpableActionMap(self, "PluginMovieSelectionActions",
			{
				"EMCOK":		(self.entrySelected,		_("Play selected movie(s)")),
#				"EMCOKL":		(self.unUsed,			"-"),
				"EMCPLAY":		(self.playAll,			_("Play All")),
				"EMCSHUFFLE":		(self.shuffleAll,		_("Shuffle All")),
				"EMCEXIT":		(self.abort,			_("Close EMC")),
				"EMCMENU":		(self.openMenu,			_("Open menu")),
				"EMCINFO":		(self.showEventInformation,	_("Show event info")),
				"EMCINFOL":		(self.CoolInfoLong,		_("IMDBSearch / EMC-TMDBInfo / TMDBInfo / TMBDInfo / CSFDInfo")),

				"EMCRed":		(self.redFunc,			helptext[0]),			#redhelptext),
				"EMCGREEN":		(self.greenFuncShort,		helptext[2]),			#greenhelptext),
				"EMCYELLOW":		(self.yellowFunc,		helptext[4]),			#yellowhelptext),
				"EMCBLUE":		(self.blueFunc,			helptext[6]),			#bluehelptext),

				"EMCREDL":		(self.redFuncLong,		helptext[1]),			#redlonghelptext),
				"EMCGREENL":		(self.greenFuncLong,		helptext[3]),			#greenlonghelptext),
				"EMCYELLOWL":		(self.yellowFuncLong,		helptext[5]), 			#yellowlonghelptext),
				"EMCBlueL":		(self.blueFuncLong,		helptext[7]),			#bluelonghelptext),
#				"EMCBlueL":		(self.openE2Bookmarks,		_("Open E2 bookmarks")),
#				"EMCBlueL":		(self.openEMCBookmarks,		_("Open EMC bookmarks")),

				"EMCLeft":		(self.pageUp,			_("Move cursor page up")),
				"EMCRight":		(self.pageDown,			_("Move cursor page down")),
				"EMCUp":		(self.moveUp,			_("Move cursor up")),
				"EMCDown":		(self.moveDown,			_("Move cursor down")),
				"EMCBqtPlus":		(self.bqtPlus,			_("Move cursor to the top / Move cursor x entries up / Switch Folders in Movie Home (up)")),
				"EMCBqtMnus":		(self.bqtMnus,			_("Move cursor to the end / Move cursor x entries down / Switch Folders in Movie Home (down)")),
				"EMCArrowNext":		(self.CoolForward,		_("Directory forward")),
#				"EMCArrowNextL":	(self.unUsed,			"-"),
				"EMCArrowPrevious":	(self.CoolBack,			_("Directory back")),
#				"EMCArrowPreviousL":	(self.directoryUp,		_("Directory up")),
				"EMCVIDEOB":		(self.toggleSelectionList,	_("Toggle service selection")),
				"EMCVIDEOL":		(self.resetSelectionList,	_("Remove service selection")),
				"EMCAUDIO":		(self.openMenuPlugins,		_("Available plugins menu")),
#				"EMCAUDIOL":		(self.unUsed,			"-"),
				"EMCMENUL":		(self.openMenuPlugins,		_("Available plugins menu")),
				"EMCTV":		(self.triggerReloadList,	_("Reload movie file list")),
				"EMCTVL":		(self.CoolTimerList,		_("Open Timer List")),
				"EMCRADIO":		(self.toggleProgress,		_("Toggle viewed / not viewed")),
#				"EMCRADIOL":		(self.unUsed,			"-"),
				"EMCTEXT":		(self.multiSelect,		_("Start / end multiselection")),
#				"EMCTEXTL":		(self.unUsed,			"-"),
				"0":			(self.CoolKey0,			"-"),
				"4":			(self.CoolAVSwitch,		"-"),
				"7":			(self.CoolTVGuide,		"-"),
				"8":			(self.CoolSingleGuide,		"-"),
				"9":			(self.CoolEasyGuide,		"-"),
			}, prio=-3)
			# give them a little more priority to win over baseclass buttons
		self["actions"].csel = self

		HelpableScreen.__init__(self)

		if self.currentPath == None:
			self.currentPath = config.EMC.movie_homepath.value
		self.tmpSelList = None		# Used for file operations
		self.tmpSelPath = None		# also used for file operations
		self.deleteAllOther = False     # also used for file operations
		self.tmpSelListOther = None	# also used for file operations
		self.deleteAllOtherList = False # also used for file operations

		# Key press short long handling
		#TODO We have to rework this key press handling in order to allow different user defined color key functions
		self.toggle = True		# Used for long / short key press detection: Toggle sort mode / order, Toggle selection / reset selection
		self.move = True
		self.busy = False			# Allow playback only in one mode: PlayEntry / PlayLast / PlayAll / ShuffleAll

		self.delayTimer = eTimer()
		try:
			self.delayTimer_conn = self.delayTimer.timeout.connect(self.updateInfoDelayed)
		except:
			self.delayTimer.callback.append(self.updateInfoDelayed)

		self.coverTimer = eTimer()
		try:
			self.coverTimer_conn = self.coverTimer.timeout.connect(self.showCoverDelayed)
		except:
			self.coverTimer.callback.append(self.showCoverDelayed)

		self.previewTimer = eTimer()
		try:
			self.previewTimer_conn = self.previewTimer.timeout.connect(self.showPreviewDelayed)
		except:
				self.previewTimer.callback.append(self.showPreviewDelayed)

		self.onShow.append(self.onDialogShow)
		self.onHide.append(self.onDialogHide)
		self["list"].onSelectionChanged.append(self.selectionChanged)

	def isProtected(self):
		try:
			return config.ParentalControl.setuppinactive.value and config.ParentalControl.config_sections.movie_list.value
		except:
			pass

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

	def CoolSingleGuide(self):
		try:
			from Plugins.Extensions.CoolTVGuide.CoolSingleGuide import CSGmain
			CSGmain(self.session)
		except: return

	def CoolEasyGuide(self):
		try:
			from Plugins.Extensions.CoolTVGuide.CoolEasyGuide import CEGmain
			CEGmain(self.session)
		except: return

	def CoolTimerList(self):
		from Screens.TimerEdit import TimerEditList
		self.session.open(TimerEditList)

	def CoolInfoLong(self):
		if config.EMC.InfoLong.value == "IMDbSearch":
			self.IMDbSearch()
		elif config.EMC.InfoLong.value == "EMC-TMDBInfo":
			self.EMCTMDBInfo()
		elif config.EMC.InfoLong.value == "TMDBInfo":
			self.TMDBInfo()
		elif config.EMC.InfoLong.value == "TMBDInfo":
			self.TMBDInfo()
		elif config.EMC.InfoLong.value == "CSFDInfo":
			self.CSFDInfo()
		else:
			self.IMDbSearch()

	def callHelpAction(self, *args):
		HelpableScreen.callHelpAction(self, *args)
		from EnhancedMovieCenter import EMCAbout
		self.session.open(MessageBox, EMCAbout, MessageBox.TYPE_INFO)

	def abort(self):
		if config.EMC.CoolStartHome.value:
			# Reload only if path is not movie home
			if self.currentPath != config.EMC.movie_homepath.value:
				#DelayedFunction(1000, self.changeDir, config.EMC.movie_homepath.value)
				self.currentPath = config.EMC.movie_homepath.value
				config.EMC.needsreload.value = True
		if self.playerInstance is not None:
			self.playerInstance.movieSelected(None)
		else:
			config.av.policy_43.cancel() # reload the default setting

			# Movie preview
			# Restore last service only if no player is active
			if self.lastservice:
				self.session.nav.playService(self.lastservice)
				self.lastservice = None
		if self.delayTimer.isActive():
			self.delayTimer.stop()
		if self.coverTimer.isActive():
			self.coverTimer.stop()
		if self.previewTimer.isActive():
			self.previewTimer.stop()

		# reset selected Files List, to reopen the list without the last selected
		self.resetSelectionList()

		self.close()

	def redFunc(self):
			self.execblueyellowbutton(config.EMC.movie_redfunc.value)

	def greenFuncShort(self):
		if config.EMC.movie_greenfunc.value != "ST":
			self.execblueyellowbutton(config.EMC.movie_greenfunc.value)
		else:
			self.toggleSortMode()

	def yellowFunc(self):
			self.execblueyellowbutton(config.EMC.movie_yellowfunc.value)

	def blueFunc(self):
			self.execblueyellowbutton(config.EMC.movie_bluefunc.value)

	def redFuncLong(self):
		self.execblueyellowbutton(config.EMC.movie_longredfunc.value)

	def greenFuncLong(self):
		if config.EMC.movie_greenfunc.value != "ST":
			self.execblueyellowbutton(config.EMC.movie_greenfunc.value)
		else:
			self.toggleSortOrder()

	def yellowFuncLong(self):
		self.execblueyellowbutton(config.EMC.movie_longyellowfunc.value)

	def blueFuncLong(self):
		self.execblueyellowbutton(config.EMC.movie_longbluefunc.value)

	def execblueyellowbutton(self, value):
		if value == "MH":
			self.returnService = None
			self["list"].resetSorting()
			self.changeDir(config.EMC.movie_homepath.value)
		elif value == "DL":
			self.coverAfterPreview()
			self.deleteFile()
		elif value == "MV":
			self.moveMovie()
		elif value == "AP":
			self.addPlaylist()
		elif value == "PL":
			self.playLast()
		elif value == "CS":
			self.imdb()
		elif value == "MI":
			self.dlMovieInfo()
		elif value == "CP":
			self.copyMovie()
		elif value == "E2":
			self.openE2Bookmarks()
		elif value == "TC":
			self.toggleCover()

	def coverAfterPreview(self):
		#test: show cover on cursormove if cover and preview is on
		if config.EMC.movie_preview.value:
			if config.EMC.movie_cover.value:
				self.cover = False
				self.toggleCover()

	def bqtPlus(self):
		if config.EMC.bqt_keys.value == "":
			self.moveTop()
		elif config.EMC.bqt_keys.value == "Skip":
			self.moveSkipUp()
		elif config.EMC.bqt_keys.value == "Folder":
			self.bqtNextFolder()

	def bqtMnus(self):
		if config.EMC.bqt_keys.value == "":
			self.moveEnd()
		elif config.EMC.bqt_keys.value == "Skip":
			self.moveSkipDown()
		elif config.EMC.bqt_keys.value == "Folder":
			self.bqtPrevFolder()

	def bqtNextFolder(self):
		dirlist = self.bqtListFolders()
		try:
			pos = (dirlist.index(self.currentPath) + 1) % len(dirlist)
		except:
			pos = 0
		self.setNextPath(dirlist[pos])

	def bqtPrevFolder(self):
		dirlist = self.bqtListFolders()
		try:
			pos = (dirlist.index(self.currentPath) - 1) % len(dirlist)
		except:
			pos = len(dirlist)-1
		self.setNextPath(dirlist[pos])

	def bqtListFolders(self):
		movie_homepath = os.path.realpath(config.EMC.movie_homepath.value)
		tmplist = [os.path.join(movie_homepath, f) for f in os.listdir(movie_homepath)]
		dirlist = []
		for i in tmplist:
			if os.path.isdir(i):
				dirlist.append(i)
		dirlist.sort()
		return dirlist

	def changeDir(self, path, service=None):
		path = os.path.normpath(path)
		self.returnService = service
		#TODOret
		if self.returnService:
			print "EMC ret chnSer " +str(self.returnService.toString())
		self.reloadList(path)

	def reloadListWithoutCache(self):
		# realod files and directories for current path without using cache
		if config.EMC.files_cache.value:
			self["list"].reloadDirList(self.currentPath)
		self.reloadList(self.currentPath)

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
				service = getPlayerService(self.currentPath)
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
		self.coverAfterPreview()
		self["list"].moveUp()
		self.updateAfterKeyPress()

	def moveDown(self):
		self.cursorDir = 1
		self.coverAfterPreview()
		self["list"].moveDown()
		self.updateAfterKeyPress()

	def pageUp(self):
		self.cursorDir = 0
		self.coverAfterPreview()
		self["list"].pageUp()
		self.updateAfterKeyPress()

	def pageDown(self):
		self.cursorDir = 0
		self.coverAfterPreview()
		self["list"].pageDown()
		self.updateAfterKeyPress()

	def moveTop(self):
		self.coverAfterPreview()
		self["list"].moveTop()
		self.updateAfterKeyPress()

	def moveSkipUp(self):
		self.coverAfterPreview()
		self.cursorDir = -1
		for _ in range(int(config.EMC.list_skip_size.value)):
			self["list"].moveUp()
		self.updateAfterKeyPress()

	def moveSkipDown(self):
		self.cursorDir = 1
		self.coverAfterPreview()
		for _ in range(int(config.EMC.list_skip_size.value)):
			self["list"].moveDown()
		self.updateAfterKeyPress()

	def moveEnd(self):
		self.coverAfterPreview()
		self["list"].moveEnd()
		self.updateAfterKeyPress()

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

	def openE2Bookmarks(self):
		self.session.openWithCallback(
			self.openBookmarksCB,
			LocationBox,
				windowTitle = _("E2 Bookmark"),
				text = _("Open E2 Bookmark path"),
				currDir = str(self.currentPath)+"/",
				bookmarks = config.movielist.videodirs,
				autoAdd = False,
				editDir = True,
				inhibitDirs = ["/bin", "/boot", "/dev", "/etc", "/lib", "/proc", "/sbin", "/sys", "/usr", "/var"],
				minFree = 0 )

	def openEMCBookmarks(self):
		#TODO Use a choicebox or a LocationBox with simulated bookmarks
		self.session.openWithCallback(
			self.openBookmarksCB,
			MovieMenu,
				"emcBookmarks",
				self,
				self["list"],
				None,
				self["list"].makeSelectionList(),
				self.currentPath )

	def openBookmarksCB(self, path=None):
		if path is not None:
			self.changeDir(path)

	def menuCallback(self, selection=None, parameter=None):
		if selection is not None:
			if selection == "Play last": self.playLast()
			elif selection == "emcPlaylist": self.openPlaylistOptions()
			elif selection == "addPlaylist": self.addPlaylist()
			elif selection == "playPlaylist": self.playPlaylist()
			elif selection == "playPlaylistRandom": self.playPlaylist(True)
			elif selection == "showPlaylist": self.showPlaylist()
			elif selection == "delPlaylist": self.delPlaylist()
			elif selection == "playall": self.playAll()
			elif selection == "shuffleall": self.shuffleAll()
			elif selection == "Movie home": self.changeDir(config.EMC.movie_homepath.value)
			elif selection == "Copy Movie": self.copyMovie()
			elif selection == "Move Movie": self.moveMovie()
			elif selection == "Movie Information": self.dlMovieInfo()
			elif selection == "reload": self.initList()
			elif selection == "plugin": self.onDialogShow()
			elif selection == "setup": self.onDialogShow()
			elif selection == "ctrash": purgeExpired()
			elif selection == "trash": self.changeDir(config.EMC.movie_trashcan_path.value)
			elif selection == "del": self.deleteFile()
			elif selection == "delete": self.deleteFile(True)
			elif selection == "cutlistmarker": self.removeCutListMarker()
			elif selection == "resMarker": self.resetMarker()
			elif selection == "openE2Bookmarks": self.openE2Bookmarks()
			elif selection == "removeE2Bookmark": self.deleteE2Bookmark(parameter)
			elif selection == "openEMCBookmarks": self.openEMCBookmarks()
			elif selection == "removeEMCBookmark": self.deleteEMCBookmark(parameter)
			elif selection == "dirup": self.directoryUp()
			elif selection == "oscripts": self.openScriptMenu()
			elif selection == "markall": self.markAll()
			elif selection == "updatetitle": self.updateTitle()
			elif selection == "imdb": self.imdb()
			elif selection == "imdbdirectory": self.imdbDirectory()
			elif selection == "rename": self.rename()
			elif selection == "emptytrash": purgeExpired(emptyTrash=True)
			elif selection == "reloadwithoutcache": self.reloadListWithoutCache()

	def openPlaylistOptions(self):
		# first we check if playlist exists
		playlist = False
		if not emcplaylist.isCurrentPlaylistEmpty():
			playlist = True
		current = self.getCurrent()
		self.session.openWithCallback(self.menuCallback, MovieMenu, "emcPlaylist", self, self["list"], current, self["list"].makeSelectionList(), self.currentPath, playlist)

	def openMenu(self):
		# first we check if playlist exists
		playlist = False
		if not emcplaylist.isCurrentPlaylistEmpty():
			playlist = True
		current = self.getCurrent()
		#if not self["list"].currentSelIsPlayable(): current = None
		self.session.openWithCallback(self.menuCallback, MovieMenu, "normal", self, self["list"], current, self["list"].makeSelectionList(), self.currentPath, playlist)

	def openMenuPlugins(self):
		# first we check if playlist exists
		playlist = False
		if not emcplaylist.isCurrentPlaylistEmpty():
			playlist = True
		current = self.getCurrent()
		if self["list"].currentSelIsPlayable():
			self.session.openWithCallback(self.menuCallback, MovieMenu, "plugins", self, self["list"], current, self["list"].makeSelectionList(), self.currentPath, playlist)

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

	def imdb(self):
		filelist = []

		# Get only the selections without a fallback to current
		selectedlist = self["list"].makeSelectionList(False)
		if selectedlist:
			# The selectedList only contains the services
			filelist = [ (service.getName() , service.getPath() ) for service in selectedlist ]
			# Collect imdb data
			self.session.open(EMCImdbScan, filelist)
			self.reloadList(self.currentPath)
			self.moveToIndex(0)
		else:
			self.session.openWithCallback(self.imdbCallback, MessageBox, _("Cover search with all Files in Subdirectories?\n\nThis may take a while on huge Disks, or Directories!"), MessageBox.TYPE_YESNO, 10)

	def imdbCallback(self, result):
		filelist = []

		if result:
			# Simulate a recursive reload to get all files and titles
			# walk through entire tree below current path. Might take a bit long on huge disks...
			selectedlist = self["list"].reload(self.currentPath, simulate=True, recursive=True)
			filelist = [ (title , path ) for (service, sorttitle, date, title, path, selnum, length, ext, cutnr, sorteventtitle, eventtitle, metaref, sortyear, sortmonth, sortday, sorthour, sortmin) in selectedlist ]
		else:
			filelist = [ (title , path ) for (service, sorttitle, date, title, path, selnum, length, ext, cutnr, sorteventtitle, eventtitle, metaref, sortyear, sortmonth, sortday, sorthour, sortmin) in self["list"].getList() if ext in plyAll ]

		# Collect imdb data
		self.session.open(EMCImdbScan, filelist)
		self.reloadList(self.currentPath)
		self.moveToIndex(0)

	def imdbDirectory(self):
		filelist = []

		if self["list"].currentSelIsDirectory():
			current = self.getCurrent()
			filelist = [ (self["list"].getCurrentSelName() , current.getPath() ) ]

		# Collect imdb data
		self.session.open(EMCImdbScan, filelist, True)
		self.reloadList(self.currentPath)
		self.moveToIndex(0)

	def markAll(self):
		for i in xrange( len (self["list"]) ):
			self["list"].toggleSelection( index=i )

	def unUsed(self):
		self.session.open(MessageBox, _("No functionality set..."), MessageBox.TYPE_INFO)

	def updateAfterKeyPress(self):
		#test: show cover on cursormove if cover and preview is on
		#self.coverAfterPreview()
		if self.returnService:
			# Service was stored for a pending update,
			# but user wants to move, copy, delete it,
			# so we have to update returnService
			if self.tmpSelList:
				#TODOret
				#print "EMC ret updSe1 " +str(self.returnService.toString())
				#print len(self.tmpSelList)
				#print self.getCurrent().toString()
				self.returnService = self.getNextSelectedService(self.getCurrent(), self.tmpSelList)
				#TODOret
				#print "EMC ret updSer " +str(self.returnService.toString())

	def selectionChanged(self):
		if self.multiSelectIdx:
			self.multiSelect( self.getCurrentIndex() )
		self.updateInfo()

	def updateInfo(self):
		self.resetInfo()
		self.delayTimer.start(int(config.EMC.movie_descdelay.value), True)

		if self.already_shown and self.shown:
			# Movie cover
			if config.EMC.movie_cover.value:
				# Show cover only for media files and directories
				#if self["list"].currentSelIsPlayable() or self["list"].currentSelIsDirectory():
				self.coverTimer.start(int(config.EMC.movie_cover_delay.value), True)
			# Movie preview
			if config.EMC.movie_preview.value:
				# Play preview only if it is a video file
				#if self["list"].currentSelIsPlayable():
				if self.playerInstance is None:
					#print "EMC: start preview timer"
					self.previewTimer.start(int(config.EMC.movie_preview_delay.value), True)

	def updateInfoDelayed(self):
		self.updateTitle()
		current = self.getCurrent()
		if current and not self["list"].serviceMoving(current) and not self["list"].serviceDeleting(current):
			self.updateEventInfo( current )
			#OE2.0 Bug start_new_thread
			#t = Thread(target=self.updateEventInfo, args=(current,))
			#t.start()

	def resetInfo(self, preview=True):
		print "EMC: resetInfo"
		if self.delayTimer.isActive():
			self.delayTimer.stop()
		if self.coverTimer.isActive():
			self.coverTimer.stop()
		if self.previewTimer.isActive():
			self.previewTimer.stop()

		self.updateTitle()
		self.updateEventInfo(None)

		if preview and self.already_shown and self.shown:
			if config.EMC.movie_cover.value:
				self.showCover(None)
			if config.EMC.movie_preview.value:
				# Avoid movie preview if player is running
				if self.playerInstance is None:
					print "EMC: reset preview"
					self.showPreview(None)

	def showCoverDelayed(self):
		#print "EMC showCoverDelayed"
		self.showCover( self.getCurrent() )

	def showPreviewDelayed(self):
		# Avoid movie preview if player is running
		#print "EMC showPreviewDelayed"
		self.showPreview( self.getCurrent() )

	def updateTitle(self):
		title = ""
		if self.multiSelectIdx:
			self.setTitle(_("*** Multiselection active ***"))
			return

		# Display the free space
		if os.path.exists(self.currentPath):
			try:
				stat = os.statvfs(self.currentPath)
				free = (stat.f_bavail if stat.f_bavail!=0 else stat.f_bfree) * stat.f_bsize / 1024 / 1024
				if free >= 10240:	#unit in Giga bytes if more than 10 GB free
					title = "(%d GB) " %(free/1024)
				else:
					title = "(%d MB) " %(free)
			except OSError:
				title = "(? GB) "

		# Display the current path
		path = self.currentPath
		path = path.replace(config.EMC.movie_homepath.value, "...")
		# Very bad but there can be both encodings
		# E2 recordings are always in utf8
		# User files can be in cp1252
		#TODO Is there no other way?
		try:
			path.decode('utf-8')
		except UnicodeDecodeError:
			try:
				path = path.decode("cp1252").encode("utf-8")
			except UnicodeDecodeError:
				path = path.decode("iso-8859-1").encode("utf-8")
		title += path or "/"

		# Display the actual sorting mode
		from Plugins.Extensions.EnhancedMovieCenter.plugin import sort_modes
		actsort = self["list"].getSorting()
		for k, v in sort_modes.items():
			if v[1] == actsort:
				title += " [" + str(k) + "]"
				break

		# Display a permanent sort marker if it is set
		perm = self["list"].isEqualPermanentSort()
		if perm == True:
			title += " <P>"

		self.setTitle(title)

	def toggleCover(self):
		if config.EMC.movie_cover.value:
			if self.cover:
				self.cover = False
				self["Cover"].hide()
				self["CoverBg"].hide()
			else:
				self.cover = True
				self["Cover"].show()
				self["CoverBg"].show()
		self.initButtons()

	def toggleSortMode(self):
		if self.browsingVLC(): return
		#WORKAROUND E2 doesn't send dedicated short or long pressed key events
		if self.toggle == False:
			self.toggle = True
			return
		service = self.getNextSelectedService(self.getCurrent())
		self.returnService = service
		self["list"].toggleSortingMode()
		self.initButtons()
		self.initCursor()
		self.updateInfo()

	def toggleSortOrder(self):
		if self.browsingVLC(): return
		self.toggle = False
		service = self.getNextSelectedService(self.getCurrent())
		self.returnService = service
		self["list"].toggleSortingOrder()
		self.initButtons()
		self.initCursor()
		self.updateInfo()

	def toggleSelectionList(self):
		#WORKAROUND E2 doesn't send dedicated short or long pressed key events
		if self["list"].currentSelIsDirectory():
			self.moveDirectory()
		else:
			if self.toggle == False:
				self.toggle = True
				return
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
				#self["list"].toggleSelection(service) # orig, let it and wait for tests from others
				# unselect for reopen the list without the last corsor-pos is selected
				self["list"].unselectService(service)

	def toggleProgress(self, service=None):
		if self.multiSelectIdx:
			self.multiSelectIdx = None
			self.updateTitle()

		self["list"].toggleProgress(service)

	def IMDbSearch(self):
		# first get current path without extension of selected entry, for saving imdb-details as new function 
		path = self["list"].getCurrentSelDir()
		savepath = os.path.splitext(path)[0]

		# now we check if the selected entry has saved details from imdb, to use it directly
		# at the moment without saved "poster.jpg"
		detailpath = savepath + ".imdbquery2.html"
		if os.path.exists(detailpath):
			localfile = True
		else:
			localfile = False

		name = ''
		if (self["list"].getCurrentSelName()):
			name = (self["list"].getCurrentSelName())
		name = getMovieNameWithoutPhrases(getMovieNameWithoutExt(name))
		try:
			from Plugins.Extensions.IMDb.plugin import IMDB
		except ImportError:
			IMDB = None

		# now try open imdb-plugin to see the details without to open the search-Site
		# TODO: we need a check to get which version is installed, like "getargs"
		# otherwise we dont know if newer options are available !!!
		if IMDB is not None:
			try:
				if localfile:
					self.session.open(IMDB, name, False, True, savepath, detailpath)
				else:
					self.session.open(IMDB, name, False, True, savepath)
			except Exception, e:
				print('[EMC] EMCImdb-version exception failure: ', str(e))
				self.session.open(IMDB, name, False)

	def EMCTMDBInfo(self):
		service = self["list"].getCurrent()
		if service:
			path = service.getPath()
			if path and path != config.EMC.movie_trashcan_path.value:
				if not path.endswith("/..") and not path.endswith("/Latest Recordings"):
					name = service.getName()
					spath = getInfoFile(path)[0]
					self.session.open(MovieInfoTMDb, name, spath)

	def TMDBInfo(self):
		name = ''
		if (self["list"].getCurrentSelName()):
			name = (self["list"].getCurrentSelName())
		try:
			from Plugins.Extensions.TMDb.plugin import TMDbMain
		except ImportError:
			TMDbMain = None
		if TMDbMain is not None:
			name = getMovieNameWithoutPhrases(getMovieNameWithoutExt(name))
			self.session.open(TMDbMain, name)

	def TMBDInfo(self):
		name = ''
		if (self["list"].getCurrentSelName()):
			name = (self["list"].getCurrentSelName())
		try:
			from Plugins.Extensions.TMBD.plugin import TMBD
		except ImportError:
			TMBD = None
		if TMBD is not None:
			name = getMovieNameWithoutPhrases(getMovieNameWithoutExt(name))
			self.session.open(TMBD, name)

	def CSFDInfo(self):
		name = ''
		if self["list"].getCurrentSelName():
			name = self["list"].getCurrentSelName()
		try:
			from Plugins.Extensions.CSFD.plugin import CSFD
		except ImportError:
			CSFD = None
		if CSFD is not None:
			name = getMovieNameWithoutPhrases(getMovieNameWithoutExt(name))
			self.session.open(CSFD, name, False)

	def rename(self):
		self.session.openWithCallback(
							self.reloadListWithoutCache,
							MovieRetitle,
							self["list"].makeSelectionList() or self.getCurrent() )

	def showEventInformation(self):
		from ServiceReference import ServiceReference

		# Get our customized event
		# first we check if the first entry is "..", securitly for possible BSOD on openXTA-image
		try:
			if self["list"].getCurrentSelDir().endswith("/.."):
				pass
			else:
				evt = self["list"].getCurrentEvent()
				if evt:
					self.session.open(IMDbEventViewSimple, evt, ServiceReference(self.getCurrent()))
		except Exception, e:
			print('[EMC] showEventInformation exception failure: ', str(e))
			pass

	def openBludiscPlayer(self, blupath):
		try:
			from Plugins.Extensions.BludiscPlayer.plugin import BludiscMenu
		except ImportError:
			BludiscMenu = None
		if BludiscMenu is not None:
			self.session.open(BludiscMenu, bd_mountpoint=blupath)
		else:
			self.session.open(MessageBox,"Plugin not found!", MessageBox.TYPE_ERROR)

	def initCursor(self, ifunknown=True):
		if self.returnService:
			# Move to next or last selected entry
			self.moveToService(self.returnService)
			self.returnService = None
			#TODOret
			if self.returnService:
				print "EMC ret retSer " +str(self.returnService.toString())

		elif ifunknown and self.playerInstance:
			# Get current service from movie player
			service = self.playerInstance.currentlyPlayedMovie()
			if service is not None:
				self.moveToService(service)

		elif ifunknown:
			# Select first entry
			#TODOret
			print "EMC ret initCursor movetop correct ????"
			self.moveTop()

		self.updateInfo()

	def setReturnCursor(self):
		if self.returnService:
			#TODOret
			print "EMC ret setCur " +str(self.returnService.toString())
			# Move to next or last selected entry
			self.moveToService(self.returnService)

	def onDialogShow(self):
		# Movie preview
		self.lastservice = self.lastservice or self.session.nav.getCurrentlyPlayingServiceReference()

		self.initButtons()

		if config.EMC.needsreload.value:
			config.EMC.needsreload.value = False
			self["list"].resetSorting()
			self.initList()

		if config.EMC.movie_reload.value \
			or len(self["list"]) == 0:
			self.initList()

		#elif config.EMC.CoolStartHome.value:
		#	# Reload only if path is not movie home
		#	if self.currentPath != config.EMC.movie_homepath.value:
		#		self.changeDir(config.EMC.movie_homepath.value)

		else:
			# Refresh is done automatically
			#self["list"].refreshList()
			self.initCursor(False)
			self.updateInfo()

	def onDialogHide(self):
		self.returnService = self.getCurrent() #self.getNextSelectedService(self.getCurrent(), self.tmpSelList)

	def getCurrentIndex(self):
		return self["list"].getCurrentIndex()

	def moveToIndex(self, index):
		self.multiSelectIdx = None
		self["list"].moveToIndex(index)
		self.updateInfo()

	def moveToService(self, service):
		self.multiSelectIdx = None
		self["list"].moveToService(service)
		self.updateInfo()

	def removeService(self, service):
		self["list"].removeService(service)

	def removeServiceOfType(self, service, type):
		self["list"].removeServiceOfType(service, type)

	def getNextSelectedService(self, current, selectedlist=None):
		return self["list"].getNextSelectedService(current, selectedlist)

	def loading(self, loading=True):
		if loading:
			self["list"].hide()
			self["wait"].setText( _("Reading directory...") )
			self["wait"].show()
		else:
			self["wait"].hide()
			self["list"].show()

	def initButtons(self):
		# Initialize buttons
		helptext = []

		#TODO get color from MovieCenter

		# Display the next sorting state
		from Plugins.Extensions.EnhancedMovieCenter.plugin import sort_modes
		#sorts = list( set( [sort for sort, desc in sort_choices] ) )
		sorts = [ v[1] for v in sort_modes.values() ]
		#print sorts
		# Toggle the mode
		mode, order = self["list"].getSorting()
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
		#print mode

		# Green button
		if config.EMC.movie_greenfunc.value == "ST":
			greenhelptext = _("Sort Mode")
			greenlonghelptext = _("Sort Order")

			for k, v in sort_modes.items():
				#print v[1], (mode, order)
				if v[1] == (mode, order):
#					self["key_green"].text = v[2]
					greentext = v[2]
#					self["key_green"].text = greentext
					break
			else:
#				self["key_green"].text = ""
				greentext = ""
		else:
			greentext = config.EMC.movie_greenfunc.description[config.EMC.movie_greenfunc.value]
			greenhelptext = greentext
			greenlonghelptext = greentext
		self["key_green"].text = greentext

		# Red button
		redhelptext = config.EMC.movie_redfunc.description[config.EMC.movie_redfunc.value]
		redlonghelptext = config.EMC.movie_longredfunc.description[config.EMC.movie_longredfunc.value]
		if config.EMC.movie_redfunc.value == "TC":
			if config.EMC.movie_cover.value:
				if self.cover:
					redtext = _("Hide Cover")
				else:
					redtext = _("Show Cover")
			else:
				redtext = _("Button disabled")
				redhelptext = _("Cover disabled in EMC-Setup")
		else:
			redtext = redhelptext
		self["key_red"].text = redtext

		# Yellow button
		yellowhelptext = config.EMC.movie_yellowfunc.description[config.EMC.movie_yellowfunc.value]
		yellowlonghelptext = config.EMC.movie_longyellowfunc.description[config.EMC.movie_longyellowfunc.value]
		if config.EMC.movie_yellowfunc.value == "TC":
			if config.EMC.movie_cover.value:
				if self.cover:
					yellowtext = _("Hide Cover")
				else:
					yellowtext = _("Show Cover")
			else:
				yellowtext = _("Button disabled")
				yellowhelptext = _("Cover disabled in EMC-Setup")
		else:
			yellowtext = yellowhelptext
		self["key_yellow"].text = yellowtext

		# Blue button
		bluehelptext = config.EMC.movie_bluefunc.description[config.EMC.movie_bluefunc.value]
		bluelonghelptext = config.EMC.movie_longbluefunc.description[config.EMC.movie_longbluefunc.value]
		if config.EMC.movie_bluefunc.value == "TC":
			if config.EMC.movie_cover.value:
				if self.cover:
					bluetext = _("Hide Cover")
				else:
					bluetext = _("Show Cover")
			else:
				bluetext = _("Button disabled")
				bluehelptext = _("Cover disabled in EMC-Setup")
		else:
			bluetext = bluehelptext
		self["key_blue"].text = bluetext

		helptext = [redhelptext, redlonghelptext, greenhelptext, greenlonghelptext, yellowhelptext, yellowlonghelptext, bluehelptext, bluelonghelptext]
		return helptext

	def initList(self):
		self.initPig()
		# Initialize list
		self.reloadList()

	def triggerReloadList(self):
		#IDEA:
		# Short TV refresh list - reloads only progress
		# Long TV reload  list - finds new movies
		self.returnService = self.getNextSelectedService(self.getCurrent(), self.tmpSelList)
		#TODOret
		if self.returnService:
			print "EMC ret triSer " +str(self.returnService.toString())
		movieFileCache.delPathFromCache(self.currentPath)
		self.reloadList()

	def reloadList(self, path=None):
		self.multiSelectIdx = None

		self.resetInfo()

		if config.EMC.moviecenter_loadtext.value:
			self.loading()

		self.__reloadList(path)
		#OE2.0 Bug start_new_thread
		#t = Thread(target=self.reloadListThread, args=(path,))
		#t.start()

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

		self.updateInfo()

	#############################################################################
	# Playback functions
	#
#	def setPlayerInstance(self, player):
#		try:
#			self.playerInstance = player
#		except Exception, e:
#			emcDebugOut("[EMCMS] setPlayerInstance exception:\n" + str(e))

	def openPlayer(self, playlist, playall=False):
		# Force update of event info after playing movie
		# Don't reset if movie preview is active
		self.resetInfo(preview=False)
		self.loading(False)

		# force a copy instead of an reference!
		self.lastPlayed = playlist[:]
		playlistcopy = playlist[:]

		# Workaround for MoviePreview with play problem, events will not be attached to the correct nav, eof recognition won't work
		if config.EMC.movie_preview.value:
			self.session.nav.stopService()

		# Start Player
		if self.playerInstance is None:
			self.close(playlistcopy, playall, self.lastservice)
			self.busy = False
		else:
			self.playerInstance.movieSelected(playlist, playall)
			self.busy = False
			self.close()

	def entrySelected(self, playall=False):
		current = self.getCurrent()
		if current is not None:
			# Save service
			#self.returnService = self.getCurrent() #self.getNextSelectedService(self.getCurrent(), self.tmpSelList)

			# Think about MovieSelection should only know about directories and files
			# All other things should be in the MovieCenter

			# detectBLUStructure
			path = current.getPath()
			if detectBLUStructure(os.path.dirname(path)):
				self.openBludiscPlayer(os.path.dirname(path))

			#detectBLUISO
			elif detectBLUISO(path):
				if not os.path.exists('/tmp/EMCISO/'):
					os.system('mkdir /tmp/EMCISO/')
				os.system('umount -d -f /tmp/EMCISO') #not really necessary, but just to play safe!
				os.system('mount -r "' + path + '" ' + '/tmp/EMCISO')
				self.openBludiscPlayer(os.path.realpath('/tmp/EMCISO/'))

			elif self["list"].currentSelIsVirtual():
				# Open folder and reload movielist
				self.setNextPath( self["list"].getCurrentSelDir() )
			elif self.browsingVLC():
				# TODO full integration of the VLC Player
				entry = self["list"].list[ self.getCurrentIndex() ]
				self.vlcMovieSelected(entry)
			elif os.path.splitext(path)[1] in extPlaylist:
				self.playlistSelected(path)
			else:
				playlist = self["list"].makeSelectionList()
				if not self["list"].serviceMoving(playlist[0]) and not self["list"].serviceDeleting(playlist[0]):
					# Avoid starting several times in different modes
					if self.busy:
						self.busy = False
						return
					self.busy = True
					self.openPlayer(playlist, playall)
				else:
					self.session.open(MessageBox, _("File not available."), MessageBox.TYPE_ERROR, 10)

	def playlistSelected(self, path):
		playlist = []
		if fileExists(path):
			plist = open(path, "r")
			if os.path.splitext(path)[1] == ".m3u":
				while True:
					service = plist.readline()
					if service == "":
						break
					service = service.replace('\n','')
					servicepath = os.path.dirname(path) + "/" + service
					ext = os.path.splitext(service)[1]
					playlist.append(getPlayerService(servicepath, service, ext))
			else:
				while True:
					service = plist.readline()
					if service == "":
						break
					service = service.replace('\n','')
					spos = service.find('/')
					servicepath = service[spos:]
					service = servicepath.split('/')[-1]
					ext = os.path.splitext(servicepath)[1]
					playlist.append(getPlayerService(servicepath, service, ext))

		if self.playerInstance is None:
			self.close(playlist, False, self.lastservice)
			self.busy = False
		else:
			self.playerInstance.movieSelected(playlist, False)
			self.busy = False
			self.close()

	def addPlaylist(self):
		selectedlist = self["list"].makeSelectionList()[:]
		if selectedlist:
			add = ""
			exist = ""
			for service in selectedlist:
				name = service.getName()
				path = service.getPath()
				added = emcplaylist.addToCurrentPlaylist(path, name, service)
				if len(selectedlist) >= 1:
					if added:
						add += "%s\n" % name
					else:
						exist += "%s\n" % name
				self["list"].unselectService(service)
			if config.EMC.playlist_message.value:
				if len(selectedlist) == 1:
					if added:
						mes = _("File added to current Playlist.")
					else:
						mes = _("File exists in current Playlist.")
				else:
					if exist == "":
						mes = _("Files added to current Playlist.")
					elif exist != "" and add != "":
						mes =  _("Files added to current Playlist:\n%s\n\nFiles exists in current Playlist:\n%s") % (add, exist)
					elif exist != "" and add == "":
						mes = _("Files exists in current Playlist:\n%s") % exist
				self.session.open(MessageBox, mes, MessageBox.TYPE_INFO, 2, True)

	def playPlaylist(self, random=False):
		playlist = []
		tmpplaylist = []
		if emcplaylist.getCurrentPlaylist() != {}:
			for x in emcplaylist.getCurrentPlaylist():
				tmpplaylist.append(emcplaylist.getCurrentPlaylistEntry(x))

			tmpplaylist.sort( key=lambda x: (x[0]) )

			for x in tmpplaylist:
				playlist.append(x[2])

			if random:
				shuffle(playlist)

			if self.playerInstance is None:
				self.close(playlist, False, self.lastservice)
				self.busy = False
			else:
				self.playerInstance.movieSelected(playlist, False)
				self.busy = False
				self.close()

	def showPlaylist(self):
		self.session.open(EMCPlaylistScreen)

	def delPlaylist(self):
		emcplaylist.delCurrentPlaylist()

	def playLast(self):
		# Avoid starting several times in different modes
		if self.busy:
			self.busy = False
			return
		if self.multiSelectIdx:
			self.multiSelectIdx = None
			self.updateTitle()
		if self.lastPlayed is None:
			self.session.open(MessageBox, _("Last played movie/playlist not available..."), MessageBox.TYPE_ERROR, 10)
		else:
			self.busy = True
			# Show a notification to indicate the Play function
			self["wait"].setText( _("Play last movie starting") )
			self["wait"].show()
			#DelayedFunction(1000, self.loading, False)
			DelayedFunction(1000, self.openPlayer, self.lastPlayed)

	def playAll(self):
		# Avoid starting several times in different modes
		if self.busy:
			self.busy = False
			return
		self.busy = True
		if self.multiSelectIdx:
			self.multiSelectIdx = None
			self.updateTitle()
		# Initialize play all
		service = self.getCurrent()
		playlist = [service]
		playall = self["list"].getNextService(service)
		# Show a notification to indicate the Play function
		self["wait"].setText( _("Play All starting") )
		self["wait"].show()
		#DelayedFunction(1000, self.loading, False)
		DelayedFunction(1000, self.openPlayer, playlist, playall)

	def shuffleAll(self):
		# Avoid starting several times in different modes
		if self.busy:
			self.busy = False
			return
		self.busy = True
		if self.multiSelectIdx:
			self.multiSelectIdx = None
			self.updateTitle()
		# Initialize shuffle all
		service = self.getCurrent()
		playlist = [service]
		shuffleall = self["list"].getRandomService(service)
		# Show a notification to indicate the Shuffle function
		self["wait"].setText( _("Shuffle All starting") )
		self["wait"].show()
		#DelayedFunction(1000, self.loading, False)
		DelayedFunction(1000, self.openPlayer, playlist, shuffleall)

	def lastPlayedCheck(self, service):
		try:
			if self.lastPlayed is not None:
				if service in self.lastPlayed:
					self.lastPlayed.remove(service)
				if len(self.lastPlayed) == 0:
					self.lastPlayed = None
		except Exception, e:
			emcDebugOut("[EMCMS] lastPlayedCheck exception:\n" + str(e))

	#############################################################################
	# Record control functions
	#
	#def isRecording(self, service):
	#	path = service.getPath()
	#	if path:
	#		return self["list"].recControl.isRecording(path)
	#	else:
	#		return False

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

	def moveRecCheck(self, service, targetPath):
		try:
			path = service.getPath()
			if self["list"].recControl.isRecording(path):
				self["list"].recControl.fixTimerPath(path, path.replace(self.currentPath, targetPath))
		except Exception, e:
			emcDebugOut("[EMCMS] moveRecCheck exception:\n" + str(e))

	#############################################################################
	# File IO functions
	#TODO Move all file operation functions to a separate class
	#
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

	def resetMarker(self):
		self.resetSelectionList()

	def mountpoint(self, path, first=True):
		if first: path = os.path.realpath(path)
		if os.path.ismount(path) or len(path)==0: return path
		return self.mountpoint(os.path.dirname(path), False)

	def deleteFile(self, permanently=False):
		if self.multiSelectIdx:
			self.multiSelectIdx = None
			self.updateTitle()
		if self.browsingVLC(): return
		movieFileCache.delPathFromCache(self.currentPath)
		self.permanentDel  = permanently or not config.EMC.movie_trashcan_enable.value
		self.permanentDel |= self.currentPath == config.EMC.movie_trashcan_path.value
		self.permanentDel |= self.mountpoint(self.currentPath) != self.mountpoint(config.EMC.movie_trashcan_path.value)
		current = self.getCurrent()	# make sure there is atleast one entry in the list
		if current is not None:
			selectedlist = self["list"].makeSelectionList()[:]
			single = len(selectedlist) == 1 and current==selectedlist[0]
			if single and self["list"].currentSelIsDirectory():
				if not config.EMC.movie_trashcan_enable.value or config.EMC.movie_delete_validation.value or self.permanentDel:
					path = current.getPath()
					movieFileCache.delPathFromCache(path)
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

			elif single and self["list"].currentSelIsE2Bookmark():
				# Delete a single E2 bookmark
				self.deleteE2Bookmark(current)
			elif single and self["list"].currentSelIsEMCBookmark():
				# Delete a single EMC bookmark
				self.deleteEMCBookmark(current)

			else:
				if self["list"].serviceBusy(selectedlist[0]): return
				if selectedlist and len(selectedlist)>0:
					self.recsToStop = []
					self.remRecsToStop = False
					for service in selectedlist:
						path = service.getPath()
						movieFileCache.delPathFromCache(os.path.dirname(path))
						if self["list"].recControl.isRecording(path):
							self.recsToStop.append(path)
						if config.EMC.remote_recordings.value and self["list"].recControl.isRemoteRecording(path):
							self.remRecsToStop = True
					if len(self.recsToStop)>0:
						self.stopRecordQ()
					else:
						self.deleteMovieQ(selectedlist, self.remRecsToStop)

	def deleteE2Bookmark(self, service):
		if service:
			path = service.getPath()
			if self.isE2Bookmark(path):
				if config.EMC.movie_delete_validation.value:
					self.session.openWithCallback(
							boundFunction(self.deleteE2BookmarkConfirmed, service),
							MessageBox,
							_("Do you really want to remove your bookmark\n%s?") % (path) )
				else:
					self.deleteE2BookmarkConfirmed(service, True)

	def deleteE2BookmarkConfirmed(self, service, confirm):
		if confirm and service and config.movielist and config.movielist.videodirs:
			path = service.getPath()
			movieFileCache.delPathFromCache(os.path.dirname(path))
			if self.removeE2Bookmark(path):
				# If service is not in list, don't care about it.
				self.removeServiceOfType(service, cmtBME2)
				self.setReturnCursor()

	def deleteEMCBookmark(self, service):
		if service:
			path = service.getPath()
			movieFileCache.delPathFromCache(os.path.dirname(path))
			if self.isEMCBookmark(path):
				if config.EMC.movie_delete_validation.value:
					self.session.openWithCallback(
							boundFunction(self.deleteEMCBookmarkConfirmed, service),
							MessageBox,
							_("Do you really want to remove your bookmark\n%s?") % (path) )
				else:
					self.deleteEMCBookmarkConfirmed(service, True)

	def deleteEMCBookmarkConfirmed(self, service, confirm):
		if confirm and service:
			path = service.getPath()
			movieFileCache.delPathFromCache(os.path.dirname(path))
			if self.removeEMCBookmark(path):
				# If service is not in list, don't care about it.
				self.removeServiceOfType(service, cmtBMEMC)
				self.setReturnCursor()

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
								self.checkExt,
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
									self.checkExt,
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

	def checkExt(self, confirmed):
		# we make it for more than one file, so we use this for all delete-ways in the future
		other = ""
		otherCount = 0
		otherFiles = False
		if confirmed:
			entrycount = len(self.tmpSelList)
			if entrycount == 1:
				nameCount = 0
				service = self.tmpSelList[0]
				path = os.path.splitext( service.getPath() )[0]
				# before we go, let us check if other mediafiles with the same name exists
				# if they dont exists, we go directly to delete with all others files they need it
				for x in extVideo:
					f = path + str(x)
					if fileExists(f):
						nameCount += 1
				if nameCount <= 1:
					self.deleteOtherConfimation(True)
				else:
					# we search for other files for this file, like covers, etc.
					extsOther = [".eit", ".jpg", ".txt", ".poster.jpg", ".imdbquery2.html"]
					for x in extsOther:
						f = path + str(x)
						if fileExists(f):
							other += "%s\n" % f
							otherFiles = True
					if otherFiles:
						otherMes = _("The following files are used for other entrys in List !\n\nAlso delete these files?\n\n%s") % other
						self.deleteOtherQ(otherMes)
					else:
						self.deleteMovieConfimation(True)

			if entrycount > 1:
				checkList = []
				pathList = []
				for service in self.tmpSelList:
					pathList.append(service.getPath())

				for service in self.tmpSelList:
					nameCount = 0
					path = os.path.splitext( service.getPath() )[0]
					# before we go, let us check if other mediafiles with the same name exists
					# if they dont exists, we go directly to delete with all others files they need it
					for x in extVideo:
						f = path + str(x)
						if fileExists(f):
							if f == service.getPath():
								nameCount += 1
							if f not in pathList:
								nameCount += 1
					if nameCount > 1:
						checkList.append(service)

				if checkList != []:
					self.tmpSelListOther = checkList

				if self.tmpSelListOther is not None:
					for x in self.tmpSelListOther:
						path = os.path.splitext( x.getPath() )[0]
						extsOther = [".eit", ".jpg", ".txt", ".poster.jpg", ".imdbquery2.html"]
						for x in extsOther:
							f = path + str(x)
							if fileExists(f):
								otherCount += 1
								if otherCount <= 9:
									other += "%s\n" % f
								if otherCount == 10:
									other += "%s\n...." % f
								otherFiles = True

					if otherFiles:
						otherMes = _("The following files are used for other entrys in List !\n\nAlso delete these files?\n\n%s") % other
						self.deleteOtherListQ(otherMes)
					else:
						self.deleteMovieConfimation(True)
				else:
					self.deleteOtherListConfimation(True)

	def deleteOtherQ(self, otherMes):
		self.session.openWithCallback(self.deleteOtherConfimation, MessageBox, otherMes, MessageBox.TYPE_YESNO )

	def deleteOtherConfimation(self, confirmed):
		if confirmed:
			self.deleteAllOther = True
		else:
			self.deleteAllOther = False
		self.deleteMovieConfimation(True)

	def deleteOtherListQ(self, otherMes):
		self.session.openWithCallback(self.deleteOtherListConfimation, MessageBox, otherMes, MessageBox.TYPE_YESNO )

	def deleteOtherListConfimation(self, confirmed):
		if confirmed:
			self.deleteAllOther = True
			self.deleteAllOtherList = True
		else:
			self.deleteAllOther = True
			self.deleteAllOtherList = False
		self.deleteMovieConfimation(True)

	def deleteMovieConfimation(self, confirmed):
		current = self.getCurrent()
		pathname = os.path.dirname(current.getPath())
		movieFileCache.delPathFromCache(pathname)
		if confirmed and self.tmpSelList is not None and len(self.tmpSelList)>0:
			if self.delCurrentlyPlaying:
				if self.playerInstance is not None:
					self.playerInstance.removeFromPlaylist(self.tmpSelList)
			delete = not config.EMC.movie_trashcan_enable.value or self.permanentDel
			if os.path.exists(config.EMC.movie_trashcan_path.value) or delete:
				movieFileCache.delPathFromCache(config.EMC.movie_trashcan_path.value)
				# if the user doesn't want to keep the movies in the trash, purge immediately
				if not self.isPathLocked(pathname):
					self.execFileOp(config.EMC.movie_trashcan_path.value, current, self.tmpSelList, op="delete", purgeTrash=delete)
				else:
					self.session.open(MessageBox, _("This element belongs to a locked folder and cannot be deleted!"), MessageBox.TYPE_ERROR, 10)

				for x in self.tmpSelList:
					self.lastPlayedCheck(x)
				self["list"].resetSelection()
				if self.delCurrentlyPlaying:
					if self.playerInstance is not None:
						self.session.nav.stopService()
						self.close()
			elif not delete:
				self.session.openWithCallback(self.trashcanCreate, MessageBox, _("Delete failed because the trashcan directory does not exist. Attempt to create it now?"), MessageBox.TYPE_YESNO)
			emcDebugOut("[EMCMS] deleteMovie")

	def isLowerPathLocked(self, path):
		locked = False
		for root, dirs, files in os.walk(path):
			if "dir.lock" in files:
				locked = True
				break
		return locked

	def isPathLocked(self, path):
		return os.path.isfile(path + "/dir.lock")

	def delPathSelRecursive(self, service, path, confirm):
		if confirm and path:
			if self.isPathLocked(path) or self.isLowerPathLocked(path):
				self.session.open(MessageBox, _("This folder is locked or contains a locked subfolder, unlock it first!"), MessageBox.TYPE_ERROR, 10)
			elif service:
				movieFileCache.delPathFromCache(path)
				cmd = []
				association = []
				cmd.append('rm -rf "' + path + '"')
				association.append((self.postFileOp))
				emcTasker.shellExecute(cmd, association, True)

	def delPathSelConfirmed(self, service, confirm):
		if confirm and service:
			path = service.getPath()
			if path != "..":
				movieFileCache.delPathFromCache(os.path.dirname(path))
				if os.path.islink(path):
					emcTasker.shellExecute("rm -f '" + path + "'")
					self.removeService(service)
					self.setReturnCursor()
				elif os.path.exists(path):
					if len(os.listdir(path))>0:
						self.session.openWithCallback(boundFunction(self.delPathSelRecursive, service, path), MessageBox, _("Directory is not empty! Do you really want to delete it?"), MessageBox.TYPE_YESNO)
					else:
						self.delPathSelRecursive(service, path, True)
					self.setReturnCursor()
			else:
				self.session.open(MessageBox, _("Cannot delete the parent directory."), MessageBox.TYPE_ERROR, 10)

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

	def moveCB(self, service):
		self["list"].highlightService(False, "move", service)	# remove the highlight
		if not config.EMC.movie_hide_mov.value:
			self.removeService(service)
			self.setReturnCursor()
		self.updateInfo()

	def delCB(self, service):
		self["list"].highlightService(False, "del", service)	# remove the highlight
		if not config.EMC.movie_hide_del.value:
			self.removeService(service)
			self.setReturnCursor()
		self.updateInfo()

	def copyCB(self, service):
		self["list"].highlightService(False, "copy", service)	# remove the highlight
		self["list"].invalidateService(service)
		self.setReturnCursor()
		self.updateInfo()

#Think about: All file operations should be in a separate class
# Uses pipes instead of os.system

	def execFileOp(self, targetPath, current, selectedlist, op="move", purgeTrash=False):
		self.returnService = self.getNextSelectedService(current, selectedlist)
		#TODOret
		if self.returnService:
			print "EMC ret exeFil " +str(self.returnService.toString())
		else:
			print "EMC ret exeFil - op:", op
			print "EMC ret exeFil - targetpath:", targetPath
			print "EMC ret exeFil - selectedlist:", selectedlist
		cmd = []
		association = []
		movieFileCache.delPathFromCache(targetPath)
		# TODO:
		# can we make one way for both Lists ?
		if self.tmpSelListOther is not None:
			for x in self.tmpSelListOther:
				ext = os.path.splitext( x.getPath() )[1]
				path = os.path.splitext( x.getPath() )[0]
				movieFileCache.delPathFromCache(os.path.dirname(x.getPath()))
				if path is not None:
					if op=="delete":	# target == trashcan
						c = []
						if purgeTrash or self.currentPath == targetPath or self.mountpoint(self.currentPath) != self.mountpoint(targetPath):
							# direct delete from the trashcan or network mount (no copy to trashcan from different mountpoint)
							#c.append( 'rm -f "'+ path +'."*' )

							#TEST_E2DELETE
							serviceHandler = eServiceCenter.getInstance()
							offline = serviceHandler.offlineOperations(x)
							result = False
							if offline is not None:
								# really delete!
								if not offline.deleteFromDisk(0):
									result = True
								if result == False:
									self.session.open(MessageBox, _("Delete failed!"), MessageBox.TYPE_ERROR)
									return
								else:
									self.removeService(x)
									self.setReturnCursor()
									path = path.replace("'","\'")
									c.append( 'rm -f "'+ path +'."*' )
									cmd.append( c )
							else:
								path = x.getPath()
								self.removeService(x)
								self.setReturnCursor()
								path = path.rsplit(".",1)[0]
								c.append( 'rm -f "'+ path +'."*' )
								cmd.append( c )
						#TEST_E2DELETE
						else:
							path = path.replace("'","\'")
							if ext in plyDVB:
								if self.deleteAllOtherList:
									extsOther = [".eit", ".jpg", ".txt", ".poster.jpg", ".imdbquery2.html"]
									for x in extsOther:
										f = path + str(x)
										if fileExists(f):
											c.append( 'touch "'+ f +'"' )
											c.append( 'mv "'+ f +'" "'+ targetPath +'/"' )
								# create a time stamp with touch
								c.append( 'touch "'+ path + str(ext) +'"' )
								c.append( 'touch "'+ path + str(ext) +'."*' )
								# move movie into the trashcan
								c.append( 'mv "'+ path + str(ext) +'" "'+ targetPath +'/"' )
								c.append( 'mv "'+ path + str(ext) +'."* "'+ targetPath +'/"' )
							else:
								if self.deleteAllOtherList:
									extsOther = [".eit", ".jpg", ".txt", ".poster.jpg", ".imdbquery2.html"]
									for x in extsOther:
										f = path + str(x)
										if fileExists(f):
											c.append( 'touch "'+ f +'"' )
											c.append( 'mv "'+ f +'" "'+ targetPath +'/"' )
								f = path + str(ext)
								if fileExists(f):
									c.append( 'touch "'+ f +'"' )
									c.append( 'mv "'+ f +'" "'+ targetPath +'/"' )
								cuts = path + str(ext) + ".cuts"
								if fileExists(cuts):
									c.append( 'touch "'+ cuts +'"' )
									c.append( 'mv "'+ cuts +'" "'+ targetPath +'/"' )

							#TEST_E2DELETE <- decrement indent
							cmd.append( c )

		for service in selectedlist:
			#path = os.path.splitext( self["list"].getFilePathOfService(service) )[0]
			# first we need the file-extension
			ext = os.path.splitext( service.getPath() )[1]
			path = os.path.splitext( service.getPath() )[0]
			movieFileCache.delPathFromCache(os.path.dirname(service.getPath()))
			if self.tmpSelListOther is not None:
				for x in self.tmpSelListOther:
					if x == service:
						path = None
			if path is not None:
				if op=="delete":	# target == trashcan
					c = []
					if purgeTrash or self.currentPath == targetPath or self.mountpoint(self.currentPath) != self.mountpoint(targetPath):
						# direct delete from the trashcan or network mount (no copy to trashcan from different mountpoint)
						#c.append( 'rm -f "'+ path +'."*' )

						#TEST_E2DELETE
						serviceHandler = eServiceCenter.getInstance()
						offline = serviceHandler.offlineOperations(service)
						result = False
						if offline is not None:
							# really delete!
							if not offline.deleteFromDisk(0):
								result = True
							if result == False:
								self.session.open(MessageBox, _("Delete failed!"), MessageBox.TYPE_ERROR)
								return
							else:
								self.removeService(service)
								self.setReturnCursor()
								path = path.replace("'","\'")
								c.append( 'rm -f "'+ path +'."*' )
								cmd.append( c )
						else:
							path = service.getPath()
							self.removeService(service)
							self.setReturnCursor()
							path = path.rsplit(".",1)[0]
							c.append( 'rm -f "'+ path +'."*' )
							cmd.append( c )
					#TEST_E2DELETE
					else:
						path = path.replace("'","\'")
						if ext in plyDVB:
							if self.deleteAllOther:
								extsOther = [".eit", ".jpg", ".txt", ".poster.jpg", ".imdbquery2.html"]
								for x in extsOther:
									f = path + str(x)
									if fileExists(f):
										c.append( 'touch "'+ f +'"' )
										c.append( 'mv "'+ f +'" "'+ targetPath +'/"' )
							# create a time stamp with touch
							c.append( 'touch "'+ path + str(ext) +'"' )
							c.append( 'touch "'+ path + str(ext) +'."*' )
							# move movie into the trashcan
							c.append( 'mv "'+ path + str(ext) +'" "'+ targetPath +'/"' )
							c.append( 'mv "'+ path + str(ext) +'."* "'+ targetPath +'/"' )
						else:
							if self.deleteAllOther:
								extsOther = [".eit", ".jpg", ".txt", ".poster.jpg", ".imdbquery2.html"]
								for x in extsOther:
									f = path + str(x)
									if fileExists(f):
										c.append( 'touch "'+ f +'"' )
										c.append( 'mv "'+ f +'" "'+ targetPath +'/"' )
							f = path + str(ext)
							if fileExists(f):
								c.append( 'touch "'+ f +'"' )
								c.append( 'mv "'+ f +'" "'+ targetPath +'/"' )
							cuts = path + str(ext) + ".cuts"
							if fileExists(cuts):
								c.append( 'touch "'+ cuts +'"' )
								c.append( 'mv "'+ cuts +'" "'+ targetPath +'/"' )

						#TEST_E2DELETE <- decrement indent
						cmd.append( c )
						association.append( (self.delCB, service) )	# put in a callback for this particular movie
						self["list"].highlightService(True, "del", service)
						#TEST_E2DELETE
						if config.EMC.movie_hide_del.value:
							self.removeService(service)
							self.setReturnCursor()
				elif op == "move":
					c = []
					#if self.mountpoint(self.currentPath) == self.mountpoint(targetPath):
					#	#self.removeService(service)	# normal direct move
					#	pass
					#else:
					# different self.mountpoint? -> reset user&group
					if self.mountpoint(targetPath) != self.mountpoint(config.EMC.movie_homepath.value):		# CIFS to HDD is ok!
						# need to change file ownership to match target filesystem file creation
						tfile = targetPath + "/owner_test"
						path = path.replace("'","\'")
						sfile = "\""+ path +".\"*"
						c.append( "touch %s;ls -l %s | while read flags i owner group crap;do chown $owner:$group %s;done;rm %s" %(tfile,tfile,sfile,tfile) )
					c.append( 'mv "'+ path +'."* "'+ targetPath +'/"' )
					cmd.append( c )
					association.append( (self.moveCB, service) )	# put in a callback for this particular movie
					self["list"].highlightService(True, "move", service)
					if config.EMC.movie_hide_mov.value:
						self.removeService(service)
						self.setReturnCursor()
					self.moveRecCheck(service, targetPath)
				elif op == "copy":
					c = []
					#if self.mountpoint(self.currentPath) == self.mountpoint(targetPath):
					#	#self.removeService(service)	# normal direct move
					#	pass
					#else:
					# different self.mountpoint? -> reset user&group
					if self.mountpoint(targetPath) != self.mountpoint(config.EMC.movie_homepath.value):		# CIFS to HDD is ok!
						# need to change file ownership to match target filesystem file creation
						tfile = targetPath + "/owner_test"
						path = path.replace("'","\'")
						sfile = "\""+ path +".\"*"
						c.append( "touch %s;ls -l %s | while read flags i owner group crap;do chown $owner:$group %s;done;rm %s" %(tfile,tfile,sfile,tfile) )
					c.append( 'cp "'+ path +'."* "'+ targetPath +'/"' )
					cmd.append( c )
					association.append( (self.copyCB, service) )	# put in a callback for this particular movie
					self["list"].highlightService(True, "copy", service)
					#if config.EMC.movie_hide_mov.value:
					#	self.removeService(service)
				self.lastPlayedCheck(service)
		self["list"].resetSelection()
		if cmd:
			association.append((self.initCursor, False)) # Set new Cursor position
			association.append((self.postFileOp))
			# Sync = True: Run script for one file do association and continue with next file
			emcTasker.shellExecute(cmd, association, True)	# first move, then delete if expiration limit is 0

	def postFileOp(self):
		self.tmpSelList = None
		self.tmpSelListOther = None
		self.deleteAllOther = False
		self.deleteAllOtherList = False

		# reload list to get the new index, otherwise you can not select again after that
		try:
				val = config.EMC.directories_info.value
				if val == "C" or val == "CS" or val == "S":
					# we make now hardreset
					movieFileCache.delcacheCountSizeList()
					self["list"].refreshList(True)
				# this we need to get the new position values,
				# otherwise no select for other files in the same directory after that
				self["list"].reload(self.currentPath)
		except Exception, e:
				print('[EMC] postFileOp exception: ', str(e))

	def moveMovie(self):
		# Avoid starting move and copy at the same time
		#WORKAROUND E2 doesn't send dedicated short or long pressed key events
		if self.move == False:
			self.move = True
			return
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
					if len(selectedlist)==1 and self["list"].serviceBusy(selectedlist[0]): return
					self.tmpSelList = selectedlist[:]
					self.session.openWithCallback(
						self.mvDirSelected,
						LocationBox,
							windowTitle = _("Move file(s):"),
							text = _("Choose directory"),
							currDir = str(self.currentPath)+"/",
							bookmarks = config.movielist.videodirs,
							autoAdd = False,
							editDir = True,
							inhibitDirs = ["/bin", "/boot", "/dev", "/etc", "/lib", "/proc", "/sbin", "/sys", "/usr", "/var"],
							minFree = 100 )
				except:
					self.session.open(MessageBox, _("How to move files:\nSelect some movies with the VIDEO-button, move the cursor on top of the destination directory and press yellow."), MessageBox.TYPE_ERROR, 10)
			emcDebugOut("[EMCMS] moveMovie")

	def mvDirSelected(self, targetPath):
		if targetPath is not None:
			current = self.getCurrent()
			self.execFileOp(targetPath, current, self.tmpSelList)
			emcDebugOut("[EMCMS] mvDirSelected")

	def copyMovie(self):
		# Avoid starting move and copy at the same time
		self.move = False
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
					self.execFileOp(targetPath, current, self.tmpSelList, op="copy")
					self["list"].resetSelection()
				else:
					if len(selectedlist) == 1:
						self.session.open(MessageBox, _("How to copy files:\nSelect some movies with the VIDEO-button, move the cursor on top of the destination directory and press yellow long."), MessageBox.TYPE_ERROR, 10)
					else:
						dialog = True
			else:
				dialog = True
			if dialog:
				try:
					if len(selectedlist)==1 and self["list"].serviceBusy(selectedlist[0]): return
					self.tmpSelList = selectedlist[:]
					self.session.openWithCallback(
						self.cpDirSelected,
						LocationBox,
							windowTitle = _("Copy file(s):"),
							text = _("Choose directory"),
							currDir = str(self.currentPath)+"/",
							bookmarks = config.movielist.videodirs,
							autoAdd = False,
							editDir = True,
							inhibitDirs = ["/bin", "/boot", "/dev", "/etc", "/lib", "/proc", "/sbin", "/sys", "/usr", "/var"],
							minFree = 100 )
				except:
					self.session.open(MessageBox, _("How to copy files:\nSelect some movies with the VIDEO-button, move the cursor on top of the destination directory and press yellow long."), MessageBox.TYPE_ERROR, 10)
			emcDebugOut("[EMCMS] copyMovie")

	def cpDirSelected(self, targetPath):
		if targetPath is not None:
			current = self.getCurrent()
			self.execFileOp(targetPath, current, self.tmpSelList, op="copy")
			emcDebugOut("[EMCMS] cpDirSelected")

	def moveDirectory(self):
		selectedPath = self["list"].getCurrentSelDir()
		try:
			self.tmpSelPath = selectedPath
			self.session.openWithCallback(
				self.mvDirectorySelected,
				LocationBox,
					windowTitle = _("Move Directory:"),
					text = _("Choose directory"),
					currDir = str(self.currentPath)+"/",
					bookmarks = config.movielist.videodirs,
					autoAdd = False,
					editDir = True,
					inhibitDirs = ["/bin", "/boot", "/dev", "/etc", "/home", "/lib", "/proc", "/run", "/sbin", "/sys", "/usr", "/var"],
					minFree = 100 )
		except Exception, e:
			print('[EMC] moveDirectory get failed: ', str(e))
		emcDebugOut("[EMCMS] moveDirectory")

	def mvDirectorySelected(self, targetPath):
		selSize = 0
		freeSize = 0
		if targetPath is not None:
			try:
				if os.path.exists(self.tmpSelPath):
					for (path, dirs, files) in os.walk(self.tmpSelPath):
						for m in files:
							filename = os.path.join(path, m)
							if os.path.exists(filename):
								selSize += os.path.getsize(filename)
				if selSize:
					selSize /= (1024.0 * 1024.0 * 1024.0)

				stat = os.statvfs(targetPath)
				free = (stat.f_bavail if stat.f_bavail!=0 else stat.f_bfree) * stat.f_bsize / 1024 / 1024
				freeSize += free/1024
			except Exception, e:
				print('[EMC] mvDirectorySelected get sizes failed: ', str(e))

			if freeSize >= selSize:
				cmd = []
				association = []
				movieFileCache.delPathFromCache(targetPath)
				movieFileCache.delPathFromCache(self.tmpSelPath)
				movieFileCache.delPathFromCache(self.currentPath)
				cmd.append( 'mv "'+ self.tmpSelPath +'" "'+ targetPath +'"' )
				try:
					if cmd:
						association.append((self.initCursor, False)) # Set new Cursor position
						association.append((self.postDirectoryOp))
						# Sync = True: Run script for one file do association and continue with next file
						emcTasker.shellExecute(cmd, association, True)	# first move, then delete if expiration limit is 0
				except Exception, e:
					print('[EMC] mvDirectorySelected execute get failed: ', str(e))
		emcDebugOut("[EMCMS] mvDirectorySelected")

	def postDirectoryOp(self):
		self.tmpSelPath = None
		try:
				self["list"].reload(self.currentPath)
		except Exception, e:
				print('[EMC] postDirectoryOp - refreshList get failed!!!', str(e))

	def trashcanCreate(self, confirmed):
		try:
			os.makedirs(config.EMC.movie_trashcan_path.value)
			if self.currentPath == os.path.dirname(config.EMC.movie_trashcan_path.value):
				# reload to show the trashcan only if the current path will contain the trashcan
				self.reloadListWithoutCache()
		except Exception, e:
			self.session.open(MessageBox, _("Trashcan create failed. Check mounts and permissions."), MessageBox.TYPE_ERROR)
			emcDebugOut("[EMCMS] trashcanCreate exception:\n" + str(e))

#	def dlMovieInfo(self):
#		selectedlist = self["list"].makeSelectionList()[:]
#		service = selectedlist[0]
#		if os.path.isfile(service.getPath()):
#			moviename = str(self["list"].getNameOfService(service))
#			self.session.open(DownloadMovieInfo, service, moviename)

	def dlMovieInfo(self):
		if config.EMC.movieinfo.switch_newold.value:
			self.EMCTMDBInfo()
		else:
			service = self["list"].getCurrent()
			if service:
				path = service.getPath()
				if path and path != config.EMC.movie_trashcan_path.value:
					if not path.endswith("/..") and not path.endswith("/Latest Recordings"):
						moviename = service.getName()
						spath = getInfoFile(path)[0]
						self.session.open(DownloadMovieInfo, spath, moviename)

#****************************************************************************************
# add possibility to call IMDb/TMDB/CSFD from movie detail via blue key
class IMDbEventViewSimple(EventViewSimple):
	def __init__(self, session, Event, Ref, callback=None, similarEPGCB=None):
		EventViewSimple.__init__(self, session, Event, Ref, callback, similarEPGCB)
		self.skinName = ["EventViewSimple", "EventView"]
		if config.EMC.InfoLong.value == "IMDbSearch":
			text_blue = _("IMDb")
		elif config.EMC.InfoLong.value == "TMDBInfo":
			text_blue = _("TMDb")
		elif config.EMC.InfoLong.value == "CSFDInfo":
			text_blue = _("CSFD")
		else:
			text_blue = _("IMDb")
		self["key_blue"] = Button(text_blue)
		self["epgactions"] = ActionMap(["EventViewEPGActions"],
			{
				"openMultiServiceEPG": self.InfoDetail,
			})

	def InfoDetail(self):
		nameM = getMovieNameWithoutPhrases(getMovieNameWithoutExt(self.event.getEventName()))
		if nameM!="":
			if config.EMC.InfoLong.value == "IMDbSearch":
				self.IMDbSearchName(nameM)
			elif config.EMC.InfoLong.value == "TMDBInfo":
				self.TMDBInfoName(nameM)
			elif config.EMC.InfoLong.value == "CSFDInfo":
				self.CSFDInfoName(nameM)
			else:
				self.IMDbSearchName(nameM)

	def setService(self, service):
		EventViewSimple.setService(self, service)
		if self.isRecording:
			self["channel"].setText("")

	def setEvent(self, event):
		EventViewSimple.setEvent(self, event)
		if (self.isRecording) and (event.getDuration()==0):
			self["duration"].setText("")

	def IMDbSearchName(self, name):
		try:
			from Plugins.Extensions.IMDb.plugin import IMDB
		except ImportError:
			IMDB = None
		if IMDB is not None:
			self.session.open(IMDB, name, False)

	def TMDBInfoName(self, name):
		try:
			from Plugins.Extensions.TMDb.plugin import TMDbMain
		except ImportError:
			TMDbMain = None
		if TMDbMain is not None:
			self.session.open(TMDbMain, name)

	def CSFDInfoName(self, name):
		try:
			from Plugins.Extensions.CSFD.plugin import CSFD
		except ImportError:
			CSFD = None
		if CSFD is not None:
			self.session.open(CSFD, name, False)

#****************************************************************************************
