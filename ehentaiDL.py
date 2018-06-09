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
import re


def mangaspider(urls, mangasession, path, errorMessage, logger):
   urlSeparateList = [] # separate urls (list) to sublist containing 24 urls in each element
   urlsDict = {'ehUrlList': [], 'exhUrlList': []}
   tempList = [] # store the API result from e-h/exh
   tempDict = {} # transfer internal data
   resultDict = {} # Contain the download result
   outDict = {}# return the information
   gidErrorDict = {'gidError': []} # Record the error gids
   strList = [] # contain the message strs.
   strDict = {} #For generate information to the user
   userInfoDict = {} # Dump information to file
   imageObjDict = {} # Get the image objects 
   queueImageObj = Queue() # store the image memory objects
   
   for url in urls:
      if url.find('exhentai') != -1:
         urlsDict['exhUrlList'].append(url)
      else:
         urlsDict['ehUrlList'].append(url)
#    print(urlsDict)
   for ulCategory in urlsDict:
      # print ('---------1--------------')
      if ulCategory == 'exhUrlList':
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
               urlSeparateList.append(subUrlList)
               subUrlList = []
         if subUrlList:
            urlSeparateList.append(subUrlList)
            subUrlList = []
      apiStop = dloptgenerate.Sleep('2-3')
      # print (urlSeparateList)
      for usl in urlSeparateList:
      #    print ('-------------------2----------------')
      #    print (usl)
         tempList.extend(download.accesstoehentai(method='post', 
                                                  mangasession=mangasession,
                                                  stop=apiStop,
                                                  urls=usl
                                                 ) 
                        )
      for tL in tempList:
         tLKey = tL.keys()
         if 'error' in tLKey:
            logger.warning('gid {0} encountered an error, delete'.format(tL['gid']))
            gidErrorDict['gidError'].append(tL['gid'])
            tempList.remove(tL)
      tempDict = datafilter.genmangainfoapi(resultJsonDict=tempList, exh=exh)
      logger.info("Retrived {0} url(s)' information".format(len(tempDict)))
      for url in tempDict:
      #    print ('----------------3---------------') 
         if config.useEntitle == False and tempDict[url]['jptitle']:
            title = tempDict[url]['jptitle'][0]
            
         elif tempDict[url]['jptitle'] == None or config.useEntitle == True:
            print (tempDict[url]['entitle'])
            title = tempDict[url]['entitle'][0]
         dlpath = path + '{0}/'.format(title) 
         resultDict.update({url: download.mangadownloadctl(mangasession=mangasession, 
                                                           url=url, 
                                                           path=dlpath,
                                                           logger=logger,
                                                           title=title)
                           }
                           )
         
      download.userfiledetect(path=path)
      with open("{0}.mangalog".format(path), 'r') as fo:
         mangaInfoDict = json.load(fo)
         mangaInfoDict.update(tempDict)
      with open("{0}.mangalog".format(path), 'w') as fo:
         json.dump(mangaInfoDict, fo)
      urlSeparateList = [] 
      tempDict = {}   #Delete all useless values 
      tempList = []
   outDict.update({'resultDict': resultDict})
   outDict.update(errorMessage)
   if gidErrorDict['gidError']:
      outDict.update(gidErrorDict)
#    print (outDict)
   return outDict


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
#    dlopt = dloptDict['dlopt']
   
   usefulCookiesDict = {'exh': False}
   if config.headers:
      mangasession.headers.update(random.choice(config.headers))
   else:
      mangasession.headers.update({{"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36",}})
   if config.proxy:
      proxypattern = re.compile(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\:\d{1,5})")
      proxy = proxypattern.search(random.choice(config.proxy)).group(1)
      proxies = {"http": proxy, "https": proxy,}
      mangasession.proxies = proxies
   else:
      pass
#    if dloptDict['dlopt'].changeCookies == True:
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
#    else:
#       requests.cookies.cookiejar_from_dict(dloptDict['dlopt'].userCookies)
#       if dloptDict['dlopt'].canEXH == True:
#          r = mangasession.get('https://exhentai.org/')
#          eh = False
#          print (r.text)
#       else:
#          mangasession.get('https://e-hentai.org/')
#          eh = True
#          print (r.text)
#       mangasessionDict = {'mangasession': mangasession, 'eh': eh}
#       time.sleep(2) # Prevent the anti-spider function
   return mangasessionDict


def Spidercontrolasfunc(dloptDict, logger):
   hasEXH = False
   urls = dloptDict['dlopt'].urls
   errorMessage = dloptDict['errorMessage']
   for url in dloptDict['dlopt'].urls:
      if url.find('exhentai') != -1:
         hasEXH = True
         break
   mangasessionDict = sessiongenfunc(dloptDict=dloptDict, logger=logger, hasEXH=hasEXH)
   mangasession = mangasessionDict['mangasession']
   print (mangasessionDict)
   if mangasessionDict['eh'] == True and hasEXH == True:
      errorMessage.update({'cookiesError': usermessage.usercookiesEXHError})
      for url in urls:
         if url.find('exhentai') != -1:
           urls.remove(url)



   outDict = mangaspider(urls=urls, 
                         mangasession=mangasession,
                         path=dloptDict['dlopt'].path,
                         errorMessage=dloptDict['errorMessage'],
                         logger=logger
                        )
   internalCookies = requests.utils.dict_from_cookiejar(mangasession.cookies)
   with open('./DLmodules/.cookiesinfo', 'r') as fo:
      cookiesInfoDict = json.load(fo)
      cookiesInfoDict['internalCookies'] = internalCookies
      if mangasessionDict['eh'] == True:
         cookiesInfoDict['canEXH'] = False
      else:
         cookiesInfoDict['canEXH'] = True
   with open('./DLmodules/.cookiesinfo', 'w+') as fo:
      json.dump(cookiesInfoDict, fo)
   return outDict






                                





