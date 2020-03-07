#!/usr/bin/python3

from telegram.ext import Updater 
from telegram.ext import MessageHandler 
from telegram.ext import Filters 
from telegram.ext import ConversationHandler

class telegramMessage():

   def __init__(self, bot, chat_id, messageContent, messageType, fileDir='', fileName=''):
      self.messageContent = messageContent
      self.messageType = messageType
      self.bot = bot
      self.chat_id = chat_id
      self.fileDir=fileDir
      self.fileName=fileName

   def photoSend(self):
      for mC in self.messageContent:
         mC.seek(0)
         self.bot.send_photo(chat_id=self.chat_id, photo=mC)
      return None

   def messageSend(self):
      # if self.messageType == 'photo':
      #    for mC in self.messageContent:

      #       mC.seek(0)
      #       self.bot.send_photo(chat_id=self.chat_id, photo=mC)
      # else:
        #  print ('send message')
        #  print (mC)
        #  print (chat_id)
      for mC in self.messageContent:  
         self.bot.send_message(chat_id=self.chat_id, text=mC)
      return None

   def fileSend(self):
      # print('send files')
      try:
         delay = config.delay
      except:
         delay = 600
      with open('{0}{1}'.format(self.fileDir, self.fileName), 'rb') as file:
         self.bot.send_document(chat_id=self.chat_id, document=file, timeout=delay)
      return None


   