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
from . import usermessage
from threading import Thread
from threading import Lock
from queue import Queue
from io import BytesIO
from shutil import make_archive
from shutil import move
from shutil import rmtree




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

def cookiesfiledetect(foresDelete=False):
   cookiesInfoDict = {'internalCookies': {},
                      'canEXH': False,
                      'userCookies': {},
                     }
   if foresDelete == True:
      os.remove('./DLmodules/.cookiesinfo')
   if os.path.isfile('./DLmodules/.cookiesinfo') == False:
      with open('./DLmodules/.cookiesinfo', 'w') as fo:
         json.dump(cookiesInfoDict, fo)
   return cookiesInfoDict


def mangadownloadctl(mangasession, url, path, logger, title, dlopt, threadQ=None, stateQ=None):
   logger.info('Begin to download gallery {0}'.format(url))
   stop = dloptgenerate.Sleep(config.rest)
   tempErrDict ={url: {}}
   resultDict = {'previewImageDict': {},
                 'dlErrorDict': {}}
   htmlContentList = accesstoehentai(method='get', 
                                     mangasession=mangasession, 
                                     stop=stop, 
                                     urls=[url]
                                    )
#    print (htmlContentList[0])
   pageContentDict = datafilter.mangadlfilter(htmlContentList[0])

   threadCounter = 0
   q = Queue()
#    print (pageContentDict)
   if pageContentDict.get('contentPages'):
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
   else:
      logger.warning('{0} does not contain any page, maybe deleted'.format(url))
      resultDict['dlErrorDict'].update({'galleryError': usermessage.galleryError})
#    print (resultDict['dlErrorDict'])
#    print (dlopt.forceZip)
#    print (dlopt.Zip)
   if dlopt.Zip == True and (resultDict['dlErrorDict'] == {} or dlopt.forceZip == True):
      t = Thread(target=zipmangadir,
                 name='{0}.zip'.format(title), 
                 kwargs={'url': url, 
                         'logger': logger,
                         'title': title, 
                         'removeDir':dlopt.removeDir, 
                         'stateQ': stateQ,
                         'threadQ': threadQ})
      threadQ.put(t)
      # t.start()
#       zipErrorDict = zipmangadir(title=title, removeDir=dlopt.removeDir, logger=logger)
#       if zipErrorDict.get(title):
#          if resultDict['dlErrorDict'].get('zipError'):
#             resultDict['dlErrorDict']['zipError'].update(zipErrorDict['zipError'])
#          else: 
#             resultDict['dlErrorDict'].update({'zipError': zipErrorDict['zipError']}) 
#    if resultDict['dlErrorDict']:
#       with open((path + 'errorLog'), 'w') as fo:
#          json.dump(resultDict['dlErrorDict'], fo)

   return resultDict

def mangadownload(url, mangasession, filename, path, logger, q):
   logger.info('Page {0} download start'.format(filename))
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

def zipmangadir(url, title, removeDir, logger, stateQ, threadQ):
   logger.info('Begin archive {0}.'.format(title))
   zipErrorDict = {}
   try:
      resultZip = make_archive(base_name=title,
                               format='zip',
                               root_dir=config.path,
                               base_dir=title)
      fileName = '{0}.zip'.format(title)
      move(src=resultZip, 
           dst=os.path.join(config.path, fileName)
          )
      if removeDir == True:
         rmtree('{0}{1}'.format(config.path, title))
   except Exception as error:
      logger.exception('Raise exception {0} while archiving {1}.'.format(str(error), title))
      zipErrorDict.update({url: {'zipArchiveError': str(error)}})
   else:
      logger.info('{0} has been archived.'.format(title))
   if zipErrorDict != None:
      stateQ.put(zipErrorDict)
   threadQ.task_done()

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


