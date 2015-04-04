# -*- coding: utf-8 -*-

from __init__ import _
from Components.ActionMap import ActionMap, HelpableActionMap
from Components.MenuList import MenuList
from Components.Button import Button
from Components.Label import Label
from Components.ScrollLabel import ScrollLabel
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.config import *
from Components.ConfigList import *

from MovieCenter import getMovieNameWithoutExt, getMovieNameWithoutPhrases

import json, os
from urllib2 import Request, urlopen
from twisted.web.client import downloadPage

# Cover
from Tools.Directories import fileExists
from Components.AVSwitch import AVSwitch
from Components.Pixmap import Pixmap
from enigma import ePicLoad, eTimer
import shutil

config.EMC.movieinfo = ConfigSubsection()
config.EMC.movieinfo.language = ConfigSelection(default='de', choices=[('de', _('German')), ('en', _('English'))])
config.EMC.movieinfo.ldruntime = ConfigSelection(default='1', choices=[('1', _('Yes')), ('0', _('No'))])
config.EMC.movieinfo.ldcountries = ConfigSelection(default='1', choices=[('1', _('Yes')), ('0', _('No'))])
config.EMC.movieinfo.ldreleasedate = ConfigSelection(default='1', choices=[('1', _('Yes')), ('0', _('No'))])
config.EMC.movieinfo.ldvote = ConfigSelection(default='1', choices=[('1', _('Yes')), ('0', _('No'))])
config.EMC.movieinfo.ldgenre = ConfigSelection(default='1', choices=[('1', _('Yes')), ('0', _('No'))])
config.EMC.movieinfo.coversave = ConfigYesNo(default = False)
config.EMC.movieinfo.coversize = ConfigSelection(default="w185", choices = ["w92", "w185", "w500", "original"])

def getMovieList(moviename):
	response = fetchdata("http://api.themoviedb.org/3/search/movie?api_key=8789cfd3fbab7dccf1269c3d7d867aff&query=" + moviename.replace(" ","+").replace("&","%26"))
	response1 = fetchdata("http://api.themoviedb.org/3/search/tv?api_key=8789cfd3fbab7dccf1269c3d7d867aff&query=" + moviename.replace(" ","+").replace("&","%26"))
	movielist = []
	idx = 0
	if response or response1 is not None:
		movies = response["results"]
		movielist = []
		for mov in movies:
			movielist.append((_(str(mov["title"])), mov["id"], "movie"))

		tvshows = response1["results"]
		for shows in tvshows:
			movielist.append((_(str(shows["name"])), shows["id"], "tvshows"))

		idx = len(movies) + len(tvshows)

        return movielist, idx

def fetchdata(url):
	try:
		headers = {"Accept": "application/json"}
		request = Request(url, headers=headers)
		jsonresponse = urlopen(request).read()
		response = json.loads(jsonresponse)
		return response
	except:
		return None

def getMovieInfo(id, cat):
	lang = config.EMC.movieinfo.language.value
	posterUrl = None
	response = fetchdata("http://api.themoviedb.org/3/movie/" + str(id) + "?api_key=8789cfd3fbab7dccf1269c3d7d867aff&language=" + lang)
	response1 = fetchdata("http://api.themoviedb.org/3/tv/" + str(id) + "?api_key=8789cfd3fbab7dccf1269c3d7d867aff&language=" + lang)

	if config.EMC.movieinfo.coversave.value:
		if cat == "movie":
			if response is not None:
				posterUrl = (str(response["poster_path"])).encode('utf-8')
		if cat == "tvshows":
			if response1 is not None:
				posterUrl = (str(response1["poster_path"])).encode('utf-8')
		if posterUrl is not None:
			getTempCover(posterUrl)

	if cat == "movie":
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
			session.open(MessageBox, _("An error occured! Internet connection broken?"), MessageBox.TYPE_ERROR, 10)
			return None

	if cat == "tvshows":
		if response1 is not None:
			blurb = (str(response1["overview"])).encode('utf-8')

			if config.EMC.movieinfo.ldruntime.value == '1':
				runtime = (_("Runtime:") + " " + str(response1["episode_run_time"]).encode('utf-8') + " " + _("Minutes") + "\n")
				if response1["episode_run_time"] == 0:
					runtime = _("Runtime: unknown") + "\n"
			else:
				runtime = ""

			if config.EMC.movieinfo.ldreleasedate.value  == '1':
				releasedate = (_("Release Date:") + " " + str(response1["first_air_date"]).encode('utf-8') + "\n")
			else:
				releasedate = ""

			if config.EMC.movieinfo.ldvote.value  == '1':
				vote = (_("Vote:") + " " + str(response1["vote_average"]).encode('utf-8') + "\n")
			else:
				vote = ""

			if config.EMC.movieinfo.ldgenre.value == '1':
				genrelist = response1["genres"]
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
				countrylist = response1["origin_country"]
				countries  = ""
				for i in countrylist:
					if countries == "":
						countries = i
					else:
						countries = countries + ", " + i
				countries = (_("Production Countries:") + " " + countries.encode('utf-8') + "\n")
			else:
				countries = ""

			return (_("Content:") + " " + blurb + "\n\n" + runtime + genres + countries + releasedate + vote)
		else:
			session.open(MessageBox, _("An error occured! Internet connection broken?"), MessageBox.TYPE_ERROR, 10)
			return None

