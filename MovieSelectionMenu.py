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

from Components.config import *
from Components.PluginComponent import plugins
from Components.ActionMap import ActionMap
from Components.Sources.List import List
from Components.Sources.StaticText import StaticText
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Screens.InputBox import InputBox
from Screens.LocationBox import MovieLocationBox
from Tools.BoundFunction import boundFunction
import os

from EMCTasker import emcTasker, emcDebugOut
from EnhancedMovieCenter import _
from Plugins.Extensions.EnhancedMovieCenter.plugin import pluginOpen as emcsetup
from PermanentSort import PermanentSort
from E2Bookmarks import E2Bookmarks
from MovieCenter import extTS
global extTS

class MovieMenu(Screen, E2Bookmarks):
	def __init__(self, session, menumode, mlist, service, selections, currentPath):
		Screen.__init__(self, session)
		self.mode = menumode
		self.mlist = mlist
		self.service = service
		self.selections = selections
		self.currentPath = currentPath
		
		self.menu = []
		if menumode == "normal":
			self["title"] = StaticText(_("Choose operation"))
			if config.EMC.movie_bluefunc.value == "MH":
				self.menu.append((_("Play last"), boundFunction(self.close, "Play last")))
			else:
				self.menu.append((_("Movie home"), boundFunction(self.close, "Movie home")))
			
			if os.path.exists(config.EMC.movie_trashcan_path.value):
				if self.service:
					self.menu.append((_("Delete permanently"), boundFunction(self.close, "delete")))
