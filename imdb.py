# -*- coding: utf-8 -*-
from Components.ActionMap import *
from Components.Label import Label
from Components.MenuList import MenuList

from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaTest
from Components.Pixmap import Pixmap
from enigma import ePicLoad
from Tools.LoadPixmap import LoadPixmap
from Components.AVSwitch import AVSwitch
from Components.Sources.StaticText import StaticText
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Tools.Directories import fileExists
from Screens.Menu import boundFunction
from Components.PluginComponent import plugins

from Components.Button import Button

from twisted.web.client import downloadPage, getPage

from Components.config import *
from Components.ConfigList import *

from enigma import eListboxPythonMultiContent, eListbox, gFont, RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_HALIGN_CENTER, loadPNG, RT_WRAP, eServiceReference
from enigma import getDesktop
from enigma import loadJPG

from Tools.BoundFunction import boundFunction
from DelayedFunction import DelayedFunction
from time import time

import re, urllib, urllib2, os, time

config.plugins.imdb = ConfigSubsection()
config.plugins.imdb.search = ConfigSelection(default="0", choices = [("0",_("imdb.de")),("1",_("themoviedb.org"))])

class AppURLopener(urllib.FancyURLopener):
    version = "Mozilla/5.0 (X11; U; Linux x86_64; de; rv:1.9.0.15) Gecko/2009102815 Ubuntu/9.04 (jaunty) Firefox/3."

class imdblist(MenuList):
	def __init__(self, list):
		MenuList.__init__(self, list, False, eListboxPythonMultiContent)
		self.l.setFont(0, gFont("Regular", 14))
		self.l.setFont(1, gFont("Regular", 16))
		self.l.setFont(2, gFont("Regular", 18))
		self.l.setFont(3, gFont("Regular", 20))
		self.l.setFont(4, gFont("Regular", 22))
		self.l.setFont(5, gFont("Regular", 24))

def imdb_show(title, pp, elapsed, genre, search_title):
	res = [ (title, pp, elapsed, genre, search_title) ]
	if not re.match('.*?(Exist|N/A)', elapsed):
		elapsed = "%s ms." % elapsed
	res.append(MultiContentEntryText(pos=(0, 0), size=(510, 24), font=4, text=search_title, flags=RT_HALIGN_LEFT))
	res.append(MultiContentEntryText(pos=(500, 0), size=(172, 24), font=4, text=elapsed, flags=RT_HALIGN_LEFT))
	return res

def showCoverlist(title, url, path):
	res = [ (title, url, path) ]
	res.append(MultiContentEntryText(pos=(0, 0), size=(550, 24), font=4, text=title, flags=RT_HALIGN_LEFT))
	return res

