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

			if info and service:
				if self.type == self.MOVIE_SHORT_DESCRIPTION:
					event = self.source.event
					shortdesc = event and info.getInfoString(service, iServiceInformation.sDescription)
					if not shortdesc:
						shortdesc = event.getShortDescription()
					if not shortdesc:
						self.eit = EitList(service)
						shortdesc = self.eit and self.eit.getEitDescription()
					if not shortdesc:
						self.meta = MetaList(service, borg=True)
						shortdesc = self.meta and self.meta.getMetaDescription()
					return shortdesc or ""
							
				elif self.type == self.MOVIE_META_DESCRIPTION:
					extdesc = info.getInfoString(service, iServiceInformation.sDescription)
					if not extdesc:
						extdesc = event and event.getExtendedDescription()
					if not extdesc:
						#print "EMC EIT extdesc Meta"
						self.meta = MetaList(service, borg=True)
						extdesc = self.meta and self.meta.getMetaDescription()
					if not extdesc:
						#print "EMC EIT extdesc Eit"
						self.eit = EitList(service)
						extdesc = self.eit and self.eit.getEitDescription()
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
