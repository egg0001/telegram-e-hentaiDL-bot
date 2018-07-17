#!/usr/bin/python3

from DLmodules import dloptgenerate
from DLmodules import config
from DLmodules import usermessage
from DLmodules import datafilter
from DLmodules import download 
import requests
import json
from ast import literal_eval
from queue import Queue
import time 
import random
from threading import Thread
import gc
import re

class urlAnalysis():
   '''This class and its objects contain a list of galleries' urls, the boolen value(exh) to 
      indicate the source (e-h or exh) of the galleries. Then, the first method (retriveInfoFormAPI)
      would retrive galleries' inforation from e-h's API and store it in the attribute (apiInfoDict)
      The seconde method (mangaObjGen) would generate some Manga objects preparing to download.'''

   def __init__(self, urlsList, exh):
      self.urlsList = urlsList
      self.exh = exh
      self.mangaObjList = []
      self.apiInfoDict = {} 
      self.gidErrorList = []

   def retriveInfoFormAPI(self, mangasession, logger):
      urlSeparateList = []
      tempList = []
      subUrlList = []
      internalCounter = 0
      if self.urlsList:  
         for url in self.urlsList:
            subUrlList.append(url)
            internalCounter += 1
            if (internalCounter %24 ) == 0:
               # The limitation of e-h's api is 25 galleries in one request and
               # This code block separates the urls' list to fullfil this requirement.
               urlSeparateList.append(subUrlList)
               subUrlList = []
         if subUrlList:
            urlSeparateList.append(subUrlList)
            subUrlList = []
      apiStop = dloptgenerate.Sleep('2-3')
      for usl in urlSeparateList:
         tempList.extend(download.accesstoehentai(method='post', 
                                                  mangasession=mangasession,
                                                  stop=apiStop,
                                                  urls=usl,
                                                  logger=logger
                                                 ) 
                        )
      for tL in tempList:
         tLKey = tL.keys()
         if 'error' in tLKey:
            logger.warning('gid {0} encountered an error, delete'.format(tL['gid']))
            self.gidErrorList.append(tL['gid'])
            tempList.remove(tL)
      # print (self.gidErrorList)
      self.apiInfoDict = datafilter.genmangainfoapi(resultJsonDict=tempList, exh=self.exh)
      return self

   def mangaObjGen(self, logger):
      for url in self.apiInfoDict:
         manga = mangaInfo()
         manga.url = url 
         manga.mangaData = self.apiInfoDict[url]
         manga.exh = self.exh
         manga.dlErrorDict = {}
         if self.apiInfoDict[url]["category"]:
            manga.category = self.apiInfoDict[url]["category"][0]
         else:
            manga.category = None
         if config.useEntitle == False and self.apiInfoDict[url]['jptitle']:
            # Replace all the invalid path characters to '_'.
            manga.title = re.sub(r'[\<\>\:\"\\\|\?\*\/]+', '_', self.apiInfoDict[url]['jptitle'][0])
         else:
            manga.title = re.sub(r'[\<\>\:\"\\\|\?\*\/]+', '_', self.apiInfoDict[url]['entitle'][0])
         self.mangaObjList.append(manga)
      f = lambda exh: 'exhentai' if exh == True else 'e-hentai'
      logger.info("Retrieved {0} gallery(s)' information in {1}.".format(len(self.apiInfoDict), f(self.exh)))
      return self

class mangaInfo():
   '''This class and each of its objects contains the information of every gallery and a method to 
      download the all the content of every gallery.'''
   __slots__ = ('url', 'category', 'title', 'mangaData', 'previewImage', 'dlErrorDict', 'exh')

   def mangaDownload(self, path, mangasession, logger, dlopt):
      self = download.mangadownloadctl(manga=self, path=path, 
                                       mangasession=mangasession, 
                                       logger=logger, dlopt=dlopt
                                      )
      return self

