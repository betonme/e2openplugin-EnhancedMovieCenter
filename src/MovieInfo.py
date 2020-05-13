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
from configlistext import ConfigListScreenExt

from MovieCenter import getMovieNameWithoutExt, getMovieNameWithoutPhrases, getNoPosterPath

import json, os, re
from urllib import quote
from urllib2 import Request, urlopen
from twisted.web.client import downloadPage

# Cover
from Tools.Directories import fileExists
from Components.AVSwitch import AVSwitch
from Components.Pixmap import Pixmap
from enigma import ePicLoad, eTimer, getDesktop
import shutil

config.EMC.movieinfo = ConfigSubsection()
config.EMC.movieinfo.language = ConfigSelection(default='en', choices=[('en', _('English')), ('de', _('German')), ('it', _('Italian')), ('es', _('Spanish')), ('fr', _('French')), ('pt', _('Portuguese'))])
config.EMC.movieinfo.ldruntime = ConfigSelection(default='1', choices=[('1', _('Yes')), ('0', _('No'))])
config.EMC.movieinfo.ldcountries = ConfigSelection(default='1', choices=[('1', _('Yes')), ('0', _('No'))])
config.EMC.movieinfo.ldreleasedate = ConfigSelection(default='1', choices=[('1', _('Yes')), ('0', _('No'))])
config.EMC.movieinfo.ldvote = ConfigSelection(default='1', choices=[('1', _('Yes')), ('0', _('No'))])
config.EMC.movieinfo.ldgenre = ConfigSelection(default='1', choices=[('1', _('Yes')), ('0', _('No'))])
config.EMC.movieinfo.coversave = ConfigYesNo(default = False)
config.EMC.movieinfo.coversize = ConfigSelection(default="w185", choices = ["w92", "w185", "w500", "original"])
config.EMC.movieinfo.cover_delay = ConfigSelectionNumber(50, 60000, 50, default= 500)

sz_w = getDesktop(0).size().width()

def getMovieList(moviename):
	response = fetchdata("http://api.themoviedb.org/3/search/movie?api_key=8789cfd3fbab7dccf1269c3d7d867aff&query=" + quote(moviename))
	response1 = fetchdata("http://api.themoviedb.org/3/search/tv?api_key=8789cfd3fbab7dccf1269c3d7d867aff&query=" + quote(moviename))
	movielist = []
	idx = 0
	if response or response1 is not None:
		movies = response["results"]
		movielist = []
		for mov in movies:
			movielist.append((str(mov["title"]) + " - " + _("Movies"), mov["id"], "movie"))

		tvshows = response1["results"]
		for shows in tvshows:
			movielist.append((str(shows["name"]) + " - " + _("TV Shows"), shows["id"], "tvshows"))

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

def getMovieInfo(id, cat, getAll=True, onlyPoster=False):
	lang = config.EMC.movieinfo.language.value
	posterUrl = None

	# TODO: try a loop here,
	# to get the details if answer is to slow
	response = fetchdata("http://api.themoviedb.org/3/movie/" + str(id) + "?api_key=8789cfd3fbab7dccf1269c3d7d867aff&language=" + lang)
	response1 = fetchdata("http://api.themoviedb.org/3/tv/" + str(id) + "?api_key=8789cfd3fbab7dccf1269c3d7d867aff&language=" + lang)

	if cat == "movie":
		if response is not None:
			posterUrl = (str(response["poster_path"])).encode('utf-8')
	if cat == "tvshows":
		if response1 is not None:
			posterUrl = (str(response1["poster_path"])).encode('utf-8')
	if posterUrl is not None:
		getTempCover(posterUrl)
	if onlyPoster:
		return

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

			txt = (_("Content:") + " " + blurb + "\n\n" + _("Runtime:") + " " + runtime + " " + _("Minutes") + "\n" + _("Genre:") + " " + genres + "\n" + _("Production Countries:") + " " + countries + "\n" + _("Release Date:") + " " + releasedate + "\n" + _("Vote:") + " " + vote + "\n")

			if getAll:
				return txt
			else:
				getTempTxt(txt)
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

			txt = (_("Content:") + " " + blurb + "\n\n" + _("Runtime:") + " " + runtime + " " + _("Minutes") + "\n" + _("Genre:") + " " + genres + "\n" + _("Production Countries:") + " " + countries + "\n" + _("Release Date:") + " " + releasedate + "\n" + _("Vote:") + " " + vote + "\n")

			if getAll:
				return txt
			else:
				getTempTxt(txt)
				return blurb, runtime, genres, countries, releasedate, vote
		else:
			return None

