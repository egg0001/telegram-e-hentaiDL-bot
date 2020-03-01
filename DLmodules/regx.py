#!/usr/bin/python3



#---------tgexhDLbot.py--------------------

authProxyPattern = (r'''(\w+)\:\/\/(.*)\:(.*)\@(.+)\:(\d+)''')

#---------tgbotconvhandler.py--------------

botUrlPattern = (r'''https://[exhentai\-]+\.org/g/\w+/\w+/''')
botMagnetPattern = ('''magnet:''')

#---------datafilter.py--------------------

exhTestPattern = (r"Front")

mangaPagePattern = (r'''https://[a-z\.\-]+\.org\/s\/[a-z0-9]+\/[a-z0-9]+\-([0-9]+)''')

nextPagePattern = (r'''<a href="(https://[a-z\.\-]+\.org\/g/[a-z0-9]+/[a-z0-9]+/\?p\=[0-9]+)" onclick="return false">&gt;</a>''')

imagePattern = ('''<img id="img" src="(https*://.+)" style="''')

reloadPattern = (r'''id\=\"loadfail\" onclick\=\"return nl\(\'([0-9\-]+)\'\)\"''')

#--------download.py------------------------

tokenPattern = (r'''https://.+\.org/g/([0-9a-z]+)\/([0-9a-z]+)\/''')