def mangaspider(urls, mangasession, path, dlopt, logger, errorStoreMangaObj):
   '''This function processes all the requested urls(galleries), including exploiting urlAnalysis class 
      and its methods to retrive galleries' information as well as generate the mangaInfo objects preparing
      to download. Then it would exploit the mangaDownload method in mangaInfo class' objects do download
      the content and prepare the result sending back to Telegram bot.'''
   urlsDict = {'e-hentai': [], 'exhentai': []}  # Separating galleries urls into two lists.
   urlAnalysisObjList = []
   mangaObjList = [] # Temporary store the mangaInfo objects.
   toMangaLogDict = {} # Transport the manga information to .mangalog file. 
   for url in urls:
      if url.find('exhentai') != -1:
         urlsDict['exhentai'].append(url)
      else:
         urlsDict['e-hentai'].append(url)
   for ulCategory in urlsDict:  
#       # This block deal with e-hentai and exhentai's galleries
#       # separately.                          
      if len(urlsDict[ulCategory]) == 0:
         logger.info('Gallery(s) of {0} not found, continue.'.format(ulCategory))
         continue 
      if ulCategory == 'exhentai':
         exh = True
      else:
         exh = False
      urlAnalysisObj = urlAnalysis(urlsList=urlsDict[ulCategory], exh=exh)
      urlAnalysisObj.retriveInfoFormAPI(mangasession=mangasession, logger=logger)
      urlAnalysisObj.mangaObjGen(logger=logger)
      urlAnalysisObjList.append(urlAnalysisObj)
   tempGidErrorList = []
   for urlAnalysisObj in urlAnalysisObjList:
      mangaObjList.extend(urlAnalysisObj.mangaObjList)
      if urlAnalysisObj.gidErrorList:
         tempGidErrorList.extend(urlAnalysisObj.gidErrorList)
   if tempGidErrorList:
      errorStoreMangaObj.dlErrorDict.update({'gidError': tempGidErrorList})
   for manga in mangaObjList:
      manga.mangaDownload(mangasession=mangasession, 
                          path=path,
                          logger=logger,
                          dlopt=dlopt)
      toMangaLogDict.update(manga.mangaData)
   mangaObjList.append(errorStoreMangaObj)   
   download.userfiledetect(path=config.path)
   # After downloaded all galleries, store the download result to a log file.
   with open("{0}.mangalog".format(config.path), 'r') as fo:
      mangaInfoDict = json.load(fo)
      mangaInfoDict.update(toMangaLogDict)
   with open("{0}.mangalog".format(config.path), 'w') as fo:
      json.dump(mangaInfoDict, fo)
   return mangaObjList


def exhcookiestest(mangasessionTest, cookies, forceCookiesEH=False):   #Evaluate whether the cookies could access exh
   requests.utils.add_dict_to_cookiejar(mangasessionTest.cookies, cookies)
   usefulCookiesDict = {'e-h': False, 'exh': False}
   if forceCookiesEH == False:
      r = mangasessionTest.get("https://exhentai.org/") 
      htmlContent = r.text
      usefulCookiesDict['exh'] = datafilter.exhtest(htmlContent=htmlContent)
      time.sleep(random.uniform(1,2))   
   else:
      r = mangasessionTest.get("https://exhentai.org/")
      htmlContent = r.text
      usefulCookiesDict['exh'] = datafilter.exhtest(htmlContent=htmlContent)
      time.sleep(random.uniform(1,2))
      if usefulCookiesDict['exh'] == False:
         r = mangasessionTest.get("https://e-hentai.org/")
         htmlContent = r.text
         usefulCookiesDict['e-h'] = datafilter.exhtest(htmlContent=htmlContent)      
         time.sleep(random.uniform(1,2))  # If access exh too fast, it would activate the anti-spider mechanism
      else: 
         usefulCookiesDict.update({'e-h': True})
   return usefulCookiesDict