def getTempTxt(txt):
	if txt is not None:
		try:
			txtpath = "/tmp/previewTxt.txt"
			file(txtpath,'w').write(txt)
		except Exception, e:
			print('[EMC] MovieInfo getTempTxt exception failure: ', str(e))

def getTempCover(posterUrl):
	if posterUrl is not None:
		try:
			if fileExists("/tmp/previewCover.jpg"):
				os.remove("/tmp/previewCover.jpg")
			coverpath = "/tmp/previewCover.jpg"
			url = "http://image.tmdb.org/t/p/%s%s" % (config.EMC.movieinfo.coversize.value, posterUrl)
			downloadPage(url, coverpath).addErrback(dataError)
		except Exception, e:
			print('[EMC] MovieInfo getTempCover exception failure: ', str(e))

def dataError(error):
	print "[EMC] MovieInfo ERROR:", error

class MovieInfoTMDb(Screen):
	if sz_w == 1920:
		skin = """
		<screen name="MovieInfoTMDb" position="center,170" size="1200,820" title="Movie Information TMDb">
		<widget name="movie_name" position="10,5" size="1180,80" font="Regular;35" halign="center" valign="center" foregroundColor="yellow"/>
		<eLabel backgroundColor="#818181" position="10,90" size="1180,1" />
		<widget name="previewlist" enableWrapAround="1" position="340,100" size="850,630" itemHeight="45" scrollbarMode="showOnDemand" />
		<widget name="previewcover" position="20,100" size="300,451" alphatest="blend"/>
		<widget name="contenttxt" position="340,100" size="850,460" font="Regular;30" />
		<widget name="runtime" position="20,590" size="160,35" font="Regular;28" foregroundColor="#000066FF" />
		<widget name="runtimetxt" position="190,590" size="330,35" font="Regular;28" />
		<widget name="genre" position="20,640" size="160,35" font="Regular;28" foregroundColor="#000066FF" />
		<widget name="genretxt" position="190,640" size="330,35" font="Regular;28" />
		<widget name="country" position="550,590" size="290,35" font="Regular;28" foregroundColor="#000066FF" />
		<widget name="countrytxt" position="850,590" size="340,35" font="Regular;28" />
		<widget name="release" position="550,640" size="290,35" font="Regular;28" foregroundColor="#000066FF" />
		<widget name="releasetxt" position="850,640" size="340,35" font="Regular;28" />
		<widget name="rating" position="20,690" size="160,35" font="Regular;28" foregroundColor="#000066FF" />
		<widget name="ratingtxt" position="190,690" size="330,35" font="Regular;28" />
		<widget name="starsbg" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img_fhd/starsbar_empty.png" position="550,690" size="300,30" alphatest="blend"/>
		<widget name="stars" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img_fhd/starsbar_filled.png" position="550,690" size="300,30" transparent="1" zPosition="1"/>
		<eLabel backgroundColor="#818181" position="10,740" size="1180,1" />
		<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img_fhd/menu.png" position="10,770" size="80,40" alphatest="blend"/>
		<widget name="setup" position="110,772" size="380,40" font="Regular;30" valign="center" />
		<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img_fhd/ok.png" position="510,770" size="80,40" zPosition="1" alphatest="blend"/>
		<widget name="key_green" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img_fhd/key_green.png" position="510,770" size="80,40" zPosition="2" alphatest="blend"/>
		<widget name="save" position="620,772" size="290,40" font="Regular;30" valign="center" />
		</screen>"""
	else:
		skin = """
		<screen name="MovieInfoTMDb" position="center,80" size="1200,610" title="Movie Information TMDb">
		<widget name="movie_name" position="10,5" size="1180,55" font="Regular;24" valign="center" halign="center" foregroundColor="yellow"/>
		<eLabel backgroundColor="#818181" position="10,70" size="1180,1" />
		<widget name="previewcover" position="20,80" size="220,330" alphatest="blend"/>
		<widget enableWrapAround="1" name="previewlist" position="270,80" size="920,330" itemHeight="30" scrollbarMode="showOnDemand" />
		<widget name="contenttxt" position="270,80" size="920,330" font="Regular;21" />
		<widget name="runtime" position="20,450" size="120,25" font="Regular;20" foregroundColor="#000066FF" />
		<widget name="runtimetxt" position="160,450" size="360,25" font="Regular;20" />
		<widget name="genre" position="20,480" size="120,25" font="Regular;20" foregroundColor="#000066FF" />
		<widget name="genretxt" position="160,480" size="360,25" font="Regular;20" />
		<widget name="country" position="600,450" size="200,25" font="Regular;20" foregroundColor="#000066FF" />
		<widget name="countrytxt" position="820,450" size="360,25" font="Regular;20" />
		<widget name="release" position="600,480" size="200,25" font="Regular;20" foregroundColor="#000066FF" />
		<widget name="releasetxt" position="820,480" size="360,25" font="Regular;20" />
		<widget name="rating" position="20,510" size="120,25" font="Regular;20" foregroundColor="#000066FF" />
		<widget name="ratingtxt" position="160,510" size="360,25" font="Regular;20" />
		<widget name="starsbg" position="595,510" size="250,25" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/starsbar_empty.png" alphatest="blend"/>
		<widget name="stars" position="595,510" size="250,25" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/starsbar_filled.png" transparent="1" zPosition="1"/>
		<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/menu.png" position="20,570" size="60,30" alphatest="blend"/>
		<widget name="setup" position="100,571" size="200,30" font="Regular;22" valign="center" />
		<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/ok.png" position="320,570" size="60,30" zPosition="1" alphatest="blend"/>
		<widget name="key_green" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/key_green.png" position="320,570" size="60,30" zPosition="2" alphatest="blend"/>
		<widget name="save" position="400,571" size="200,30" font="Regular;22" valign="center" />
		</screen>"""

