#!/usr/bin/python
# encoding: utf-8

from __init__ import _
from enigma import eListboxPythonMultiContent, RT_VALIGN_CENTER, RT_HALIGN_RIGHT, gFont, eListbox

from Screens.Screen import Screen

from Components.ActionMap import ActionMap
from Components.Button import Button
from Components.GUIComponent import GUIComponent

from skin import parseColor, parseFont


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
	skin = """
		<screen position="center,center" size="710,510" title="EMC Playlist" >
			<widget name="playlist" position="5,5" size="700,450" scrollbarMode="showOnDemand" posColor="#FFFFFF" posColorSel="#FFFFFF" nameColor="#FFFFFF" nameColorSel="#FFFFFF" />
			<ePixmap pixmap="skin_default/buttons/red.png" position="17,460" zPosition="0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="192,460" zPosition="0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/yellow.png" position="372,460" zPosition="0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/blue.png" position="552,460" zPosition="0" size="140,40" alphatest="on" />
			<widget name="cancel" position="17,460" size="140,40" valign="center" halign="center" zPosition="1" font="Regular;17" transparent="1" backgroundColor="red" />
			<widget name="ok" position="192,460" size="140,40" valign="center" halign="center" zPosition="1" font="Regular;17" transparent="1" backgroundColor="green" />
			<widget name="delete" position="372,460" size="140,40" valign="center" halign="center" zPosition="1" font="Regular;17" transparent="1" backgroundColor="yellow" />
			<widget name="deleteall" position="552,460" size="140,40" valign="center" halign="center" zPosition="1" font="Regular;17" transparent="1" backgroundColor="blue" /> 
		</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)

		self.skinName = "EMCPlaylist"

		self["playlist"] = PlayList()

		self["ok"] = Button(_("OK"))
		self["cancel"] = Button(_("Cancel"))
		self["delete"] = Button(_("Delete Entry"))
		self["deleteall"] = Button(_("Delete All"))

		self["actions"] = ActionMap(["SetupActions", "ColorActions"], 
		{
			"ok": self.keyOk,
			"ok": self.keyGreen,
			"cancel": self.keyRed,
			"yellow": self.keyYellow,
			"blue": self.keyBlue,
		}, -2)

		self.onClose.append(self.__closed)
		self.onLayoutFinish.append(self.__layoutFinished)

	def __closed(self):
		pass

	def __layoutFinished(self):
		self.setTitle(_("EMC Playlist" + " - " + "current playlist"))

	def keyOk(self):
		self.close()

	def keyRed(self):
		self.close()

	def keyGreen(self):
		self.close()

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

		self.posFont = parseFont("Regular;20", ((1,1),(1,1)))
		self.nameFont = parseFont("Regular;20", ((1,1),(1,1)))

		self.itemHeight = 30

		self.posColor = 0xFFFFFF
		self.posColorSel = 0xFFFFFF
		self.nameColor = 0xFFFFFF
		self.nameColorSel = 0xFFFFFF

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

	def playlistEntrys(self, pos, name, service):
		entrys = [ service ]
		pos = str(pos)
		entrys.append((eListboxPythonMultiContent.TYPE_TEXT, 5, 1, 45, 26, 0, RT_VALIGN_CENTER|RT_HALIGN_RIGHT, pos, self.posColor, self.posColorSel))
		entrys.append((eListboxPythonMultiContent.TYPE_TEXT,80, 1, 610, 26, 1, RT_VALIGN_CENTER, name, self.nameColor, self.nameColorSel))
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