class imdbscan(Screen):
	if getDesktop(0).size().width() == 1280:
		skin = """
			<screen position="center,center" size="900,560" title="EMC iMDB">
				<widget name="menulist" position="220,100" size="672,408" scrollbarMode="showOnDemand" transparent="1"/>
				<widget name="info" position="30,10" size="300,24" zPosition="0" font="Regular;21" halign="left" valign="center" transparent="1" foregroundColor="#ffffff" backgroundColor="black"/>
				<widget name="poster" position="20,40" size="165,230" zPosition="4" backgroundColor="#00000000" alphatest="off" transparent="0" />
				<widget name="m_info" position="200,40" size="800,24" zPosition="0" font="Regular;21" halign="center" valign="center" transparent="1" foregroundColor="#ffffff" backgroundColor="black"/>
				<widget name="download" position="10,398" size="200,24" zPosition="0" font="Regular;21" halign="left" valign="center" transparent="1" foregroundColor="#ffffff" backgroundColor="black"/>
				<widget name="exist" position="10,350" size="200,24" zPosition="0" font="Regular;21" halign="left" valign="center" transparent="1" foregroundColor="#ffffff" backgroundColor="black"/>
				<widget name="no_poster" position="10,374" size="200,24" zPosition="0" font="Regular;21" halign="left" valign="center" transparent="1" foregroundColor="#ffffff" backgroundColor="black"/>
				<widget name="genre" position="200,64" size="800,24" zPosition="0" font="Regular;21" halign="center" valign="center" transparent="1" foregroundColor="#ffffff" backgroundColor="black"/>
				<widget name="done_msg" position="0,512" size="940,48" zPosition="0" font="Regular;21" halign="center" valign="center" transparent="1" foregroundColor="#ffffff" backgroundColor="black"/>
				<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/key-green.png" position="10,293" size="30,30" alphatest="on" />
				<!-- <widget name="ButtonGreen" pixmap="skin_default/buttons/key_green.png" position="21,300" zPosition="10" size="35,25" transparent="1" alphatest="on" /> -->
				<widget name="ButtonGreenText" position="54,300" size="300,22" valign="center" halign="left" zPosition="1" font="Regular;20" transparent="1" />
				<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/key-red.png" position="10,453" size="30,30" alphatest="on" />
				<!-- <widget name="ButtonRed" pixmap="skin_default/buttons/key_red.png" position="21,460" zPosition="10" size="35,25" transparent="1" alphatest="on" /> -->
				<widget name="ButtonRedText" position="54,460" size="300,22" valign="center" halign="left" zPosition="1" font="Regular;20" transparent="1" />
			</screen>"""
	else:
		skin = """
			<screen position="center,center" size="720,500" title="EMC iMDB">
				<widget name="menulist" position="10,10" size="710,380" scrollbarMode="showOnDemand" />
			</screen>"""

	def __init__(self, session, data):
		Screen.__init__(self, session, data)
		self.m_list = data
		self["actions"] = HelpableActionMap(self, "EMCimdb",
		{
			"EMCEXIT":		self.exit,
			"EMCOK":                self.ok,
			"EMCGreen":		self.imdb,
			"EMCRed":		self.red,
			"EMCMenu":		self.config,
		}, -1)

		self["ButtonGreen"] = Pixmap()
		self["ButtonGreenText"] = Label(_("Start"))
		self["ButtonRed"] = Pixmap()
    		self["ButtonRedText"] = Label(_("Loeschen"))
		self["poster"] = Pixmap()
		self.menulist = []
		self["menulist"] = imdblist([])
		self["info"] = Label("")
		self["m_info"] = Label("")
		self["genre"] = Label("")
		self["download"] = Label("")
		self["exist"] = Label("")
		self["no_poster"] = Label("")
		self["done_msg"] = Label("Um die Suche zu starten, drück bitte die Gruene-Taste")
		self["info"].setText("")
		self.no_image_poster = "/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/no_poster.png"
		self.check = "false"
		#if self.check == "true":
		self["menulist"].onSelectionChanged.append(self.showInfo)
		self.running = "false"

	def showInfo(self):
		if self.check == "true":
			m_title = self["menulist"].getCurrent()[0][0]
			m_poster_path = self["menulist"].getCurrent()[0][1]
			#m_real_title = self["menulist"].getCurrent()[0][2]
			m_genre = self["menulist"].getCurrent()[0][3]
			#m_o_title = self["menulist"].getCurrent()[0][4]
			if os.path.exists(m_poster_path):
				DelayedFunction(500, self.poster_resize(m_poster_path))
			else:
				DelayedFunction(500, self.poster_resize(self.no_image_poster))
			self["m_info"].setText(m_title)
			self["genre"].setText(m_genre)

	def no_cover(self):
		if os.path.exists(self.no_image_poster):
			DelayedFunction(500, self.poster_resize(self.no_image_poster))

	def imdb(self):
		if self.running == "true":
			print "EMC iMDB: Search already Running."
                        
		elif self.running == "false":
                        print "EMC iMDB: Search started..."
			self.no_cover()
			self.running = "true"
			self.counter = 0
			self.counter2 = 0
			self.counter3 = 0
			self.counter_download = 0
			self.counter_exist = 0
			self.counter_no_poster = 0
			self.t_elapsed = 0
			self.menulist = []
			self.count_movies = len(self.m_list)
			#self.poster_resize(self.no_image_poster)
			self["exist"].setText("Exist: 0")
			self["no_poster"].setText("No Cover: 0")
			self["download"].setText("Download: 0")
			self["done_msg"].setText("Searching...")
			self.counter_a = 0
			self.starttime = 0
                        self.t_start_time = time.clock()
			self.s_supertime = time.time()
			self.file_format = "(.ts|.avi|.mkv|.divx|.f4v|.flv|.img|.iso|.m2ts|.m4v|.mov|.mp4|.mpeg|.mpg|.mts|.vob)"
                        self.cm_list = self.m_list[:]
			self.search_list = []
			self.exist_list = []
			self.check = "false"
			self["done_msg"].setText("Creating Search List..")
			for each in self.cm_list:
                                (title, path) = each
				path = re.sub(self.file_format + "$", '.jpg', path)
				if os.path.exists(path):
					#elem = (title, path)
					#self.exist_list.append(elem)
					self.counter2 += 1
                                        #self.gotall += 1
                                        print "EMC iMDB: Cover vorhanden - %s" % title
                                        self.display_exist(title, path)
                                        #if self.gotall == 10:
                                        #print "EMC iMDB: N/A Jump"
                                        #self.imdb_start()

				else:
					elem2 = (title, path)
					self.search_list.append(elem2)

			#print "exist:", self.exist_list
			#print "search:", self.search_list
			self.imdb_start()
			
        def imdb_start(self):
		self["done_msg"].setText("Searching..")
		self.starttime = time.time()
		#self.gotall = 0
		self.run10 = "false"
		for i in xrange(10):
			if self.search_list:
				(title, path) = self.search_list.pop()
				self.start_time = time.clock()
                                
				if config.plugins.imdb.search.value == "0":
					self.name = title.replace(' ','.').replace(':','.').replace('..','.')
       					path = re.sub(self.file_format + "$", '.jpg', path)
					search_title = self.name.replace('.',' ')
				
					if not os.path.exists(path):
                                                self.counter3 += 1
						url = "http://www.imdbapi.com/?t=" + self.name.replace('Ã¶','%F6')
						##replace('Ã¶','%F6')
						print "EMC imdbapi.com:", url
						getPage(url, timeout = 10).addCallback(self.imdbapi, search_title, path).addErrback(self.errorLoad, search_title)
