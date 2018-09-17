#!/usr/bin/python3

#-----------------bot session-------------------
UserCancel = 'You have cancel the process.'

welcomeMessage = ('User identity conformed, please input gallery urls ' +
                  'and use space to separate them'
                 )

denyMessage = 'You are not the admin of this bot, conversation end.'

urlComform = ('Received {0} gallery url(s). \nNow begin to download the content. ' +
              'Once the download completed, you will receive a report.'
             )

magnetLinkConform = ('Received a magnetLink. Now send it to bittorrent client')

magnetResultMessage = ('Torrent {0} has been added bittorrent client.')

urlNotFound = 'Could not find any gallery url, please check and re-input.'

gidError = 'Encountered an error gid: {0}'
#------------------magnet download session---------------------

emptyFileListError = ('Could not retrive file list for this link, maybe still '+
                      'downloading meta data.')

#-----------------dloptgenerate session---------------------

userCookiesFormError = 'userCookies form error, please check the config file.'

#-----------------managgessiongen session-------------------

usercookiesEXHError = 'This cookies could not access EXH' 

#-----------------ehlogin session---------------------------

ehloginError = 'username or password error, please check.'

exhError = 'This username could not access exhentai.'

#------------------download session------------------------

galleryError = 'Gallery does not contain any page, maybe deleted.'
