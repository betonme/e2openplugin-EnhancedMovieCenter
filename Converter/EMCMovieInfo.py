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
from Plugins.Extensions.EnhancedMovieCenter.MovieCenter import getMovieName

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
				shortdesc = info and service and info.getInfoString(service, iServiceInformation.sDescription)
				print "EMC shortdesc1 " + str(shortdesc)
				if not shortdesc:
					self.meta = service and MetaList(service)
					shortdesc = self.meta and self.meta.getMetaDescription()
					print "EMC shortdesc1a " + str(shortdesc)
				if not shortdesc:
					event = self.source.event
					shortdesc = event and event.getShortDescription()
					print "EMC shortdesc2 " + str(shortdesc)
				if not shortdesc:
					self.eit = service and EitList(service)
					shortdesc = self.eit and self.eit.getEitShortDescription()
					print "EMC shortdesc3 " + str(shortdesc)
				#TODO Movie title
				if not shortdesc:
					filename, ext = os.path.splitext(service.getPath())
					shortdesc = getMovieName(filename, service, "")
					#	rec_ref_str = info and info.getInfoString(service, iServiceInformation.sServiceref)
					#	shortdesc = rec_ref_str and ServiceReference(rec_ref_str).getServiceName()
					print "EMC shortdesc4 getMovieName " + str(shortdesc)
				return shortdesc or ""
						
			elif self.type == self.MOVIE_META_DESCRIPTION:
				extdesc = info and service and info.getInfoString(service, iServiceInformation.sDescription)
				print "EMC extdesc1 " + str(extdesc)
				if not extdesc:
					self.meta = service and MetaList(service, borg=True)
					extdesc = self.meta and self.meta.getMetaDescription()
					print "EMC extdesc3 " + str(extdesc)
				return extdesc or ""
				
			elif self.type == self.MOVIE_REC_SERVICE_NAME:
				rec_ref_str = info.getInfoString(service, iServiceInformation.sServiceref)
				return ServiceReference(rec_ref_str).getServiceName()
				
			elif self.type == self.MOVIE_REC_FILESIZE:
				filesize = info.getInfoObject(service, iServiceInformation.sFileSize)
				if filesize is not None:
					return "%d MB" % (filesize / (1024*1024))
				
		except Exception, e:
			print "[EMCMI] getText exception:" + str(e)

	text = property(getText)
