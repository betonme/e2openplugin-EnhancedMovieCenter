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

from Components.Converter.Converter import Converter
from Components.Converter.MovieInfo import MovieInfo
from Components.Element import cached, ElementError

class EMCMovieInfo(MovieInfo):
	def __init__(self, type):
		MovieInfo.__init__(self, type)