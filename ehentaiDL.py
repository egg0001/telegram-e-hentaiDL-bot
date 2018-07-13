#!/usr/bin/python3

from DLmodules import dloptgenerate
from DLmodules import config
from DLmodules import usermessage
from DLmodules import datafilter
from DLmodules import ehlogin
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

class mangaInfo():
   '''This class and each of its objects contain the information of every gallery'''
   __slots__ = ('url', 'category', 'title', 'mangaData', 'previewImage', 'dlErrorDict', 'exh')

def mangaspider(urls, mangasession, path, dlopt, logger, errorStoreMangaObj):
   '''This function processes all the requested urls(galleries), including retriving their information,
      sends every of them to the partical download function and return the download result to telegram
      bot.'''
   urlSeparateList = [] # separate urls (list) to sublist containing 24 urls in each element
   urlsDict = {'e-hentai': [], 'exhentai': []}  # Separating galleries urls into two lists.
   tempList = [] # store the API result from e-h/exh
   tempDict = {} # transfer internal data
   mangaObjList = [] # Temporary store the mangaInfo objects.
   toMangaLogDict = {} # Transport the manga information to .mangalog file. 
   resultObjList = [] # Contain the download result objects
#    outDict = {}# return the information
   gidErrorDict = {'gidError': []} # Record the error gids
   for url in urls:
      if url.find('exhentai') != -1:
         urlsDict['exhentai'].append(url)
      else:
         urlsDict['e-hentai'].append(url)
#    print(urlsDict)
   for ulCategory in urlsDict:  
      # This block deal with e-hentai and exhentai's galleries
      # separately.                          
      if len(urlsDict[ulCategory]) == 0:
         logger.info('Gallery(s) of {0} not found, continue.'.format(ulCategory))
         continue 
      if ulCategory == 'exhentai':
         exh = True
      else:
         exh = False
      subUrlList = []
      internalCounter = 0
      if urlsDict[ulCategory]:  
         for url in urlsDict[ulCategory]:
            subUrlList.append(url)
            internalCounter += 1
            if (internalCounter %24 ) == 0:
               # The limitation of e-h's api is 25 galleries in one request and
               # This block separates the urls' list to fullfil this requirement.
               urlSeparateList.append(subUrlList)
               subUrlList = []
         if subUrlList:
            urlSeparateList.append(subUrlList)
            subUrlList = []
      apiStop = dloptgenerate.Sleep('2-3')
      for usl in urlSeparateList:
      #    print (usl)
         tempList.extend(download.accesstoehentai(method='post', 
                                                  mangasession=mangasession,
                                                  stop=apiStop,
                                                  urls=usl,
                                                  logger=logger
                                                 ) 
                        )
         # This list contains all the galleries' information retrived from e-h's api
         # Then it removes all the error results. 
      for tL in tempList:
         tLKey = tL.keys()
         if 'error' in tLKey:
            logger.warning('gid {0} encountered an error, delete'.format(tL['gid']))
            gidErrorDict['gidError'].append(tL['gid'])
            tempList.remove(tL)
      if gidErrorDict['gidError']:
         errorStoreMangaObj.dlErrorDict.update(gidErrorDict)
      tempDict = datafilter.genmangainfoapi(resultJsonDict=tempList, exh=exh)
      # Re-classify the information and prepare to generate the manga objects.
      for url in tempDict:
         manga = mangaInfo()
         manga.url = url 
         manga.mangaData = tempDict[url]
         manga.exh = exh
         manga.dlErrorDict = {}
         if tempDict[url]["category"]:
            manga.category = tempDict[url]["category"][0]
         else:
            manga.category = None
         if config.useEntitle == False and tempDict[url]['jptitle']:
            # Replace all the invalid path characters to '_'.
            manga.title = re.sub('[^\w\-_\.\(\)\[\] ]', '_', tempDict[url]['jptitle'][0])
         else:
            manga.title = re.sub('[^\w\-_\.\(\)\[\] ]', '_', tempDict[url]['entitle'][0])
         mangaObjList.append(manga)
      logger.info("Retrieved {0} gallery(s)' information in {1}.".format(len(mangaObjList), ulCategory))
      for manga in mangaObjList:
         # ...Then send all the manga objects to partical manga download function...
         resultObjList.append(download.mangadownloadctl(mangasession=mangasession, 
                                                        path=path,
                                                        logger=logger,
                                                        manga=manga,
                                                        dlopt=dlopt,
                                                      #   zipThreadQ=zipThreadQ,
                                                      #   zipStateQ=zipStateQ,
                                                      #   threadContainor=threadContainor
                                                      )
                             ) 
         toMangaLogDict.update(manga.mangaData)
      urlSeparateList = [] 
      tempDict = {}   # Reset all the loop relating variables  
      tempList = []
      mangaObjList = []
   resultObjList.append(errorStoreMangaObj)   
   download.userfiledetect(path=config.path)
   # After downloaded all galleries, store the download result to a log file.
   with open("{0}.mangalog".format(config.path), 'r') as fo:
      mangaInfoDict = json.load(fo)
      mangaInfoDict.update(toMangaLogDict)
   with open("{0}.mangalog".format(config.path), 'w') as fo:
      json.dump(mangaInfoDict, fo)
   return resultObjList


def exhcookiestest(mangasessionTest, cookies, forceCookiesEH=False):   #Evaluate whether the cookies could access exh
   requests.utils.add_dict_to_cookiejar(mangasessionTest.cookies, cookies)
   usefulCookiesDict = {'e-h': False, 'exh': False}
   if forceCookiesEH == False:
      r = mangasessionTest.get("https://exhentai.org/") 
      htmlContent = r.text
      usefulCookiesDict['exh'] = datafilter.exhtest(htmlContent=htmlContent)
      time.sleep(random.uniform(3,5))   
   else:
      r = mangasessionTest.get("https://exhentai.org/")
      htmlContent = r.text
      usefulCookiesDict['exh'] = datafilter.exhtest(htmlContent=htmlContent)
      time.sleep(random.uniform(3,5))
      if usefulCookiesDict['exh'] == False:
         r = mangasessionTest.get("https://e-hentai.org/")
         htmlContent = r.text
         usefulCookiesDict['e-h'] = datafilter.exhtest(htmlContent=htmlContent)      
         time.sleep(random.uniform(3,5))  # If access exh too fast, it would activate the anti-spider mechanism
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
#        print (usefulCookiesDict)
   if usefulCookiesDict['exh'] == True:
      eh = False
   else:
      eh = True
   mangasessionDict = {'mangasession': mangasession, 'eh': eh}
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
#    print (mangasessionDict)
   if mangasessionDict['eh'] == True and hasEXH == True:   
      # If user's cookies could not access exhentai, the program would delete exh's url(s).                                                     
      errorStoreMangaObj.dlErrorDict.update({'cookiesError': usermessage.usercookiesEXHError})
      for url in dloptDict['dlopt'].urls:
         if url.find('exhentai') != -1:
           dloptDict['dlopt'].urls.remove(url)
   resultObjList = mangaspider(urls=dloptDict['dlopt'].urls, 
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
   return resultObjList






                                





