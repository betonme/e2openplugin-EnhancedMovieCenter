#!/usr/bin/python
# encoding: utf-8
#
# PermanentSort
# Copyright (C) 2011 betonme
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

import os, pickle

from collections import defaultdict

from EMCTasker import emcDebugOut

global cfg_file
cfg_file = "/etc/enigma2/emc-permsort.cfg"


# PermanentSort class
class PermanentSort():
	
	def __init__(self, path=None):
		self.permanentSort = defaultdict(list)
		self.permanentSort.update( self.readPermanentSortCfgFile() )

	def hasPermanentSort(self, path):
		return self.hasFolderPermanentSort(path) or self.hasParentPermanentSort(path)

	def hasFolderPermanentSort(self, path):
		path = os.path.normpath(path)
		if path in self.permanentSort:
			return True
		else:
			return False

	def hasParentPermanentSort(self, path):
		path = os.path.normpath(path)
		while len(path)>1:
			path = os.path.dirname(path)
			if path in self.permanentSort:
				return path
		return False

	def setPermanentSort(self, path, sort):
		path = os.path.normpath(path)
		self.permanentSort[path] = sort
		self.writePermanentSortCfgFile(self.permanentSort)

	def getPermanentSort(self, path):
		path = os.path.normpath(path)
		while len(path)>1:
			if path in self.permanentSort:
				return self.permanentSort[path]
			path = os.path.dirname(path)
		return None

	def removePermanentSort(self, path):
		path = os.path.normpath(path)
		if path in self.permanentSort:
			del self.permanentSort[path]
			self.writePermanentSortCfgFile(self.permanentSort)

	def readPermanentSortCfgFile(self):
		data = {}
		f = None
		try:
			f = open(cfg_file, "r")
			data = pickle.load(f)
		except Exception, e:
			emcDebugOut("[EMC] Exception in readPermanentSortCfgFile: " + str(e))
		finally:
			if f is not None:
				f.close()
		return data
	
	def writePermanentSortCfgFile(self, data):
		f = None
		try:
			f = open(cfg_file, "wb")
			pickle.dump(data, f)
		except Exception, e:
			emcDebugOut("[EMC] Exception in writePermanentSortCfgFile: " + str(e))
		finally:
			if f is not None:
				f.close()