# page 0 = details
# page 1 = list
	def __init__(self, session, moviename, spath=None):
		Screen.__init__(self, session)
		#self.session = session
		self.moviename = getMovieNameWithoutExt(moviename)
		moviename = getMovieNameWithoutPhrases(self.moviename)
		self.movielist = None
		self.spath = spath
		self["previewcover"] = Pixmap()
		self.picload = ePicLoad()
		try:
			self.picload_conn = self.picload.PictureData.connect(self.showPreviewCoverCB)
		except:
			self.picload.PictureData.get().append(self.showPreviewCoverCB)
		self.previewTimer = eTimer()
		try:
			self.previewTimer_conn = self.previewTimer.timeout.connect(self.showPreviewCover)
		except:
			self.previewTimer.callback.append(self.showPreviewCover)
		self.selectionTimer = eTimer()
		try:
			self.selectionTimer_conn = self.selectionTimer.timeout.connect(self.updateSelection)
		except:
			self.selectionTimer.callback.append(self.updateSelection)
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
		self["key_green"] = Pixmap()
		self.ratingstars = -1
		self.movielist = getMovieList(moviename)
		if self.movielist is not None:
			self["previewlist"] = MenuList(self.movielist[0])
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
				self["previewlist"].hide()
				self["movie_name"] = Label(_("Movie Information Preview for:") + "   " + moviename)
		else:
			self["movie_name"] = Label(_("Search results for:") + "   " + moviename)
			self["contenttxt"].setText(_("Nothing was found !"))

		self.file_format = "(\.ts|\.avi|\.mkv|\.divx|\.f4v|\.flv|\.img|\.iso|\.m2ts|\.m4v|\.mov|\.mp4|\.mpeg|\.mpg|\.mts|\.vob|\.asf|\.wmv|.\stream|.\webm)"

		# for file-operations
		self.txtsaved = False
		self.jpgsaved = False
		self.mpath = None

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
		self["previewlist"].onSelectionChanged.append(self.selectionChanged)

	def selectionChanged(self):
		if self.page == 1:
			self.selectionTimer.start(int(config.EMC.movieinfo.cover_delay.value), True)

	def updateSelection(self):
		if self.page == 1:
			sel = self["previewlist"].l.getCurrentSelection()
			if sel is not None:
				getMovieInfo(sel[1], sel[2], False, True)
				self.previewTimer.start(int(config.EMC.movieinfo.cover_delay.value), True)

	def layoutFinished(self):
		self.setTitle(_("Movie Information TMDb"))
		self.switchPage()

	def switchPage(self, id=None, cat=None):
		if self.page == 1:
			self["previewlist"].show()
			self.selectionChanged()
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
			self["stars"].hide()
			self["starsbg"].hide()
			self["save"].hide()
			self["key_green"].hide()
		else:
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
				self["key_green"].show()
				self.previewTimer.start(int(config.EMC.movieinfo.cover_delay.value), True)

	def showMsg(self, askNo=False):
		if self.txtsaved and self.jpgsaved:
			msg = (_('Movie Information and Cover downloaded successfully!'))
		elif self.txtsaved and not self.jpgsaved:
			if config.EMC.movieinfo.coversave.value:
				if askNo:
					msg = (_('Movie Information downloaded successfully!'))
				else:
					msg = (_('Movie Information downloaded successfully!\n\nCan not write Movie Cover File\n\n%s') % (self.mpath + ".jpg"))
			else:
				msg = (_('Movie Information downloaded successfully!'))
		elif self.jpgsaved and not self.txtsaved:
			msg = (_('Movie Cover downloaded successfully!\n\nCan not write Movie Information File\n\n%s') % (self.mpath + ".txt"))
		elif not self.jpgsaved and not self.txtsaved:
			msg = (_('Can not write Movie Information and Cover File\n\n%(info)s\n%(file)s') % {'info':self.mpath + ".txt", 'file':self.mpath + ".jpg"})
		elif not self.txtsaved and not config.EMC.movieinfo.coversave.value:
			msg = (_('Can not write Movie Information File\n\n%s') % (self.mpath + ".txt"))

		self.session.open(MessageBox, msg, MessageBox.TYPE_INFO, 5)

	def save(self):
		if self.page == 0 and self.spath is not None:
			self.txtsaved = False
			self.mpath = re.sub(self.file_format + "$", '.jpg', self.spath, flags=re.IGNORECASE)
			try:
				txtpath = self.mpath + ".txt"
				if fileExists("/tmp/previewTxt.txt"):
					shutil.copy2("/tmp/previewTxt.txt", txtpath)
					self.txtsaved = True
			except Exception, e:
				print('[EMC] MovieInfo saveTxt exception failure: ', str(e))

			if config.EMC.movieinfo.coversave.value:
				self.getPoster()
			else:
				self.showMsg()

	def getPoster(self):
		if fileExists(self.mpath + ".jpg"):
			self.session.openWithCallback(self.posterCallback, MessageBox, _("Cover %s exists!\n\nDo you want to replace the existing cover?") % (self.mpath + ".jpg"), MessageBox.TYPE_YESNO)
		else:
			self.savePoster()

	def posterCallback(self, result):
		if result:
			try:
				if fileExists(self.mpath + ".jpg"):
					os.remove(self.mpath + ".jpg")
			except Exception, e:
				print('[EMC] MovieInfo posterCallback exception failure: ', str(e))
			self.savePoster()
		else:
			self.showMsg(True)

	def savePoster(self):
		self.jpgsaved = False
		try:
			coverpath = self.mpath + ".jpg"
			if fileExists("/tmp/previewCover.jpg"):
				shutil.copy2("/tmp/previewCover.jpg", coverpath)
				self.jpgsaved = True
		except Exception, e:
			print('[EMC] MovieInfo savePoster exception failure: ', str(e))

		self.showMsg()

	def ok(self):
		if self.page == 0:
			pass
		else:
			sel = self["previewlist"].l.getCurrentSelection()
			if sel is not None:
				self["previewlist"].hide()
				self.page = 0
				self["movie_name"].setText(_("Movie Information Preview for:") + "   " + self.moviename)
				self.switchPage(sel[1], sel[2])

	def pageUp(self):
		if self.page == 0:
			self["contenttxt"].pageUp()
		if self.page == 1:
			if self.selectionTimer.isActive():
				self.selectionTimer.stop()
			self["previewlist"].up()

	def pageDown(self):
		if self.page == 0:
			self["contenttxt"].pageDown()
		if self.page == 1:
			if self.selectionTimer.isActive():
				self.selectionTimer.stop()
			self["previewlist"].down()

	def showPreviewCoverCB(self, picInfo=None):
		ptr = self.picload.getData()
		if ptr != None:
			self["previewcover"].instance.setPixmap(ptr.__deref__())
			if self.page == 0:
				self["previewcover"].show()
		else:
			self["previewcover"].hide()

	def showPreviewCover(self):
		if fileExists("/tmp/previewCover.jpg"):
			previewpath = "/tmp/previewCover.jpg"
		else:
			previewpath = getNoPosterPath() #"/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/no_poster.png"
		sc = AVSwitch().getFramebufferScale()
		self.picload.setPara((self["previewcover"].instance.size().width(), self["previewcover"].instance.size().height(), sc[0], sc[1], False, 1, "#00000000"))
		self.picload.startDecode(previewpath)

	def exit(self):
		if self.movielist is not None:
			if self.page == 0 and self.movielist[1] > 1:
				self.page = 1
				self["movie_name"].setText(_("Search results for:") + "   " + self.moviename)
				self.switchPage()
			else:
				if fileExists("/tmp/previewCover.jpg"):
					os.remove("/tmp/previewCover.jpg")
				if fileExists("/tmp/previewTxt.txt"):
					os.remove("/tmp/previewTxt.txt")
				if self.selectionTimer.isActive():
					self.selectionTimer.stop()
				if self.previewTimer.isActive():
					self.previewTimer.stop()
				self.close()
		else:
			self.close()

	def setup(self):
		self.session.open(MovieInfoSetup)

