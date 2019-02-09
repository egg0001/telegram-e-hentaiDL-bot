#!/usr/bin/python3

from telegram.ext import Updater 
from telegram.ext import MessageHandler 
from telegram.ext import Filters 
from telegram.ext import ConversationHandler

class telegramMessage():

   def __init__(self, bot, chat_id, messageContent, messageType):
      self.messageContent = messageContent
      self.messageType = messageType
      self.bot = bot
      self.chat_id = chat_id

   def messageSend(self):
      if self.messageType == 'photo':
         for mC in self.messageContent:

            mC.seek(0)
            self.bot.send_photo(chat_id=self.chat_id, photo=mC)
      else:
        #  print ('send message')
        #  print (mC)
        #  print (chat_id)
         for mC in self.messageContent:  
            self.bot.send_message(chat_id=self.chat_id, text=mC)
      return None

   