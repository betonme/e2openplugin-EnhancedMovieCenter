#!/usr/bin/python
# encoding: utf-8
#
# EMCEventName
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
import NavigationInstance

from Components.config import *

from Components.Converter.Converter import Converter
from Components.Converter.MovieInfo import MovieInfo
from Components.Element import cached, ElementError
from enigma import iServiceInformation, eServiceReference
from ServiceReference import ServiceReference

from Plugins.Extensions.EnhancedMovieCenter.MetaSupport import MetaList
from Plugins.Extensions.EnhancedMovieCenter.EitSupport import EitList


class EMCMovieInfo(MovieInfo):
	def __init__(self, type):
		MovieInfo.__init__(self, type)
		self.meta = None
		self.eit = None

	@cached
	def getText(self):
		try:
			service = self.source.service
			info = self.source.info
			
			if service and not isinstance(service, eServiceReference):
				if NavigationInstance and NavigationInstance.instance:
					service = NavigationInstance.instance.getCurrentlyPlayingServiceReference()
			
			if self.type == self.MOVIE_SHORT_DESCRIPTION:
				# Maybe call only if ts file
				shortdesc = info and service and info.getInfoString(service, iServiceInformation.sDescription)
				#TODO con print "EMC mi shortdesc1 " + str(shortdesc)
				if not shortdesc:
					if service:
						path = service.getPath()
						self.meta = service and MetaList(path)
						shortdesc = self.meta and self.meta.getMetaDescription()
						#TODO con print "EMC mi shortdesc1a " + str(shortdesc)
						if not shortdesc:
							# Maybe call only if ts file
							event = self.source.event
							shortdesc = event and event.getShortDescription()
							#TODO con print "EMC mi shortdesc2 " + str(shortdesc)
						if not shortdesc:
							self.eit = service and EitList(path)
							shortdesc = self.eit and self.eit.getEitShortDescription()
							#TODO con print "EMC mi shortdesc3 " + str(shortdesc)
						if not shortdesc:
							#1
							#	rec_ref_str = info and info.getInfoString(service, iServiceInformation.sServiceref)
							#	shortdesc = rec_ref_str and ServiceReference(rec_ref_str).getServiceName()
							#2
							# filename = os.path.basename(service.getPath())
							# shortdesc = getFileTitle(filename, service)[0]
							#3
							shortdesc = service.getName()
							#TODO con print "EMC mi shortdesc4 Service getName " + str(shortdesc)
							#Fallback basename path
				return shortdesc or ""
						
			elif self.type == self.MOVIE_META_DESCRIPTION:
				# Maybe call only if ts file
				extdesc = info and service and info.getInfoString(service, iServiceInformation.sDescription)
				#TODO con print "EMC mi extdesc1 " + str(extdesc)
				if not extdesc:
					if service:
						path = service.getPath()
						self.meta = service and MetaList(path)
						extdesc = self.meta and self.meta.getMetaDescription()
						#TODO con print "EMC mi extdesc3 " + str(extdesc)
						if not extdesc:
								if not os.path.isfile(path):
									# Resolve symbolic link
									extdesc = os.path.realpath(path)
									#TODO con print "EMC en extdesc4 " + str(extdesc)
#								elif path == "..":
#									# Resolve symbolic link of dirname
#									#TODO where to get the directory
#									extdesc = os.path.realpath( os.path.dirname(path) )
#									#TODO con print "EMC en extdesc3a " + str(extdesc)
#								elif os.path.isdir(path):
#									# Resolve symbolic link
#									extdesc = os.path.realpath(path)
#									#TODO con print "EMC en extdesc4 " + str(extdesc)
				return extdesc or ""
				
			elif self.type == self.MOVIE_REC_SERVICE_NAME:
				# Maybe call only if ts file
				rec_ref_str = info.getInfoString(service, iServiceInformation.sServiceref)
				recsername = ServiceReference(rec_ref_str).getServiceName()
				if not recsername:
					#filename = os.path.basename(service.getPath())
					#recsername = getFileTitle(filename, service)[0]
					recsername = service.getName()
					#TODO con print "EMC mi recsername Service getName " + str(recsername)
					#Fallback basename path
				return recsername or ""
				
			elif self.type == self.MOVIE_REC_FILESIZE:
				filesize = info.getInfoObject(service, iServiceInformation.sFileSize)
				#TODO con print "EMC mi filesize " + str(filesize)
				if filesize is not None:
					return "%d MB" % (filesize / (1024*1024))
				return ""
				
		except Exception, e:
			print "[EMCMI] getText exception:" + str(e)

	text = property(getText)
