# -*- coding: utf-8 -*-

from __init__ import _
from Components.ActionMap import ActionMap, HelpableActionMap
from Components.MenuList import MenuList
from Components.Button import Button
from Components.Label import Label
from Components.ProgressBar import ProgressBar
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
config.EMC.movieinfo.shownewversion = ConfigYesNo(default = False)

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

def getMovieInfo(id, cat, getAll=True):
	lang = config.EMC.movieinfo.language.value
	posterUrl = None

	# TODO: try a loop here,
	# to get the details if answer is to slow
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
				runtime = str(response["runtime"]).encode('utf-8')
				if response["runtime"] == 0:
					runtime = ""
			else:
				runtime = ""

			if config.EMC.movieinfo.ldreleasedate.value  == '1':
				releasedate = str(response["release_date"]).encode('utf-8')
			else:
				releasedate = ""

			if config.EMC.movieinfo.ldvote.value  == '1':
				vote = str(response["vote_average"]).encode('utf-8')
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
				genres = genres.encode('utf-8')
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
				countries = countries.encode('utf-8')
			else:
				countries = ""

			if getAll:
				return (_("Content:") + " " + blurb + "\n\n" + _("Runtime:") + " " + runtime + " " + _("Minutes") + "\n" + _("Genre:") + " " + genres + "\n" + _("Production Countries:") + " " + countries + "\n" + _("Release Date:") + " " + releasedate + "\n" + _("Vote:") + " " + vote + "\n")
			else:
				return blurb, runtime, genres, countries, releasedate, vote
		else:
			return None

	if cat == "tvshows":
		if response1 is not None:
			blurb = (str(response1["overview"])).encode('utf-8')

			if config.EMC.movieinfo.ldruntime.value == '1':
				runtime = str(response1["episode_run_time"]).encode('utf-8')
				if response1["episode_run_time"] == 0:
					runtime = _("unknown")
			else:
				runtime = ""

			if config.EMC.movieinfo.ldreleasedate.value  == '1':
				releasedate = str(response1["first_air_date"]).encode('utf-8')
			else:
				releasedate = ""

			if config.EMC.movieinfo.ldvote.value  == '1':
				vote = str(response1["vote_average"]).encode('utf-8')
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
				genres = genres.encode('utf-8')
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
				countries = countries.encode('utf-8')
			else:
				countries = ""

			if getAll:
				return (_("Content:") + " " + blurb + "\n\n" + _("Runtime:") + " " + runtime + " " + _("Minutes") + "\n" + _("Genre:") + " " + genres + "\n" + _("Production Countries:") + " " + countries + "\n" + _("Release Date:") + " " + releasedate + "\n" + _("Vote:") + " " + vote + "\n")
			else:
				return blurb, runtime, genres, countries, releasedate, vote
		else:
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
			else:
				self.session.open(MessageBox, _("An error occured! Internet connection broken?"), MessageBox.TYPE_ERROR, 10)

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
			if preview is not None:
				if config.EMC.movieinfo.coversave.value:
					try:
						self.session.open(MovieInfoPreview, preview, self.moviename, True)
					except Exception, e:
						print('[EMC] MovieInfo getPreviewPoster exception failure: ', str(e))
						self.session.open(MovieInfoPreview, preview, self.moviename)
				else:
					self.session.open(MovieInfoPreview, preview, self.moviename)
			else:
				self.session.open(MessageBox, _("An error occured! Internet connection broken?"), MessageBox.TYPE_ERROR, 10)

	def setup(self):
		self.session.open(MovieInfoSetup)


