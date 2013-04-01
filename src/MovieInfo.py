from Components.ActionMap import ActionMap, HelpableActionMap
from Components.MenuList import MenuList
from Screens.Screen import Screen
from Components.Label import Label
from Screens.MessageBox import MessageBox

import json, os
from urllib2 import Request, urlopen


class DownloadMovieInfo(Screen):
	skin = """
		<screen position="center,center" size="600,450" title="Movie Information Download (TMDb)">
		<widget name="movie_name" position="5,5" size="600,22" zPosition="0" font="Regular;21" valign="center" transparent="1" foregroundColor="#00bab329" backgroundColor="#000000"/>
		<widget name="movielist" position="10,50" size="570,350" scrollbarMode="showOnDemand"/>
		<widget name="resulttext" position="5,400" size="600,22" zPosition="0" font="Regular;21" valign="center" transparent="1" foregroundColor="#00bab329" backgroundColor="#000000"/>
		</screen>"""

	def __init__(self, session, movies, moviename, service):
		Screen.__init__(self, session)
		self.session = session
		self.service = service

		movielist = []
		for mov in movies:
			movielist.append((_(str(mov["title"])), mov["id"]))

		self["actions"] = HelpableActionMap(self, "EMCMovieInfo",
		{
			"EMCEXIT":		self.exit,
			"EMCOK":		self.ok,
			#"EMCINFO":		self.info
		}, -1)

		self["movie_name"] = Label("Search results for:   " + moviename)
		self["movielist"] = MenuList(movielist)
		self["resulttext"] = Label(str(len(movies)) + " movies found!")

	def exit(self):
		self.close()
		
	def ok(self):		
		sel = self["movielist"].l.getCurrentSelection()

		if sel is not None:
			id = sel[1]
			noerror = True
			try:
				headers = {"Accept": "application/json"}
				request = Request("http://api.themoviedb.org/3/movie/" + str(id) + "?api_key=8789cfd3fbab7dccf1269c3d7d867aff&language=de", headers=headers)
				jsonresponse = urlopen(request).read()
				response = json.loads(jsonresponse)
			except:
				noerror = False

			if noerror:
				blurb = (str(response["overview"])).encode('utf-8')
				runtime = (str(response["runtime"])).encode('utf-8')
				releasedate = (str(response["release_date"])).encode('utf-8')	
				countrylist = response["production_countries"]
				countries  = ""
				for i in countrylist:
					if countries == "":
						countries = i["name"]
					else:
						countries = countries + ", " + i["name"]

				(moviepath,ext) = os.path.splitext(self.service.getPath())
				file(moviepath + ".txt",'w').write("Laufzeit: " + runtime + " Minuten\n\n" + "Inhalt: " + blurb + "\n\nProduktionsland: " + countries)
				self.session.open(MessageBox, _('Movie Information downloaded successfully!'), MessageBox.TYPE_INFO, 10)
				self.exit()
			else:
				self.session.open(MessageBox, _("An error occured! Internet connection broken?"), MessageBox.TYPE_ERROR, 10)
			
	#def info(self):
		#TODO
