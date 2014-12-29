# -*- coding: utf-8 -*-
from threading import Lock

class ThreadQueue:
	def __init__(self):
		self.__list = [ ]
		self.__lock = Lock()

	def push(self, val):
		lock = self.__lock
		lock.acquire()
		self.__list.append(val)
		lock.release()

	def pop(self):
		lock = self.__lock
		lock.acquire()
		if self.__list:
			ret = self.__list.pop()
		else:
			ret = (1, None, None)
		lock.release()
		return ret
