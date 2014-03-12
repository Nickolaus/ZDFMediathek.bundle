import re, datetime
from string import ascii_uppercase
# +++++ ZDF Mediathek Plugin for Plex +++++
#
# Version 2.0
#
# Version 1.1
# (c) 2011 by Robert Kleinschmager (http://www.kleinschmager.net)
# Initial version based on code by Sebastian Majstorovic and Marcel Dischinger (http://www.digital-tea.net)
# 
# Licensed under the GPL, Version 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#  
#    http://www.gnu.org/licenses/gpl-3.0-standalone.html
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Artwork (folder 'Resources'): (c) ZDF

# TODO
# - Live TV support

####################################################################################################

THUMBNAIL = [
  '946x532',
  '644x363'
]

SENDUNGENAZ = [
  ['ABC', 'A', 'C'],
  ['DEF', 'D', 'F'],
  ['GHI', 'G', 'I'],
  ['JKL', 'J', 'L'],
  ['MNO', 'M', 'O'],
  ['PQRS', 'P', 'S'],
  ['TUV', 'T', 'V'],
  ['WXYZ', 'W', 'Z'],
  ['0-9', '0-9', '0-9']
]

ZDF_RUBRIKEN         = 'http://www.zdf.de/ZDFmediathek/xmlservice/web/rubriken'
ZDF_THEMEN           = 'http://www.zdf.de/ZDFmediathek/xmlservice/web/themen'
ZDF_MEISTGESEHEN     = 'http://www.zdf.de/ZDFmediathek/xmlservice/web/meistGesehen?id=_GLOBAL&maxLength=10&offset=%s'
ZDF_SENDUNGEN_AZ     = 'http://www.zdf.de/ZDFmediathek/xmlservice/web/sendungenAbisZ?characterRangeStart=%s&characterRangeEnd=%s&detailLevel=2'
ZDF_SENDUNG_VERPASST = 'http://www.zdf.de/ZDFmediathek/xmlservice/web/sendungVerpasst?enddate=%s&maxLength=50&startdate=%s&offset=%s'
ZDF_SENDUNG          = 'http://www.zdf.de/ZDFmediathek/xmlservice/web/aktuellste?id=%s&maxLength=25&offset=%s'
ZDF_BEITRAG          = 'http://www.zdf.de/ZDFmediathek/beitrag/%s/%s'

NAME = 'ZDF Mediathek'

ART = 'art-default.jpg'
ICON = 'icon-default.png'

BASE_URL = "http://www.zdf.de"


####################################################################################################

def Start():
    Plugin.AddViewGroup("InfoList", viewMode="InfoList", mediaType="items")
    Plugin.AddViewGroup("List", viewMode="List", mediaType="items")

    ObjectContainer.art        = R(ART)
    ObjectContainer.title1     = NAME
    ObjectContainer.view_group = "InfoList"
    DirectoryItem.thumb        = R(ICON)

    HTTP.CacheTime = CACHE_1HOUR

@handler('/video/zdfmediathek', NAME, art = ART, thumb = ICON)
def VideoMainMenu():
    oc = ObjectContainer(view_group="List")
    
    oc.add(DirectoryObject(key=Callback(SendungVerpasst, name="Sendung Verpasst"), title="Sendung Verpasst"))
    oc.add(DirectoryObject(key=Callback(SendungenAZ, name="Sendungen A-Z"), title="Sendungen A-Z"))
    oc.add(DirectoryObject(key=Callback(RubrikenThemen, name="Rubriken"), title="Rubriken"))
    oc.add(DirectoryObject(key=Callback(RubrikenThemen, name="Themen"), title="Themen"))
    oc.add(DirectoryObject(key=Callback(Sendung, title="Meist Gesehen", assetId="MEISTGESEHEN"), title="Meist Gesehen"))
    
    return oc

@route('/video/zdfmediathek/sendungverpasst')
def SendungVerpasst(name):
  oc = ObjectContainer(title2=name, view_group="List")
  day = datetime.date.today()
  for n in range(7):
    oc.add(DirectoryObject(key=Callback(Sendung, title=day.strftime("%d.%m.%y"), assetId="VERPASST_"+day.strftime("%d%m%y")), title=day.strftime("%d.%m.%y")))
    day = day + datetime.timedelta(-1)
  return oc

####################################################################################################
@route('/video/zdfmediathek/rubrikenthemen')
def RubrikenThemen(name):
  oc = ObjectContainer(title2=name, view_group="List")
  if(name == 'Rubriken'):
    content = XML.ElementFromURL(ZDF_RUBRIKEN, cacheTime=CACHE_1HOUR)
  elif(name == 'Themen'):
    content = XML.ElementFromURL(ZDF_THEMEN, cacheTime=CACHE_1HOUR)
  else:
    raise Ex.MediaNotAvailable
  teasers = content.xpath('//teaserlist/teasers/teaser')
  for teaser in teasers:
      type = teaser.xpath('./type')[0].text
      if(type != 'rubrik' and type != 'topthema' and type != 'thema'):
        Log('RubrikenThemen: Unsupported type ' + type)
        continue
      
      for res in THUMBNAIL:
        thumb = teaser.xpath('./teaserimages/teaserimage[@key="%s"]' % (res))[0].text
        if thumb.find('fallback') == -1:
          break
      
      title = teaser.xpath('./information/title')[0].text
      summary = teaser.xpath('./information/detail')[0].text
      assetId = teaser.xpath('./details/assetId')[0].text
      
      tagline = None
      if(type == 'topthema'):
        title = 'Topthema - %s' % (title)
        tagline = 'Topthema'
      oc.add(DirectoryObject(key=Callback(Sendung, title=title, assetId=assetId), title=title, thumb=thumb, summary=summary, tagline=tagline))
  return oc
	
