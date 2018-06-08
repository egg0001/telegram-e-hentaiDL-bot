#!/usr/bin/python3


import os
import requests
import time
import json
from PIL import Image
import re
import random
from . import config
from . import dloptgenerate
from . import datafilter
from threading import Thread
from queue import Queue
from io import BytesIO




def userfiledetect(path):
   if os.path.exists(path) == False:
      os.makedirs(path, exist_ok=True)
      userdict = {}
      with open("{0}.mangalog".format(path), 'w') as fo:
         json.dump(userdict, fo)
   elif os.path.isfile("{0}.mangalog".format(path)) == False:
      userdict = {}
      with open("{0}.mangalog".format(path), 'w') as fo:
         json.dump(userdict, fo)
   else:
      with open("{0}.mangalog".format(path), 'r') as fo: 
         try:
            usersdict = json.load(fo)
         except json.decoder.JSONDecodeError:
            broken_file = os.path.join(path, '.mangalog')
            bkm = 'userdata.broken.TIME'
            backup_file_name = bkm.replace('TIME', str(time.asctime(time.localtime())))
            backup_file_name = backup_file_name.replace(":", ".")
            backup_file = os.path.join(path, backup_file_name)
            os.rename(broken_file, backup_file)
            userdict = {}
            with open("{0}.mangalog".format(path), 'w') as fo:
               json.dump(userdict, fo)
         else:
            pass

def cookiesfiledetect():
   if os.path.isfile('./DLmodules/.cookiesinfo') == False:
      cookiesInfoDict = {'internalCookies': {},
                         'canEXH': False,
                         'userCookies': {},
                        }
      with open('./DLmodules/.cookiesinfo', 'w') as fo:
         json.dump(cookiesInfoDict, fo)
   else:
      with open('./DLmodules/.cookiesinfo', 'r+') as fo:
         try:
            cookiesInfoDict = json.load(fo)
         except json.decoder.JSONDecodeError:
            cookiesInfoDict = {'internalCookies': {},
                               'canEXH': False,
                               'userCookies': {},
                              }
            json.dump(cookiesInfoDict, fo)
         else:
            if cookiesInfoDict.get('internalCookies') and cookiesInfoDict.get('canEXH') and cookiesInfoDict.get('userCookies'):
               pass
            else:
               cookiesInfoDict = {'internalCookies': {},
                                  'canEXH': False,
                                  'userCookies': {},
                                 }
               json.dump(cookiesInfoDict, fo)           

      #       broken_file = './DLmodules/.cookiesinfo'
      #       bkm = '.cookiesinfo.broken.TIME'
      #       backup_file_name = bkm.replace('TIME', str(time.asctime(time.localtime())))
      #       backup_file_name = backup_file_name.replace(":", ".")
      #       backup_file = './DLmodules/{0}'.format(backup_file_name)
      #       os.rename(broken_file, backup_file)
      #    else:
      #       if cookiesInfoDict.get('internalCookies') and cookiesInfoDict.get('canEXH') and cookiesInfoDict.get('userCookies'):
      #          pass
      #       else:
               


def mangadownloadctl(mangasession, url, path, logger, title):
   stop = dloptgenerate.Sleep(config.rest)
   tempErrDict ={url: {}}
   previewimageDict = {}
   resultDict = {'previewImageDict': {},
                 'dlErrorDict': {}}
   htmlContentList = accesstoehentai(method='get', 
                                     mangasession=mangasession, 
                                     stop=stop, 
                                     urls=[url]
                                    )
   pageContentDict = datafilter.mangadlfilter(htmlContentList[0])

   threadCounter = 0
   q = Queue()
   while pageContentDict['nextPage']:
      for mP in pageContentDict['contentPages']:
         t = Thread(target=mangadownload, 
                    name=mP[0],
                    kwargs={'url': mP[1],
                            'mangasession': mangasession,
                            'filename': mP[0],
                            'path': path,
                            'logger': logger,
                            'q': q
                            }
                  )
         threadCounter += 1
         t.start()
         if threadCounter >= config.dlThreadLimit:
            t.join()
            threadCounter = 0
      t.join()
      if pageContentDict['nextPage'] != -1:
         htmlContentList = accesstoehentai(method='get', 
                                           mangasession=mangasession, 
                                           stop=stop, 
                                           urls=[pageContentDict['nextPage']]
                                          )
         try:
            pageContentDict = datafilter.mangadlfilter(htmlContentList[0])
         except Exception as error:
            logger.exception('Raise a crucial exception during analysis {0}'.format(url))
            resultDict['dlErrorDict'].update({'nextPageError': {url: str(error)}})
            break
      else:
         pageContentDict['nextPage'] = ''
   while not q.empty():
      temp = q.get()
      tempErrDict[url].update(temp)
   if tempErrDict[url]:
      resultDict['dlErrorDict'].update(tempErrDict[url])
   filesList = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
   previewImage = filesList[0]
   previewImageFormat = (previewImage.split('.'))[-1]
   if previewImageFormat == 'JPG' or previewImageFormat == 'jpg':
      previewImageFormat = 'jpeg'
   try:
      i = Image.open('{0}{1}'.format(path, previewImage))
      bio = BytesIO()
      bio.name = title
      i.save(bio, format=previewImageFormat)
      resultDict['previewImageDict'].update({title: bio,})
   except Exception as error:
      logger.exception('Raise {0} while opening preview image of {1}'.format(error, title))
      resultDict['dlErrorDict'].update({'openFileError': {url: str(error)}})

   if resultDict['dlErrorDict']:
      with open((path + 'errorLog'), 'w') as fo:
         json.dump(resultDict['dlErrorDict'], fo)
