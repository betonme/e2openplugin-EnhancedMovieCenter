#!/usr/bin/python
# encoding: utf-8
#
# Copyright (C) 2011 by Coolman & Swiss-MAD
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

from enigma import eServiceReference
from EMCTasker import emcDebugOut
from Screens.MessageBox import MessageBox

global vlcSrv, vlcDir, vlcFil

# VLC types
vlcSrv  = "VLCS"
vlcDir  = "VLCD"
vlcFil  = "VLCF"


class VlcFileListWrapper:
	def __init__(self):
		pass
	def getNextFile(self):
		return None, None
	def getPrevFile(self):
		return None, None


class VlcPluginInterfaceSel():
	def __init__(self):
		pass

	def browsingVLC(self):
		return self.currentPath.find("VLC servers") > -1

	def vlcMovieSelected(self, entry):
		# TODO full integration of the VLC Player
		try:
			if entry:
				self.hide()
				#TODO Open EMC after playback ends if configured
				try:	# v2.5
					self["list"].vlcServer.play(self, entry[4], entry[3], VlcFileListWrapper())
				except:	# v2.6
					self["list"].vlcServer.play(self.session, entry[4], entry[3], VlcFileListWrapper())
				self.close()
		except Exception, e:
			emcDebugOut("[EMC_VLC] vlcMovieSelected exception:\n" + str(e))


class VlcPluginInterfaceList():
	def __init__(self):
		self.vlcServers = None
		self.vlcServer = None

	def createVlcServerList(self, loadPath):
		try:
			vlcserverlist = []
			from Plugins.Extensions.VlcPlayer.VlcServerConfig import vlcServerConfig
			# Settings change requires running this
			#IDEA: Can the change be detected to avoid unnecessary reloads
			self.vlcServers = vlcServerConfig.getServerlist()
			if self.vlcServers:
				for srv in self.vlcServers:
					srvName = srv.getName()
					emcDebugOut("[EMC_VLC] srvName = " + str(srvName))
					vlcserverlist.append( (os.path.join(loadPath, srvName), srvName, vlcSrv) )
			return vlcserverlist
		except:
			pass

	def createVlcFileList(self, loadPath):
		vlcdirlist = []
		vlcfilelist = []
		# Extract server/dir/name/
		#TODO Find a more stable variant
		vlcPath = loadPath[loadPath.find("VLC servers/")+12:]
		serverName = vlcPath.split("/")[0]
		vlcPath = vlcPath[len(serverName)+1:]
		emcDebugOut("[EMC_VLC] path on %s = %s" %(serverName, vlcPath))
		server = None
		self.vlcServer = None
		if self.vlcServers:
			for srv in self.vlcServers:
				if srv.getName() == serverName: 
					emcDebugOut("[EMC_VLC] srv = " + str(srv))
					server = srv	# find the server
		if server is not None:
			try:
				self.vlcServer = server
				baseDir = server.getBasedir()
				emcDebugOut("[EMC_VLC] baseDir = " + baseDir)
				#vlcPath = vlcPath[len(serverName):]
				emcDebugOut("[EMC_VLC] vlcPath = " + vlcPath)
				# Build path
				path = os.path.join(baseDir, vlcPath)
				# Load path
				emcDebugOut("[EMC_VLC] path = " + path)
				try: 
					(vlcFiles, vlcDirs) = server.getFilesAndDirs(path, None)
				except URLError:
					self.session.open(MessageBox, _("VLC Server not reachable"), MessageBox.TYPE_ERROR)
				emcDebugOut("[EMC_VLC] got dirs and files...")
				if vlcDirs:
					for name, path in vlcDirs:
						emcDebugOut("[EMC_VLC] dir = " + str(name))
						vlcdirlist.append( (os.path.join(loadPath, name), name, vlcDir) )
						#vlcdirlist.append( (os.path.join(loadPath, path), name, vlcDir) )
						#vlcdirlist.append( (path, name, vlcDir) )
				if vlcFiles:
					for name, path in vlcFiles:
						from Plugins.Extensions.VlcPlayer.VlcFileList import MEDIA_EXTENSIONS
						ext = os.path.splitext(name)[1].lower()[1:]
						#TODO all media extensions should be indicated by the vlc player
						if MEDIA_EXTENSIONS.has_key(ext):
							# Maybe later return real file extension
							emcDebugOut("[EMC_VLC] media file = " + str(name))
							vlcfilelist.append( (path, name, vlcFil) )
						else:
							emcDebugOut("[EMC_VLC] file = " + str(name))
			except Exception, e:
				emcDebugOut("[EMC_VLC] reloadVlcFilelist exception:\n" + str(e))
		
		return vlcdirlist, vlcfilelist

