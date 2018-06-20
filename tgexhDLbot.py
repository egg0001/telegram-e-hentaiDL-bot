#!/usr/bin/python3

import logging
import json
import os
import time
import datetime
from threading import Thread
from ast import literal_eval
from telegram.ext import Updater
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler 
from telegram.ext import Filters
from telegram.ext import ConversationHandler
# from tgbotconvhandler import messageanalyze
from tgbotconvhandler import ehdownloader
from tgbotconvhandler import urlanalysisdirect
from DLmodules import config
from DLmodules import usermessage
from queue import Queue



# def start(bot, update, user_data, chat_data):
#    user_data.clear()
#    chat_data.clear()
#    user_data.update({"actualusername": str(update.message.from_user.username),
#                      "chat_id": update.message.chat_id}
#                    )
#    logger.info("Actual username is %s.", str(update.message.from_user.username))
# #    update.message.reply_text(text="Welcome to Nakazawa Bookstore, please show your vip card.")
#    chat_data.update({'state': 'verify'})
#    outputDict = messageanalyze(
#                                user_data=user_data, 
#                                chat_data=chat_data,
#                                logger=logger
#                               )
#    user_data.update(outputDict["outputUser_data"])
#    chat_data.update(outputDict["outputChat_data"])
#    messageDict = {"messageContent": outputDict["outputTextList"],
#                   'messageCate': 'message',
#                   }
#    channelmessage(bot=bot, 
#                   messageDict=messageDict, 
#                   chat_id=update.message.chat_id,
#                   logger=logger
#                  )
#    if outputDict["outputChat_data"]['state'] != 'END':
#       state = STATE
#    else:
#       state = ConversationHandler.END
#    return state

# def state(bot, update, user_data, chat_data):
#    inputStr = update.message.text
#    user_data.update({'chat_id': update.message.chat_id})
#    outputDict = messageanalyze(inputStr=inputStr, 
#                                user_data=user_data, 
#                                chat_data=chat_data,
#                                logger=logger
#                               )
#    user_data.update(outputDict["outputUser_data"])
#    chat_data.update(outputDict["outputChat_data"])
#    if outputDict["outputChat_data"]['state'] != 'END':
#       state =STATE
#       messageDict = {"messageContent": outputDict["outputTextList"],
#                      'messageCate': 'message',
#                     }
#       channelmessage(bot=bot, 
#                      messageDict=messageDict, 
#                      chat_id=update.message.chat_id,
#                      logger=logger
#                     )
#    else:
#       state = ConversationHandler.END
#       messageDict = {"messageContent": outputDict["outputTextList"],
#                      'messageCate': 'message',
#                     }
#       channelmessage(bot=bot, 
#                      messageDict=messageDict, 
#                      chat_id=update.message.chat_id,
#                      logger=logger
#                     )
#       Ttime = time.asctime(time.localtime()) 
#       treadName = '{0}.{1}'.format(str(update.message.from_user.username), Ttime)
#       t = Thread(target=downloadfunc, 
#                  name=treadName, 
#                  kwargs={'bot':bot,
#                          'urlResultList': outputDict['urlResultList'], 
#                          'logger': logger,
#                          "chat_id": update.message.chat_id,
#                          'threadQ': threadQ})
#       threadQ.put(t)

#    return state


def state(bot, update, user_data, chat_data):
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
      t = Thread(target=downloadfunc, 
                 name=treadName, 
                 kwargs={'bot':bot,
                         'urlResultList': outDict['urlResultList'], 
                         'logger': logger,
                         "chat_id": update.message.chat_id,
                         'threadQ': threadQ})
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
      
def thread_containor(threadQ):
   # Put any threads to this function and it would run separately.
   # But please remember put the threadQ obj into the functions in those threads to use threadQ.task_done().
   # Or the program would stock.
   threadCounter = 0
   while True:
      t = threadQ.get()
      t.start()
      threadCounter += 1
      if threadCounter == 1:  # This condition limit the amount of threads running simultaneously.
         t.join() 
         threadCounter = 0
      t.join()     

def downloadfunc(bot, urlResultList, logger, chat_id, threadQ):
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
   for result in outDict['resultDict']:
      if outDict['resultDict'][result]['previewImageDict']: 
         for image in outDict['resultDict'][result]['previewImageDict']:
            messageDict = {"messageContent": [outDict['resultDict'][result]['previewImageDict'][image]],
                           'messageCate': 'photo',
                          }
            channelmessage(bot=bot, 
                           messageDict=messageDict, 
                           chat_id=chat_id,
                           logger=logger
                          )        
            messageDict = {"messageContent": [image],
                           'messageCate': 'message',
                          }
            channelmessage(bot=bot, 
                           messageDict=messageDict, 
                           chat_id=chat_id,
                           logger=logger
                          )       
      if outDict['resultDict'][result]['dlErrorDict']:
         for error in outDict['resultDict'][result]['dlErrorDict']:
            messageDict = {"messageContent": [error,  outDict['resultDict'][result]['dlErrorDict'][error]],
                           'messageCate': 'message',
                          }
            channelmessage(bot=bot, 
                           messageDict=messageDict, 
                           chat_id=chat_id,
                           logger=logger
                          )             
   logger.info('All results has been sent.')
   threadQ.task_done()


def channelmessage(bot, messageDict, chat_id, logger):
#    logger.info("Began to send sth...")
#    print (messageDict)
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
   update.message.reply_text(text=usermessage.UserCancel) 
   logger.info("User %s has canceled the process.", str(update.message.from_user.username))
   user_data.clear()
   chat_data.clear()
   logger.info("The user_data and chat_data of user %s has cleared", str(update.message.from_user.username))
   return ConversationHandler.END

def error(bot, update, error):
   logger.warning('Update "%s" caused error "%s"', update, error)


def main(): 
   if config.proxy:
      updater = Updater(token=config.token, request_kwargs={'proxy_url': config.proxy[0]})
   else:   
      updater = Updater(token=config.token)
   dp = updater.dispatcher
#    conv_handler = ConversationHandler(
#                   entry_points=[CommandHandler('start', start, pass_user_data=True, pass_chat_data=True)],
#                   states={STATE: [MessageHandler(Filters.text, state, pass_user_data=True, pass_chat_data=True)]
#                   },
#                   fallbacks=[CommandHandler('cancel', cancel, pass_user_data=True, pass_chat_data=True)],
#    )

   messageHandler =  MessageHandler(Filters.text, state, pass_user_data=True, pass_chat_data=True)

#    dp.add_handler(conv_handler)
   dp.add_handler(messageHandler)
   dp.add_error_handler(error)
   updater.start_polling(poll_interval=1.0, timeout=1.0)
   tc = Thread(target=thread_containor, 
               name='tc', 
               kwargs={'threadQ': threadQ},
               daemon=True)
   tc.start()
   logger.info('Download thread containor initiated.')
   logger.info('Bot started.')
   updater.idle()
   

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)
logging.getLogger('requests').setLevel(logging.CRITICAL)
threadQ = Queue()  # This queue object put the download function into the thread containor 
                   # Using this thread containor wound also limits the download function thread
                   # to prevent e-h to ban IP.
(STATE) = range(1)

if __name__ == '__main__':
   main()