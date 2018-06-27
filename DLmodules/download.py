#!/usr/bin/python3

# The download function also needs a thread containor 
# Or it would raise some strange errors 

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
from . import regx
from threading import Thread
from queue import Queue
from io import BytesIO
from shutil import make_archive
from shutil import move
from shutil import rmtree
from zipfile import ZipFile




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

def mangadownloadctl(mangasession, url, path, logger, title, 
                     dlopt, mangaData, threadContainor, 
                     category=None, zipThreadQ=None, zipStateQ=None):
   pageContentDict = {}  # Contains the current manga pages' information to download
   errorPageList = [] # Contains the error download pages in previous download
                      # Only useful while the program has detected some broken download history.
   if category == None:
      dlPath = path
   else:
      dlPath = '{0}{1}/'.format(path, category)
   downloadThreadQ = Queue() #Contain the image download threads 
   q = Queue()  # Contin the report of download errors  
   imageDownloadContainor = Thread(target=threadContainor, 
                                   name='tc', 
                                   kwargs={'threadQ': downloadThreadQ,
                                           'threadLimit': config.dlThreadLimit},
                                   daemon=True)
   imageDownloadContainor.start()
   logger.info('Begin to download gallery {0}'.format(url))
   stop = dloptgenerate.Sleep(config.rest)
   tempErrDict ={url: {}}
   resultDict = {'previewImageDict': {},
                 'dlErrorDict': {}}
   analysisPreviousDLResultDict = analysisPreviousDL(dlPath=dlPath, url=url, title=title, 
                                                     mangaData=mangaData, logger=logger)

   htmlContentList = accesstoehentai(method='get', 
                                     mangasession=mangasession, 
                                     stop=stop, 
                                     urls=[url],
                                     logger=logger
                                    )

#    print (htmlContentList[0])
   pageContentDict = datafilter.mangadlfilter(htmlContentList[0])
   if analysisPreviousDLResultDict['downloadIssue'] == True and analysisPreviousDLResultDict['completeDownload'] == False:
      errorPageDict = datafilter.mangadlfilter(analysisPreviousDLResultDict['errorPageStr'])
      if errorPageDict.get('contentPages'):
         for ePD in errorPageDict['contentPages']:
            errorPageList.append(ePD[0])
#    threadCounter = 0
   if pageContentDict.get('contentPages') and analysisPreviousDLResultDict['completeDownload'] == False:
      while pageContentDict['nextPage']:
         for mP in pageContentDict['contentPages']:
            if errorPageList:
               if mP[0] not in errorPageList:
                  logger.info('Page {0} has been downloaded in previous process, continue.'.format(mP[0]))
                  continue
            t = Thread(target=mangadownload, 
                       name=mP[0],
                       kwargs={'url': mP[1],
                               'mangasession': mangasession,
                               'filename': mP[0],
                               'path': '{0}{1}/'.format(dlPath, title),
                               'logger': logger,
                               'q': q,
                               'threadQ': downloadThreadQ
                               }
                     )
            downloadThreadQ.put(t)
         if pageContentDict['nextPage'] != -1:
            htmlContentList = accesstoehentai(method='get', 
                                              mangasession=mangasession, 
                                              stop=stop, 
                                              urls=[pageContentDict['nextPage']],
                                              logger=logger
                                             )
            try:
               pageContentDict = datafilter.mangadlfilter(htmlContentList[0])
            except Exception as error:
               logger.exception('Raise a crucial exception during analysis {0}'.format(url))
               resultDict['dlErrorDict'].update({'nextPageError': {url: str(error)}})
               break
         else:
            pageContentDict['nextPage'] = ''
      downloadThreadQ.join()
      logger.info('{0} download completed.'.format(url))
      while not q.empty():
         temp = q.get()
         tempErrDict[url].update(temp)
      if tempErrDict[url].get('Download error'):
         logger.error("Encountered a critical error while downloading images of {0}. ".format(url) +
                      "An error log would be deployed; and the zip function would be disabled.")
         resultDict['dlErrorDict'].update(tempErrDict[url])
      fileList = [f for f in os.listdir('{0}{1}/'.format(dlPath, title)) if os.path.isfile(os.path.join('{0}{1}/'.format(dlPath, title), f))] 
      # print (fileList)
      if '.mangaLog' in fileList:
         fileList.remove('.mangaLog')
      # print (fileList)
      fileList.sort()
      previewImage = fileList[0]

      previewImageFormat = (previewImage.split('.'))[-1]
      if previewImageFormat == 'JPG' or previewImageFormat == 'jpg':
         previewImageFormat = 'jpeg'
      try:
         with open('{0}{1}/{2}'.format(dlPath, title, previewImage), 'rb') as fo:
            imageByte = fo.read()
         bio = BytesIO(imageByte) 
         bio.name = title
         resultDict['previewImageDict'].update({title: bio})
      except Exception as error:
         logger.exception('Raise {0} while opening preview image of {1}'.format(error, title))
         resultDict['dlErrorDict'].update({'openFileError': {url: str(error)}})
   
   elif  analysisPreviousDLResultDict['completeDownload'] == True:
      logger.info('{0} had been completed in previous process.'.format(url))
      resultDict['previewImageDict'].update(analysisPreviousDLResultDict['previewImageDict'])
   else:
      logger.warning('{0} does not contain any page, maybe deleted'.format(url))
      resultDict['dlErrorDict'].update({'galleryError': usermessage.galleryError})