class MovieInfoSetup(Screen, ConfigListScreenExt):
	if sz_w == 1920:
		skin = """
		<screen name="EMCMovieInfoSetup" position="center,170" size="1200,820" title="Movie Information Download Setup">
		<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img_fhd/red.png" position="10,5" size="300,70" alphatest="blend"/>
		<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img_fhd/green.png" position="310,5" size="300,70" alphatest="blend"/>
		<widget backgroundColor="#9f1313" font="Regular;30" halign="center" name="key_red" position="10,5" foregroundColor="white" shadowColor="black" shadowOffset="-2,-2" size="300,70" transparent="1" valign="center" zPosition="1" />
		<widget backgroundColor="#1f771f" font="Regular;30" halign="center" name="key_green" position="310,5" foregroundColor="white" shadowColor="black" shadowOffset="-2,-2" size="300,70" transparent="1" valign="center" zPosition="1" />
		<widget font="Regular;34" halign="right" position="1050,25" render="Label" size="120,40" source="global.CurrentTime">
			<convert type="ClockToText">Default</convert>
		</widget>
		<widget font="Regular;34" halign="right" position="800,25" render="Label" size="240,40" source="global.CurrentTime">
			<convert type="ClockToText">Date</convert>
		</widget>
		<eLabel backgroundColor="#818181" position="10,80" size="1180,1" />
		<widget enableWrapAround="1" name="config" position="10,90" itemHeight="45" scrollbarMode="showOnDemand" size="1180,720" />
		</screen>"""
	else:
		skin = """
		<screen name="EMCMovieInfoSetup" position="center,120" size="820,520" title="Movie Information Download Setup">
		<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/red.png" position="10,5" size="200,40" alphatest="blend"/>
		<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/green.png" position="210,5" size="200,40" alphatest="blend"/>
		<widget name="key_red" position="10,5" size="200,40" zPosition="1" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-2,-2" />
		<widget name="key_green" position="210,5" size="200,40" zPosition="1" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-2,-2" />
		<widget source="global.CurrentTime" render="Label" position="740,14" size="70,24" font="Regular;22" halign="right">
			<convert type="ClockToText">Default</convert>
		</widget>
		<eLabel position="10,50" size="800,1" backgroundColor="#818181" />
		<widget name="config" itemHeight="30" position="10,60" size="800,450" enableWrapAround="1" scrollbarMode="showOnDemand" />
		</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		self.list = []
		self.list.append(getConfigListEntry(_("Language:"), config.EMC.movieinfo.language))
		self.list.append(getConfigListEntry(_("Load Runtime:"), config.EMC.movieinfo.ldruntime))
		self.list.append(getConfigListEntry(_("Load Genre:"), config.EMC.movieinfo.ldgenre))
		self.list.append(getConfigListEntry(_("Load Production Countries:"), config.EMC.movieinfo.ldcountries))
		self.list.append(getConfigListEntry(_("Load Release Date:"), config.EMC.movieinfo.ldreleasedate))
		self.list.append(getConfigListEntry(_("Load Vote:"), config.EMC.movieinfo.ldvote))
		self.list.append(getConfigListEntry(_("Save Cover"), config.EMC.movieinfo.coversave))
		self.list.append(getConfigListEntry(_("Coversize"), config.EMC.movieinfo.coversize))
		self.list.append(getConfigListEntry(_("Cover delay in ms"), config.EMC.movieinfo.cover_delay))

		ConfigListScreenExt.__init__(self, self.list, session)
		self["actions"] = HelpableActionMap(self, "EMCMovieInfo",
		{
			"EMCEXIT":		self.keyCancel,
			"EMCGreen":		self.keySave,
			"EMCRed":		self.keyCancel,
		}, -1)
		self["key_red"] = Button(_("Cancel"))
		self["key_green"] = Button(_("OK"))
		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self.setTitle(_("Movie Information Download Setup"))

	def keySave(self):
		for x in self["config"].list:
			x[1].save()
		configfile.save()
		self.close()