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
from queue import Queue
import platform


def state(bot, update, user_data, chat_data):
   '''The major function of this bot. It would receive user's message and initiate 
      a download thread/process.'''
   user_data.update({'chat_id': update.message.chat_id,
                     'actualusername': str(update.message.from_user.username),
                     'userMessage': update.message.text})
   logger.info("Actual username is %s.", str(update.message.from_user.username))
   outDict = urlanalysisdirect(user_data=user_data, logger=logger)
   if outDict['identified'] == True and outDict['urlComfirm'] == True:
      messageDict = {"messageContent": outDict["outputTextList"],
                     'messageCate': 'message',
                    }
      channelmessage(bot=bot, 
                     messageDict=messageDict, 
                     chat_id=update.message.chat_id,
                     logger=logger
                    )
      Ttime = time.asctime(time.localtime()) 
      treadName = '{0}.{1}'.format(str(update.message.from_user.username), Ttime)
      if platform.system() == 'Windows':   # Windows does not allow the daemon thread to initiate a 
                                           # new child process. 
         t = Thread(target=downloadfunc, 
                    name=treadName, 
                    kwargs={'bot':bot,
                            'urlResultList': outDict['urlResultList'], 
                            'logger': logger,
                            "chat_id": update.message.chat_id,
                            }
                    )  
         threadQ.put(t)      
      else:
         t = Process(target=downloadfunc, 
                     name=treadName, 
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
                     chat_id=update.message.chat_id,
                     logger=logger
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
      

def downloadfunc(bot, urlResultList, logger, chat_id):
   ''' The bot's major function would call this download and result 
       sending function to deal with user's requests.'''
   outDict = ehdownloader(urlResultList=urlResultList, logger=logger)
   logger.info('Begin to send download result(s).')
   if outDict.get('cookiesError'):
      messageDict = {"messageContent": [outDict['cookiesError']],
                     'messageCate': 'message',
                    }
      channelmessage(bot=bot, 
                     messageDict=messageDict, 
                     chat_id=chat_id,
                     logger=logger
                    )
   if outDict.get('gidError'): 
      gidErrorList = []
      for gE in outDict['gidError']:
         gidErrorList.append(usermessage.gidError.format(gE))
      messageDict = {"messageContent": gidErrorList,
                     'messageCate': 'message',
                    }
      channelmessage(bot=bot, 
                     messageDict=messageDict, 
                     chat_id=chat_id,
                     logger=logger
                    )
   for manga in outDict['resultObjList']:
      if manga.previewImage:

         messageDict = {"messageContent": [manga.previewImage],
                        'messageCate': 'photo',
                          }
         channelmessage(bot=bot, 
                        messageDict=messageDict, 
                        chat_id=chat_id,
                        logger=logger
                        )        
      messageDict = {"messageContent": [manga.title],
                     'messageCate': 'message',
                    }
      channelmessage(bot=bot, 
                     messageDict=messageDict, 
                     chat_id=chat_id,
                     logger=logger
                     )       
      if manga.dlErrorDict:
         for error in manga.dlErrorDict:
            messageDict = {"messageContent": [error,  manga.dlErrorDict[error]],
                           'messageCate': 'message',
                          }
            channelmessage(bot=bot, 
                           messageDict=messageDict, 
                           chat_id=chat_id,
                           logger=logger
                          )             
   logger.info('All results has been sent.')


def channelmessage(bot, messageDict, chat_id, logger):
   ''' All the functions containing user interaction would use this function to send messand to user.
       It has the basic error and retry ability. '''
   messageContent = messageDict["messageContent"]
   for mC in messageContent:
      err = 0
      for err in range(config.messageTimeOutRetry):
         try:
            if messageDict['messageCate'] == 'photo':
               mC.seek(0)
               bot.send_photo(chat_id=chat_id, photo=mC)
            else:
               bot.send_message(chat_id=chat_id, text=mC)
         except:
            err += 1
            time.sleep(1)
            logger.warning('Message timeout {0}'.format(err))
         else:

            time.sleep(0.5)
            err = 0
            break
      else:
         logger.warning('Message retry limitation reached')
         err = 0

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


logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)
logging.getLogger('requests').setLevel(logging.CRITICAL) # Rule out the requests' common loggings since
                                                         # they are useless. 
threadQ = Queue()  # This queue object put the download function into the thread containor 
                   # Using this thread containor wound also limits the download function thread
                   # to prevent e-h to ban IP.

(STATE) = range(1)

if __name__ == '__main__':
   main()