####################################################################################################
@route('/video/zdfmediathek/sendungenaz')
def SendungenAZ(name):
    oc = ObjectContainer(title2=name, view_group="List")
    
    # A to Z
    for page in SENDUNGENAZ:
        oc.add(DirectoryObject(key=Callback(SendungenAZList, char=page[0]), title=page[0]))
    
    return oc

####################################################################################################
@route('/video/zdfmediathek/sendungenaz/{char}')
def SendungenAZList(char):
  oc = ObjectContainer(title2=char, view_group="List")
  for page in SENDUNGENAZ:
    if page[0] != char:
      continue
    content = XML.ElementFromURL(ZDF_SENDUNGEN_AZ % (page[1], page[2]), cacheTime=CACHE_1HOUR)
    teasers = content.xpath('//teaserlist/teasers/teaser')
    for teaser in teasers:
      for res in THUMBNAIL:
        thumb = teaser.xpath('./teaserimages/teaserimage[@key="%s"]' % (res))[0].text
        if thumb.find('fallback') == -1:
          break
      
      title = teaser.xpath('./information/title')[0].text
      summary = teaser.xpath('./information/detail')[0].text
      assetId = teaser.xpath('./details/assetId')[0].text
      oc.add(DirectoryObject(key=Callback(Sendung, title=title, assetId=assetId), title=title, thumb=thumb, summary=summary))
  
  if len(oc) == 0:
    return MessageContainer("Empty", "There aren't any speakers whose name starts with " + char)

  return oc

@route('/video/zdfmediathek/sendung/{assetId}', allow_sync = True)
def Sendung(title, assetId, offset=0):
  oc = ObjectContainer(title2=title.decode(encoding="utf-8", errors="ignore"), view_group="InfoList")
  if(assetId == 'MEISTGESEHEN'):
    maxLength = 10
    content = XML.ElementFromURL(ZDF_MEISTGESEHEN % (offset), cacheTime=CACHE_1HOUR)
  elif(assetId.find('VERPASST_') != -1):
    maxLength = 50
    d = re.search('VERPASST_([0-9]{1,6})', assetId)
    if(d == None):
      return oc
    day = d.group(1)
    content = XML.ElementFromURL(ZDF_SENDUNG_VERPASST % (day, day, offset), cacheTime=CACHE_1HOUR)
  else:
    maxLength = 25
    content = XML.ElementFromURL(ZDF_SENDUNG % (str(assetId), offset), cacheTime=CACHE_1HOUR)
  more = content.xpath('//teaserlist/additionalTeaser')[0].text == 'true'
  teasers = content.xpath('//teaserlist/teasers/teaser')
  for teaser in teasers:
      type = teaser.xpath('./type')[0].text
      for res in THUMBNAIL:
        thumb = teaser.xpath('./teaserimages/teaserimage[@key="%s"]' % (res))[0].text
        if thumb.find('fallback') == -1:
          break
      
      ttitle = teaser.xpath('./information/title')[0].text
      tsummary = teaser.xpath('./information/detail')[0].text
      tassetId = teaser.xpath('./details/assetId')[0].text
      if(type == 'video'):
        show = teaser.xpath('./details/originChannelTitle')[0].text
        if(show != title):
          ttitle = '%s - %s' % (show, ttitle)
        date = Datetime.ParseDate(teaser.xpath('./details/airtime')[0].text).date()
        duration = CalculateDuration(teaser.xpath('./details/length')[0].text)
        oc.add(VideoClipObject(url=ZDF_BEITRAG % ('video', tassetId), title=ttitle, originally_available_at=date, summary=tsummary, thumb=thumb, duration=duration))
      elif(type == 'thema' or type == 'sendung'):
        oc.add(DirectoryObject(key=Callback(Sendung, title=ttitle, assetId=tassetId), title=ttitle, thumb=thumb, summary=tsummary))
      elif(type == 'imageseries_informativ'):
        oc.add(PhotoAlbumObject(url=ZDF_BEITRAG % ('bilderserie', tassetId), title=ttitle, summary=tsummary, thumb=thumb))
  #Somehow the webservice does not support an offset over 100	
  if more and int(offset) + maxLength <= 100:
    oc.add(NextPageObject(key=Callback(Sendung, title=title, assetId=assetId, offset=str(int(offset)+maxLength)), title=str("Weitere Beiträge").decode('utf-8', 'strict'), summary=None, thumb="more.png"))
  return oc

####################################################################################################
def CalculateDuration(timecode):
  milliseconds = 0
  hours        = 0
  minutes      = 0
  seconds      = 0
  d = re.search('([0-9]{1,2}) min', timecode)
  if(None != d):
    minutes = int( d.group(1) )
  else:
    d = re.search('([0-9]{1,2}):([0-9]{1,2}):([0-9]{1,2}).([0-9]{1,3})', timecode)
    if(None != d):
      hours = int ( d.group(1) )
      minutes = int ( d.group(2) )
      seconds = int ( d.group(3) )
      milliseconds = int ( d.group(4) )
  milliseconds += hours * 60 * 60 * 1000
  milliseconds += minutes * 60 * 1000
  milliseconds += seconds * 1000
  return milliseconds