class MovieInfoPreview(Screen):
	skin = """
		<screen name="EMCMovieInfoPreview" position="center,center" size="1000,515" title="Movie Information Preview">
		<widget name="movie_name" position="20,5" size="960,42" zPosition="0" font="Regular;21" valign="center" halign="center" transparent="1" foregroundColor="unbab329" backgroundColor="black" />
		<widget name="previewtext" position="20,62" size="960,390" font="Regular;20" scrollbarMode="showOnDemand" />
		<widget name="previewlist" position="20,62" size="960,390" font="Regular;20" scrollbarMode="showOnDemand" />
		<widget name="previewcover" position="20,62" size="204,285" alphatest="blend" zPosition="2" />
		<widget name="contenttxt" position="240,62" size="740,285" font="Regular;20" />
		<widget name="runtime" position="20,362" size="200,25" font="Regular;20" foregroundColor="#000066FF" />
		<widget name="runtimetxt" position="240,362" size="230,25" font="Regular;20" />
		<widget name="genre" position="20,397" size="200,25" font="Regular;20" foregroundColor="#000066FF" />
		<widget name="genretxt" position="240,397" size="230,25" font="Regular;20" />
		<widget name="country" position="530,362" size="200,25" font="Regular;20" foregroundColor="#000066FF" />
		<widget name="countrytxt" position="750,362" size="230,25" font="Regular;20" />
		<widget name="release" position="530,402" size="200,25" font="Regular;20" foregroundColor="#000066FF" />
		<widget name="releasetxt" position="750,402" size="230,25" font="Regular;20" />
		<widget name="rating" position="20,432" size="200,25" font="Regular;20" foregroundColor="#000066FF" />
		<widget name="ratingtxt" position="240,432" size="230,25" font="Regular;20" />
		<widget name="starsbg" position="530,435" size="210,21" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/starsbar_empty_10.png" zPosition="3" alphatest="blend" />
		<widget name="stars" position="530,435" size="210,21" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/starsbar_filled_10.png" zPosition="4" transparent="1" />
		<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/line_blue.png" position="50,470" size="900,2" alphatest="on" />
		<widget name="setup" position="45,475" size="150,25" font="Regular;18" halign="center" valign="center" transparent="1" />
		<widget name="key_menu" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/key_menu_line.png" position="45,500" size="150,2" alphatest="on" />
		<widget name="save" position="320,475" size="150,25" font="Regular;18" halign="center" valign="center" transparent="1" />
		<widget name="key_red" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/key-red_line.png" position="320,500" size="150,2" alphatest="on" />
	</screen>"""

