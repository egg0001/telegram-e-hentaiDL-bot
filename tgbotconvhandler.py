#!/usr/bin/python3
import json
import logging
import re
from ast import literal_eval
from io import BytesIO
from DLmodules import usermessage
from DLmodules import dloptgenerate
from DLmodules import config
from ehentaiDL import Spidercontrolasfunc
from threading import Lock


# def verify(user_data, chat_data, logger, inputStr=None):
#    outputTextList = []
#    if user_data["actualusername"] == config.telegramUsername:
#       logger.info('User {0} identity conformed'.format(user_data["actualusername"]))
#       outputTextList.append(usermessage.welcomeMessage)
#       chat_data.update({'state': 'urlanalysis'})
#    else: 
#       logger.info('User {0} identity denied'.format(user_data["actualusername"]))
#       outputTextList.append(usermessage.denyMessage)
#       chat_data.update({'state': 'END'})
#    outputDict = {"outputTextList": outputTextList,
#                  "outputChat_data": chat_data, 
#                  "outputUser_data": user_data
#                 }
#    return outputDict

# def urlanalysis(user_data, chat_data, logger, inputStr=None):
#    outputTextList = []
#    urlResultList = []
#    urlPattern = re.compile(r'''https://[exhentai\-]+\.org/g/\w+/\w+/''')
#    urlResult = urlPattern.finditer(inputStr)
#    for uR in urlResult:
#       urlResultList.append(uR.group())
#    if urlResult:
#       chat_data.update({'state': 'END'})
#       logger.info('Collected {0} urls, send the result to actual download function'.format(len(urlResultList)))
#       outputTextList.append(usermessage.urlComform.format(len(urlResultList)))
#    else:
#       chat_data.update({'state': 'urlanalysis'})
#       logger.info('Could not find any urls, the inputmessage is ({0})'.format(inputStr))
#       outputTextList.append(usermessage.urlNotFound)
#    outputDict = {"outputTextList": outputTextList,
#                  "outputChat_data": chat_data, 
#                  "outputUser_data": user_data,
#                  "urlResultList": urlResultList
#                 }
#    return outputDict


def urlanalysisdirect(user_data, logger, chat_data=None):
   
   outDict = {'identified': False, 'urlComfirm': False, 'outputTextList': [], 'urlResultList': []}
   if user_data['actualusername'] == config.telegramUsername:
      outDict['identified'] = True
      urlPattern = re.compile(r'''https://[exhentai\-]+\.org/g/\w+/\w+/''')
      urlResult = urlPattern.finditer(user_data['userMessage'])
      for uR in urlResult:
         outDict['urlResultList'].append(uR.group())
      if outDict['urlResultList']:
         outDict['urlComfirm'] = True
         logger.info('Collected {0} url(s), send the result to actual download function'.format(len(outDict['urlResultList'])))
         outDict['outputTextList'].append(usermessage.urlComform.format(len(outDict['urlResultList'])))
      else:
         logger.info('Could not find any urls, the inputmessage is ({0})'.format(user_data['userMessage']))
         outDict['outputTextList'].append(usermessage.urlNotFound)
   else:
      logger.info('User {0} identity denied'.format(user_data["actualusername"]))
      outDict['outputTextList'].append(usermessage.denyMessage)


   return outDict


def ehdownloader(urlResultList, logger):
   tLock = Lock()
   tLock.acquire()
   logger.info('Download function initiated.')
   dloptDict = dloptgenerate.dloptgenerate(urls=urlResultList, logger=logger)
   outDict = Spidercontrolasfunc(dloptDict=dloptDict, logger=logger)
   logger.info("Download completed.")
   tLock.release()
   return outDict


# def messageanalyze(inputStr=None, user_data=None, chat_data=None, logger=None):
#    messageFuncDict = {'verify': verify,
#                       'urlanalysis': urlanalysis
#                      }
#    outputDict = messageFuncDict[chat_data['state']](inputStr=inputStr, 
#                                                     user_data=user_data, 
#                                                     chat_data=chat_data,
#                                                     logger=logger
#                                                    )
#    return outputDict