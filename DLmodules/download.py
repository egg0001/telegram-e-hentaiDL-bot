#!/usr/bin/python3

import os
import requests
import time
import json
import re
import random
from . import config
from . import dloptgenerate
from . import datafilter
from . import usermessage
from . import regx 
from concurrent.futures import ThreadPoolExecutor
from queue import Queue
from io import BytesIO
from shutil import make_archive
from shutil import move
from shutil import rmtree
from zipfile import ZipFile

def userfiledetect(path):
   ''' Detect the  working path, if no, create a new one.'''
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
   ''' Detect the internal cookies file. '''
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

def mangadownloadctl(mangasession, path, logger, manga, dlopt):
   ''' This function would download every page of every gallery(manga object). Before download, 
       it would even detect the previous download status and determin whether the gallery should 
       be download. Then, it would analyze the index pages of the gallery and retrive the pages' urls  
       needing to download the images. The information would be submitted to ThreadPoolExecutor's 
       objects. Then an executor would initiate the download threads concurrently. After all the 
       downloads completed, this function would store a preview image as a bytes object into the manga 
       object. After that, it would zip the download folder if user required. Lastly, it would also 
       store all the crucial error messages (if have) to the manga object parparing to return.'''
   pageContentDict = {}  # Contains the current manga pages' information to download
   errorPageList = [] # Contains the error download pages in previous download
                      # Only useful while the program has detected some broken download history.
   htmlContentList = [] # Contain ONE gallery index page
   dlErrorDict = {}  # Contains all the critical error message while downloading images
   threadPoolList = [] # Contains all the future objects for ThreadPoolExecutor to exectue.
   q = Queue()  # Contin the report of download errors 
#    manga.dlErrorDict = None  # Default variable of this attribute
   if manga.category == None:
      dlPath = path
   else:
      dlPath = '{0}{1}/'.format(path, manga.category)
    
   logger.info('Begin to download gallery {0}'.format(manga.url))
   stop = dloptgenerate.Sleep(config.rest)
   tempErrDict ={manga.url: {}}
#    resultDict = {'previewImageDict': {},
#                  'dlErrorDict': {}}
   analysisPreviousDLResultDict = analysisPreviousDL(dlPath=dlPath, url=manga.url, title=manga.title, 
                                                     mangaData=manga.mangaData, logger=logger)
   # Analysis the previous download history.
   htmlContentList = accesstoehentai(method='get', 
                                     mangasession=mangasession, 
                                     stop=stop, 
                                     urls=[manga.url],
                                     logger=logger
                                    )

#    print (htmlContentList[0])
   pageContentDict = datafilter.mangadlfilter(htmlContentList[0])
   # Then retrive the first page of the gallery index.
   if analysisPreviousDLResultDict['downloadIssue'] == True and analysisPreviousDLResultDict['completeDownload'] == False:
      errorPageDict = datafilter.mangadlfilter(analysisPreviousDLResultDict['errorPageStr'])
      if errorPageDict.get('contentPages'):
         for ePD in errorPageDict['contentPages']:
            errorPageList.append(ePD[0])
