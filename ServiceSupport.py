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

from Components.config import *
from Components.Element import cached
from Components.Sources.ServiceEvent import ServiceEvent as eServiceEvent
from Components.Sources.CurrentService import CurrentService as eCurrentService
from enigma import eServiceCenter, iServiceInformation, eServiceReference
from ServiceReference import ServiceReference

from CutListSupport import CutList
from MetaSupport import MetaList
from EitSupport import EitList


instance = None


class CurrentService(eCurrentService):
	def __init__(self, navcore):
		eCurrentService.__init__(self, navcore)
		self.__cutlist = None
		self.__path = None

	def cueSheet(self):
		return self.__cutlist

	@cached
	def getCurrentService(self):
		path = None
		service = self.navcore.getCurrentService()
		if service:
			if not isinstance(service, eServiceReference):
				ref = self.navcore.getCurrentlyPlayingServiceReference()
				path = ref and ref.getPath()
			else:
				path = service.getPath()
		if path and path != self.__path:
			self.__path = path
			self.__cutlist = CutList(path)
			service.cueSheet = self.cueSheet
		return service

	service = property(getCurrentService)


class ServiceEvent(eServiceEvent):
	def __init__(self):
		eServiceEvent.__init__(self)
	
	@cached
	def getInfo(self):
		return self.service and ServiceCenter.getInstance().info(self.service)
	
	info = property(getInfo)


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

	#TODO def newService(self):

	def cueSheet(self):
		return self.info and self.info.cueSheet() or []

	def getLength(self, service):
		#self.newService(service)
		return self.info and self.info.getLength(service) or 0
	
	def getInfoString(self, service, type):
		#self.newService(service)
		if type == iServiceInformation.sServiceref:
			return self.info and self.info.getServiceReference() or ""
		if type == iServiceInformation.sDescription:
			return self.info and self.info.getShortDescription() or ""
		if type == iServiceInformation.sTags:
			return self.info and self.info.getTags() or ""
		return "None"

	def getInfo(self, service, type):
		#self.newService(service)
		if type == iServiceInformation.sTimeCreate:
			return self.info and self.info.getMTime() or 0
		return None
	
	def getInfoObject(self, service, type):
		#self.newService(service)
		if type == iServiceInformation.sFileSize:
			return self.info and self.info.getSize() or None
		return None
	
	def getName(self, service):
		#self.newService(service)
		return self.info and self.info.getName() or ""
	
	def getEvent(self, service):
		#self.newService(service)
		return self.info


class Info:
	def __init__(self, service):
		
		# Temporary variables
		path = service and service.getPath()
		self.isfile = os.path.isfile(path)
		self.isdir = os.path.isdir(path)
		meta = path and MetaList(path)			#TODO dynamic or not
		eit = path and EitList(path)				#TODO dynamic or not
		
		# Information which we need later
		self.__cutlist = path and CutList(path) or []		#TODO dynamic or not
		
		self.__size = self.isfile and os.stat(path).st_size \
								or self.isdir and config.EMC.directories_info.value and self.getFolderSize(path) \
								or None
								#TODO or isdvd
		
		self.__mtime = self.isfile and long(os.stat(path).st_mtime) or 0
									#TODO show same time as list
									#TODO or isdir but show only start date
		
		self.__name = service and service.getName() or ""
		self.__reference = service or ""
		
		#TODO dynamic or not
		self.__shortdescription = meta and meta.getMetaDescription() \
													or eit and eit.getEitShortDescription() \
													or self.__name
		self.__tags = meta and meta.getMetaTags() or ""
		
		self.__eventname = self.__name
		
		#TODO dynamic or not
		self.__extendeddescription = eit and eit.getEitDescription() \
																	or meta and meta.getMetaDescription() \
																	or self.isdir and os.path.realpath(path) \
																	or ""
		self.__id = 0
		
		#TODO move upto ServiceInfo
		service.cueSheet = self.cueSheet

	def cueSheet(self):
		return self.__cutlist
	
	def getName(self):
		#EventName NAME
		return self.__name
	
	def getServiceReference(self):
		return self.__reference
	
	def getServiceName(self):
		#MovieInfo MOVIE_REC_SERVICE_NAME
		return ServiceReference(self.__reference).getServiceName() or ""
	
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
		d = datetime.fromtimestamp(self.__mtime)
		return d.strftime("%d.%m.%Y %H:%M")

	def getMTime(self):
		return self.__mtime
	
	def getSize(self):
		return self.__size
	
	def getLength(self, service):
		# Should stay dynamic if it is a record
		#self.newService(service)
		length = 0
		if self.isfile:
			#TODO isfile and isdvd
			esc = eServiceCenter.getInstance()
			info = esc and esc.info(service)
			length = info and info.getLength(service) or 0
		if not length:
			length = self.__cutlist and self.__cutlist.getCutListLength()
		return length or 0
	
	def getBeginTime(self):
		self.getMTime()
	
	def getDuration(self):
		self.getLength()
	
	def getFolderSize(self, loadPath):
		folder_size = 0
		for (path, dirs, files) in os.walk(loadPath):
			for file in files:    
				filename = os.path.join(path, file)
				if os.path.exists(filename):
					folder_size += os.path.getsize(filename)
		return folder_size