#    print (resultDict['dlErrorDict'])
#    print (dlopt.forceZip)
#    print (dlopt.Zip)
#    print (path)
   if analysisPreviousDLResultDict['completeDownload'] == False:
      with open(('{0}{1}/.mangaLog'.format(dlPath, title)), 'w') as fo:
         json.dump({url: mangaData}, fo)
   if resultDict['dlErrorDict']:
      with open(('{0}{1}/errorLog'.format(dlPath, title)), 'w') as fo:
         json.dump(resultDict['dlErrorDict'], fo)
   elif os.path.isfile('{0}{1}/errorLog'.format(dlPath, title)):
      os.remove('{0}{1}/errorLog'.format(dlPath, title))
#    print (resultDict['dlErrorDict'])
   criticalDownloadError = False
   for u in resultDict['dlErrorDict']:
      if resultDict['dlErrorDict'][u].get('Download error'):
         criticalDownloadError = True
         break
   if (dlopt.Zip == True and analysisPreviousDLResultDict['completeDownload'] == False 
       and (criticalDownloadError == False or dlopt.forceZip == True)):
      t = Thread(target=zipmangadir, 
                 name="{0}.zip".format(title),
                 kwargs={'url': url,
                        'path': dlPath,
                        'title': title,
                        'removeDir': dlopt.removeDir,
                        'logger': logger,
                        'zipStateQ': zipStateQ,
                        'zipThreadQ': zipThreadQ})
      zipThreadQ.put(t)

   return resultDict

def mangadownload(url, mangasession, filename, path, logger, q, threadQ):
   logger.info('Page {0} download start'.format(filename))
   errorMessage = {url: {}}
   downloadUrlsDict = {'imageUrl': "", 'reloadUrl': ''}
   err = 0
   for err in range(config.timeoutRetry):
      try:   
         if err != 0 and downloadUrlsDict['reloadUrl']:
            mangaUrl = url
         else: 
            mangaUrl = url
         htmlContentList = accesstoehentai(method="get", 
                                           mangasession=mangasession,
                                           stop=dloptgenerate.Sleep('1-2'),
                                           urls=[mangaUrl],
                                           logger=logger)
         if htmlContentList == []:
            raise htmlPageError('Empty html response.')
         downloadUrlsDict = datafilter.mangadlhtmlfilter(htmlContent = htmlContentList[0], url=url)
         imageUrl = downloadUrlsDict['imageUrl']
         os.makedirs(path, exist_ok=True)
         previewimage = mangasession.get(imageUrl, stream=True)
         if previewimage.status_code == 200:
            contentTypeList = previewimage.headers['Content-Type'].split('/')
            with open("{0}{1}.{2}".format(path, filename, contentTypeList[1]), 'wb') as handle:
               for chunk in previewimage:
                  handle.write(chunk)
            if int(previewimage.headers['Content-Length']) != int(os.path.getsize("{0}{1}.{2}".format(path, filename, contentTypeList[1]))):
               raise jpegEOIError('Image is corrupted')
         else:
            raise downloadStatusCodeError('Download status code error.')
      except Exception as error:
         logger.exception('{0} has encounter an error {1}'.format(url, error))
         errorMessage[url].update({err: str(error)})
         err += 1
         time.sleep(0.5)
      #    with open('{0}{1}-{2}{3}'.format(path, filename, err, '.htmlcontent'), 'w') as fo:
      #       fo.write(htmlContentList[0])
      else:
         err=0
         break
   else:
      logger.exception("{0}'s error achieve {1} times, discarded.".format(url, config.timeoutRetry))
      errorMessage[url].update({'Download error': 'Reached maximum retry counts while download this page.'})
   if errorMessage[url]:  
      q.put(errorMessage)
   else:
      pass
   threadQ.task_done()


