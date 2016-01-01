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

from enigma import eTimer, eConsoleAppContainer
from Components.config import *
from Screens.Standby import *
import Screens.Standby
import os, sys, traceback
from collections import Callable, deque
from pipes import quote
from itertools import izip_longest

def emcDebugOut(outtxt, outfile=None, fmode="aw", forced=False):
	try:	# fails if called too early during Enigma startup
		if config.EMC.debug.value or forced:
			if not os.path.exists(config.EMC.folder.value):
				emcTasker.shellExecute("mkdir " + config.EMC.folder.value)
			if outfile is None:
				outfile = os.path.join(config.EMC.folder.value, config.EMC.debugfile.value)
				ltim = localtime()
				headerstr = "%04d%02d%02d %02d:%02d " %(ltim[0],ltim[1],ltim[2],ltim[3],ltim[4])
				outtxt = headerstr + outtxt
			deb = open(outfile, fmode)
			deb.write(outtxt + "\n")
		print "EMC: %s" %(outtxt)
		# Print detailed informationon error
		if sys.exc_info()[0]:
			print "Unexpected error:", sys.exc_info()[0]
			traceback.print_exc(file=sys.stdout)
			traceback.print_exc(file=deb)
		deb.close()
	except: pass


class EMCExecutioner:
	def __init__(self, identifier):
		self.identifier = identifier   #TODO could be remove
		self.container = eConsoleAppContainer()
		try:
			self.container_appClosed_conn = self.container.appClosed.connect(self.runFinished)
			# this will cause interfilesystem transfers to stall Enigma
			self.container_dataAvail_conn = self.container.dataAvail.connect(self.dataAvail)
		except:
			self.container_appClosed_conn = None
			self.container_dataAvail_conn = None
			self.container.appClosed.append(self.runFinished)
			self.container.dataAvail.append(self.dataAvail)	# this will cause interfilesystem transfers to stall Enigma
		self.script = deque()
		self.associated = deque()
		self.executing = ""
		self.returnData = ""

	def isIdle(self):
		return len(self.script)==0

	def shellExecute(self, script, associated=None, sync=False):
		# Parameters:
		#  script = single command:   cmd
		#			list of commands: [cmd, cmd]
		#  associated = single callback: callback
		#				single tuple:    (callback, args)
		#				list of tuples:  [(callback),(callback, args),(...)]
		#    callback = function to be executed
		#    args = single parameter:    arg or (arg) or (a, b) or [a,b]
		#			multiple parameters: arg1, arg2
		#  sync (synchronous callback):
		#    True  = After every command, one callback entry is executed, additionally callbacks will be executed after the last command
		#            If the callback entry is a tuple or list, alle subcallbacks will be executed
		#    False = All callbacks are executed at the end
		if not sync or not isinstance(script, list):
			# Single command execution
			self.script.append( script )
			self.associated.append( associated )
		else:
			for s, a in izip_longest(script, associated):
				self.script.append( s )
				self.associated.append( [a] )

		if self.executing == "":
			emcDebugOut("[emcTasker] Run script")
			self.execCurrent()
		else:
			emcDebugOut("[emcTasker] Run after current execution")

	def execCurrent(self):
		try:
			script = self.script.popleft()
			if script:
				if isinstance(script, list):
					script = '; '.join( script )

				self.executing = quote( script )
				self.container.execute( "sh -c " + self.executing )
				emcDebugOut("[emcTasker] executing: " + self.executing )
			else:
				self.runFinished()
		except Exception, e:
			emcDebugOut("[emcTasker] execCurrent exception:\n" + str(e))

	def runFinished(self, retval=None):
		try:
			associated = self.associated.popleft()
			emcDebugOut("[emcTasker] sh exec %s finished, return status = %s %s" %(self.executing, str(retval), self.returnData))
			if associated:
				#P3 for foo, bar, *other in tuple:
				for fargs in associated:
					try:
						if isinstance(fargs, tuple) or isinstance(fargs, list):
							f, args = [e for e in fargs[:1]] + [fargs[1:]]
							if isinstance(f, Callable):
								if args:
									f(*args)
								else:
									f(args)
						else:
							if isinstance(fargs, Callable):
								fargs()
					except Exception, e:
						#emcDebugOut("[emcTasker] runFinished exception:\n" + str(e))
						pass
			self.returnData = ""

			if self.script:
				# There is more to be executed
				emcDebugOut("[emcTasker] sh exec rebound")
				self.execCurrent()
			else:
				self.executing = ""

				#TODO MAYBE we want do cleanup the whole container
				#del self.container.dataAvail[:]
				#del self.container.appClosed[:]
				#del self.container

		except Exception, e:
			emcDebugOut("[emcTasker] runFinished exception:\n" + str(e))

	def dataAvail(self, string):
		self.returnData += "\n" + string.replace("\n","")