#					else:
#                                                self.counter2 += 1
#						self.gotall += 1
#                                                print "EMC iMDB: Cover vorhanden"
#						self.display_exist(search_title, path)
#						if self.gotall == 10:
 #                                                       print "EMC iMDB: N/A Jump"
  #                                                      self.imdb_start()

				if config.plugins.imdb.search.value == "1":
					self.name = title.replace(' ','+').replace(':','+').replace('-','').replace('++','+')
        				path = re.sub(self.file_format + "$", '.jpg', path)
        				search_title = self.name.replace('+',' ')
                                
					if not os.path.exists(path):
						self.counter3 += 1
						url = "http://api.themoviedb.org/2.1/Movie.search/de/xml/8789cfd3fbab7dccf1269c3d7d867aff/" + self.name
						print "EMC themoviedb.org:", url						
						getPage(url, timeout = 10).addCallback(self.themoviedb, search_title, path).addErrback(self.errorLoad, search_title)
#					else:
#						self.counter2 += 1
#						self.gotall += 1
#						print "EMC iMDB: Cover vorhanden - %s" % search_title
#						self.display_exist(search_title, path)
#						if self.gotall == 10:
#							print "EMC iMDB: N/A Jump"
#							self.imdb_start()
			else:
				print "EMC iMDB: MovieList is empty, search is DONE."
				self.e_supertime = time.time()
				total_movie = self.counter3 + self.counter2 
                		total_time = self.e_supertime - self.s_supertime
				avg = (total_time / total_movie)
				self.done = "%s Filme in %.1f sec gefunden. Avg. Speed: %.1f sec" % (total_movie, total_time, avg) 
                		self["done_msg"].setText(self.done)
				#self.check = "false"
				self.running = "false"
				#if self["menulist"].instance:
	        	        #        print "move to TOP"
        	        	#        self["menulist"].instance.moveSelection(self["menulist"].instance.moveTop)
				#DelayedFunction(1000, self.check = "true")
				break
		
		#self.check = "true"

	def themoviedb(self, data, search_title, path):
		if self.search_list and self.run10 == "false":
		#and self.counter_a % 10 == 0:
                        print "EMC iMDB: 10sec. DelayFunction gestatet"
			DelayedFunction(10000 - int(time.time() - self.starttime) + 100, boundFunction(self.imdb_start))
			self.display_delay()
			self.run10 = "true"
		### Parsing infos from data ###
		if re.match('.*?<opensearch:totalResults>0</opensearch:totalResults>|.*?Error 503 Service Unavailable|.*?500 Internal Server Error',data, re.S):
			print "EMC iMDB: Themoviedb.org is down or No results found - %s" % search_title
			self.display_na(search_title, path)
		else:
			movie_title = re.findall('<name>(.*?)</name>', data)
			poster_url = re.findall('<image type="poster" url="(.*?)" size="cover"', data)
			if poster_url:
				print "EMC themoviedb: Download", search_title, poster_url[0]
                                ### Cover Download ###
	      			urllib._urlopener = AppURLopener()
       				urllib.urlretrieve(poster_url[0], path)
        			urllib.urlcleanup()
        			if os.path.exists(path):
					self.display_download(movie_title[0], search_title, path)
		   	 	else:
		        		print "EMC iMDB: Film gefunden aber kein poster vorhanden - %s" % search_title
                                        self.display_na(search_title, path)
                        else:
                                print "EMC iMDB: Themoviedb.org is down or No results found - %s" % search_title
                                self.display_na(search_title, path)
                        
		self["menulist"].l.setList(self.menulist)
		self["menulist"].l.setItemHeight(24)

	def imdbapi(self, data, search_title, path):
                self.counter_a += 1
		if self.search_list and self.run10 == "false":
		#and self.counter_a % 10 == 0:
                        print "EMC iMDB: 10sec. DelayFunction gestatet"
			self.display_delay()
			DelayedFunction(10000 - int(time.time() - self.starttime) + 100, boundFunction(self.imdb_start))
			self.run10 = "true"
		
		### Parsing infos from data ###
		if re.match('.*?"Response":"True"', data):
			movie_name = re.findall('"Title":"(.*?)"."Year":"(.*?)"', data)
			movie_title = str(movie_name[0][0]) + " " + str(movie_name[0][1])
			poster_url = re.findall('"Poster":"(.*?)"', data)
			if poster_url[0] == "N/A":
                                print "EMC iMDB: theimdbapi.com is down or No results found - %s" % search_title
				self.display_na(search_title, path)
			else:
                                print "EMC iMDB: theimdbapi.com Download", search_title, poster_url[0]
                                ### Cover Download ###
				urllib._urlopener = AppURLopener()
				urllib.urlretrieve(poster_url[0], path)
				urllib.urlcleanup()
				if os.path.exists(path):
					self.display_download(movie_title, search_title, path)
                                else:
		        		print "EMC iMDB: Film gefunden aber kein poster vorhanden - %s" % search_title
                                        self.display_na(search_title, path)
       
		elif re.match('.*?"Response":"Parse Error"', data):
			print "EMC iMDB: theimdbapi.com is down or No results found - %s" % search_title
			self.display_na(search_title, path)

		self["menulist"].l.setList(self.menulist)
		self["menulist"].l.setItemHeight(24)

	def errorLoad(self, error, search_title):
		print "keine daten zu %s gefunden." % search_title
		#print "Please report: %s" % str(error)
                
        def display_na(self, search_title, path):
		self.counter += 1
                self.counter_no_poster = self.counter_no_poster + 1
                self.count = "Film: %s von %s" % (self.counter, self.count_movies)
                self["info"].setText(self.count)
                self["m_info"].setText(search_title)
                self["no_poster"].setText("No Cover: %s" % str(self.counter_no_poster))
                self.menulist.append(imdb_show(search_title, path, "N/A", "", search_title))
                self["menulist"].l.setList(self.menulist)
		self["menulist"].l.setItemHeight(24)
		if self.count_movies == self.counter:
			self.check = "true"
                
        def display_exist(self, search_title, path):
		self.counter += 1
		self.counter_exist = self.counter_exist + 1
		self.count = "Film: %s von %s" % (self.counter, self.count_movies)
		self["info"].setText(self.count)
          	self["m_info"].setText(search_title)
          	self["exist"].setText("Exist: %s" % str(self.counter_exist))
          	self.menulist.append(imdb_show(search_title, path, "Exist", "", search_title))
		self["menulist"].l.setList(self.menulist)
		self["menulist"].l.setItemHeight(24)
		if self.count_movies == self.counter:
                        self.check = "true"
        
        def display_download(self, movie_title, search_title, path):
		print "debug:", movie_title
		self.counter += 1
	      	self.counter_download = self.counter_download + 1
       		self.end_time = time.clock()
        	elapsed = (self.end_time - self.start_time) * 10
        	self.count = "Film: %s von %s" % (self.counter, self.count_movies)
                self["info"].setText(self.count)
		self["m_info"].setText(movie_title)
		self["download"].setText("Download: %s" % str(self.counter_download))
                self.menulist.append(imdb_show(movie_title, path, str(elapsed), "", search_title))
                self["menulist"].l.setList(self.menulist)
		self["menulist"].l.setItemHeight(24)
		if self.count_movies == self.counter:
                        self.check = "true"


	def display_delay(self):
		self["done_msg"].setText("Delay of 10 sec. due the search flooding..")		
		
	def exit(self):
		self.check = "false"
		self.close()

	def red(self):
		if self.check == "true":
			m_poster_path = self["menulist"].getCurrent()[0][1]
			if os.path.exists(m_poster_path):
				if m_poster_path == self.no_image_poster:
					print "no_poster.jpg kann nicht geloescht werden."
				else:
					os.system("rm '%s'" % (m_poster_path))
					done = "%s removed." % m_poster_path
					self.no_cover()
					self["done_msg"].setText(done)
	def ok(self):
                if self.check == "true":
			data_list = []
			m_title = self["menulist"].getCurrent()[0][0]
			m_poster_path = self["menulist"].getCurrent()[0][1]
			print m_poster_path
			data_list = [(m_title, m_poster_path)]
                        #self.session.open(getCover, data_list)
			self.session.openWithCallback(self.setupFinished, getCover, data_list)

	### Cover resize ###
	def poster_resize(self, poster_path):
		self["poster"].instance.setPixmap(None)
		self["poster"].hide()
		sc = AVSwitch().getFramebufferScale() # Maybe save during init
		self.picload = ePicLoad()
		self.picload.PictureData.get().append(self.showCoverCallback)
		size = self["poster"].instance.size()
		self.picload.setPara((size.width(), size.height(), sc[0], sc[1], False, 1, "#00000000")) # Background dynamically
		self.picload.startDecode(poster_path)

	def showCoverCallback(self, picInfo=None):
                if picInfo:
                        ptr = self.picload.getData()
                        if ptr != None:
                                print "anzeigen"
                                self["poster"].instance.setPixmap(ptr)
                                self["poster"].show()
		else:
			print "nicht angezeigt"
		
	def config(self):
		self.session.openWithCallback(self.setupFinished, imdbSetup)

	def setupFinished(self, result):
		print "showwwww it meeee ttto :D"
		if result:
			self.showInfo()			

