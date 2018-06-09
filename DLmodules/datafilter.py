#!/usr/bin/python3
import re

def exhtest(htmlContent):

   pattern = re.compile(r"Front Page")
   usefulCookies = False
   if bool(re.search(pattern, htmlContent)):
      usefulCookies = True
#    print (usefulCookies)
   return usefulCookies


def genmangainfoapi(resultJsonDict, exh):
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
                #        "imageurlSmall": imageurlSmall,
                #        "imageForm": imageForm
                      }})
#    print (mangaInfo)
   return mangaInfo


def mangadlfilter(htmlContent):
   pageContentDict = {'nextPage': '',
                      'contentPages': []}
   mangaPagepattern = re.compile(r'''https://[a-z\.\-]+\.org\/s\/[a-z0-9]+\/[a-z0-9]+\-([0-9]+)''')
   nextPagePattern = re.compile(r'''<a href="(https://[a-z\.\-]+\.org\/g/[a-z0-9]+/[a-z0-9]+/\?p\=[0-9]+)" onclick="return false">&gt;</a>''')
   mangaPages = mangaPagepattern.finditer(htmlContent)
   nextPage = nextPagePattern.search(htmlContent)
   try:
      pageContentDict['nextPage'] = nextPage.group(1)
   except AttributeError:
      # print ("No next page.")
      pageContentDict['nextPage'] = -1
   for mP in mangaPages:
      pageContentDict['contentPages'].append((mP.group(1), mP.group()))
#    print (pageContentDict)
   return pageContentDict


      