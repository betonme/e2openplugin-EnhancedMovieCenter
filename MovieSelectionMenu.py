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
from Screens.LocationBox import LocationBox
from Tools.BoundFunction import boundFunction
import os

from EMCTasker import emcTasker, emcDebugOut
from EnhancedMovieCenter import _
from Plugins.Extensions.EnhancedMovieCenter.plugin import pluginOpen as emcsetup
from PermanentSort import PermanentSort
from E2Bookmarks import E2Bookmarks
from EMCBookmarks import EMCBookmarks
from RogueFileCheck import RogueFileCheck
from MovieCenter import extTS
global extTS


class MovieMenu(Screen, E2Bookmarks, EMCBookmarks):
	def __init__(self, session, menumode, mselection, mlist, service, selections, currentPath):
		Screen.__init__(self, session)
		self.mode = menumode
		self.mselection = mselection
		self.mlist = mlist
		self.service = service
		self.selections = selections
		self.currentPath = currentPath
		
		self.menu = []
		if menumode == "normal":
			self["title"] = StaticText(_("Choose operation"))
			
			if os.path.realpath(self.currentPath) != os.path.realpath(config.EMC.movie_homepath.value):
				self.menu.append((_("Movie home"), boundFunction(self.close, "Movie home")))
			
			if currentPath == config.EMC.movie_pathlimit.value:
				self.menu.append((_("Directory up"), boundFunction(self.close, "dirup")))
			
			self.menu.append((_("Play last"), boundFunction(self.close, "Play last")))

			
			self.menu.append((_("Play All"), boundFunction(self.close, "playall")))
			self.menu.append((_("Shuffle All"), boundFunction(self.close, "shuffleall")))
			
			if config.EMC.movie_trashcan_enable.value and os.path.exists(config.EMC.movie_trashcan_path.value):
				if service:
					self.menu.append((_("Delete permanently"), boundFunction(self.close, "delete")))
				self.menu.append((_("Empty trashcan"), boundFunction(self.emptyTrash)))
				self.menu.append((_("Go to trashcan"), boundFunction(self.close, "trash")))
			
			self.menu.append((_("Mark all movies"), boundFunction(self.close, "markall")))
			self.menu.append((_("Remove rogue files"), boundFunction(self.remRogueFiles)))
			
			self.menu.append((_("Create link"), boundFunction(self.createLink, currentPath)))
			self.menu.append((_("Create directory"), boundFunction(self.createDir, currentPath)))
			
			if self.service or self.selections:
				self.menu.append((_("Remove cut list marker"), boundFunction(self.remCutListMarker)))
			if service:
				ext = os.path.splitext(self.service.getPath())[1].lower()
				if ext in extTS:
					# Only valid for ts files: CutListEditor, DVDBurn, ...
					self.menu.extend([(p.description, boundFunction(self.execPlugin, p)) for p in plugins.getPlugins(PluginDescriptor.WHERE_MOVIELIST)])
			
			self.menu.append((_("Open E2 Bookmark path"), boundFunction(self.close, "openE2Bookmarks")))
			if not self.isE2Bookmark(currentPath):
				self.menu.append((_("Add directory to E2 Bookmarks"), boundFunction(self.addDirToE2Bookmarks, currentPath)))
			else:
				self.menu.append((_("Remove directory from E2 Bookmarks"), boundFunction(self.removeDirFromE2Bookmarks, currentPath)))
			if service and self.isE2Bookmark(service.getPath()):
				self.menu.append((_("Remove selected E2 Bookmark"), boundFunction(self.close, "removeE2Bookmark", service)))
			
			self.menu.append((_("Open EMC Bookmark path"), boundFunction(self.close, "openEMCBookmarks")))
			if not self.isEMCBookmark(currentPath):
				self.menu.append((_("Add directory to EMC Bookmarks"), boundFunction(self.addDirToEMCBookmarks, currentPath)))
			else:
				self.menu.append((_("Remove directory from EMC Bookmarks"), boundFunction(self.removeDirFromEMCBookmarks, currentPath)))
			if service and self.isEMCBookmark(service.getPath()):
				self.menu.append((_("Remove selected EMC Bookmark"), boundFunction(self.close, "removeEMCBookmark", service)))
			
			self.menu.append((_("Set permanent sort"), boundFunction(self.setPermanentSort, currentPath, mlist.actualSort)))
			if mlist.hasFolderPermanentSort(currentPath):
				self.menu.append((_("Remove permanent sort"), boundFunction(self.removePermanentSort, currentPath)))
			else:
				path = mlist.hasParentPermanentSort(currentPath)
				if path:
					self.menu.append((_("Remove permanent sort from parent"), boundFunction(self.removePermanentSort, path)))
			
			#self.menu.append((_("Open shell script menu"), boundFunction(self.close, "oscripts")))
			self.menu.append((_("EMC Setup"), boundFunction(self.execPlugin, emcsetup)))
			
		elif menumode == "plugins":
			self["title"] = StaticText(_("Choose plugin"))
			if self.service is not None:
				for p in plugins.getPlugins(PluginDescriptor.WHERE_MOVIELIST):
					self.menu.append((p.description, boundFunction(self.execPlugin, p)))
					
		elif menumode == "emcBookmarks":
			self["title"] = StaticText(_("Choose bookmark"))
			bm = self.getEMCBookmarks()
			if bm:
				for line in bm:
					self.menu.append((line, boundFunction(self.close, line)))

		self["menu"] = List(self.menu)
		self["actions"] = ActionMap(["OkCancelActions"],
			{
				"ok":		self.okButton,
				"cancel":	self.close,
			})
		self.skinName = "Menu"
		self.onShow.append(self.onDialogShow)

	def createDir(self, currentPath):
		self.hide()
		self.session.openWithCallback(
				boundFunction(self.createDirCB, currentPath),
				InputBox,
				title=_("Enter name for new directory."),
				windowTitle=_("Create directory") )

	def createDirCB(self, currentPath, name):
		if name is not None:
			name = os.path.join(currentPath, name)
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

	def createLink(self, path):
		self.session.openWithCallback(
				boundFunction( self.createLinkCB, path ),
				LocationBox,
					windowTitle = _("Create Link")
					text = _("Choose directory"),
					currDir = str(path)+"/",
					bookmarks = config.movielist.videodirs,
					autoAdd = False,
					editDir = True,
					inhibitDirs = ["/bin", "/boot", "/dev", "/etc", "/lib", "/proc", "/sbin", "/sys", "/usr", "/var"],
					minFree = 0 )

	def createLinkCB(self, currentPath, linkPath):
		if currentPath == linkPath or linkPath == None:
			self.close(None)
		else:
			try:
				name = os.path.basename(linkPath)
				cmd = 'ln -s "'+ linkPath +'" "'+ os.path.join(currentPath, name) +'"'
				if cmd != "":
					association = []
					association.append((self.mselection.reloadList, None))	# Force list reload after creating the link
					emcTasker.shellExecute(cmd, association)
			except Exception, e:
				emcDebugOut("[EMCMM] createLink exception:\n" + str(e))
			self.close(None)

	def emptyTrash(self):
		self.hide()
		self.session.openWithCallback(
				self.emptyTrashCB,
				MessageBox,
				_("Permanently delete all files in trashcan?"),
				MessageBox.TYPE_YESNO )

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
		self.session.openWithCallback(
				self.remRogueFilesCB,
				MessageBox,
				_("Locate rogue files and remove them? (permanently if no trashcan available, may take a minute or so)"),
				MessageBox.TYPE_YESNO )

	def remRogueFilesCB(self, confirmed):
		if confirmed:
			check = RogueFileCheck(self.currentPath)
			path = config.EMC.movie_trashcan_enable.value and config.EMC.movie_trashcan_path.value
			emcTasker.shellExecute( check.getScript(path) )
			self.session.open(MessageBox, check.getStatistics(), MessageBox.TYPE_INFO)
		self.close(None)

	def remCutListMarker(self):
		self.hide()
		self.session.openWithCallback(
				self.remCutListMarkerCB,
				MessageBox,
				_("Remove all cut file marker permanently?"),
				MessageBox.TYPE_YESNO )

	def remCutListMarkerCB(self, confirm):
		if confirm:
			self.close("cutlistmarker")
		else:
			self.close(None)
			
	def execPlugin(self, plugin):
		plugin(session=self.session, service=self.service)
		if (plugin == emcsetup):
			# Close the Menü and reload the movielist
			self.close("setup")

	def addDirToE2Bookmarks(self, path):
		if path and self.addE2Bookmark( path ) \
			and (config.EMC.bookmarks.value == "Both" or config.EMC.bookmarks.value == "E2") \
			and path == config.EMC.movie_homepath.value:
			#TODO Avoid reload
			# If the custom entry has sortingkeys, maybe an addService will do it
			self.close("reload")
		else:
			self.close(None)

	def removeDirFromE2Bookmarks(self, path):
		if config.EMC.movie_delete_validation.value:
			self.session.openWithCallback(
					boundFunction(self.removeDirFromE2BookmarksConfirmed, path),
					MessageBox,
					_("Do you really want to remove your bookmark\n%s?") % (path) )
		else:
			self.removeDirFromE2BookmarksConfirmed(path, True)

	def removeDirFromE2BookmarksConfirmed(self, path, confirm):
		if confirm \
			and path and self.removeE2Bookmark(path) \
			and (config.EMC.bookmarks.value == "Both" or config.EMC.bookmarks.value == "E2") \
			and path == config.EMC.movie_homepath.value:
			#TODO Avoid reload
			# Just a remove service will do the job
			self.close("reload")
		else:
			self.close(None)

	def addDirToEMCBookmarks(self, path):
		if path and self.addEMCBookmark( path ) \
			and (config.EMC.bookmarks.value == "Both" or config.EMC.bookmarks.value == "EMC") \
			and path == config.EMC.movie_homepath.value:
			#TODO Avoid reload
			# If the custom entry has sortingkeys, maybe an addService will do it
			self.close("reload")
		else:
			self.close(None)

	def removeDirFromEMCBookmarks(self, path):
		if config.EMC.movie_delete_validation.value:
			self.session.openWithCallback(
					boundFunction(self.removeDirFromEMCBookmarksConfirmed, path),
					MessageBox,
					_("Do you really want to remove your bookmark\n%s?") % (path) )
		else:
			self.removeDirFromEMCBookmarksConfirmed(path, True)

	def removeDirFromEMCBookmarksConfirmed(self, path, confirm):
		if confirm \
			and path and self.removeEMCBookmark(path) \
			and (config.EMC.bookmarks.value == "Both" or config.EMC.bookmarks.value == "EMC") \
			and path == config.EMC.movie_homepath.value:
			#TODO Avoid reload
			# Just a remove service will do the job
			self.close("reload")
		else:
			self.close(None)

	def createDir(self):
		self.hide()
		self.session.openWithCallback(self.createDirCB, InputBox, title=_("Enter name for new directory."), windowTitle=_("Create directory"))

	def setPermanentSort(self, path, sort):
		self.mlist.setPermanentSort(path, sort)
		self.close("updatetitle")

	def removePermanentSort(self, path):
		self.mlist.removePermanentSort(path)
		self.close("updatetitle")
	
