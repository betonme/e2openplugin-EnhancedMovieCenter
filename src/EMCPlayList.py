#!/usr/bin/python
# encoding: utf-8

from enigma import eListboxPythonMultiContent, RT_VALIGN_CENTER, gFont

from Screens.Screen import Screen

from Components.ActionMap import ActionMap
from Components.Button import Button
from Components.MenuList import MenuList


class EMCPlaylist():
	def __init__(self):
		self.currentPlaylist = {}
		self.count = 0

	def addToCurrentPlaylist(self, path, name, service):
		if self.currentPlaylist.has_key(path):
			return
		else:
			if self.currentPlaylist == {}:
				self.count = 0
			else:
				self.count += 1
			self.currentPlaylist[path] = self.count, name, service

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
			if self.count >= 0:
				self.count -= 1
		print "EMC delete currentPlaylistEntry: ", path

	def delCurrentPlaylist(self):
		self.currentPlaylist = {}
		print "EMC delete currentPlaylist"

emcplaylist = EMCPlaylist()

class EMCPlaylistScreen(Screen):
	skin = """
		<screen position="center,center" size="710,510" title="EMC Playlist - current playlist" >
			<widget name="playlist" position="5,5" size="700,450" scrollbarMode="showOnDemand" />
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
		self.title = _("EMC Playlist - current playlist")
		Screen.__init__(self, session)

		self.playlist = PlayList()
		self["playlist"] = self.playlist

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

		self.readPlaylist()

		self.onClose.append(self.__closed)
		self.onLayoutFinish.append(self.__layoutFinished)

	def __closed(self):
		pass

	def __layoutFinished(self):
		self.setTitle(self.title)

	def readPlaylist(self):
		tmpplaylist = []
		if emcplaylist.getCurrentPlaylist() != {}:
			for x in emcplaylist.getCurrentPlaylist():
				tmpplaylist.append(emcplaylist.getCurrentPlaylistEntry(x))

			tmpplaylist.sort( key=lambda x: (x[0]) )

			for x in tmpplaylist:
				self.playlist.addEntry(x)

	def keyOk(self):
		self.close()

	def keyRed(self):
		self.close()

	def keyGreen(self):
		self.close()

	def keyYellow(self):
		current = self.playlist.getCurrent()
		emcplaylist.delCurrentPlaylistEntry(current.getPath())
		self.reloadList()

	def keyBlue(self):
		emcplaylist.delCurrentPlaylist()
		self.reloadList()

	def reloadList(self):
		self.playlist.resetList()
		self.readPlaylist()
		self.playlist.refreshList()


class PlayList(MenuList):
	def __init__(self, enableWrapAround = True):
		MenuList.__init__(self, [], enableWrapAround, eListboxPythonMultiContent)
		self.l.setFont(0, gFont("Regular", 20))
		self.l.setItemHeight(30)

	def playlistEntrys(self, count, name, service):
		entrys = [ service ]
		count = str(count)
		entrys.append((eListboxPythonMultiContent.TYPE_TEXT, 5, 1, 40, 26, 0, RT_VALIGN_CENTER, count))
		entrys.append((eListboxPythonMultiContent.TYPE_TEXT,50, 1, 470, 26, 0, RT_VALIGN_CENTER, name))
		return entrys

	def addEntry(self, entry):
		self.list.append(self.playlistEntrys(entry[0], entry[1], entry[2]))

	def getCurrent(self):
		return self.l.getCurrentSelection()[0]

	def resetList(self):
		self.list = []

	def refreshList(self):
		self.l.setList(self.list)