#				self.menu.append((_("Cleanup trashcan"), boundFunction(self.cleanTrash)))
				self.menu.append((_("Empty trashcan"), boundFunction(self.emptyTrash)))
				self.menu.append((_("Go to trashcan"), boundFunction(self.close, "trash")))
			self.menu.append((_("Mark all movies"), boundFunction(self.markAllMovies)))
			self.menu.append((_("Remove rogue files"), boundFunction(self.remRogueFiles)))
			self.menu.append((_("Create link(s)"), boundFunction(self.createLinks)))
			self.menu.append((_("Create directory"), boundFunction(self.createDir)))
			if self.service or self.selections:
				self.menu.append((_("Remove cut list marker"), boundFunction(self.remCutListMarker)))
			if self.service:
				ext = os.path.splitext(self.service.getPath())[1].lower()
				if ext in extTS:
					# Only valid for ts files: CutListEditor, DVDBurn, ...
					self.menu.extend([(p.description, boundFunction(self.execPlugin, p)) for p in plugins.getPlugins(PluginDescriptor.WHERE_MOVIELIST)])
			self.menu.append((_("Open E2 Bookmark path"), boundFunction(self.openE2Bookmark)))
			self.menu.append((_("Add E2 Bookmark"), boundFunction(self.addE2Bookmark)))
			self.menu.append((_("Set permanent sort"), boundFunction(self.setPermanentSort, currentPath, mlist.alphaSort)))
			if mlist.hasFolderPermanentSort(currentPath):
				self.menu.append((_("Remove permanent sort"), boundFunction(self.removePermanentSort, currentPath)))
			else:
				path = mlist.hasParentPermanentSort(currentPath)
				if path:
					self.menu.append((_("Remove permanent sort from parent"), boundFunction(self.removePermanentSort, path)))
			self.menu.append((_("EMC Setup"), boundFunction(self.execPlugin, emcsetup)))
			
		elif menumode == "plugins":
			self["title"] = StaticText(_("Choose plugin"))
			if self.service is not None:
				for p in plugins.getPlugins(PluginDescriptor.WHERE_MOVIELIST):
					self.menu.append((p.description, boundFunction(self.execPlugin, p)))
		
		self["menu"] = List(self.menu)
		self["actions"] = ActionMap(["OkCancelActions"],
			{
				"ok":		self.okButton,
				"cancel":	self.close,
			})
		self.skinName = "Menu"
		self.onShown.append(self.onDialogShow)

	def createDir(self):
		self.hide()
		self.session.openWithCallback(self.createDirCB, InputBox, title=_("Enter name for new directory."), windowTitle=_("Create directory"))

	def createDirCB(self, name):
		if name is not None:
			name = os.path.join(self.currentPath, name)
			if os.path.exists(name):
				self.session.open(MessageBox, _("Directory "+name+" already exists."), MessageBox.TYPE_ERROR)
			else:
				try:
					os.mkdir(name)
				except Exception, e:
					emcDebugOut("[EMCMM] createDir exception:\n" + str(e))
				self.close("reload")
		else:
			self.close(None)

	def createLinks(self):
		self.session.openWithCallback(self.createLinksCB, MovieLocationBox, text = _("Choose directory"), dir = str(self.currentPath)+"/", minFree = 0)

	def createLinksCB(self, targetPath):
		try:
			if self.currentPath == targetPath or targetPath == None: return
			cmd = ""
			for x in self.selections:
				path = self.mlist.getFilePathOfService(x)
				name = os.path.basename(path)
				cmd += '; ln -s "'+ path +'" "'+ targetPath + name +'"'
			if cmd != "":
				emcTasker.shellExecute(cmd[2:])	# first move, then delete if expiration limit is 0
				self.close(None)
		except Exception, e:
			emcDebugOut("[EMCMM] createLinks exception:\n" + str(e))

	def emptyTrash(self):
		self.hide()
		self.session.openWithCallback(self.emptyTrashCB, MessageBox, _("Permanently delete all files in trashcan?"), MessageBox.TYPE_YESNO)

	def emptyTrashCB(self, confirmed):
		if confirmed:
			# TODO append callback refreshlist
			emcTasker.shellExecute("rm -f %s/*"%config.EMC.movie_trashcan_path.value)
		self.close(None)

	def onDialogShow(self):
		self.setTitle(_("Movie Selection Menu"))

	def okButton(self):
		try:
			self["menu"].getCurrent()[1]()
		except:pass

	def remRogueFiles(self):
		self.hide()
		self.session.openWithCallback(self.remRogueFilesCB, MessageBox, _("Locate rogue files and remove them? (permanently if no trashcan available, may take a minute or so)"), MessageBox.TYPE_YESNO)

	def remRogueFilesCB(self, confirmed):
		if confirmed:
			self.close("rogue")
		else:
			self.close(None)

	def markAllMovies(self):
		for i in xrange( len (self.mlist) ):
			self.mlist.toggleSelection( index=i )
		self.close(None)

	def remCutListMarker(self):
		self.hide()
		self.session.openWithCallback(self.remCutListMarkerCB, MessageBox, _("Remove all cut file marker permanently?"), MessageBox.TYPE_YESNO)

	def remCutListMarkerCB(self, confirmed):
		if confirmed:
			self.close("cutlistmarker")
		else:
			self.close(None)
			
	def execPlugin(self, plugin):
		plugin(session=self.session, service=self.service)
		if (plugin == emcsetup):
			# Close the Menü and reload the movielist
			self.close("setup")

	def openE2Bookmark(self):
		self.session.openWithCallback(self.openE2BookmarkCB, MovieLocationBox, text = _("Open E2 Bookmark path"), dir = str(self.currentPath)+"/")

	def openE2BookmarkCB(self, path=None):
		if path is not None:
			self.close("bookmark", path)
		else:
			self.close(None)

	def addE2Bookmark(self):
		if self.addBookmark( self.currentPath ):
			if config.EMC.bookmarks_e2.value and self.currentPath == config.EMC.movie_homepath.value:
				#TODO Avoid reload
				# If the custom entry has sortingkeys, maybe an addService will do it
				self.close("reload")
			else:
				self.close(None)

	def setPermanentSort(self, path, sort):
		self.mlist.setPermanentSort(path, sort)
		self.close(None)

	def removePermanentSort(self, path):
		self.mlist.removePermanentSort(path)
		self.close(None)
	
