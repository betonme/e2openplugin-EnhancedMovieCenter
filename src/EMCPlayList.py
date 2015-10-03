#!/usr/bin/python
# encoding: utf-8

import os

from __init__ import _
from enigma import eListboxPythonMultiContent, RT_VALIGN_CENTER, RT_HALIGN_RIGHT, gFont, eListbox, getDesktop

from Screens.Screen import Screen
from Screens.ChoiceBox import ChoiceBox
from Screens.HelpMenu import HelpableScreen
from Screens.InputBox import InputBox
from Screens.LocationBox import LocationBox
from Screens.MessageBox import MessageBox
from Screens.VirtualKeyBoard import VirtualKeyBoard
from Components.ActionMap import *
from Components.Button import Button
from Components.config import *
from Components.ConfigList import *
from Components.FileList import FileList
from Components.GUIComponent import GUIComponent
from Tools.Directories import fileExists

from skin import parseColor, parseFont

from MetaSupport import MetaList
from MovieCenter import plyDVB
from EnhancedMovieCenter import imgVti

global plyDVB

config.EMC.playlist = ConfigSubsection()
config.EMC.playlist.default_playlist_path = ConfigDirectory(default = "/media/hdd/")
config.EMC.playlist.default_playlist_name = ConfigText(default = "EmcPlaylist")
config.EMC.playlist.save_default_list = ConfigYesNo(default = False)


def readPlaylist(path):
	if path:
		overview = []
		plist = open(path, "r")
		if os.path.splitext(path)[1] == ".e2pls":
			while True:
				service = plist.readline()
				if service == "":
					break
				service = service.replace('\n','')
				spos = service.find('/')
				servicepath = service[spos:]
				service = servicepath.split('/')[-1]
				name = service + "\n"
				overview.append(name)
		return overview

class EMCPlaylist():
	def __init__(self):
		self.currentPlaylist = {}
		self.count = 0

	def addToCurrentPlaylist(self, path, name, service):
		if self.currentPlaylist.has_key(path):
			return False
		else:
			if self.currentPlaylist == {}:
				self.count = 0
			else:
				self.count += 1
			self.currentPlaylist[path] = self.count, name, service
			return True

	def getCurrentPlaylistEntry(self, path):
		if self.currentPlaylist.has_key(path):
			return self.currentPlaylist[path]

	def getCurrentPlaylist(self):
		return self.currentPlaylist

	def isCurrentPlaylistEmpty(self):
		if self.currentPlaylist != {}:
			return False
		else:
			return True

	def delCurrentPlaylistEntry(self, path):
		if self.currentPlaylist.has_key(path):
			del self.currentPlaylist[path]
		print "EMC delete currentPlaylistEntry: ", path

	def delCurrentPlaylist(self):
		self.currentPlaylist = {}
		print "EMC delete currentPlaylist"

emcplaylist = EMCPlaylist()

