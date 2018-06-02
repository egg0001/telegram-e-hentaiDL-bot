import requests
from requests import Request, Session
from . import datafilter
from . import usermessage


 
 

def ehlogin(dloptDict, mangasession, logger):
   ehloginDict = {'loginError': False,
                  'canEXH': False,
                  'isEH': False,
                  'isEXH': False,
                  'mangasession': None
                 }
   payload = {"UserName": dloptDict['dlopt'].username,
              "PassWord": dloptDict['dlopt'].password,
              'returntype':'8',
               'CookieDate':'1',
               'b':'d',
               'bt':'pone',
             }

   loginurl = "https://forums.e-hentai.org/index.php?act=Login&CODE=01"
   loginres = mangasession.post(loginurl, data=payload)
   htmlcontent = loginres.text
   if htmlcontent.find("incorrect") != -1:
       ehloginDict.update({'loginError': True})
       dloptDict['errorMessage'].update({'loginError': usermessage.ehloginError})
       logger.info("Error username or password.")

   else:
      ehloginDict.update({'isEH': True})
      exhres = mangasession.get("https://exhentai.org/")
      isEXH = datafilter.exhtest(htmlContent=exhres.text)
      if isEXH == False:
         dloptDict['errorMessage'].update({'loginError': usermessage.exhError})
         logger.info("This username could not use exhentai")
      ehloginDict.update({'isEXH': isEXH, 'mangasession': mangasession, 'errorMessage': dloptDict['errorMessage']})
   return ehloginDict