def getTempCover(posterUrl):
	if posterUrl is not None and config.EMC.movieinfo.coversave.value:
		try:
			coverpath = "/tmp/previewCover.jpg"
			url = "http://image.tmdb.org/t/p/%s%s" % (config.EMC.movieinfo.coversize.value, posterUrl)
			downloadPage(url, coverpath).addErrback(dataError)
		except Exception, e:
			print('[EMC] MovieInfo getTempCover exception failure: ', str(e))

def dataError(error):
	print "[EMC] MovieInfo ERROR:", error


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

		movielist = getMovieList(moviename)
		if movielist is not None:
			self["movielist"] = MenuList(movielist[0])
			self["resulttext"] = Label(str(movielist[1]) + " " + _("movies found!"))
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
			cat = sel[2]
			info = getMovieInfo(id, cat)
			if info is not None:
				moviepath = os.path.splitext(self.spath)[0]
				file(moviepath + ".txt",'w').write(info)
				self.session.open(MessageBox, (_('Movie Information downloaded successfully!')), MessageBox.TYPE_INFO, 5)

				if config.EMC.movieinfo.coversave.value:
					self.getPoster()
				self.exit()

	def getPoster(self):
		moviepath = os.path.splitext(self.spath)[0]
		if fileExists(moviepath + ".jpg"):
			self.session.openWithCallback(self.posterCallback, MessageBox, _("Cover %s exists!\n\nDo you want to replace the existing cover?") % (moviepath + ".jpg"), MessageBox.TYPE_YESNO)
		else:
			self.savePoster()

	def posterCallback(self, result):
		if result:
			moviepath = os.path.splitext(self.spath)[0]
			if fileExists(moviepath + ".jpg"):
				os.remove(moviepath + ".jpg")
			self.savePoster()

	def savePoster(self):
		try:
			moviepath = os.path.splitext(self.spath)[0]
			coverpath = moviepath + ".jpg"
			if fileExists("/tmp/previewCover.jpg"):
				shutil.copy2("/tmp/previewCover.jpg", coverpath)
		except Exception, e:
			print('[EMC] MovieInfo savePoster exception failure: ', str(e))

	def info(self):
		sel = self["movielist"].l.getCurrentSelection()
		if sel is not None:
			preview = getMovieInfo(sel[1], sel[2])
			if config.EMC.movieinfo.coversave.value:
				try:
					self.session.open(MovieInfoPreview, preview, self.moviename, True)
				except Exception, e:
					print('[EMC] MovieInfo getPreviewPoster exception failure: ', str(e))
					self.session.open(MovieInfoPreview, preview, self.moviename)
			else:
				self.session.open(MovieInfoPreview, preview, self.moviename)

	def setup(self):
		self.session.open(MovieInfoSetup)


