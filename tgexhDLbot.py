#!/usr/bin/python3

import logging
import json
import os
import time
import datetime
from multiprocessing import Process
from threading import Thread
from telegram.ext import Updater 
from telegram.ext import MessageHandler 
from telegram.ext import Filters 
from telegram.ext import ConversationHandler
from tgbotconvhandler import ehdownloader
from tgbotconvhandler import urlanalysisdirect
from DLmodules import config
from DLmodules import usermessage
from DLmodules import regx
from DLmodules import magnet
from queue import Queue
import platform
import re
from functools import wraps



def state(bot, update, user_data, chat_data):
   '''The major function of this bot. It would receive user's message and initiate 
      a download thread/process.'''
   user_data.update({'chat_id': update.message.chat_id,
                     'actualusername': str(update.message.from_user.username),
                     'userMessage': update.message.text})
   logger.info("Actual username is %s.", str(update.message.from_user.username))
   outDict = urlanalysisdirect(user_data=user_data, logger=logger)
   if outDict['identified'] == True and outDict['ehUrl'] == True:
      messageDict = {"messageContent": outDict["outputTextList"],
                     'messageCate': 'message',
                    }
      channelmessage(bot=bot, 
                     messageDict=messageDict, 
                     chat_id=update.message.chat_id
                    )
      Ttime = time.asctime(time.localtime()) 
      threadName = '{0}.{1}'.format(str(update.message.from_user.username), Ttime)
      if platform.system() == 'Windows':   # Windows does not allow the daemon thread to initiate a 
                                           # new child process. 
         t = Thread(target=downloadfunc, 
                    name=threadName, 
                    kwargs={'bot':bot,
                            'urlResultList': outDict['urlResultList'], 
                            'logger': logger,
                            "chat_id": update.message.chat_id,
                            }
                    )  
         threadQ.put(t)      
      else:
         t = Process(target=downloadfunc, 
                     name=threadName, 
                     kwargs={'bot':bot,
                             'urlResultList': outDict['urlResultList'], 
                             'logger': logger,
                             "chat_id": update.message.chat_id,
                            })
         threadQ.put(t)  
   elif (outDict['identified'] == True and 
        outDict['magnetLink'] == True and 
        (config.hasAria2 == True or config.hasQbittorrent == True)):
      messageDict = {"messageContent": outDict["outputTextList"],
                     'messageCate': 'message',
                    }
      channelmessage(bot=bot, 
                     messageDict=messageDict, 
                     chat_id=update.message.chat_id
                    )
      Ttime = time.asctime(time.localtime()) 
      threadName = '{0}.{1}'.format(str(update.message.from_user.username), Ttime)  
      if platform.system() == 'Windows':   # Windows does not allow the daemon thread to initiate a 
                                           # new child process.
         t = Thread(target=magnetLinkDownload, 
                    name=threadName,
                    kwargs={'bot':bot, 
                            'urlResultList': outDict['urlResultList'],
                            'logger': logger,
                            'chat_id': update.message.chat_id})
         threadQ.put(t)
      else:
         t = Process(target=magnetLinkDownload, 
                     name=threadName, 
                     kwargs={'bot':bot,
                             'urlResultList': outDict['urlResultList'], 
                             'logger': logger,
                             "chat_id": update.message.chat_id,
                            })
         threadQ.put(t)  
   else:
      messageDict = {"messageContent": outDict["outputTextList"],
                     'messageCate': 'message',
                    }
      channelmessage(bot=bot, 
                     messageDict=messageDict, 
                     chat_id=update.message.chat_id
                    )
   return ConversationHandler.END
      
def threadContainor(threadQ, threadLimit=1):
   '''A simple thread/process containor daemon thread to limit the amount of the download 
      process thus prevent e-hentai bans user's IP. The t = threadQ.get() would block this 
      loop until it receive a user request sent by the bot's user interaction function.'''
   # Put any threads to this function and it would run separately.
   # But please remember put the threadQ obj into the functions in those threads to use threadQ.task_done().
   # Or the program would stock.
   threadCounter = 0
   while True:
      t = threadQ.get()
      t.start()
      threadCounter += 1
      if threadCounter == threadLimit:  # This condition limit the amount of threads running simultaneously.
         t.join() 
         threadCounter = 0

def magnetLinkDownload(bot, urlResultList, logger, chat_id):
   '''This function exploits xmlprc to send command to aria2c. However, it seems that after sending 
      the commend, it would trigger a strange bug in python-telegram-bot. To prevent this situation, 
      the bot would not send any message currently.'''
   logger.info('magnetLinkDownload initiated.')
   if config.hasQbittorrent == True:
      torrentList = magnet.torrentDownloadqQbt(magnetLinkList=urlResultList,
                                               logger=logger)
   else:
      torrentList = magnet.torrentDownloadAria2c(magnetLinkList=urlResultList,
                                                 logger=logger)
   for torrent in torrentList:
      messageList = []
      messageList.append(usermessage.magnetResultMessage.format(torrent.hash))
      tempFileList = []
      if torrent.error:
         messageList.append(torrent.error)
      for file in torrent.fileList:
         tempFileList.append(file)
         if len(tempFileList) >=4:
            messageList.append(tempFileList)
            tempFileList = []

      if tempFileList:
         messageList.append(tempFileList)
      messageDict = {"messageContent": messageList,
                     'messageCate': 'message',
                     }
      channelmessage(bot=bot, 
                     messageDict=messageDict, 
                     chat_id=chat_id
                     )


