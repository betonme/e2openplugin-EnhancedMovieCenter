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

from Components.config import *

global CFG_FILE
CFG_FILE = "/etc/enigma2/emc-permsort.cfg"

# PermanentSort class
class PermanentSort():

	def __init__(self, path=None):
		self.__permanentSort = defaultdict(list)
		self.__permanentSort.update( self.__readPermanentSortCfgFile() )

	def hasPermanentSort(self, path):
		return self.hasFolderPermanentSort(path) or self.hasParentPermanentSort(path)

	def hasFolderPermanentSort(self, path):
		path = os.path.normpath(path)
		if path in self.__permanentSort:
			return True
		else:
			return False

	def hasParentPermanentSort(self, path):
		path = os.path.normpath(path)
		while len(path)>1:
			path = os.path.dirname(path)
			if path in self.__permanentSort:
				return path
		return False

	def setPermanentSort(self, path, sort):
		path = os.path.normpath(path)
		self.__permanentSort[path] = sort
		self.__writePermanentSortCfgFile(self.__permanentSort)

	def getPermanentSort(self, path):
		path = os.path.normpath(path)
		while len(path)>1:
			if path in self.__permanentSort:
				sort, order = self.__permanentSort[path]
				return sort, order
			path = os.path.dirname(path)
		return None

	def removePermanentSort(self, path):
		path = os.path.normpath(path)
		if path in self.__permanentSort:
			del self.__permanentSort[path]
			self.__writePermanentSortCfgFile(self.__permanentSort)

	def __readPermanentSortCfgFile(self):
		data = {}
		if os.path.exists(CFG_FILE):
			f = None

			# Read from file
			try:
				f = open(CFG_FILE, "rb")
				data = pickle.load(f)
			except Exception, e:
				emcDebugOut("[EMC] Exception in readPermanentSortCfgFile Load: " + str(e))
			finally:
				if f is not None:
					f.close()

			# Parse the data
			try:
				for key, value in data.items():
					if not isinstance(value, tuple):
						# There is only the sorting stored, add the default order
						#data[key] = (value, config.EMC.moviecenter_sort.value[1])
						from Plugins.Extensions.EnhancedMovieCenter.plugin import sort_modes
						data[key] = (value, sort_modes.get( config.EMC.moviecenter_sort.value )[1][1])
			except Exception, e:
				emcDebugOut("[EMC] Exception in readPermanentSortCfgFile Parse: " + str(e))

		return data

	def __writePermanentSortCfgFile(self, data):
		f = None
		try:
			f = open(CFG_FILE, "wb")
			pickle.dump(data, f)
		except Exception, e:
			emcDebugOut("[EMC] Exception in writePermanentSortCfgFile: " + str(e))
		finally:
			if f is not None:
				f.close()