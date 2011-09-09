'''
Copyright (C) 2011 betonme

In case of reuse of this source code please do not remove this copyright.

	This program is free software: you can redistribute it and/or modify
	it under the terms of the GNU General Public License as published by
	the Free Software Foundation, either version 3 of the License, or
	(at your option) any later version.

	This program is distributed in the hope that it will be useful,
	but WITHOUT ANY WARRANTY; without even the implied warranty of
	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
	GNU General Public License for more details.

	For more information on the GNU General Public License see:
	<http://www.gnu.org/licenses/>.

For example, if you distribute copies of such a program, whether gratis or for a fee, you 
must pass on to the recipients the same freedoms that you received. You must make sure 
that they, too, receive or can get the source code. And you must show them these terms so they know their rights.
'''

import os
import struct

from Components.Element import cached
from Components.Sources.ServiceEvent import ServiceEvent as eServiceEvent
from enigma import eServiceCenter, iServiceInformation
#from Tools.Directories import fileExists

from CutListSupport import CutList
from MetaSupport import MetaList
from EitSupport import EitList


instance = None

# def getFolderSize(loadPath):
# 	folder_size = 0
# 	for (path, dirs, files) in os.walk(loadPath):
# 		for file in files:    
# 			filename = os.path.join(path, file)    
# 			folder_size += os.path.getsize(filename)
# 	return folder_size

# def detectDVDStructure(loadPath):
# 	if not os.path.isdir(loadPath):
# 		return None
# 	if fileExists(loadPath + "VIDEO_TS.IFO"):
# 		return loadPath + "VIDEO_TS.IFO"
# 	if fileExists(loadPath + "VIDEO_TS/VIDEO_TS.IFO"):
# 		return loadPath + "VIDEO_TS/VIDEO_TS.IFO"
# 	return None


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
		serviceInfo = eServiceCenter.getInstance().info(service)
		if serviceInfo is not None:
#TODO why should we replace it
# 			from MovieCenter import extTS
# 			global extTS
# 			path = service.getPath()
# 			if os.path.splitext(path)[1].lower() in extTS:
# 				# Replace original cuesheet
# 				serviceInfo.cueSheet = CutList(path)
# 				return serviceInfo
# 			return ServiceInfo(service)
			return serviceInfo
		else:
			return ServiceInfo(service)


class ServiceInfo:
	def __init__(self, service):
		self.service = None
		self.cutlist = None
		self.meta = None
		self.eit = None
		self.info = None
		self.newService(service)
	
	def newService(self, service):
		if self.service != service:
			path = service.getPath()
			self.service = service
			self.path = path
			self.__size = os.path.isfile(path) and  os.path.getsize(path) or 0 # TODO folder
			self.__mtime = os.path.exists(path) and long(os.stat(path).st_mtime) or 0 # TODO folder
			
			self.cutlist = CutList(path)
			self.meta = MetaList(path)
			self.eit = EitList(path)
			
			self.info = Info(self, service)
			self.event = Event(self, service)
			service.cueSheet = self.cueSheet
	
	def cueSheet(self):
		return self.cutlist
	
	def getLength(self, service):
		#self.newService(service)
		return self.cutlist.getCutListLength()
	
	def getInfoString(self, service, type):
		#self.newService(service)
		if type == iServiceInformation.sServiceref:
			return service.ref.toString()
		if type == iServiceInformation.sDescription:
			return self.info.getShortDescription()
		if type == iServiceInformation.sTags:
			return self.info.getTags()
		return "None"

	def getInfo(self, service, type):
		#self.newService(service)
		if type == iServiceInformation.sTimeCreate:
			return self.__mtime
		return None
	
	def getInfoObject(self, service, type):
		#self.newService(service)
		# TODO EMC Folder handling
# 		if type == iServiceInformation.sFileSize:
# 			dvd = detectDVDStructure(service.getPath()+"/")
# 			if dvd:
# 				return getFolderSize(os.path.dirname(dvd))
# 			return os.path.getsize(service.getPath())
		return self.__size
	
#	def getServiceReference(self):
#		return self.info
	
	def getName(self, service):
		#self.newService(service)
		return self.info.name
	
	def getEvent(self, service):
		#self.newService(service)
# 		#TODO Performance
# 		if os.path.exists(service.getPath() + ".eit"):
# 			return EventInformationTable(service.getPath() + ".eit")
# 		else:
		return self.event


class Info:
	def __init__(self, serviceInfo):
		meta = serviceInfo.meta
		meta = serviceInfo.meta
		service = serviceinfo.service
		
		self.__name = service.getName() or ""
		self.__servicename = service.getServiceName() or ""
		self.__description = meta and meta.getShortDescription() \
													or eit and eit.getEitShortDescription() \
													or self.name
		self.__tags = meta and meta.getMetaTags() or ""

	def getName(self):
		#EventName NAME
		return self.__name

	def getServiceName(self):
		#MovieInfo MOVIE_REC_SERVICE_NAME
		return self.__servicename

	def getShortDescription(self):
		#MovieInfo MOVIE_META_DESCRIPTION
		#MovieInfo SHORT_DESCRIPTION
		#EventName SHORT_DESCRIPTION
		return self.__description

	def getTags(self):
		return self.__tags


class Event:
	def __init__(self, serviceinfo):
		path = serviceinfo.path
		self.__eventname = serviceinfo.info.getName()
		self.__shortdescription = serviceinfo.info.getShortDescription()
		self.__extendeddescription = serviceinfo.eit.getEitDescription() \
																	or serviceinfo.meta.getMetaDescription() \
																	or not os.path.isfile(path) and os.path.realpath(path) \
																	or ""
	
	def getEventName(self):
		return self.__eventname
	
	def getShortDescription(self):
		return self.__shortdescription

	def getExtendedDescription(self):
		#EventName EXTENDED_DESCRIPTION
		return self.__extendeddescription

	def getEventId(self):
		#EventName ID
		return 0

# 	def getBeginTimeString(self):
# 		from datetime import datetime
# 		begin = self.serviceInfo.getInfo(self.service, iServiceInformation.sTimeCreate)
# 		d = datetime.fromtimestamp(begin)
# 		return d.strftime("%d.%m.%Y %H:%M")
	
#	def getDuration(self):
#		return self.serviceInfo.length
	