def downloadfunc(bot, urlResultList, logger, chat_id):
   ''' The bot's major function would call this download and result 
       sending function to deal with user's requests.'''
   mangaObjList = ehdownloader(urlResultList=urlResultList, logger=logger)
   logger.info('Begin to send download result(s).')
   for manga in mangaObjList:
      if manga.title != 'errorStoreMangaObj':
         if manga.previewImage:
            messageDict = {"messageContent": [manga.previewImage],
                           'messageCate': 'photo',
                          }
            channelmessage(bot=bot, 
                           messageDict=messageDict, 
                           chat_id=chat_id
                           )        
         messageDict = {"messageContent": [manga.title],
                        'messageCate': 'message',
                       }
         channelmessage(bot=bot, 
                        messageDict=messageDict, 
                        chat_id=chat_id
                        )   
      else:
         pass    
      if manga.dlErrorDict:
        #  print (manga.dlErrorDict)
         for error in manga.dlErrorDict:
            messageDict = {"messageContent": [error,  manga.dlErrorDict[error]],
                           'messageCate': 'message',
                          }
            channelmessage(bot=bot, 
                           messageDict=messageDict, 
                           chat_id=chat_id
                          )             
   logger.info('All results has been sent.')

def retryDocorator(func, retry=config.messageTimeOutRetry):
   '''This simple retry decorator provides a try-except looping to the channelmessage function to
      overcome network fluctuation.'''
   @wraps(func)
   def wrapperFunction(*args, **kwargs):
    #   print ('outer func')
      err = 0 
      for err in range(retry):
         try:
            func(*args, **kwargs)
            break
         except Exception as error:
           err += 1
           logger.warning(str(error))
      else:
         logger.warning('Retry limitation reached')
         
      return None
   return wrapperFunction

@retryDocorator
def channelmessage(bot, messageDict, chat_id):
   ''' All the functions containing user interaction would use this function to send messand 
       to user.'''
#    print ('inner func')
   messageContent = messageDict["messageContent"]
   for mC in messageContent:
      if messageDict['messageCate'] == 'photo':
         mC.seek(0)
         bot.send_photo(chat_id=chat_id, photo=mC)
      else:
        #  print ('send message')
        #  print (mC)
        #  print (chat_id)
         bot.send_message(chat_id=chat_id, text=mC)
   return None

def cancel(bot, update, user_data, chat_data):  
   '''Bot's cancel function, useless.'''
   update.message.reply_text(text=usermessage.UserCancel) 
   logger.info("User %s has canceled the process.", str(update.message.from_user.username))
   user_data.clear()
   chat_data.clear()
   logger.info("The user_data and chat_data of user %s has cleared", str(update.message.from_user.username))
   return ConversationHandler.END

def error(bot, update, error):
   '''Bot's error collecting function, may also be useless. '''
   logger.warning('Update "%s" caused error "%s"', update, error)

 
def main():
   '''The bot's initiation sequence.'''
   if config.proxy:
      if config.proxy[0].find('@') != -1:
         proxyPattern = re.compile(regx.authProxyPattern)
         proxyMatch = proxyPattern.search(config.proxy[0])
         proxyAddress = '{0}://{1}:{2}'.format(proxyMatch.group(1), proxyMatch.group(4), proxyMatch.group(5))
         proxyUsername = proxyMatch.group(2)
         proxyPassword = proxyMatch.group(3)
         updater = Updater(token=config.token, request_kwargs={'proxy_url': proxyAddress, 
                                                               'urllib3_proxy_kwargs': 
                                                               {'username': proxyUsername,
                                                                'password': proxyPassword}})
      else:
         updater = Updater(token=config.token, request_kwargs={'proxy_url': config.proxy[0]})
   else:   
      updater = Updater(token=config.token)
   dp = updater.dispatcher
   messageHandler =  MessageHandler(Filters.text, state, pass_user_data=True, pass_chat_data=True)
   dp.add_handler(messageHandler)
   dp.add_error_handler(error)
   updater.start_polling(poll_interval=1.0, timeout=1.0)
   tc = Thread(target=threadContainor, 
               name='tc', 
               kwargs={'threadQ': threadQ},
               daemon=True)    # This daemon thread would keep observering whether
                               # the bot generates a download request and put it into the threadQ.
                               # Ones detects a request and there is no other ongoing requests,
                               # this daemon thread would start the request thread.
   tc.start()
   logger.info('Download thread containor initiated.')
   logger.info('Bot started.')
   updater.idle()


logging.basicConfig(format='%(asctime)s - %(module)s.%(funcName)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)
logging.getLogger('requests').setLevel(logging.CRITICAL) # Rule out the requests' common loggings since
                                                         # they are useless. 
threadQ = Queue()  # This queue object put the download function into the thread containor 
                   # Using this thread containor wound also limits the download function thread
                   # to prevent e-h to ban IP.

(STATE) = range(1)

if __name__ == '__main__':
   main()