# page 0 = details
# page 1 = list
# config.EMC.movieinfo.shownewversion - switch between old style and new style
	def __init__(self, session, preview, moviename, previewCover=False, previewMode=False, spath=None, isDirectory=False):
		Screen.__init__(self, session)
		#self.session = session
		self.preview = preview
		self.moviename = moviename
		self.movielist = None
		self.previewCover = previewCover
		self.previewMode = previewMode
		self.spath = spath
		self.isDirectory = isDirectory
		self["previewcover"] = Pixmap()
		self.picload = ePicLoad()
		self.picload.PictureData.get().append(self.showPreviewCoverCB)
		self.previewTimer = eTimer()
		self.previewTimer.callback.append(self.showPreviewCover)
		self["previewlist"] = MenuList([])
		self.page = 0
		self.id = None
		self.cat = None
		self["contenttxt"] = ScrollLabel()
		self["runtime"] = Label("")
		self["runtimetxt"] = Label("")
		self["genre"] = Label("")
		self["genretxt"] = Label("")
		self["country"] = Label("")
		self["countrytxt"] = Label("")
		self["release"] = Label("")
		self["releasetxt"] = Label("")
		self["rating"] = Label("")
		self["ratingtxt"] = Label("")
		self["stars"] = ProgressBar()
		self["starsbg"] = Pixmap()
		self["stars"].hide()
		self["starsbg"].hide()
		self["setup"] = Label(_("Setup"))
		self["key_menu"] = Pixmap()
		self["save"] = Label(_("Save"))
		self["key_red"] = Pixmap()
		self.ratingstars = -1
		if self.preview is not None:
			self["previewlist"].hide()
			self["movie_name"] = Label(_("Movie Information Preview for:") + "   " + moviename)
			self["previewtext"] = ScrollLabel(_(str(preview)))
		else:
			self.movielist = getMovieList(moviename)
			if self.movielist is not None:
				self["previewlist"] = MenuList(self.movielist[0])
				self["previewtext"] = ScrollLabel()
				if self.movielist[1] > 1:
					self.page = 1
					self["movie_name"] = Label(_("Search results for:") + "   " + moviename)
				else:
					self.page = 0
					sel = self["previewlist"].l.getCurrentSelection()
					if sel is not None:
						preview = getMovieInfo(sel[1], sel[2])
						if preview is not None:
							self.id = sel[1]
							self.cat = sel[2]
							self["previewtext"].setText(_(str(preview)))
					self["previewlist"].hide()
					self["movie_name"] = Label(_("Movie Information Preview for:") + "   " + moviename)
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
			"EMCGreen":	self.save,
			"EMCMenu":	self.setup,
			#"EMCINFO":	self.info,
			#"EMCRed":	self.red,
		}, -1)

	def save(self):
		pass

	def ok(self):
		if self.page == 0:
			pass
		else:
			sel = self["previewlist"].l.getCurrentSelection()
			if sel is not None:
				preview = getMovieInfo(sel[1], sel[2])
				if preview is not None:
					self["previewlist"].hide()
					self.page = 0
					self["movie_name"].setText(_("Movie Information Preview for:") + "   " + self.moviename)
					if self.previewCover:
						self.previewTimer.start(300, True)
					self["previewtext"].setText(_(str(preview)))
					self.switchPage(sel[1], sel[2])
				else:
					self.session.open(MessageBox, _("An error occured! Internet connection broken?"), MessageBox.TYPE_ERROR, 10)

	def pageUp(self):
		if self.page == 0:
			if config.EMC.movieinfo.shownewversion.value:
				self["contenttxt"].pageUp()
			else:
				self["previewtext"].pageUp()
		if self.page == 1:
			self["previewlist"].up()

	def pageDown(self):
		if self.page == 0:
			if config.EMC.movieinfo.shownewversion.value:
				self["contenttxt"].pageDown()
			else:
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
		self.switchPage()

	def switchPage(self, id=None, cat=None):
		if self.page == 1:
			self["previewlist"].show()
			self["runtime"].hide()
			self["genre"].hide()
			self["country"].hide()
			self["release"].hide()
			self["rating"].hide()
			self["previewtext"].hide()
			self["contenttxt"].hide()
			self["runtimetxt"].hide()
			self["genretxt"].hide()
			self["countrytxt"].hide()
			self["releasetxt"].hide()
			self["ratingtxt"].hide()
			self["stars"].hide()
			self["starsbg"].hide()
			self["previewcover"].hide()
			self["save"].hide()
			self["key_red"].hide()
		if self.page == 0 and self.preview is not None:
			self["runtime"].hide()
			self["genre"].hide()
			self["country"].hide()
			self["release"].hide()
			self["rating"].hide()
			self["contenttxt"].hide()
			self["runtimetxt"].hide()
			self["genretxt"].hide()
			self["countrytxt"].hide()
			self["releasetxt"].hide()
			self["ratingtxt"].hide()
			self["save"].hide()
			self["key_red"].hide()
		else:
			if self.previewCover and not self.page == 1:
				if config.EMC.movieinfo.shownewversion.value:
					self["previewtext"].hide()
					self["runtime"].setText(_("Runtime:"))
					self["genre"].setText(_("Genre:"))
					self["country"].setText(_("Production Countries:"))
					self["release"].setText(_("Release Date:"))
					self["rating"].setText(_("Vote:"))
					if id is None:
						if self.id is not None:
							id = self.id
					if cat is None:
						if self.cat is not None:
							cat = self.cat
					if id is not None or cat is not None:
							content, runtime, genres, countries, release, vote = getMovieInfo(id, cat, False)
							self["runtime"].show()
							self["genre"].show()
							self["country"].show()
							self["release"].show()
							self["rating"].show()
							self["contenttxt"].show()
							self["runtimetxt"].show()
							self["genretxt"].show()
							self["countrytxt"].show()
							self["releasetxt"].show()
							self["ratingtxt"].show()
							self["contenttxt"].setText(content)
							if runtime != "":
								self["runtimetxt"].setText(runtime + " " + _("Minutes"))
							else:
								self["runtimetxt"].setText(runtime)
							self["genretxt"].setText(genres)
							self["countrytxt"].setText(countries)
							self["releasetxt"].setText(release)
							if vote:
								self["ratingtxt"].setText(vote.replace('\n','') + " / 10")
								self.ratingstars = int(10*round(float(vote.replace(',','.')),1))
								if self.ratingstars > 0:
									self["starsbg"].show()
									self["stars"].show()
									self["stars"].setValue(self.ratingstars)
								else:
									self["starsbg"].show()
									self["stars"].hide()
							else:
								self["ratingtxt"].setText(" 0 / 10")
								self["starsbg"].show()
								self["stars"].hide()
							self["save"].show()
							self["key_red"].show()
							self.previewTimer.start(300, True)
				else:
					self["previewtext"].show()
					self["runtime"].hide()
					self["genre"].hide()
					self["country"].hide()
					self["release"].hide()
					self["rating"].hide()
					self["contenttxt"].hide()
					self["runtimetxt"].hide()
					self["genretxt"].hide()
					self["countrytxt"].hide()
					self["releasetxt"].hide()
					self["ratingtxt"].hide()
					self["save"].hide()
					self["key_red"].hide()

	def exit(self):
		if self.movielist is not None:
			if self.page == 0 and self.movielist[1] > 1:
				self.page = 1
				self["movie_name"].setText(_("Search results for:") + "   " + self.moviename)
				self.switchPage()
			else:
				if fileExists("/tmp/previewCover.jpg"):
					os.remove("/tmp/previewCover.jpg")
				self.close()
		else:
			self.close()

	def setup(self):
		self.session.open(MovieInfoSetup)

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
		self.list.append(getConfigListEntry(_("Show new Skin Version"), config.EMC.movieinfo.shownewversion))

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