def sessiongenfunc(dloptDict, logger, hasEXH):
   mangasession = requests.Session()
   usefulCookiesDict = {'exh': False}
   if config.headers:
      mangasession.headers.update(random.choice(config.headers))
   else:
      mangasession.headers.update({{"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36",}})
   if config.proxy:
      if config.proxy[0].find('socks5://') != -1:
         proxy = config.proxy[0].replace('socks5://', 'socks5h://')
      else:
         proxy = config.proxy[0]
      proxies = {"http": proxy, "https": proxy,}
      mangasession.proxies = proxies
   else:
      pass
   if dloptDict['dlopt'].userCookies and hasEXH == True:
      usefulCookiesDict = exhcookiestest(mangasessionTest=mangasession, 
                                         cookies=dloptDict['dlopt'].userCookies, 
                                         forceCookiesEH=config.forceCookiesEH
                                        ) 
   elif dloptDict['dlopt'].userCookies and config.forceCookiesEH == True:
      requests.utils.add_dict_to_cookiejar(mangasession.cookies, dloptDict['dlopt'].userCookies)
#    print (usefulCookiesDict)

   if usefulCookiesDict['exh'] == True:
      eh = False
   else:
      eh = True
   mangasessionDict = {'mangasession': mangasession, 'eh': eh, 'exh': usefulCookiesDict['exh']}
   return mangasessionDict


def Spidercontrolasfunc(dloptDict, logger):
   '''This function is the entry and the basic plot of the whole download process,
      including generating a requests session, examing whether the cookies could 
      access exhentai, and send the session as well as all galleries urls to download 
      function.'''
   errorStoreMangaObj = mangaInfo() # This mangaInfo object stores all the general errors,
                                    # including cookies errors and galleries' token errors.
   errorStoreMangaObj.dlErrorDict = dloptDict['errorMessage']
   errorStoreMangaObj.title = 'errorStoreMangaObj'
   hasEXH = False  
   # This bool variable determin whether the request contains url(s)
   # to exhentai requiring some special methods to view.
   for url in dloptDict['dlopt'].urls:
      if url.find('exhentai') != -1:
         hasEXH = True
         break
   mangasessionDict = sessiongenfunc(dloptDict=dloptDict, logger=logger, hasEXH=hasEXH)
   # This mangasessionDict contains a requests' session object having basic information to 
   # access e-hentai/exhentai. It also contains a bool value to determin whether user's cookies could
   # access exhentai.
   mangasession = mangasessionDict['mangasession']
   dloptDict['dlopt'].canEXH = mangasessionDict['exh']
#    print (mangasessionDict)
   if mangasessionDict['eh'] == True and hasEXH == True:   
      # If user's cookies could not access exhentai, the program would delete exh's url(s).                                                     
      errorStoreMangaObj.dlErrorDict.update({'cookiesError': usermessage.usercookiesEXHError})
      for url in dloptDict['dlopt'].urls:
         if url.find('exhentai') != -1:
           dloptDict['dlopt'].urls.remove(url)
   mangaObjList = mangaspider(urls=dloptDict['dlopt'].urls, 
                               mangasession=mangasession,
                               path=dloptDict['dlopt'].path,
                               dlopt=dloptDict['dlopt'],
                               logger=logger,
                               errorStoreMangaObj=errorStoreMangaObj
                              )
   #This outDict contains the download results for all the url(s) including images and
   # titles of the gallery(s) and the error reports it encounters while downloading.
   internalCookies = requests.utils.dict_from_cookiejar(mangasession.cookies)
   with open('./DLmodules/.cookiesinfo', 'r') as fo:  
      # After download, it stores the updated cookies for later use.
      cookiesInfoDict = json.load(fo)
      cookiesInfoDict['internalCookies'] = internalCookies
      if mangasessionDict['eh'] == True:
         cookiesInfoDict['canEXH'] = False
      else:
         cookiesInfoDict['canEXH'] = True
   with open('./DLmodules/.cookiesinfo', 'w+') as fo:
      json.dump(cookiesInfoDict, fo)
   gc.collect()
   return mangaObjList






                                





