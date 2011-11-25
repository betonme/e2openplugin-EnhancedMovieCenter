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


class EMCBookmarks():
	def __init__(self):
		pass

	# Is the EMC bookmarks as a list
	def isEMCBookmark(self, path):
		bm = self.getEMCBookmarks()
		if path in bm:
			return True
		return False

	# Returns the EMC bookmarks as a list
	def getEMCBookmarks(self):
		bm = []
		f = None
		try:
			f = open("/etc/enigma2/emc-bookmarks.cfg", "r")
			bm = f.readlines()
		except Exception, e:
			emcDebugOut("[EMCBookmarks] Exception in getEMCBookmarks: " + str(e))
		finally:
			if f is not None:
				f.close()
		bm = map(lambda b:b[:-1], bm)
		return bm

	# Add a path to the EMC bookmark list
	# Returns True on success
	# Returns False on already in bookmarklist or failure
	def addEMCBookmark(self, path):
		if path:
			try:
			if path.endswith("/"):	path = path[:-1]
			bmfile = open("/etc/enigma2/emc-bookmarks.cfg", "a")
			bmfile.write(path + "\n")
			bmfile.close()
			return True
		except Exception, e:
			emcDebugOut("[EMCMM] addEMCBookmark exception:\n" + str(e))
		return False

	# Remove a path from the EMC bookmark list
	# Returns True on success
	# Returns False on already in bookmarklist or failure
	def removeEMCBookmark(self, path):
		if path:
			try:
				bm = []
				bmfile = open("/etc/enigma2/emc-bookmarks.cfg", "r+")
				bm = f.readlines()
				bm = map(lambda b:b[:-1], bm)
				if path in bm:
					bm.remove(path)
					bmfile.writelines([ p for p in bm ])		
				bmfile.close()
				return True
			except Exception, e:
				emcDebugOut("[EMCMM] removeEMCBookmark exception:\n" + str(e))
		return False
