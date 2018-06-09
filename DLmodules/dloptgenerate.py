#!/usr/bin/python3

from . import config
from . import download
import json
from ast import literal_eval
from . import usermessage
import time
import random



class dloptgene():
   def __init__(self, urls, userCookies, path, changeCookies, canEXH=False, username=None, password=None):
      self.urls = urls # list
      self.userCookies = userCookies # dict
      self.path = path # str
      self.username = username # str, test propose
      self.password = password # str, test propose
      self.changeCookies = changeCookies # Bool
      self.canEXH = canEXH # Bool, default is false

 

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
#    print ('dlopt func')
   userCookies = config.userCookies
   errorMessage = {}
   dloptDict = {}
   if isinstance(userCookies, dict) == False:
      userCookies = {}
      errorMessage.update({'configError': [usermessage.userCookiesFormError]})
      logger.error('userCookies form error')
   download.cookiesfiledetect()
   with open('./DLmodules/.cookiesinfo', 'r') as fo:
      try:
         cookiesinfoDict = json.load(fo)
      except:
         logger.warning('Internal cookies file is broken, delete and replace.')
         internalCookiesFile = False
      else:
         internalCookiesFile = True
   if internalCookiesFile == False:
      cookiesinfoDict = download.cookiesfiledetect(foresDelete=True)
   if cookiesinfoDict['userCookies'] == config.userCookies:
      # print ('Use internal cookies.')
      userCookies = cookiesinfoDict['internalCookies']
      canEXH = cookiesinfoDict['canEXH']
      changeCookies = False
   else:
      print ('Cookies changed')
      userCookies = userCookies
      changeCookies = True
      canEXH = False
      cookiesinfoDict['userCookies'] = config.userCookies
      cookiesinfoDict['canEXH'] = False
      with open('./DLmodules/.cookiesinfo', 'w') as fo:
         json.dump(cookiesinfoDict, fo)
   dlopt = dloptgene(urls=urls,
                     userCookies=userCookies,
                     path=config.path,
                     changeCookies=changeCookies,
                     canEXH=canEXH
                    )
#    print (dlopt.urls)
   dloptDict.update({'dlopt': dlopt, 'errorMessage': errorMessage})
   return dloptDict