class EMCPlaylistScreen(Screen):
	if getDesktop(0).size().width() == 1920:
		skin = """
			<screen position="center,center" size="992,714" title="EMC Playlist" >
			<widget name="playlist" position="5,5" size="982,630" itemHeight="40" scrollbarMode="showOnDemand" posWidth="63" nameWidth="852" posColor="#FFFFFF" posColorSel="#FFFFFF" nameColor="#FFFFFF" nameColorSel="#FFFFFF" />
			<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/line_blue.png" position="46,653" size="660,2" alphatest="on" />
			<widget name="cancel" position="27,657" size="180,40" valign="center" halign="center" zPosition="1" font="Regular;26" transparent="1" backgroundColor="red" />
			<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/key-red_line.png" position="42,692" size="150,2" zPosition="0" alphatest="on" />
			<widget name="save" position="282,657" size="180,40" valign="center" halign="center" zPosition="1" font="Regular;26" transparent="1" backgroundColor="green" />
			<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/key-green_line.png" position="297,692" size="150,2" zPosition="0" alphatest="on" />
			<widget name="delete" position="535,657" size="180,40" valign="center" halign="center" zPosition="1" font="Regular;26" transparent="1" backgroundColor="yellow" />
			<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/key-yellow_line.png" position="550,692" size="150,2" zPosition="0" alphatest="on" />
			<widget name="deleteall" position="785,657" size="180,40" valign="center" halign="center" zPosition="1" font="Regular;26" transparent="1" backgroundColor="blue" />
			<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/key-blue_line.png" position="800,692" size="150,2" zPosition="0" alphatest="on" />
		</screen>"""
	else:
		skin = """
			<screen position="center,center" size="710,510" title="EMC Playlist" >
			<widget name="playlist" position="5,5" size="700,450" itemHeight="30" scrollbarMode="showOnDemand" posWidth="45" nameWidth="610" posColor="#FFFFFF" posColorSel="#FFFFFF" nameColor="#FFFFFF" nameColorSel="#FFFFFF" />
			<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/line_blue_playlist1.png" position="25,453" size="330,2" alphatest="on" />
			<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/line_blue_playlist2.png" position="355,453" size="330,2" alphatest="on" />
			<widget name="cancel" position="17,460" size="140,40" valign="center" halign="center" zPosition="1" font="Regular;17" transparent="1" backgroundColor="red" />
			<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/key-red_line.png" position="12,492" size="150,2" zPosition="0" alphatest="on" />
			<widget name="save" position="192,460" size="140,40" valign="center" halign="center" zPosition="1" font="Regular;17" transparent="1" backgroundColor="green" />
			<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/key-green_line.png" position="187,492" size="150,2" zPosition="0" alphatest="on" />
			<widget name="delete" position="372,460" size="140,40" valign="center" halign="center" zPosition="1" font="Regular;17" transparent="1" backgroundColor="yellow" />
			<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/key-yellow_line.png" position="367,492" size="150,2" zPosition="0" alphatest="on" />
			<widget name="deleteall" position="552,460" size="140,40" valign="center" halign="center" zPosition="1" font="Regular;17" transparent="1" backgroundColor="blue" />
			<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/key-blue_line.png" position="547,492" size="150,2" zPosition="0" alphatest="on" />
		</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		self.skinName = "EMCPlaylist"
		self.spath = None
		self["playlist"] = PlayList()
		self["save"] = Button(_("Save"))
		self["cancel"] = Button(_("Cancel"))
		self["delete"] = Button(_("Delete Entry"))
		self["deleteall"] = Button(_("Delete All"))

		self["actions"] = HelpableActionMap(self, "PluginMovieSelectionActions",
		{
			"EMCOK":	self.keyOk,
			"EMCEXIT":	self.keyRed,
			"EMCMENU":	self.keySetup,
			"EMCRed":	self.keyRed,
			"EMCGREEN":	self.keyGreen,
			"EMCYELLOW":	self.keyYellow,
			"EMCBLUE":	self.keyBlue,
		}, -1)

		self.onClose.append(self.__closed)
		self.onLayoutFinish.append(self.__layoutFinished)

	def __closed(self):
		pass

	def __layoutFinished(self):
		self.setTitle(_("EMC Playlist" + " - " + "current playlist"))

	def keyOk(self):
		self.close()

	def keySetup(self):
		menu = []
		text = _("EMC Playlist Menu")
		menu.append((_("Playlist open"), self.openPlaylistCheck))
		menu.append((_("Setup open"), self.showSetup))
		def boxAction(choice):
			if choice:
				choice[1]()
		self.session.openWithCallback(boxAction, ChoiceBox, title=text, list=menu)

	def openPlaylistCheck(self):
		if not emcplaylist.isCurrentPlaylistEmpty():
			self.session.openWithCallback(self.showOpenPlaylistMessageCB, MessageBox, (_("Default Playlist is not empty!\n\nSave default Playlist?")), MessageBox.TYPE_YESNO)
		else:
			self.openPlaylist()

	def showOpenPlaylistMessageCB(self, result):
		if result:
			self.keyGreen()
		else:
			self.openPlaylist()

	def openPlaylist(self):
		val = config.EMC.playlist.default_playlist_path.value
		self.session.openWithCallback(self.openPlaylistCB, EMCFileBrowser, currDir=val)

	def openPlaylistCB(self, path):
		if path:
			plist = open(path, "r")
			from MovieCenter import getPlayerService, getMovieNameWithoutExt, getMovieNameWithoutPhrases
			emcplaylist.delCurrentPlaylist()
			if os.path.splitext(path)[1] == ".e2pls":
				while True:
					service = plist.readline()
					if service == "":
						break
					service = service.replace('\n','')
					spos = service.find('/')
					servicepath = service[spos:]
					service = servicepath.split('/')[-1]
					ext = os.path.splitext(servicepath)[1]
					name = getMovieNameWithoutExt(service)
					name = getMovieNameWithoutPhrases(name)
					service = getPlayerService(servicepath, service, ext)
					added = emcplaylist.addToCurrentPlaylist(servicepath, name, service)

			if added:
				self["playlist"].readPlaylist()
				self["playlist"].refreshList()

	def showSetup(self):
		self.session.open(EMCPlaylistSetup)

	def keyRed(self):
		self.close()

	def keyGreen(self):
		if emcplaylist.getCurrentPlaylist() != {}:
			self.spath = config.EMC.playlist.default_playlist_path.value + config.EMC.playlist.default_playlist_name.value
			self.checkPlaylistExist()

	def checkPlaylistExist(self, path=None):
		if path is not None:
			if fileExists(path + ".e2pls"):
				self.showMessage()
			else:
				self.save(path)
		else:
			if fileExists(self.spath + ".e2pls"):
				self.showMessage()
			else:
				self.save(self.spath)

	def showMessage(self):
		self.session.openWithCallback(self.showMessageCB, MessageBox, (_("Playlist with same name exists!\n\nTry to save the Playlist with another name?")), MessageBox.TYPE_YESNO)

	def showMessageCB(self, result):
		if result:
			self.session.openWithCallback(self.checkPlaylistExist, InputBox, title=_("Change the filename to save current Playlist:"), windowTitle = _("Save current Playlist"), text=self.spath)
		else:
			return

	def save(self, filename):
		if filename:
			tmplist = []
			plist = emcplaylist.getCurrentPlaylist()
			for x in plist:
				tmplist.append(emcplaylist.getCurrentPlaylistEntry(x))

			tmplist.sort( key=lambda x: (x[0]) )

			try:
				file = open(filename + ".e2pls", "w")
				for x in tmplist:
					file.write(str(x[2].toString()).replace(":%s" % x[1], "") + "\n")
				file.close()
				self.session.open(MessageBox, (_("Current Playlist saved successfully!")), MessageBox.TYPE_INFO, 5)
			except Exception, e:
				print('[EMCPlayList] savePlaylist get failed: ', str(e))
				self.session.open(MessageBox, (_("Can not save current Playlist!")), MessageBox.TYPE_ERROR, 10)

	def keyYellow(self):
		current = self["playlist"].getCurrent()
		emcplaylist.delCurrentPlaylistEntry(current.getPath())
		self.reloadList()

	def keyBlue(self):
		emcplaylist.delCurrentPlaylist()
		self.reloadList()

	def reloadList(self):
		self["playlist"].resetList()
		self["playlist"].readPlaylist()
		self["playlist"].refreshList()


class PlayList(GUIComponent):
	def __init__(self, enableWrapAround = True):
		GUIComponent.__init__(self)

		self.screenwidth = getDesktop(0).size().width()
		if self.screenwidth and self.screenwidth == 1920:
			if imgVti:
				self.posFont = parseFont("Regular;26", ((1,1),(1,1)))
				self.nameFont = parseFont("Regular;26", ((1,1),(1,1)))
			else:
				self.posFont = parseFont("Regular;28", ((1,1),(1,1)))
				self.nameFont = parseFont("Regular;28", ((1,1),(1,1)))
			self.itemHeight = 40
		elif self.screenwidth and self.screenwidth == 3840:
			if imgVti:
				self.posFont = parseFont("Regular;56", ((1,1),(1,1)))
				self.nameFont = parseFont("Regular;56", ((1,1),(1,1)))
			else:
				self.posFont = parseFont("Regular;56", ((1,1),(1,1)))
				self.nameFont = parseFont("Regular;56", ((1,1),(1,1)))
			self.itemHeight = 70
		else:
			if imgVti:
				self.posFont = parseFont("Regular;18", ((1,1),(1,1)))
				self.nameFont = parseFont("Regular;18", ((1,1),(1,1)))
			else:
				self.posFont = parseFont("Regular;20", ((1,1),(1,1)))
				self.nameFont = parseFont("Regular;20", ((1,1),(1,1)))
			self.itemHeight = 30

		self.posColor = 0xFFFFFF
		self.posColorSel = 0xFFFFFF
		self.nameColor = 0xFFFFFF
		self.nameColorSel = 0xFFFFFF

		self.posWidth = -1
		self.nameWidth = -1

		self.l = eListboxPythonMultiContent()
		self.l.setFont(0, self.posFont)
		self.l.setFont(1, self.nameFont)

		self.onSelectionChanged = []

	def selectionChanged(self):
		for f in self.onSelectionChanged:
			try:
				f()
			except Exception, e:
				emcDebugOut("[EMCPlayList] External observer exception: \n" + str(e))

	def applySkin(self, desktop, parent):
		attribs = []
		if self.skinAttributes is not None:
			for (attrib, value) in self.skinAttributes:
				if attrib == "posFont":
					self.posFont = parseFont(value, ((1,1),(1,1)))
					self.l.setFont(0, self.posFont)
				elif attrib == "nameFont":
					self.nameFont = parseFont(value, ((1,1),(1,1)))
					self.l.setFont(1, self.nameFont)
				elif attrib == "posWidth":
					self.posWidth = int(value)
				elif attrib == "nameWidth":
					self.nameWidth = int(value)
				elif attrib == "posColor":
					self.posColor = parseColor(value).argb()
				elif attrib == "posColorSel":
					self.posColorSel = parseColor(value).argb()
				elif attrib == "nameColor":
					self.nameColor = parseColor(value).argb()
				elif attrib == "nameColorSel":
					self.nameColorSel = parseColor(value).argb()
				elif attrib == "itemHeight":
					self.itemHeight = int(value)
				else:
					attribs.append((attrib, value))
		self.readPlaylist()
		self.refreshList()
		self.setItemHeight()
		self.skinAttributes = attribs
		return GUIComponent.applySkin(self, desktop, parent)

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

	def readPlaylist(self):
		self.list = []
		tmpplaylist = []
		pos = 0
		if emcplaylist.getCurrentPlaylist() != {}:
			for x in emcplaylist.getCurrentPlaylist():
				tmpplaylist.append(emcplaylist.getCurrentPlaylistEntry(x))

			tmpplaylist.sort( key=lambda x: (x[0]) )

			for x in tmpplaylist:
				pos += 1
				self.addEntry(pos, x)

	def getMetaInfos(self, path):
		eventtitle = ""
		meta = MetaList(path)
		if meta:
			eventtitle = meta.getMetaTitle()
		return eventtitle

	def playlistEntrys(self, pos, name, service):
		entrys = [ service ]
		pos = str(pos)
		metastring = ""
		movie_metaload = config.EMC.movie_metaload.value
		if movie_metaload:
			path = service.getPath()
			ext = os.path.splitext(path)[1].lower()
			if ext in plyDVB:
				metastring = self.getMetaInfos(path)
				if metastring != "":
					name = name + " - " + metastring
		if self.screenwidth and self.screenwidth == 1920:
			entrys.append((eListboxPythonMultiContent.TYPE_TEXT, 5, 1, self.posWidth, 34, 0, RT_VALIGN_CENTER|RT_HALIGN_RIGHT, pos, self.posColor, self.posColorSel))
			entrys.append((eListboxPythonMultiContent.TYPE_TEXT,5 + self.posWidth + 30, 1, self.nameWidth, 34, 1, RT_VALIGN_CENTER, name, self.nameColor, self.nameColorSel))
		elif self.screenwidth and self.screenwidth == 3840:
			entrys.append((eListboxPythonMultiContent.TYPE_TEXT, 5, 1, self.posWidth, 60, 0, RT_VALIGN_CENTER|RT_HALIGN_RIGHT, pos, self.posColor, self.posColorSel))
			entrys.append((eListboxPythonMultiContent.TYPE_TEXT,5 + self.posWidth + 58, 1, self.nameWidth, 60, 1, RT_VALIGN_CENTER, name, self.nameColor, self.nameColorSel))
		else:
			entrys.append((eListboxPythonMultiContent.TYPE_TEXT, 5, 1, self.posWidth, 26, 0, RT_VALIGN_CENTER|RT_HALIGN_RIGHT, pos, self.posColor, self.posColorSel))
			entrys.append((eListboxPythonMultiContent.TYPE_TEXT,5 + self.posWidth + 20, 1, self.nameWidth, 26, 1, RT_VALIGN_CENTER, name, self.nameColor, self.nameColorSel))
		return entrys

	def addEntry(self, pos, entry):
		self.list.append(self.playlistEntrys(pos, entry[1], entry[2]))

	def getCurrent(self):
		return self.l.getCurrentSelection()[0]

	def resetList(self):
		self.list = []

	def refreshList(self):
		self.l.setList(self.list)

	def setItemHeight(self):
		self.l.setItemHeight(self.itemHeight)


def image():
	if getDesktop(0).size().width() == 1920:
		if imgVti:
			return 40
		else:
			return 38
	else:
		if imgVti:
			return 30
		else:
			return 28

class EMCPlaylistSetup(Screen, ConfigListScreen):
	if getDesktop(0).size().width() == 1920:
		skin = """
			<screen position="center,center" size="750,535" title="EMC Playlist Setup">
			<widget name="config" position="5,10" size="740,450" itemHeight="%s" scrollbarMode="showOnDemand" />
			<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/line_blue_playlist1.png" position="25,473" size="330,2" alphatest="on" />
			<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/line_blue_playlist2.png" position="395,473" size="330,2" alphatest="on" />
			<widget name="cancel" position="155,480" size="140,40" valign="center" halign="center" zPosition="1" font="Regular;26" transparent="1" backgroundColor="red" />
			<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/key-red_line.png" position="150,517" size="150,2" zPosition="0" alphatest="on" />
			<widget name="save" position="465,480" size="140,40" valign="center" halign="center" zPosition="1" font="Regular;26" transparent="1" backgroundColor="green" />
			<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/key-green_line.png" position="460,517" size="150,2" zPosition="0" alphatest="on" />
		</screen>""" % image()
	else:
		skin = """
			<screen position="center,center" size="600,435" title="EMC Playlist Setup">
			<widget name="config" position="5,10" size="590,350" itemHeight="%s" scrollbarMode="showOnDemand" />
			<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/line_blue_playlist1.png" position="25,383" size="330,2" alphatest="on" />
			<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/line_blue_playlist2.png" position="245,383" size="330,2" alphatest="on" />
			<widget name="cancel" position="105,390" size="140,30" valign="center" halign="center" zPosition="1" font="Regular;19" transparent="1" backgroundColor="red" />
			<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/key-red_line.png" position="100,417" size="150,2" zPosition="0" alphatest="on" />
			<widget name="save" position="355,390" size="140,30" valign="center" halign="center" zPosition="1" font="Regular;19" transparent="1" backgroundColor="green" />
			<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/key-green_line.png" position="350,417" size="150,2" zPosition="0" alphatest="on" />
		</screen>""" % image()

	def __init__(self, session):
		Screen.__init__(self, session)
		#self.session = session
		self.list = []
		self.list.append(getConfigListEntry(_("Default Playlist path"), config.EMC.playlist.default_playlist_path))
		self.list.append(getConfigListEntry(_("Default Playlist name"), config.EMC.playlist.default_playlist_name))
		self.list.append(getConfigListEntry(_("Always save current Playlist"), config.EMC.playlist.save_default_list))

		ConfigListScreen.__init__(self, self.list, session)
		self["actions"] = ActionMap(["SetupActions", "ColorActions"],
		{
			"ok": self.ok,
			"cancel": self.exit,
			"green": self.save,
		}, -2)
		self["cancel"] = Button(_("Cancel"))
		self["save"] = Button(_("Save"))
		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self.setTitle(_("EMC Playlist Setup"))

	def openDirectoryBrowser(self, path):
		try:
			self.session.openWithCallback(
				self.openDirectoryBrowserCB,
				LocationBox,
					windowTitle = _("Choose Directory:"),
					text = _("Choose directory"),
					currDir = str(path),
					bookmarks = config.movielist.videodirs,
					autoAdd = False,
					editDir = True,
					inhibitDirs = ["/bin", "/boot", "/dev", "/etc", "/home", "/lib", "/proc", "/run", "/sbin", "/sys", "/usr", "/var"],
					minFree = 15 )
		except Exception, e:
			print('[EMCPlayList] openDirectoryBrowser get failed: ', str(e))

	def openDirectoryBrowserCB(self, path):
		if path is not None:
			config.EMC.playlist.default_playlist_path.setValue(path)

	def openVirtualKeyboard(self, name):
		try:
			self.session.openWithCallback(lambda x : self.openVirtualKeyboardCB(x, 'playlist_name'), VirtualKeyBoard, title = (_('Enter Name for Playlist')), text = name)
		except Exception, e:
			print('[EMCPlayList] openVirtualKeyboard get failed: ', str(e))

	def openVirtualKeyboardCB(self, callback = None, entry = None):
		if callback is not None and len(callback) and entry is not None and len(entry):
			if entry == 'playlist_name':
				config.EMC.playlist.default_playlist_name.setValue(callback)

	def ok(self):
		if self["config"].getCurrent()[1] == config.EMC.playlist.default_playlist_path:
			self.openDirectoryBrowser(config.EMC.playlist.default_playlist_path.value)
		elif self["config"].getCurrent()[1] == config.EMC.playlist.default_playlist_name:
			self.openVirtualKeyboard(config.EMC.playlist.default_playlist_name.value)
		else:
			self.exit()       # should we use save on this way too?

	def exit(self):
		for x in self["config"].list:
			x[1].cancel()
		self.close(False)

	def save(self):
		for x in self["config"].list:
			x[1].save()
		configfile.save()
		self.close(True)

class EMCFileBrowser(Screen, HelpableScreen):
	skin = """
		<screen name="EMCFilebrowser" position="center,center" size="560,435" title="EMC Filebrowser">
		<widget name="filelist" position="5,5" size="550,370" />
		<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/line_blue_playlist1.png" position="25,386" size="330,2" alphatest="on" />
		<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/line_blue_playlist2.png" position="200,386" size="330,2" alphatest="on" />
		<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/key-red_line.png" position="50,420" size="150,2" alphatest="on" />
		<widget name="cancel" position="55,393" size="140,30" valign="center" halign="center" zPosition="1" font="Regular;19" transparent="1" backgroundColor="red" />
		<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/key-green_line.png" position="355,420" size="150,2" alphatest="on" />
		<widget name="open" position="360,393" size="140,30" valign="center" halign="center" zPosition="1" font="Regular;19" transparent="1" backgroundColor="green" />
	</screen>"""

	def __init__(self, session, currDir):
		Screen.__init__(self, session)
		self.skinName = ["EMCFileBrowser"]
		HelpableScreen.__init__(self)
		self["cancel"] = Button(_("Cancel"))
		self["open"] = Button(_("Open"))
		self.filelist = FileList(currDir, showFiles=True, matchingPattern=".(e2pls|m3u)")
		self["filelist"] = self.filelist
		self.lastDir = currDir
		self["FilelistActions"] = ActionMap(["SetupActions", "ColorActions"],
			{
				"green": self.use,
				"red": self.exit,
				"ok": self.ok,
				"cancel": self.exit
			})
		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self.setTitle(_("EMC Filebrowser"))
		self.filelist.descent()

	def ok(self):
		if self.filelist.canDescent():
			self.filelist.descent()
		else:
			self.use()

	def use(self):
		path = ""
		if self["filelist"].getFilename() is not None:
			fname = self["filelist"].getFilename()
			dirname = self["filelist"].getCurrentDirectory()
			path = dirname + fname
			self.close(path)

	def exit(self):
		self.close(False)