#    threadCounter = 0

   if pageContentDict.get('contentPages') and analysisPreviousDLResultDict['completeDownload'] == False:
      executor = ThreadPoolExecutor(max_workers=config.dlThreadLimit)
      logger.info("Begin to retrive image pages' urls from index pages, this would take a while.")
      # Create a ThreadPoolExecutor object to handle the image download threads.
      logger.info("Begin to retrive images' urls from index pages, this would take a while.")
      while pageContentDict['nextPage']:
         
         for mP in pageContentDict['contentPages']:
            if errorPageList:
               if mP[0] not in errorPageList:
                  logger.info('Page {0} has been downloaded in previous process, continue.'.format(mP[0]))
                  continue
            threadPoolList.append(executor.submit(fn=mangadownload,
                                                  url=mP[1],
                                                  mangasession=mangasession,
                                                  filename=mP[0],
                                                  path='{0}{1}/'.format(dlPath, manga.title),
                                                  logger=logger,
                                                  q=q))
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
               logger.exception('Raise a crucial exception during analysis {0}'.format(manga.url))
               dlErrorDict.update({'nextPageError': {manga.url: str(error)}})
               break
         else:
            pageContentDict['nextPage'] = ''
      # Then run the download threads in the pool and retrive the error report(if have)
      logger.info("Retrive process completed.")
      for t in threadPoolList:
         t.result()
      executor.shutdown()
      logger.info('{0} download completed.'.format(manga.url))
      while not q.empty():
         temp = q.get()
         tempErrDict[manga.url].update(temp)
      if tempErrDict[manga.url].get('Download error'):
         logger.error("Encountered a critical error while downloading images of {0}. ".format(manga.url) +
                      "An error log would be deployed; and the zip function would be disabled.")
         dlErrorDict.update(tempErrDict[manga.url])
      # Retrive the first page as the preview page, store it as an attribute in the manga object in the memory. 
      fileList = [f for f in os.listdir('{0}{1}/'.format(dlPath, manga.title)) if os.path.isfile(os.path.join('{0}{1}/'.format(dlPath, manga.title), f))] 
      # print (fileList)
      if '.mangaLog' in fileList:
         fileList.remove('.mangaLog')
      # print (fileList)
      fileList.sort()
      previewImage = fileList[0]
      # previewImageFormat = (previewImage.split('.'))[-1]
      # if previewImageFormat == 'JPG' or previewImageFormat == 'jpg':
      #    previewImageFormat = 'jpeg'
      try:
         bio = BytesIO()
         with open('{0}{1}/{2}'.format(dlPath, manga.title, previewImage), 'rb') as fo:
            imageByte = fo.read()
         bio = BytesIO(imageByte) 
         bio.name = manga.title
         manga.previewImage = bio
      except Exception as error:
         logger.exception('Raise {0} while opening preview image of {1}'.format(error, manga.url))
         dlErrorDict.update({'openFileError': {manga.url: str(error)}})
         manga.previewImage = None
      if analysisPreviousDLResultDict['completeDownload'] == False:
         with open(('{0}{1}/.mangaLog'.format(dlPath, manga.title)), 'w') as fo:
            json.dump({manga.url: manga.mangaData}, fo)
      # Zip the download folder if user required. If the dlErrorDict not empty indicating the 
      # download process has encountered the critical errors, the zip function would be disabled. 
      if (dlopt.Zip == True and analysisPreviousDLResultDict['completeDownload'] == False 
      and (len(dlErrorDict) == 0 or dlopt.forceZip == True)):
         zipErrorDict = zipmangadir(url=manga.url, path=dlPath, title=manga.title,
                                    removeDir=dlopt.removeDir, logger=logger)
         if zipErrorDict:
            dlErrorDict.update(zipErrorDict)
      if dlErrorDict:
         manga.dlErrorDict = dlErrorDict
         with open(('{0}{1}/errorLog'.format(dlPath, manga.title)), 'w') as fo:
            json.dump(dlErrorDict, fo)
      elif os.path.isfile('{0}{1}/errorLog'.format(dlPath, manga.title)):
         os.remove('{0}{1}/errorLog'.format(dlPath, manga.title))
   elif  analysisPreviousDLResultDict['completeDownload'] == True:
      logger.info('{0} had been completed in previous process.'.format(manga.url))
      manga.previewImage =(analysisPreviousDLResultDict['previewImageDict'][manga.title])
   else:
      manga.previewImage = None
      logger.warning('{0} does not contain any page, maybe deleted'.format(manga.url))
      manga.dlErrorDict.update({'galleryError': usermessage.galleryError})
#    print (resultDict['dlErrorDict'])
#    print (dlopt.forceZip)
#    print (dlopt.Zip)
#    print (path)

   return manga

def mangadownload(url, mangasession, filename, path, logger, q):
   ''' This function would retrive the image url from the webpage and then download it on 
       the disk. To handle the network fluctuation, including the empty htmlpage, the error
       network status codes and the corrupted images, it exploits a combination of for loop 
       and the try-except syntax to overcome them. Users could determin how many times the 
       program should retry downloading the image before abort. If the retry times reach 
       the limitation, it would generate a report and put it into a queue object. After all
       download completed, the mangadownloadctl function would retrive this report. '''
   logger.info('Page {0} download start'.format(filename))
   errorMessage = {url: {}}
   downloadUrlsDict = {'imageUrl': "", 'reloadUrl': ''}
   err = 0
   for err in range(config.timeoutRetry):
      try:   
         if err != 0 and downloadUrlsDict['reloadUrl']:
            mangaUrl = downloadUrlsDict['reloadUrl']
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
               for chunk in previewimage.iter_content(chunk_size=4096):
                  handle.write(chunk)
            if int(previewimage.headers['Content-Length']) != int(os.path.getsize("{0}{1}.{2}".format(path, filename, contentTypeList[1]))):
               os.remove("{0}{1}.{2}".format(path, filename, contentTypeList[1]))
               raise jpegEOIError('Image is corrupted')
         else:
            raise downloadStatusCodeError('Download status code error.')
      except Exception as error:
         logger.exception('{0} has encounter an error {1}'.format(url, error))
         errorMessage[url].update({err: str(error)})
         err += 1
         time.sleep(0.5)
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
   del htmlContentList
#    threadQ.task_done()


def analysisPreviousDL(dlPath, url, title, mangaData, logger):
   '''Determin the previous download status from folder or zip files. If the program detects a successful
      previous download (no errorLog file in the folder), it would retrive the first image as an bytes 
      object and return it to mangadownloadctl function as previous image. It would also analysis previous 
      download's errorLog file to determin which page should be download again. However, if the previous 
      file has been archived, it would assume that the previous download was successful and retrive the
      first page as the preview page.'''
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

def zipmangadir(url, path, title, removeDir, logger):
   '''This function would archive the download folder as zip file and then 
      delete the original folder(if user required). If encounters any exception,
      it would return the exception to mangadownloadctl function.'''
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
   return zipErrorDict

def accesstoehentai(method, mangasession, stop, logger, urls=None):
   ''' Most of the parts of the  program would use this function to retrive the htmlpage, and galleries'
       information by using e-h's API. It provides two methods to access e-hentai/exhentai. The GET 
       methot would return the htmlpage; and the POST method would extract the gallery ID and gallery
       key to generate the json payload sending exploit e-h's API then return the API's result. It 
       also exploits a combination of for loop and try-except syntax to deal with the unstable network.'''
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


