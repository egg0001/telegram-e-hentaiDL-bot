#!/usr/bin/python3
import json
import logging
import re
from ast import literal_eval
from io import BytesIO
from DLmodules import usermessage
from DLmodules import dloptgenerate
from DLmodules import config
from DLmodules import regx
from ehentaiDL import Spidercontrolasfunc

def urlanalysisdirect(user_data, logger, chat_data=None):
   ''' This function identifies the user's  identity and exploit regx to analyze user's 
       request (gallery(s)' urls) and pass the result to the bot's major function.'''
   
   outDict = {'identified': False, 'outputTextList': [], 'urlResultList': [], 'ehUrl': False, 'magnetLink': False}
   if user_data['actualusername'] == config.telegramUsername:
      outDict['identified'] = True
      urlPattern = re.compile(regx.botUrlPattern)
      urlResult = urlPattern.finditer(user_data['userMessage'])
      magnetResult = re.search(regx.botMagnetPattern, user_data['userMessage'])
      for uR in urlResult:
         outDict['urlResultList'].append(uR.group())
      if outDict['urlResultList']: 
         outDict['ehUrl'] = True
         logger.info('Collected {0} url(s), send the result to actual download function.'.format(len(outDict['urlResultList'])))
         outDict['outputTextList'].append(usermessage.urlComform.format(len(outDict['urlResultList'])))
      elif magnetResult:
         logger.info('Collected megnet link(s), send the result to actual download function.')
         linksList=user_data['userMessage'].split(regx.botMagnetPattern)
         for link in linksList:
            torrentHashRex = re.search(r'''btih:([a-zA-Z0-9]+)''', link)
            if torrentHashRex:
               link = regx.botMagnetPattern + link
               outDict['urlResultList'].append(link)

        #  outDict['urlResultList'].append(magnetResult.group())
         outDict['magnetLink'] = True
         outDict['outputTextList'].append(usermessage.magnetLinkConform)
      else:
         logger.info('Could not find any urls, the inputmessage is ({0})'.format(user_data['userMessage']))
         outDict['outputTextList'].append(usermessage.urlNotFound)
   else:
      logger.info('User {0} identity denied'.format(user_data["actualusername"]))
      outDict['outputTextList'].append(usermessage.denyMessage)
   return outDict


def ehdownloader(urlResultList, logger):
   ''' A simple function transports  the download relating variable to the actual download function.'''
   logger.info('Download function initiated.')
   dloptDict = dloptgenerate.dloptgenerate(urls=urlResultList, logger=logger) 
   # This dloptDict contains an object storing the download variable and the error messages 
   # while generating this object.
   mangaObjList = Spidercontrolasfunc(dloptDict=dloptDict, logger=logger)
   # This is the entry of the download control function.
   logger.info("Download completed.")
   return mangaObjList