def analysisPreviousDL(dlPath, url, title, mangaData, logger):
   '''Determin the previous download status '''
   analysisPreviousDLResultDict = {'errorPageStr': '',
                                   'downloadIssue': True,
                                   'completeDownload': False,
                                   'previewImageDict': {}}

   try:
      if os.path.isdir('{0}{1}/'.format(dlPath, title)):
         if 'errorLog' in os.listdir('{0}{1}/'.format(dlPath, title)):
            logger.warning('Gallery {0} has encountered some issues in previous download, retry the problematic page(s).'.format(url))
            with open('{0}{1}/errorLog'.format(dlPath, title), 'r') as fo:
               errorLog = json.load(fo)
            for eL in errorLog:
               if errorLog[eL].get("Download error"):
                  analysisPreviousDLResultDict['errorPageStr'] += (eL + "   ")
                  analysisPreviousDLResultDict['downloadIssue'] = True
         else:
            fileList = [f for f in os.listdir('{0}{1}/'.format(dlPath, title)) if os.path.isfile(os.path.join('{0}{1}/'.format(dlPath, title), f))]
            if '.mangaLog' in fileList:
               fileList.remove('.mangaLog')
            if 'errorLog' in fileList:
               fileList.remove('errorLog')
            if len(fileList) == int(mangaData['length'][0]):
               analysisPreviousDLResultDict.update({'downloadIssue': False, 'completeDownload': True})
               fileList.sort()
               previewImage = fileList[0]
               with open('{0}{1}/{2}'.format(dlPath, title, previewImage), 'rb') as fo:
                  print ('{0}{1}/{2}'.format(dlPath, title, previewImage))
                  imageByte = fo.read()
               bio = BytesIO(imageByte)
               bio.name = title

               analysisPreviousDLResultDict['previewImageDict'].update({title: bio})
      elif os.path.isfile('{0}{1}.zip'.format(dlPath, title)):
         trueFileList = []
         fileDir = ''
         with ZipFile('{0}{1}.zip'.format(dlPath, title), 'r') as zF:
            fileList = (zF.namelist())
            for fL in fileList:
               tempList = fL.split('/')
               if tempList[1]:
                  trueFileList.append(tempList[1])
               else:
                 fileDir = tempList[0]
            if '.mangaLog' in trueFileList:
               trueFileList.remove('.mangaLog')
            if 'errorLog' in trueFileList:
               trueFileList.remove('errorLog')
            trueFileList.sort()
            previewImage = trueFileList[0]
            imageData = zF.read('{0}/{1}'.format(fileDir,previewImage))

         bio = BytesIO(imageData)
         bio.name = title
         analysisPreviousDLResultDict['previewImageDict'].update({title: bio})
         analysisPreviousDLResultDict.update({'downloadIssue': False, 'completeDownload': True})
   except Exception as error:
      logger.error('Raised an error while analyzing errorLog, discard. - {0}'.format(str(error)))
      analysisPreviousDLResultDict = {'errorPageStr': '',
                                      'downloadIssue': True,
                                      'completeDownload': False,
                                      'previewImageDict': {}}

   return analysisPreviousDLResultDict


#-------------Several personalized Exceptions----------------------

class jpegEOIError(Exception):
   pass

class htmlPageError(Exception):
   pass

class downloadStatusCodeError(Exception):
   pass

#---------------------------------------------------------------------

def zipmangadir(url, path, title, removeDir, logger, zipStateQ=None, zipThreadQ=None):
   logger.info('Begin archiving gallery files of {0}.'.format(url))
   zipErrorDict = {}
   try:
      resultZip = make_archive(base_name=title,
                               format='zip',
                               root_dir=path,
                               base_dir=title)
      fileName = '{0}.zip'.format(title)
      move(src=resultZip, 
           dst=os.path.join(path, fileName)
          )
      if removeDir == True:
         rmtree('{0}{1}'.format(path, title))
   except Exception as error:
      logger.exception('Raise exception {0} while archiving files of {1}.'.format(str(error), url))
      zipErrorDict.update({url: {'zipArchiveError': str(error)}})
   else:
      logger.info('Gallery files of {0} has been archived.'.format(url))
   if zipErrorDict != None and zipStateQ != None:
      zipStateQ.put(zipErrorDict)
   if zipThreadQ != None:
      zipThreadQ.task_done()
   else:
      pass
   return zipErrorDict

def accesstoehentai(method, mangasession, stop, logger, urls=None):
#    print (urls)
   resultList = []
   if method == 'get':
      inputInfo = urls
   elif method == 'post':
      tokenPattern = re.compile(regx.tokenPattern)
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
         logger.error('Network error reached limit, discard.')
         err = 0
   return resultList