class MovieInfoPreview(Screen):
	skin = """
		<screen name="EMCMovieInfoPreview" position="center,center" size="800,550" title="Movie Information Preview">
		<widget name="movie_name" position="20,5" size="650,100" zPosition="0" font="Regular;21" valign="center" transparent="1" foregroundColor="unbab329" backgroundColor="black" />
		<widget name="previewtext" position="20,152" size="760,380" font="Regular;20" scrollbarMode="showOnDemand" />
		<widget name="previewlist" position="20,152" size="760,380" font="Regular;20" scrollbarMode="showOnDemand" />
		<widget name="previewcover" position="684,6" size="100,140" alphatest="blend" zPosition="2" />
	</screen>"""

	def __init__(self, session, preview, moviename, previewCover=False, previewMode=False):
		Screen.__init__(self, session)
		#self.session = session
		self.preview = preview
		self.moviename = moviename
		self.previewCover = previewCover
		self.previewMode = previewMode
		self["previewcover"] = Pixmap()
		self.picload = ePicLoad()
		self.picload.PictureData.get().append(self.showPreviewCoverCB)
		self["previewlist"] = MenuList([])
		self.page = 0
		if self.preview is not None:
			self["previewlist"].hide()
			self["movie_name"] = Label(_("Movie Information Preview for:") + "   " + moviename)
			self["previewtext"] = ScrollLabel(_(str(preview)))
		else:
			movielist = getMovieList(moviename)
			if movielist is not None:
				self["previewlist"] = MenuList(movielist[0])
				self["previewtext"] = ScrollLabel()
				if movielist[1] > 1:
					self["movie_name"] = Label(_("Search results for:") + "   " + moviename)
					self.page = 1
				else:
					sel = self["previewlist"].l.getCurrentSelection()
					if sel is not None:
						preview = getMovieInfo(sel[1], sel[2])
					self["previewlist"].hide()
					self["movie_name"] = Label(_("Movie Information Preview for:") + "   " + moviename)
					self["previewtext"].setText(_(str(preview)))
					self.page = 0
			else:
				self["movie_name"] = Label(_("Search results for:") + "   " + moviename)
				self["previewtext"] = ScrollLabel(_("Nothing was found !"))
		self.onLayoutFinish.append(self.layoutFinished)
		self["actions"] = HelpableActionMap(self, "EMCMovieInfo",
		{
			"EMCEXIT":	self.exit,
			"EMCUp":	self.pageUp,
			"EMCDown":	self.pageDown,
			"EMCOK":	self.ok,
			#"EMCMenu":	self.setup,
			#"EMCINFO":	self.info,
			#"EMCGreen":	self.green,
			#"EMCRed":	self.red,
		}, -1)
		self.previewTimer = eTimer()
		self.previewTimer.callback.append(self.showPreviewCover)

	def ok(self):
		if self.page == 0:
			pass
		else:
			sel = self["previewlist"].l.getCurrentSelection()
			if sel is not None:
				preview = getMovieInfo(sel[1], sel[2])
				self["previewlist"].hide()
				self["movie_name"].setText(_("Movie Information Preview for:") + "   " + self.moviename)
				self["previewtext"].setText(_(str(preview)))
				self["previewtext"].show()
				if self.previewCover:
					self.previewTimer.start(300, True)
				self.page = 0

	def pageUp(self):
		if self.page == 0:
			self["previewtext"].pageUp()
		if self.page == 1:
			self["previewlist"].up()

	def pageDown(self):
		if self.page == 0:
			self["previewtext"].pageDown()
		if self.page == 1:
			self["previewlist"].down()

	def showPreviewCoverCB(self, picInfo=None):
		ptr = self.picload.getData()
		if ptr != None:
			self["previewcover"].instance.setPixmap(ptr.__deref__())
			self["previewcover"].show()
		else:
			self["previewcover"].hide()

	def showPreviewCover(self):
		if fileExists("/tmp/previewCover.jpg"):
			previewpath = "/tmp/previewCover.jpg"
		else:
			previewpath = "/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/no_poster.png"
		sc = AVSwitch().getFramebufferScale()
		self.picload.setPara((self["previewcover"].instance.size().width(), self["previewcover"].instance.size().height(), sc[0], sc[1], False, 1, "#00000000"))
		self.picload.startDecode(previewpath)

	def layoutFinished(self):
		self.setTitle(_("Movie Information Preview"))
		if self.page == 1:
			self["previewtext"].hide()
		if self.previewCover and not self.page == 1:
			self.previewTimer.start(300, True)

	def exit(self):
		if fileExists("/tmp/previewCover.jpg"):
			os.remove("/tmp/previewCover.jpg")
		self.close()

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
		self.list.append(getConfigListEntry(_("Save Cover"), config.EMC.movieinfo.coversave))
		self.list.append(getConfigListEntry(_("Coversize"), config.EMC.movieinfo.coversize))

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
