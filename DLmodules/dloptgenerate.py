#!/usr/bin/python3

from . import config
import json
from ast import literal_eval
from . import usermessage
import time
import random


class dloptgene():
   def __init__(self, urls, userCookies, path):
      self.urls = urls # list
      self.userCookies = userCookies # dict
      self.path = path



class Sleep():   #Just a sleep function
   minsleep = 0
   maxsleep = 0
   def __init__(self, sleepstr):
      self.sleepstr = sleepstr
      if self.sleepstr.find("-") != -1:
         sleeptime = self.sleepstr.split("-")
         Sleep.minsleep = int(sleeptime[0])
         Sleep.maxsleep = int(sleeptime[1])
      else:
         Sleep.minsleep = int(self.sleepstr)
         Sleep.maxsleep = int(self.sleepstr)
   
   def Havearest(self):
      time.sleep(random.uniform(Sleep.minsleep, Sleep.maxsleep))


def dloptgenerate(urls, logger):
   print ('dlopt func')
   userCookies = config.userCookies
   errorMessage = {}
   dloptDict = {}
   if isinstance(userCookies, dict) == False:
      userCookies = {}
      errorMessage.update({'configError': [usermessage.userCookiesFormError]})
      logger.error('userCookies form error') 
   dlopt = dloptgene(urls=urls,
                     userCookies=userCookies,
                     path=config.path
                    )
   print (dlopt.urls)
   dloptDict.update({'dlopt': dlopt, 'errorMessage': errorMessage})
   return dloptDict