#    print (resultDict)
   return resultDict

def mangadownload(url, mangasession, filename, path, logger, q):
   print ('Start download page {0}'.format(filename))
   errorMessage = {url: {}}
   err = 0
   for err in range(config.timeoutRetry):
      try:   
         htmlContentList = accesstoehentai(method="get", 
                                           mangasession=mangasession,
                                           stop=dloptgenerate.Sleep('1-2'),
                                           urls=[url])
         imagepattern = re.compile(r'''src=\"(http://[0-9:\.]+\/[a-zA-Z0-9]\/[a-zA-Z0-9-]+\/keystamp=[a-zA-Z0-9-]+;fileindex=[a-zA-Z0-9]+;xres=[a-zA-Z0-9]+\/.+\.([a-zA-Z]+))" style=''')
         matchUrls = imagepattern.search(htmlContentList[0])
         imagepatternAlter = re.compile(r'''\"(http://[0-9:\.]+\/[a-zA-Z0-9]\/[a-zA-Z0-9-]+\/keystamp=[a-zA-Z0-9-]+[;fileindex=]?[a-zA-Z0-9]?[;xres=]?[a-zA-Z0-9]?\/.+\.[a-zA-Z]+)\"''')
         matchUrlsAlter = imagepatternAlter.search(htmlContentList[0])
         if matchUrls:                     # This block still has some strange issues..... 
            imageUrl = matchUrls.group(1)
            imageForm = matchUrls.group(2)
         else:
            imageUrl = matchUrlsAlter.group(1)
            try:
               imageForm = matchUrlsAlter.group(2)
            except Exception as error:
               imageForm = 'jpg'    # This is a quick fix. Strange
               logger.exception('{0} has encountered a rex issue'.format(url))
               with open('{0}{1}{2}{3}{4}'.format(path, filename, 'rexE', err, '.htmlcontent'), 'w') as fo:
                  fo.write(htmlContentList[0])
            else: 
               pass
         os.makedirs(path, exist_ok=True)
         previewimage = mangasession.get(imageUrl, stream=True)
         handle = open("{0}{1}.{2}".format(path, filename, imageForm), 'wb')
         for chunk in previewimage.iter_content(chunk_size=512):
            if chunk:
               handle.write(chunk)
         handle.close()
      except Exception as error:
         logger.exception('{0} has encounter an error {1}'.format(url, error))
         errorMessage[url].update({err: str(error)})
         err += 1
         time.sleep(0.5)
         with open('{0}{1}{2}{3}'.format(path, filename, err, '.htmlcontent'), 'w') as fo:
            fo.write(htmlContentList[0])
      else:
         err=0
         break
   else:
      logger.exception("{0}'s error achieve {1} times, discarded.".format(url, config.timeoutRetry))

   if errorMessage[url]:    
      q.put(errorMessage)
   else:
      pass



def accesstoehentai(method, mangasession, stop, urls=None):
#    print (urls)
   resultList = []
   if method == 'get':
      inputInfo = urls
   elif method == 'post':
      tokenPattern = re.compile(r'''https://.+\.org/g/([0-9a-z]+)\/([0-9a-z]+)\/''')
      mangaJsonPayload = {
                          "method": "gdata",
                          "gidlist": [],
                          "namespace": 1
                         }
      for url in urls:
         mangaTokenMatch = tokenPattern.search(url)
         mangaJsonPayload["gidlist"].append([mangaTokenMatch.group(1), mangaTokenMatch.group(2)])

      inputInfo = [mangaJsonPayload]
   else:
      inputInfo = ''
   for ii in inputInfo:
      err = 0
      for err in range(config.timeoutRetry):
         try:
            if method == 'get':
               r = mangasession.get(ii)
               resultList.append(r.text)
            else:
            #    if exh == False:
               r = mangasession.post('https://api.e-hentai.org/api.php', json=ii)
            #    else:
            #       r = mangasession.post('https://api .exhentai.org/api.php', json=ii)
               mangaDictMeta = r.json()
               resultList.extend(mangaDictMeta['gmetadata'])
         except:
            err += 1
            dloptgenerate.Sleep.Havearest(stop)
         else:
            dloptgenerate.Sleep.Havearest(stop)
            err = 0
            break
      else:
         print ("network issue")
         err = 0
   return resultList