class imdbSetup(Screen, ConfigListScreen):
	skin = """
		<screen position="center,center" size="550,400" title="EMC imdb Setup" >
			<widget name="config" position="20,10" size="510,330" scrollbarMode="showOnDemand" />
			<widget name="key_red" position="0,350" size="140,40" valign="center" halign="center" zPosition="5" transparent="1" foregroundColor="white" font="Regular;18"/>
			<widget name="key_green" position="140,350" size="140,40" valign="center" halign="center" zPosition="5" transparent="1" foregroundColor="white" font="Regular;18"/>
			<ePixmap name="red" pixmap="skin_default/buttons/red.png" position="0,350" size="140,40" zPosition="4" transparent="1" alphatest="on"/>
			<ePixmap name="green" pixmap="skin_default/buttons/green.png" position="140,350" size="140,40" zPosition="4" transparent="1" alphatest="on"/>
		</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)

		self["key_red"] = Button(_("Cancel"))
		self["key_green"] = Button(_("OK"))

		self.list = []
		self.list.append(getConfigListEntry(_("Search Site:"), config.plugins.imdb.search))
		ConfigListScreen.__init__(self, self.list, session)
		self["setupActions"] = ActionMap(["SetupActions", "ColorActions"],
		#self["actions"] = HelpableActionMap(self, "sjActions",
		{
			"green":	self.keySave,
			"cancel":	self.keyClose,
			"ok":		self.keySave,
		}, -2)

	def keySave(self):
		for x in self["config"].list:
			x[1].save()
		configfile.save()
		self.close(True)

	def keyClose(self):
		for x in self["config"].list:
			x[1].cancel()
		self.close(False)
                
class getCover(Screen):
	skin = """
		<screen position="center,center" size="550,430" title="EMC Cover Selecter" >
			<widget name="menulist" position="0,0" size="550,195" scrollbarMode="showOnDemand" transparent="1"/>
			<widget name="poster" zPosition="2" position="0,200" size="165,230" alphatest="blend" />
		</screen>"""

	def __init__(self, session, data):
		Screen.__init__(self, session, data)

		#["key_red"] = Button(_("Cancel"))
		#self["key_green"] = Button(_("OK"))

		self["actions"] = HelpableActionMap(self, "EMCimdb",
		{
			"EMCEXIT":	self.exit,
			#"green":	self.keySave,
			#"cancel":	self.keyClose,
			"EMCOK":	self.ok,
		}, -1)
                
		(title, o_path) = data.pop()
		self.title =  title
		self.o_path = o_path
		self.menulist = []
		self["menulist"] = imdblist([])
		self["poster"] = Pixmap()
		self["menulist"].onSelectionChanged.append(self.showInfo)
		self.check = "false"
                self.path = "/tmp/tmp.jpg"
		self.searchCover(self.title)

        def searchCover(self, title):
                print title
		url = "http://m.imdb.com/find?q=%s" % title.replace(' ','+')
		getPage(url).addCallback(self.showCovers, title).addErrback(self.errorLoad, title)

	def showCovers(self, data, title):
		print "EMB iMDB: Cover Select - %s" % title
		#print data
		bild = re.findall('<img src="http://ia.media-imdb.com/images/(.*?)".*?<a href="/title/(.*?)/".*?">(.*?)</a>.*?\((.*?)\)', data, re.S)
		if bild:
			for each in bild:
				imdb_title = each[2]
				imdb_url = each[0]
				self.menulist.append(showCoverlist(imdb_title, imdb_url, self.o_path))
		else:
			print "EMC iMDB: keine infos gefunden - %s" % title

		self["menulist"].l.setList(self.menulist)
		self["menulist"].l.setItemHeight(24)
		self.check = "true"
		self.showInfo()

	def errorLoad(self, error, title):
		print "keine daten zu %s gefunden." % title
		print error

	def showInfo(self):
		if self.check == "true":
                        m_title = self["menulist"].getCurrent()[0][0]
			m_url = self["menulist"].getCurrent()[0][1]
                        if m_url:
                                m_url = re.findall('(.*?)\.', m_url)
                                extra_imdb_convert = "._V1._SX175_SY230_.jpg"
                                m_url = "http://ia.media-imdb.com/images/%s%s" % (m_url[0], extra_imdb_convert)
                                print "EMC iMDB: Download Poster - %s" % m_url
                                urllib._urlopener = AppURLopener()
                                urllib.urlretrieve(m_url, self.path)
                                urllib.urlcleanup()
                                if os.path.exists(self.path):
                                        ptr = LoadPixmap(self.path)
                                        if ptr is None:
                                                ptr = LoadPixmap("/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/no_poster.png")
                                                print "EMC iMDB: Load default NO Poster."
                                        if ptr is not None:
                                                self["poster"].instance.setPixmap(ptr.__deref__())
                                                print "EMC iMDB: Load Poster - %s" % m_title
                        else:
                                print "EMC iMDB: No url found for - %s" % m_title

	def exit(self):
		self.check = "false"
		#self["poster"].hide()
		self.close(False)

	def ok(self):
		if self.check == "true":
			os.system("mv %s '%s'" % (self.path, self.o_path))
			print "EMC iMDB: mv poster to real path - %s %s" % (self.path, self.o_path) 
			self.check = "false"
			self.close(True)
