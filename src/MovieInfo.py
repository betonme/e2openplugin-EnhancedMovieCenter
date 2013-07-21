# -*- coding: utf-8 -*-

from __init__ import _
from Components.ActionMap import ActionMap, HelpableActionMap
from Components.MenuList import MenuList
from Components.Button import Button
from Components.Label import Label
from Screens.Screen import Screen
from Components.Label import Label
from Screens.MessageBox import MessageBox
from Components.config import *
from Components.ConfigList import *

from MovieCenter import getMovieNameWithoutExt, getMovieNameWithoutPhrases

import json, os
from urllib2 import Request, urlopen

config.EMC.movieinfo = ConfigSubsection()
config.EMC.movieinfo.language = ConfigSelection(default='de', choices=[('de', _('German')), ('en', _('English'))])
config.EMC.movieinfo.ldruntime = ConfigSelection(default='1', choices=[('1', _('Yes')), ('0', _('No'))])
config.EMC.movieinfo.ldcountries = ConfigSelection(default='1', choices=[('1', _('Yes')), ('0', _('No'))])
config.EMC.movieinfo.ldreleasedate = ConfigSelection(default='1', choices=[('1', _('Yes')), ('0', _('No'))])
config.EMC.movieinfo.ldvote = ConfigSelection(default='1', choices=[('1', _('Yes')), ('0', _('No'))])
config.EMC.movieinfo.ldgenre = ConfigSelection(default='1', choices=[('1', _('Yes')), ('0', _('No'))])

class DownloadMovieInfo(Screen):
	skin = """
		<screen name="EMCDownloadMovieInfo" position="center,center" size="700,500" title="Movie Information Download (TMDb)">
		<widget name="movie_name" position="5,5" size="695,44" zPosition="0" font="Regular;21" valign="center" transparent="1" foregroundColor="#00bab329" backgroundColor="#000000"/>
		<widget name="movielist" position="10,54" size="670,379" scrollbarMode="showOnDemand"/>
		<widget name="resulttext" position="5,433" size="700,22" zPosition="0" font="Regular;21" valign="center" transparent="1" foregroundColor="#00bab329" backgroundColor="#000000"/>
		<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/key_menu.png" position="5,460" size="35,25" alphatest="on" />
		<widget name="setup" position="45,460" size="300,25" font="Regular;18" halign="left" valign="center" transparent="1" />
		<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/key_ok.png" position="280,460" size="35,25" alphatest="on" />
		<widget name="save" position="320,460" size="300,25" font="Regular;18" halign="left" valign="center" transparent="1" />
		<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/key_info.png" position="505,460" size="35,25" alphatest="on" />
		<widget name="movieinfo" position="545,460" size="300,25" font="Regular;18" halign="left" valign="center" transparent="1" />
	</screen>"""

#	def __init__(self, session, service, moviename):
	def __init__(self, session, spath, moviename):
		Screen.__init__(self, session)
		self.session = session
#		self.service = service
		self.spath = spath
		self["actions"] = HelpableActionMap(self, "EMCMovieInfo",
		{
			"EMCEXIT":		self.exit,
			"EMCOK":		self.ok,
			"EMCMenu":		self.setup,
			"EMCINFO":		self.info,
		}, -1)

		self.onLayoutFinish.append(self.layoutFinished)
#		(moviepath,ext) = os.path.splitext(service.getPath())  #do we need this line ?

		self.moviename = getMovieNameWithoutExt(moviename)
		moviename = getMovieNameWithoutPhrases(self.moviename) 

		self["movie_name"] = Label(_("Search results for:") + "   " + moviename)
		self["setup"] = Label(_("Setup"))
		self["save"] = Label(_("Save"))
		self["movieinfo"] = Label(_("Movie Info"))

		response=self.fetchdata("http://api.themoviedb.org/3/search/movie?api_key=8789cfd3fbab7dccf1269c3d7d867aff&query=" + moviename.replace(" ","+"))
		if response is not None:
			movies = response["results"]
			movielist = []
			for mov in movies:
				movielist.append((_(str(mov["title"])), mov["id"]))

			self["movielist"] = MenuList(movielist)
			self["resulttext"] = Label(str(len(movies)) + " " + _("movies found!"))
		else:
			self["movielist"] = MenuList([])
			self["resulttext"] = Label(_("An error occured! Internet connection broken?"))

	def layoutFinished(self):
		self.setTitle(_("Movie Information Download (TMDb)"))

	def exit(self):
		self.close()

	def ok(self):
		sel = self["movielist"].l.getCurrentSelection()
		if sel is not None:
			id = sel[1]
			info = self.getMovieInfo(id)
			if info is not None:
#				(moviepath,ext) = os.path.splitext(self.service.getPath())
				moviepath = os.path.splitext(self.spath)[0]

				file(moviepath + ".txt",'w').write(info)
				self.session.open(MessageBox, (_('Movie Information downloaded successfully!')), MessageBox.TYPE_INFO, 5)
				self.exit()

	def getMovieInfo(self, id):
		lang = config.EMC.movieinfo.language.value
		response = self.fetchdata("http://api.themoviedb.org/3/movie/" + str(id) + "?api_key=8789cfd3fbab7dccf1269c3d7d867aff&language=" + lang)

		if response is not None:
			blurb = (str(response["overview"])).encode('utf-8')

			if config.EMC.movieinfo.ldruntime.value == '1':
				runtime = (_("Runtime:") + " " + str(response["runtime"]).encode('utf-8') + " " + _("Minutes") + "\n")
				if response["runtime"] == 0:
					runtime = _("Runtime: unknown") + "\n"
			else:
				runtime = ""

			if config.EMC.movieinfo.ldreleasedate.value  == '1':
				releasedate = (_("Release Date:") + " " + str(response["release_date"]).encode('utf-8') + "\n")
			else:
				releasedate = ""

			if config.EMC.movieinfo.ldvote.value  == '1':
				vote = (_("Vote:") + " " + str(response["vote_average"]).encode('utf-8') + "\n")
			else:
				vote = ""

			if config.EMC.movieinfo.ldgenre.value == '1':
				genrelist = response["genres"]
				genres = ""
				for i in genrelist:
					if genres == "":
						genres = i["name"]
					else:
						genres = genres + ", " + i["name"]
				genres = (_("Genre:") + " " + genres.encode('utf-8') + "\n")
			else:
				genres = ""
			
			if config.EMC.movieinfo.ldcountries.value  == '1':
				countrylist = response["production_countries"]
				countries  = ""
				for i in countrylist:
					if countries == "":
						countries = i["name"]
					else:
						countries = countries + ", " + i["name"]
				countries = (_("Production Countries:") + " " + countries.encode('utf-8') + "\n")
			else:
				countries = ""

			return (_("Content:") + " " + blurb + "\n\n" + runtime + genres + countries + releasedate + vote)
		else:
			self.session.open(MessageBox, _("An error occured! Internet connection broken?"), MessageBox.TYPE_ERROR, 10)
			return None

	def info(self):
		sel = self["movielist"].l.getCurrentSelection()
		if sel is not None:
			preview = self.getMovieInfo(sel[1])
			self.session.open(MovieInfoPreview, preview, self.moviename)

	def fetchdata(self, url):
		try:
			headers = {"Accept": "application/json"}
			request = Request(url, headers=headers)
			jsonresponse = urlopen(request).read()
			response = json.loads(jsonresponse)
			return response
		except:
			return None

	def setup(self):
		self.session.open(MovieInfoSetup)


class MovieInfoPreview(Screen):
	skin = """
		<screen name="EMCMovieInfoPreview" position="center,center" size="800,450" title="Movie Information Preview">
		<widget name="movie_name" position="5,5" size="795,44" zPosition="0" font="Regular;21" valign="center" transparent="1" foregroundColor="#00bab329" backgroundColor="#000000"/>
		<widget name="previewtext" position="10,53" size="760,380" font="Regular;20" />
	</screen>"""

	def __init__(self, session, preview, moviename):
		Screen.__init__(self, session)
		#self.session = session
		self.preview = preview
		self["movie_name"] = Label(_("Movie Information Preview for:") + "   " + moviename)
		self["previewtext"]=Label(_(str(preview)))
		self.onLayoutFinish.append(self.layoutFinished)
		self["actions"] = HelpableActionMap(self, "EMCMovieInfo",
		{
			"EMCEXIT":		self.close,
			#"EMCOK":		self.red,
			#"EMCMenu":		self.setup,
			#"EMCINFO":		self.info,
			#"EMCGreen":	self.green,
			#"EMCRed":		self.red,
		}, -1)

	def layoutFinished(self):
		self.setTitle(_("Movie Information Preview"))

class MovieInfoSetup(Screen, ConfigListScreen):
	skin = """
		<screen name="EMCMovieInfoSetup" position="center,center" size="600,450" title="Movie Information Download Setup">
		<widget name="config" position="5,10" size="570,350" scrollbarMode="showOnDemand" />
		<widget name="key_red" position="0,390" size="140,40" valign="center" halign="center" zPosition="5" transparent="1" foregroundColor="#ffffff" font="Regular;18"/>
		<widget name="key_green" position="140,390" size="140,40" valign="center" halign="center" zPosition="5" transparent="1" foregroundColor="#ffffff" font="Regular;18"/>
		<ePixmap name="red" pixmap="skin_default/buttons/red.png" position="0,390" size="140,40" zPosition="4" transparent="1" alphatest="on"/>
		<ePixmap name="green" pixmap="skin_default/buttons/green.png" position="140,390" size="140,40" zPosition="4" transparent="1" alphatest="on"/>
	</screen>"""
	
	def __init__(self, session):
		Screen.__init__(self, session)
		#self.session = session
		self.list = []
		self.list.append(getConfigListEntry(_("Language:"), config.EMC.movieinfo.language))
		self.list.append(getConfigListEntry(_("Load Runtime:"), config.EMC.movieinfo.ldruntime))
		self.list.append(getConfigListEntry(_("Load Genre:"), config.EMC.movieinfo.ldgenre))
		self.list.append(getConfigListEntry(_("Load Production Countries:"), config.EMC.movieinfo.ldcountries))
		self.list.append(getConfigListEntry(_("Load Release Date:"), config.EMC.movieinfo.ldreleasedate))
		self.list.append(getConfigListEntry(_("Load Vote:"), config.EMC.movieinfo.ldvote))

		ConfigListScreen.__init__(self, self.list, session)
		self["actions"] = HelpableActionMap(self, "EMCMovieInfo",
		{
			"EMCEXIT":		self.exit,
			"EMCOK":		self.red,
			#"EMCMenu":		self.setup,
			#"EMCINFO":		self.info,
			"EMCGreen":		self.green,
			"EMCRed":		self.red,
		}, -1)
		self["key_red"] = Button(_("Cancel"))
		self["key_green"] = Button(_("OK"))
		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self.setTitle(_("Movie Information Download Setup"))

	def exit(self):
		self.close()

	def green(self):
		for x in self["config"].list:
			x[1].save()
		configfile.save()
		self.close(True)
		
	def red(self):
		for x in self["config"].list:
			x[1].cancel()
		self.close(False)
