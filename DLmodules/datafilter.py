#!/usr/bin/python3
import re
from . import regx 

def exhtest(htmlContent):
   '''Detect whether user's cookies allow to access exhentai by searching
      the "Front page" keyword.''' 
   pattern = re.compile(r"Front Page")
   usefulCookies = False
   if bool(re.search(pattern, htmlContent)):
      usefulCookies = True
#    print (usefulCookies)
   return usefulCookies


def genmangainfoapi(resultJsonDict, exh):
   '''Transform the raw galleries' information from API result to a more easy to handle form.'''
   mangaInfo = {}
   resultDict = {}
   for gmd in resultJsonDict:
      male_tags = []
      female_tags = []
      artist = []
      group = []
      character = []
      parody = []
      misc_tags = []
      lang = []
      entitle = []
      jptitle = []
      length = []
      category = []
#       imageurlSmall = ""
#       imageForm = ""
      if exh == False:
         galleryUrl = 'https://e-hentai.org/g/{0}/{1}/'.format(gmd['gid'], gmd['token'])
      else:
         galleryUrl = 'https://exhentai.org/g/{0}/{1}/'.format(gmd['gid'], gmd['token'])
      if gmd.get('title'):
         entitle.append(gmd['title'])
      if gmd.get('title_jpn'):
         jptitle.append(gmd['title_jpn'])
      if gmd.get('filecount'):
         length.append(gmd['filecount'])
      if gmd.get('category'):
         category.append(gmd['category'])
#       if gmd.get('thumb'):
#          imageurlSmall = gmd['thumb']
#          print (imageurlSmall)
#          imageMatch = re.search(r'''(https://[a-z0-9\.]+\.org\/[a-z0-9]+\/[a-z0-9]+\/[a-z0-9_-]+)\.(\w{3,4})''', imageurlSmall)
#          imageForm = imageMatch.group(2)
      if gmd.get('tags'):
         for tag in gmd['tags']:
            parodyMatch = re.search(r'''parody:(.+)''', tag)
            femaleMatch = re.search(r'''female:(.+)''', tag)
            maleMatch = re.search(r'''male:(.+)''', tag)
            artistMatch = re.search(r'''artist:(.+)''', tag)
            groupMatch = re.search(r'''group:(.+)''', tag)
            characterMatch = re.search(r'''character:(.+)''', tag)
            languageMatch = re.search(r'''language:(.+)''', tag)
            if parodyMatch:
               parody.append(parodyMatch.group(1))
            elif femaleMatch:
               female_tags.append(femaleMatch.group(1))
            elif maleMatch:
               male_tags.append(maleMatch.group(1))
            elif artistMatch:
               artist.append(artistMatch.group(1))
            elif groupMatch:
               group.append(groupMatch.group(1))
            elif characterMatch:
               character.append(characterMatch.group(1))
            elif languageMatch:
               lang.append(languageMatch.group(1))
            else:
               misc_tags.append(tag)
      if lang:
         pass
      else:
         lang.append('Japanese')
      mangaInfo.update({galleryUrl:
                      {"entitle": entitle, 
                       "jptitle": jptitle, 
                       "artist": artist, 
                       "lang": lang, 
                       "length": length,
                       "female": female_tags,
                       "male": male_tags,
                       "misc":  misc_tags,
                       "group": group,
                       "parody": parody,
                       "character": character,
                       "category": category
                      }})
#    print (mangaInfo)
   return mangaInfo


def mangadlfilter(htmlContent, url=None):
   '''The mangadownloadctl function would exploit this function to retrive every page's url and 
      the url of next index page from the gallery's current index page. Moreover, while the the 
      gallery constains 'Content Warning' key words, it would generate the conform to view link
      as the next pages link'''
   pageContentDict = {'nextPage': '',
                      'contentPages': []}
   mangaPagePattern = re.compile(regx.mangaPagePattern)
   nextPagePattern = re.compile(regx.nextPagePattern)
   mangaPages = mangaPagePattern.finditer(htmlContent)
   nextPage = nextPagePattern.search(htmlContent)
   contentWarningPattern = re.search('Content Warning', htmlContent)
   try:
      pageContentDict['nextPage'] = nextPage.group(1)
   except AttributeError:
      # print ("No next page.")
      pageContentDict['nextPage'] = -1
   for mP in mangaPages:
      pageContentDict['contentPages'].append((mP.group(1), mP.group()))
#    print (pageContentDict)
   if (pageContentDict['contentPages'] == [] and pageContentDict['nextPage'] == -1
   and bool(contentWarningPattern) == True and url):
      pageContentDict['nextPage'] = "{0}?nw=session".format(url)
   return pageContentDict


def mangadlhtmlfilter(htmlContent, url):
   '''The mangadownload function would use this function to retrive the image file's url to
      download as well as the page reload botton's url to handle the error download exceptions. 
      Once the download raises an exception, the program would use this reload page url to access
      another hath server to download the image.'''
   downloadUrlsDict = {'imageUrl': "", 'reloadUrl': ''}
   imagePattern = re.compile(regx.imagePattern)
   matchUrls = imagePattern.search(htmlContent)
   reloadPattern = re.compile(regx.reloadPattern)
   reloadUrl = reloadPattern.search(htmlContent)
   if matchUrls:                     # This block still has some strange issues..... 
      downloadUrlsDict['imageUrl'] = matchUrls.group(1)
   if reloadUrl:
      downloadUrlsDict['reloadUrl'] = '{0}?nl={1}'.format(url, reloadUrl.group(1))
   return downloadUrlsDict

def error509Filter(error509Dict):
   '''This function would provide the error 509-image quota exceeded-detection for mangadownloadctl 
      function in download module. If this function detects error 509, it would break the for loop 
      and return True, else False.'''
   encounter509Error = False
   for url in error509Dict:
      for err in error509Dict[url]:
         if error509Dict[url][err].find('509') != -1:
           encounter509Error = True
           break
      if encounter509Error == True:
         break
   return encounter509Error
      