#!/usr/bin/python3

from qbittorrent import Client
from DLmodules import config, usermessage
import re
import time
from xmlrpc import client



class TorrentQbt():
   '''This class and its objects represent the magnet links using qbittorrent client.
      The addTorrentLink method means send the link to the client. The torrentStatus 
      method would retrive the files' info preparing to send to user.'''

   def __init__(self, link):
      self.link = link
      self.fileList = []
      self.hash = ''
      self.error = ''

   def addTorrentLink(self, qbt, logger):
      try:
         qbt.download_from_link(link=self.link, savepath=config.dlPath)
         torrentHashRex = re.search(r'''btih:([a-zA-Z0-9]+)''', self.link)
         self.hash = torrentHashRex.group(1)
      except Exception as error:
         logger.warning(str(error))
         self.error = str(error)

   def torrentStatus(self, qbt, logger):
      try:
         if self.hash:
            retryTimes = 0 
            for retryTimes in range(config.retriveRetry):
               time.sleep(config.retriveDelay)
               statusList = qbt.get_torrent_files(infohash=self.hash)
               if statusList:
                  break
               else:
                  retryTimes += 1
            if statusList:
               for fileInfo in statusList:
               # print (fileInfo)
                  self.fileList.append(fileInfo['name'])
            else:
               pass
            if self.fileList == []:
               self.error = usermessage.emptyFileListError
      except Exception as error:
         logger.warning(str(error))
         self.error = str(error)


class TorrentAria2c():
   '''This class and its objects represent the magnet links using aria2c client.
      The addTorrentLink method means send the link to the client. The torrentStatus 
      method would retrive the files' info preparing to send to user.'''
   def __init__(self, link):
      self.link = link
      self.gid = ''
      self.fileList = []
      self.hash = ""
      self.error = ''
   
   def addTorrentLink(self, aria2c, token, logger):
      try:
         self.gid = aria2c.aria2.addUri(token, [self.link], {'dir': config.dlPath})
         torrentHashRex = re.search(r'''btih:([a-zA-Z0-9]+)''', self.link)
         self.hash = torrentHashRex.group(1)
      except Exception as error:
         logger.warning(str(error))
         self.error = str(error)

   def torrentStatus(self, aria2c, token, logger):
      # torrentHashRex = re.search(r'''btih:([a-zA-Z0-9]+)''', self.link)
      try:
         if self.hash:
      #    self.hash = torrentHashRex.group(1)
            retryTimes = 0
            for retryTimes in range(config.retriveRetry):
               time.sleep(config.retriveDelay)
               statusList = aria2c.aria2.getFiles(token, self.gid)
               if statusList:
                  break
               else:
                  retryTimes += 1
            if statusList:
               for fileInfo in statusList:
                  self.fileList.append(fileInfo['path'])
            else: 
               pass
            if self.fileList == []:
               self.error = usermessage.emptyFileListError
      except Exception as error:
         logger.warning(str(error))
         self.error = str(error)



def torrentDownloadqQbt(magnetLinkList, logger):
   '''This function controls the process downloading a list of links. Firstly, it constructs
      a lot of torrent objects representing links. Then it exploits the download method in these
      objects to send the information to bt client. After that, it also exploits file list retrieve
      to get the files' information for users.'''
   logger.info('Trying to use qbittorrent to download.')
   qbt = Client(config.clientAddress)
   torrentList = []
   if config.user and config.password:
      qbt.login(username=config.user, password=config.password)
   else:
      qbt.login() 
   for link in magnetLinkList:
      torrent = TorrentQbt(link=link)
      torrent.addTorrentLink(qbt=qbt, logger=logger)
      torrentList.append(torrent)
   for torrent in torrentList:
      torrent.torrentStatus(qbt=qbt, logger=logger)
   logger.info('magnetLinkDownload completed.')
   return torrentList

def torrentDownloadAria2c(magnetLinkList, logger):
   '''Similar to torrentDownloadQbt'''
   logger.info('Trying to use aria2c to download.')
   torrentList = []
   s = client.ServerProxy(config.aria2Server)
   token = 'token:{0}'.format(config.aria2Token)
      # print(s.aria2.addUri(token, magnetLinkList))
      # resultStrList.append('Succeed')
   for link in magnetLinkList:
      torrent = TorrentAria2c(link=link)
      torrent.addTorrentLink(aria2c=s, token=token, logger=logger)
      torrentList.append(torrent)
   for torrent in torrentList:
      if torrent.error:
         pass
      else:
         torrent.torrentStatus(aria2c=s, token=token, logger=logger)

   logger.info('magnetLinkDownload completed.')
#    except Exception as error:
      # logger.warning('Encountered an error while communicating with aria2 - {0}'.format(str(error)))
      # resultStrList.append(str(error))
   return torrentList
