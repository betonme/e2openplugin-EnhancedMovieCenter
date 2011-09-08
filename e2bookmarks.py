#!/usr/bin/python
# encoding: utf-8
#
# Copyright (C) 2011 by betonme
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
from operator import isCallable

from Components.config import *

from EMCTasker import emcTasker, emcDebugOut


class E2Bookmarks(Screen):
	def __init__(self):
		pass

	# Returns the E2 bookmarks as a list
	def getBookmarks(self):
		if config.movielist and config.movielist.videodirs:
			return [os.path.normpath(e2bm) for e2bm in config.movielist.videodirs.value]
		else
			return []

	# Add a path to the E2 bookmark list
	# Returns True on success
	# Returns False on already in bookmarklist or failure
	def addBookmark(self, bookmark):
		bookmark = os.path.normpath(bookmark)+"/"
		if bookmark and config.movielist and config.movielist.videodirs:
			bookmarks = [os.path.normpath(e2bm)+"/" for e2bm in config.movielist.videodirs.value]
			if bookmark not in bookmarks:
				bookmarks.append(bookmark)
				bookmarks.sort()
				config.movielist.videodirs.value = bookmarks
				config.movielist.videodirs.save()
				return True
		return False

	# Remove a path from the E2 bookmark list
	# Callback is only called on success
	def removeBookmark(self, service, callback=None):
		if service and config.movielist and config.movielist.videodirs:
			bookmark = os.path.normpath(service.getPath())+"/"
			bookmarks = [os.path.normpath(e2bm)+"/" for e2bm in config.movielist.videodirs.value]
			if bookmark in bookmarks:
				# Adapted from LocationBox
				self.session.openWithCallback(
					boundFunction(self.__removeBookmarkConfirmed, service, callback),
					MessageBox,
					_("Do you really want to remove your bookmark of %s?") % (bookmark) )

	def __removeBookmarkConfirmed(self, service, callback, confirm):
		if confirm:
			bookmark = os.path.normpath(service.getPath())+"/"
			bookmarks = [os.path.normpath(e2bm)+"/" for e2bm in config.movielist.videodirs.value]
			if bookmark in bookmarks:
				bookmarks.remove(bookmark)
				bookmarks.sort()
				config.movielist.videodirs.value = bookmarks
				config.movielist.videodirs.save()
				if callback is not None and isCallable(callback):
					callback(service)
