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
from tgbotconvhandler import messageanalyze
from tgbotconvhandler import ehdownloader
from DLmodules import config
from DLmodules import usermessage



def start(bot, update, user_data, chat_data):
   user_data.clear()
   chat_data.clear()
   user_data.update({"actualusername": str(update.message.from_user.username),
                     "chat_id": update.message.chat_id}
                   )
   logger.info("Actual username is %s.", str(update.message.from_user.username))
#    update.message.reply_text(text="Welcome to Nakazawa Bookstore, please show your vip card.")
   chat_data.update({'state': 'verify'})
   outputDict = messageanalyze(
                               user_data=user_data, 
                               chat_data=chat_data,
                               logger=logger
                              )
   user_data.update(outputDict["outputUser_data"])
   chat_data.update(outputDict["outputChat_data"])
   messageDict = {"messageContent": outputDict["outputTextList"],
                  'messageCate': 'message',
                  }
   channelmessage(bot=bot, 
                  messageDict=messageDict, 
                  chat_id=update.message.chat_id,
                  logger=logger
                 )
   if outputDict["outputChat_data"]['state'] != 'END':
      state = STATE
   else:
      state = ConversationHandler.END
   return state

def state(bot, update, user_data, chat_data):
   inputStr = update.message.text
   user_data.update({'chat_id': update.message.chat_id})
   outputDict = messageanalyze(inputStr=inputStr, 
                               user_data=user_data, 
                               chat_data=chat_data,
                               logger=logger
                              )
   user_data.update(outputDict["outputUser_data"])
   chat_data.update(outputDict["outputChat_data"])
   if outputDict["outputChat_data"]['state'] != 'END':
      state =STATE
      messageDict = {"messageContent": outputDict["outputTextList"],
                     'messageCate': 'message',
                    }
      channelmessage(bot=bot, 
                     messageDict=messageDict, 
                     chat_id=update.message.chat_id,
                     logger=logger
                    )
   else:
      state = ConversationHandler.END
      messageDict = {"messageContent": outputDict["outputTextList"],
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
                         'urlResultList': outputDict['urlResultList'], 
                         'logger': logger,
                         "chat_id": update.message.chat_id})
      t.start()

   return state

def downloadfunc(bot, urlResultList, logger, chat_id):
   outDict = ehdownloader(urlResultList=urlResultList, logger=logger)
   logger.info('Began to send download result(s).')
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
            messageDict = {"messageContent": [error, '{0}: {1}'.format(result, outDict['resultDict'][result]['dlErrorDict'][error])],
                           'messageCate': 'message',
                          }
            channelmessage(bot=bot, 
                           messageDict=messageDict, 
                           chat_id=chat_id,
                           logger=logger
                          )             
   logger.info('All results has been sent.')


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
   conv_handler = ConversationHandler(
                  entry_points=[CommandHandler('start', start, pass_user_data=True, pass_chat_data=True)],
                  states={STATE: [MessageHandler(Filters.text, state, pass_user_data=True, pass_chat_data=True)]
                  },
                  fallbacks=[CommandHandler('cancel', cancel, pass_user_data=True, pass_chat_data=True)],
   )
   dp.add_handler(conv_handler)
   dp.add_error_handler(error)
   updater.start_polling(poll_interval=1.0, timeout=1.0)
   updater.idle()

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)
logging.getLogger('requests').setLevel(logging.CRITICAL)
(STATE) = range(1)

if __name__ == '__main__':
   main()