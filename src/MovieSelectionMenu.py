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
import struct

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
from Tools.Notifications import AddPopup

from EMCFileCache import movieFileCache
from EMCTasker import emcTasker, emcDebugOut
from EnhancedMovieCenter import _
from Plugins.Extensions.EnhancedMovieCenter.plugin import pluginOpen as emcsetup
from PermanentSort import PermanentSort
from E2Bookmarks import E2Bookmarks
from EMCBookmarks import EMCBookmarks
from RogueFileCheck import RogueFileCheck
from MovieCenter import extTS, extMedia
from EnhancedMovieCenter import imgVti
global extTS

cutsParser = struct.Struct('>QI') # big-endian, 64-bit PTS and 32-bit type

def image():
	if imgVti:
		return 30
	else:
		return 28


class MovieMenu(Screen, E2Bookmarks, EMCBookmarks):
	skin = """
	<screen name="EMCMenu" position="center,center" size="600,480" title="EMC menu">
	<widget source="title" render="Label" position="10,10" size="580,35" font="Regular;27" halign="center" />
	<widget source="menu" render="Listbox" position="10,55" size="580,430" itemHeight="%s" scrollbarMode="showOnDemand" enableWrapAround="1">
		<convert type="StringList" />
	</widget>
	</screen>""" % image()

	def __init__(self, session, menumode, mselection, mlist, service, selections, currentPath, playlist=False):
		Screen.__init__(self, session)
		self.mode = menumode
		self.mselection = mselection
		self.mlist = mlist
		self.service = service
		self.selections = selections
		self.currentPath = currentPath
		self.plist = playlist
		self.reloadafterclose = False

		self.menu = []
		if menumode == "normal":
			self["title"] = StaticText(_("Choose operation"))

			if os.path.realpath(self.currentPath) != os.path.realpath(config.EMC.movie_homepath.value):
				self.menu.append((_("Movie home"), boundFunction(self.close, "Movie home")))

			if currentPath == config.EMC.movie_pathlimit.value:
				self.menu.append((_("Directory up"), boundFunction(self.close, "dirup")))

			self.menu.append((_("Reload current directory"), boundFunction(self.close, "reloadwithoutcache")))

			self.menu.append((_("Playlist Options"), boundFunction(self.close, "emcPlaylist")))
			if service is not None:
				ext = os.path.splitext(service.getPath())[1].lower()
				if ext in extMedia:
					self.menu.append((_("Add to current Playlist"), boundFunction(self.close, "addPlaylist")))

			self.menu.append((_("Play last"), boundFunction(self.close, "Play last")))

			self.menu.append((_("Play All"), boundFunction(self.close, "playall")))
			self.menu.append((_("Shuffle All"), boundFunction(self.close, "shuffleall")))

			self.menu.append((_("Cover search"), boundFunction(self.close, "imdb")))
			if service is not None:
				if os.path.isdir(service.getPath()):
					self.menu.append((_("Directory-Cover search"), boundFunction(self.close, "imdbdirectory")))
			self.menu.append((_("Delete"), boundFunction(self.close, "del")))

			if config.EMC.movie_trashcan_enable.value and os.path.exists(config.EMC.movie_trashcan_path.value):
				if service is not None:
					self.menu.append((_("Delete permanently"), boundFunction(self.close, "delete")))
				self.menu.append((_("Empty trashcan"), boundFunction(self.emptyTrash)))
				self.menu.append((_("Go to trashcan"), boundFunction(self.close, "trash")))

			self.menu.append((_("Mark all movies"), boundFunction(self.close, "markall")))
			self.menu.append((_("Remove rogue files"), boundFunction(self.remRogueFiles)))

			self.menu.append((_("Delete cut file(s)"), boundFunction(self.deleteCutFileQ)))

			self.menu.append((_("Create link"), boundFunction(self.createLink, currentPath)))
			self.menu.append((_("Create directory"), boundFunction(self.createDir, currentPath)))

			self.menu.append((_("(Un-)Lock Directory"), boundFunction(self.lockDir, currentPath)))

			if service is not None:
				if os.path.isfile(service.getPath()):
					# can we use it for both ?
					# selections comes also with one file !!! so we can it use.
					if self.selections:
						self.menu.append((_("Copy Movie"), boundFunction(self.close, "Copy Movie", self.selections)))
						self.menu.append((_("Move Movie"), boundFunction(self.close, "Move Movie", self.selections)))
					else:
						self.menu.append((_("Copy Movie"), boundFunction(self.close, "Copy Movie")))
						self.menu.append((_("Move Movie"), boundFunction(self.close, "Move Movie")))
					#self.menu.append((_("Download Movie Information"), boundFunction(self.close, "Movie Information")))
				if service.getPath() != config.EMC.movie_trashcan_path.value:
					if not service.getPath().endswith("/..") and not service.getPath().endswith("/Latest Recordings"):
						self.menu.append((_("Download Movie Information"), boundFunction(self.close, "Movie Information")))
						#self.menu.append((_("Download Movie Cover"), boundFunction(self.close, "dlcover")))

			if self.service is not None or self.selections:
				self.menu.append((_("Rename selected movie(s)"), boundFunction(self.renameMovies)))
				self.menu.append((_("Remove cut list marker"), boundFunction(self.remCutListMarker)))
				self.menu.append((_("Reset marker from selected movie(s)"), boundFunction(self.resMarker)))
				show_plugins = True
				if self.selections:
					for service in self.selections:
						ext = os.path.splitext(service.getPath())[1].lower()
						if ext not in extTS:
							show_plugins = False
							break
				else:
					ext = os.path.splitext(self.service.getPath())[1].lower()
					if ext not in extTS:
						show_plugins = False
				if show_plugins:
					# Only valid for ts files: CutListEditor, DVDBurn, ...
					self.menu.extend([(p.description, boundFunction(self.execPlugin, p)) for p in plugins.getPlugins(PluginDescriptor.WHERE_MOVIELIST)])

			self.menu.append((_("Open E2 Bookmark path"), boundFunction(self.close, "openE2Bookmarks")))
			if not self.isE2Bookmark(currentPath):
				self.menu.append((_("Add directory to E2 Bookmarks"), boundFunction(self.addDirToE2Bookmarks, currentPath)))
			else:
				self.menu.append((_("Remove directory from E2 Bookmarks"), boundFunction(self.removeDirFromE2Bookmarks, currentPath)))
			if service is not None:
				if self.isE2Bookmark(service.getPath()):
					self.menu.append((_("Remove selected E2 Bookmark"), boundFunction(self.close, "removeE2Bookmark", service)))

			self.menu.append((_("Open EMC Bookmark path"), boundFunction(self.close, "openEMCBookmarks")))
			if not self.isEMCBookmark(currentPath):
				self.menu.append((_("Add directory to EMC Bookmarks"), boundFunction(self.addDirToEMCBookmarks, currentPath)))
			else:
				self.menu.append((_("Remove directory from EMC Bookmarks"), boundFunction(self.removeDirFromEMCBookmarks, currentPath)))
			if service is not None:
				if self.isEMCBookmark(service.getPath()):
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

		elif menumode == "emcPlaylist":
			self["title"] = StaticText(_("Playlist Options"))
			self.menu.append((_("Show current Playlist"), boundFunction(self.close, "showPlaylist")))
			if service is not None:
				ext = os.path.splitext(service.getPath())[1].lower()
				if ext in extMedia:
					self.menu.append((_("Add to current Playlist"), boundFunction(self.close, "addPlaylist")))
			if self.plist:
				self.menu.append((_("Play current Playlist"), boundFunction(self.close, "playPlaylist")))
				self.menu.append((_("Play random current Playlist"), boundFunction(self.close, "playPlaylistRandom")))
				self.menu.append((_("Delete current Playlist"), boundFunction(self.close, "delPlaylist")))
			self.menu.append((_("Playlist Setup"), boundFunction(self.close, "setupPlaylist")))

		self["menu"] = List(self.menu)
		self["actions"] = ActionMap(["OkCancelActions", "ColorActions"],
			{
				"ok":       self.okButton,
				"cancel":   self.close,
				"red":      self.redButton,
			})
		self.onShow.append(self.onDialogShow)

	def redButton(self):
		if self.mode != "emcBookmarks": return
		current = self["menu"].getCurrent()
		path = current and current[0]
		if path and self.removeEMCBookmark(path):
			self.menu.remove(current)
			self["menu"].setList(self.menu)
			if (config.EMC.bookmarks.value == "Both" or config.EMC.bookmarks.value == "EMC") \
				and path == config.EMC.movie_homepath.value:
				#TODO Avoid reload
				# Just a remove service will do the job
				self.reloadafterclose = True

	def createDir(self, currentPath):
		self.session.openWithCallback(
				boundFunction(self.createDirCB, currentPath),
				InputBox,
				title=_("Enter name for new directory:"),
				windowTitle=_("Create directory") )

	def createDirCB(self, currentPath, name):
		if name is not None:
			name = os.path.join(currentPath, name)
			if os.path.exists(name):
				self.session.open(MessageBox, _("Directory %s already exists!") % (name), MessageBox.TYPE_ERROR)
			else:
				try:
					os.mkdir(name)
					movieFileCache.delPathFromCache(currentPath)
				except Exception, e:
					emcDebugOut("[EMCMM] createDir exception:\n" + str(e))
				self.close("reload")
		else:
			self.close(None)

	def lockDir(self, currentPath):
		self.hide
		if not os.path.exists(currentPath + '/dir.lock'):
			self.session.openWithCallback(boundFunction(self.lockDirConfirmed, currentPath, False), MessageBox, _("Do you really want to lock the directory %s and all its subfolders?") % (currentPath), MessageBox.TYPE_YESNO)
		else:
			self.session.openWithCallback(boundFunction(self.lockDirConfirmed, currentPath, True), MessageBox, _("The directory %s is already locked. Do you want to unlock it and all its subfolders?") % (currentPath), MessageBox.TYPE_YESNO)

	def lockDirConfirmed(self, currentPath, locked, confirmed):
		if not locked:
			if confirmed:
				emcTasker.shellExecute('touch "' + currentPath + '/dir.lock"')
				movieFileCache.delPathFromCache(currentPath)
				for root, dirs, files in os.walk(currentPath):
					for dir in dirs:
						movieFileCache.delPathFromCache(root + '/' + dir)
						emcTasker.shellExecute('touch "' + root + '/' + dir +  '/dir.lock"')
		else:
			if confirmed:
				emcTasker.shellExecute('rm -f "' + currentPath + '/dir.lock"')
				movieFileCache.delPathFromCache(currentPath)
				for root, dirs, files in os.walk(currentPath):
					for dir in dirs:
						movieFileCache.delPathFromCache(root + '/' + dir)
						emcTasker.shellExecute('rm -rf "' + root + '/' + dir +  '/dir.lock"')

	def createLink(self, path):
		self.session.openWithCallback(
				boundFunction( self.createLinkCB, path ),
				LocationBox,
					windowTitle = _("Create Link"),
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
				movieFileCache.delPathFromCache(currentPath)
				movieFileCache.delPathFromCache(linkPath)
				name = os.path.basename(linkPath)
				cmd = 'ln -s "'+ linkPath +'" "'+ os.path.join(currentPath, name) +'"'
				if cmd != "":
					association = []
					association.append((self.mselection.reloadList))	# Force list reload after creating the link
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
			#emcTasker.shellExecute("rm -f %s/*"%config.EMC.movie_trashcan_path.value)
			self.close("emptytrash")
		else:
			self.close(None)

	def onDialogShow(self):
		self.setTitle(_("Movie Selection Menu"))

	def okButton(self):
		try:
			self["menu"].getCurrent()[1]()
		#except:pass
		except Exception, e:
			import os, sys, traceback
			print _("exception ") + str(e)
			exc_type, exc_value, exc_traceback = sys.exc_info()
			traceback.print_exception(exc_type, exc_value, exc_traceback, file=sys.stdout)

	def remRogueFiles(self):
		self.hide()
		self.session.openWithCallback(
				self.remRogueFilesCB,
				MessageBox,
				_("Locate rogue files and remove them? (permanently if no trashcan available, may take a minute or so)"),
				MessageBox.TYPE_YESNO )

	def remRogueFilesCB(self, confirmed):
		if confirmed:
			movieFileCache.delPathFromCache(self.currentPath)
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

	def resMarker(self):
		self.hide()
		self.session.openWithCallback(
				self.resMarkerCB,
				MessageBox,
				_("Remove all marker permanently?"),
				MessageBox.TYPE_YESNO )

	def resMarkerCB(self, confirm):
		if confirm:
			try:
				if self.selections:
					for service in self.selections:
						path = service.getPath() + ".cuts"
						self.delMarker(path)
					self.close("resMarker")
				else:
					if self.service:
						path = self.service.getPath() + ".cuts"
						self.delMarker(path)
					self.close()
			except Exception, e:
				print("[EMC] Exception in resMarkerCB: " + str(e))
				self.close()
		else:
			self.close(None)

	def delMarker(self, path):
		f = open(path, 'rb')
		cutlist = []
		while 1:
			data = f.read(cutsParser.size)
			if len(data) < cutsParser.size:
				break
			cut, cutType = cutsParser.unpack(data)
			if cutType != 3:
				cutlist.append(data)
		f.close()
		f = open(path, 'wb')
		f.write(''.join(cutlist))
		f.close()

	def renameMovies(self):
		self.close("rename")

	def execPlugin(self, plugin):
		# Very bad but inspect.getargspec won't work
		# Plugins should always be designed to accept additional parameters!
		try:
			plugin(self.session, self.service, self.selections)
		except:
			plugin(session=self.session, service=self.service)

		#self.close("reload")

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
			movieFileCache.delPathFromCache(path)
			self.close("reload")
		else:
			self.close(None)

	def addDirToEMCBookmarks(self, path):
		if path and self.addEMCBookmark( path ) \
			and (config.EMC.bookmarks.value == "Both" or config.EMC.bookmarks.value == "EMC") \
			and path == config.EMC.movie_homepath.value:
			#TODO Avoid reload
			# If the custom entry has sortingkeys, maybe an addService will do it
			movieFileCache.delPathFromCache(path)
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
			movieFileCache.delPathFromCache(path)
			self.close("reload")
		else:
			self.close(None)

	def setPermanentSort(self, path, sort):
		self.mlist.setPermanentSort(path, sort)
		self.close("updatetitle")

	def removePermanentSort(self, path):
		self.mlist.removePermanentSort(path)
		self.close("updatetitle")

	# Overwrite Screen close function
	def close(self, parameter = None, selections = None):
		if parameter is None:
			if self.reloadafterclose:
				parameter = "reload"
		# Call baseclass function
		if selections is not None:
			Screen.close(self, parameter, selections)
		else:
			Screen.close(self, parameter)

	def deleteCutFileQ(self):
		self.session.openWithCallback(self.deleteCutFile, MessageBox, _("Do you really want to delete the cut file?\nIf you have selected a directory, all cut files within the folder and its subfolders will be deleted!"))

	def deleteCutFile(self, confirm):
		if confirm:
			if os.path.isdir(self.service.getPath()):
				emcTasker.shellExecute('find ' + '"' + self.service.getPath() + '" -name "*.cuts" -exec rm -f \'{}\' +')
			else:
				file = self.service.getPath() + ".cuts"
				emcTasker.shellExecute('rm -f "' + file + '"')
				movieFileCache.delPathFromCache(os.path.dirname(self.service.getPath()))
		self.close("reload")