class EMCTasker:
	def __init__(self):
		self.restartTimer = eTimer()
		try:
			self.restartTimer_conn = self.restartTimer.timeout.connect(self.RestartTimerStart)
		except:
			self.restartTimer.timeout.get().append(self.RestartTimerStart)
		self.minutes = 0
		self.timerActive = False
		self.executioners = []
		#TODO instantiate the executioner as we need them
		self.executioners.append( EMCExecutioner("A") )
		self.executioners.append( EMCExecutioner("B") )
		self.executioners.append( EMCExecutioner("C") )

	def shellExecute(self, script, associated=None, sync=False):
		for x in self.executioners:
			if x.isIdle():
				x.shellExecute(script, associated, sync)
				return
		# all were busy, just append to any task list randomly
		import random
		self.executioners[ random.randint(0, 2) ].shellExecute(script, associated, sync)

	def Initialize(self, session):
		self.session = session
		if config.EMC.restart.value != "":
			from DelayedFunction import DelayedFunction
			DelayedFunction(60 * 1000, self.RestartTimerStart, True)	# delay auto restart timer to make sure there's time for clock init

	def ShowAutoRestartInfo(self):
		# call the Execute/Stop function to update minutes
		if config.EMC.restart.value != "":
			self.RestartTimerStart(True)
		else:
			self.RestartTimerStop()

		from EnhancedMovieCenter import _
		if self.timerActive:
			mints = self.minutes % 60
			hours = self.minutes / 60
			self.session.open(MessageBox, _("Next auto-start in ")+ str(hours) +" h "+ str(mints) +" min", MessageBox.TYPE_INFO, 4)
		else:
			self.session.open(MessageBox, _("auto-start is currently not active."), MessageBox.TYPE_INFO, 4)

	def RestartTimerStop(self):
		self.restartTimer.stop()
		self.timerActive = False
		self.minutes = 0

	def InitRestart(self):
		if Screens.Standby.inStandby:
			self.LaunchRestart(True)	# no need to query if in standby mode
		else:
			if config.EMC.restart.value == "0": # Standby
				stri = _("Your Box is about to go into Standby, continue?\n Select no to delay one hour")
			elif config.EMC.restart.value == "1": # DeepStandby
				stri = _("Your Box is about to go into DeepStandby, continue?\n Select no to delay one hour")
			elif config.EMC.restart.value == "2": # Reboot
				stri = _("Your Box is about to go into Reboot, continue?\n Select no to delay one hour")
			else: # E2 Restart
				stri = _("Your Box is about to go into E2 Restart, continue?\n Select no to delay one hour")
			self.session.openWithCallback(self.LaunchRestart, MessageBox, stri, MessageBox.TYPE_YESNO, 30)

	def LaunchRestart(self, confirmFlag=True):
		if confirmFlag:
			emcDebugOut("+++ Enigma restart NOW")
			flag = os.path.join(config.EMC.folder.value, "EMC_standby_flag.tmp")
			if Screens.Standby.inStandby or config.EMC.restart_stby.value:
				emcDebugOut("!", flag, fmode="w", forced=True)
			else:
				self.shellExecute("rm -rf " + flag)
			if config.EMC.restart.value == "0": # Standby
				self.session.open(Standby)
				return "true"
			elif config.EMC.restart.value == "1": CoolRestart = 1 # DeepStandby
			elif config.EMC.restart.value == "2": CoolRestart = 2 # Reboot
			else: CoolRestart = 3 # E2 Restart
			self.session.open(TryQuitMainloop, CoolRestart)
			# this means that we're going to be re-instantiated after Enigma has restarted
		else:
			self.RestartTimerStart(True, 60)

	def RestartTimerStart(self, initializing=False, postponeDelay=0):
		try:
			self.restartTimer.stop()
			self.timerActive = False

			lotime = localtime()
			wbegin = config.EMC.restart_begin.value
			wend = config.EMC.restart_end.value
			xtimem = lotime[3]*60 + lotime[4]
			ytimem = wbegin[0]*60 + wbegin[1]
			ztimem = wend[0]*60 + wend[1]

			if ytimem > ztimem:	ztimem += 12*60
			emcDebugOut("+++ Local time is " +str(lotime[3:5]) + ", auto-start window is %s - %s" %(str(wbegin), str(wend)) )

			if postponeDelay > 0:
				self.restartTimer.start(postponeDelay * 60000, False)
				self.timerActive = True
				mints = postponeDelay % 60
				hours = postponeDelay / 60
				emcDebugOut("+++ User postponed auto-start by " +str(hours)+ "h " +str(mints)+ "min")
				return

			minsToGo = ytimem - xtimem
			if xtimem > ztimem:	minsToGo += 24*60

			if initializing or minsToGo > 0:
				if minsToGo < 0:		# if initializing
					minsToGo += 24*60	# today's window already passed
				elif minsToGo == 0:
					minsToGo = 1
				self.restartTimer.start(minsToGo * 60000, False)
				self.timerActive = True
				self.minutes = minsToGo
				mints = self.minutes % 60
				hours = self.minutes / 60
				emcDebugOut("+++ Auto start rescheduled in " +str(hours)+ "h " +str(mints)+ "min")
			else:
				recordings = len(self.session.nav.getRecordings())
				next_rec_time = self.session.nav.RecordTimer.getNextRecordingTime()
				if not recordings and (((next_rec_time - time()) > 360) or next_rec_time < 0):
					emcDebugOut("--> emcTasker.InitRestart()")
					self.InitRestart()
				else:
					emcDebugOut("+++ REC in progress, auto restart rescheduled in 15 min")
					self.minutes = 15
					self.restartTimer.start(15*60*1000, False)
					self.timerActive = True
		except Exception, e:
			emcDebugOut("[emcTasker] RestartTimerStart exception:\n" + str(e))

emcTasker = EMCTasker()
