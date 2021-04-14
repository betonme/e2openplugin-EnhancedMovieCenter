#!/usr/bin/python
# encoding: utf-8
#
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
import struct
from datetime import datetime
from time import mktime

from Components.config import *
from Components.Element import cached
from enigma import eServiceCenter, iServiceInformation, eServiceReference
from ServiceReference import ServiceReference
from EMCFileCache import movieFileCache

from CutListSupport import CutList
from MetaSupport import MetaList, getInfoFile
from EitSupport import EitList
from RecordingsControl import getRecording
instance = None

class ServiceCenter:
	def __init__(self):
		global instance
		instance = eServiceCenter.getInstance()
		instance.info = self.info

	@staticmethod
	def getInstance():
		global instance
		if instance is None:
			ServiceCenter()
		return instance

	def info(self, service):
		return ServiceInfo(service)

class ServiceInfo:
	def __init__(self, service):
		if service:
			self.service = service
			self.info = Info(service)
		else:
			self.service = None
			self.info = None

	def cueSheet(self):
		return self.info and self.info.cueSheet() or []

	def getLength(self, service):
		return self.info and self.info.getLength(service) or 0

	def getInfoString(self, service, type):
		if type == iServiceInformation.sServiceref:
			return self.info and self.info.getServiceReference() or ""
		if type == iServiceInformation.sDescription:
			return self.info and self.info.getShortDescription() or ""
		if type == iServiceInformation.sTags:
			return self.info and self.info.getTags() or ""
		return "None"

	def getInfo(self, service, type):
		if type == iServiceInformation.sTimeCreate:
			# Return time in seconds
			return self.info and self.info.getMTime() or 0
		return None

	def getInfoObject(self, service, type):
		if type == iServiceInformation.sFileSize:
			return self.info and self.info.getSize() or None
		return None

	def getName(self, service):
		return self.info and self.info.getName() or ""

	def getEvent(self, service):
		return self.info


class Info:
	def __init__(self, service):

		self.__name = service and service.getName() or ""

		self.path = path = service and service.getPath()

		self.isfile = os.path.isfile(path)
		self.isdir = os.path.isdir(path)
		ext = path and os.path.splitext(path)[1].lower()

		meta = path and MetaList(path)
		eit = path and EitList(path)

		# Information which we need later
		self.__cutlist = path and CutList(path) or []

		self.__size = self.isfile and os.stat(path).st_size or self.isdir and (config.EMC.directories_info.value or config.EMC.directories_size_skin.value) and self.getFolderSize(path) or None

		self.__mtime = self.isfile and hasattr(service, "date") and mktime(service.date.timetuple()) or None

		self.__reference = service or ""
		self.__rec_ref_str = meta and meta.getMetaServiceReference() or ""

		self.__shortdescription = meta and meta.getMetaDescription() or eit and eit.getEitShortDescription() or ""

		self.__tags = meta and meta.getMetaTags() or ""

		self.__eventname = meta and meta.getMetaName() or eit and eit.getEitName() or self.__name

		self.__extendeddescription = eit and eit.getEitDescription() or ""

		#No Description in *.eit file or no *.eit file exists
		#Try reading description from *.txt file
		if not self.__extendeddescription:

			exts = [".txt"]
			txtpath = getInfoFile(path, exts)[1]

			# read the playlist-entrys to show the list as overview
			if ext == ".e2pls":
				from EMCPlayList import readPlaylist
				plistdesc = ""
				plist = readPlaylist(service.getPath())
				for x in plist:
					plistdesc += x
				self.__extendeddescription = plistdesc
			else:

				if os.path.exists(txtpath):
					txtdescarr = open(txtpath).readlines()
					txtdesc = ""
					for line in txtdescarr:
						txtdesc += line
					self.__extendeddescription = txtdesc

				elif config.EMC.show_path_extdescr.value:
					if config.EMC.movie_real_path.value:
						desc = os.path.realpath(path)
					else:
						desc = path

					# Very bad but there can be both encodings
					# E2 recordings are always in utf8
					# User files can be in cp1252
					#TODO Is there no other way?
					try:
						desc.decode('utf-8')
					except UnicodeDecodeError:
						try:
							desc = path.decode("cp1252").encode("utf-8")
						except UnicodeDecodeError:
							desc = path.decode("iso-8859-1").encode("utf-8")
					self.__extendeddescription = desc
				else:
					self.__extendeddescription = ""

		self.__id = 0

		service.cueSheet = self.cueSheet

	def cueSheet(self):
		return self.__cutlist

	def getName(self):
		#EventName NAME
		return self.__name

	def getServiceReference(self):
		return self.__rec_ref_str

	def getTags(self):
		return self.__tags

	def getEventName(self):
		return self.__eventname

	def getShortDescription(self):
		#MovieInfo MOVIE_META_DESCRIPTION
		#MovieInfo SHORT_DESCRIPTION
		#EventName SHORT_DESCRIPTION
		return self.__shortdescription

	def getExtendedDescription(self):
		#EventName EXTENDED_DESCRIPTION
		return self.__extendeddescription

	def getEventId(self):
		#EventName ID
		return self.__id

	def getBeginTimeString(self):
		d = self.__mtime and datetime.fromtimestamp(self.__mtime)
		if d:
			if config.EMC.movie_date_format.value:
				return d.strftime(config.EMC.movie_date_format.value)
			else:
				return d.strftime("%d.%m.%Y %H:%M")
		else:
			return ""

	def getMTime(self):
		return self.__mtime

	def getSize(self):
		return self.__size

	def getLength(self, service=None):
		#TODO read from meta eit
		#E2 will read / calculate it directly from ts file
		# Should stay dynamic if it is a copy or move

		# If it is a record we will force to use the timer duration
		length = 0
		if config.EMC.record_show_real_length.value:
			record = getRecording(self.path)
			if record:
				begin, end, service = record
				length = end - begin # times = (begin, end) : end - begin
			if length:
				return length
		service = service or self.__reference
		if self.isfile:
			esc = eServiceCenter.getInstance()
			info = esc and esc.info(service)
			length = info and info.getLength(service) or 0
		if length <= 0:
			length = self.__cutlist and self.__cutlist.getCutListLength()
		if length > 86400:
			length = 0
		return length or 0

	def getBeginTime(self):
		return self.getMTime()

	def getDuration(self):
		return self.getLength()

	def getFolderSize(self, loadPath):
		folder_size = 0
		if config.EMC.directories_size_skin.value:
			getValues = movieFileCache.getCountSizeFromCache(loadPath)
			if getValues is not None:
				count, size = getValues
				if size is not None:
					folder_size = size * 1024 * 1024 * 1024
		return folder_size
