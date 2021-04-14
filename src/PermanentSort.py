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

import os
import pickle

from collections import defaultdict

from EMCTasker import emcDebugOut

from Components.config import *

from Tools.XMLTools import stringToXML
import xml.etree.cElementTree

global CFG_FILE
CFG_FILE = "/etc/enigma2/emc-permsort.cfg"
global XML_FILE
XML_FILE = "/etc/enigma2/emc-permsort.xml"

# PermanentSort class
class PermanentSort():

	def __init__(self, path=None):
		self.__permanentSort = defaultdict(list)
		if os.path.exists(XML_FILE):
			self.__permanentSort.update(self.__readPermanentSortXmlFile())
		else:
			#read old format and convert to xml
			self.__permanentSort.update(self.__readPermanentSortCfgFile())
			self.__writePermanentSortXmlFile(self.__permanentSort)

	def hasPermanentSort(self, path):
		return self.hasFolderPermanentSort(path) or self.hasParentPermanentSort(path)

	def hasFolderPermanentSort(self, path):
		path = os.path.normpath(path).decode('utf-8')
		if path in self.__permanentSort:
			return True
		else:
			return False

	def hasParentPermanentSort(self, path):
		path = os.path.normpath(path).decode('utf-8')
		while len(path) > 1:
			path = os.path.dirname(path).decode('utf-8')
			if path in self.__permanentSort:
				return path
		return False

	def setPermanentSort(self, path, sort):
		path = os.path.normpath(path).decode('utf-8')
		self.__permanentSort[path] = sort
		self.__writePermanentSortXmlFile(self.__permanentSort)

	def getPermanentSort(self, path):
		path = os.path.normpath(path).decode('utf-8')
		while len(path) > 1:
			if path in self.__permanentSort:
				sort, order = self.__permanentSort[path]
				return sort, order
			path = os.path.dirname(path).decode('utf-8')
		return None

	def removePermanentSort(self, path):
		path = os.path.normpath(path).decode('utf-8')
		if path in self.__permanentSort:
			del self.__permanentSort[path]
			self.__writePermanentSortXmlFile(self.__permanentSort)

	def __readPermanentSortXmlFile(self):
		data = {}
		if os.path.exists(XML_FILE):
			f = None

			# Read from file
			try:
				f = open(XML_FILE, "rb")
				doc = xml.etree.cElementTree.parse(f)
				root = doc.getroot()
			except Exception, e:
				emcDebugOut("[EMC] Exception in __readPermanentSortXmlFile Load: " + str(e))
			finally:
				if f is not None:
					f.close()

			# Parse the data
			try:
				for entry in root.findall("entry"):
					key = entry.get("key")
					modestring = entry.get("modestring")
					from Plugins.Extensions.EnhancedMovieCenter.plugin import sort_modes
					value = sort_modes.get(modestring)[1]
					data[key] = value
			except Exception, e:
				emcDebugOut("[EMC] Exception in __readPermanentSortXmlFile Parse: " + str(e))

		return data

	def __writePermanentSortXmlFile(self, data):
		f = None
		try:
			from Plugins.Extensions.EnhancedMovieCenter.plugin import sort_modes
			list = ['<?xml version="1.0" ?>\n']
			list.append('<PermanentSort>\n')
			for key, value in data.items():
				modestring = [k for k, v in sort_modes.items() if v[1] == value][0]
				list.append('<entry')
				list.append(' key="' + stringToXML(str(key)) + '"')
				list.append(' modestring="' + str(modestring) + '"')
				list.append('>')
				list.append('</entry>\n')
			list.append('</PermanentSort>\n')

			f = open(XML_FILE, "wb")
			for x in list:
				f.write(x)
		except Exception, e:
			emcDebugOut("[EMC] Exception in __writePermanentSortXmlFile: " + str(e))
		finally:
			if f is not None:
				f.close()

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
						data[key] = (value, sort_modes.get(config.EMC.moviecenter_sort.value)[1][1])
			except Exception, e:
				emcDebugOut("[EMC] Exception in readPermanentSortCfgFile Parse: " + str(e))

		return data

#	def __writePermanentSortCfgFile(self, data):
#		f = None
#		try:
#			f = open(CFG_FILE, "wb")
#			pickle.dump(data, f)
#		except Exception, e:
#			emcDebugOut("[EMC] Exception in writePermanentSortCfgFile: " + str(e))
#		finally:
#			if f is not None:
#				f.close()
