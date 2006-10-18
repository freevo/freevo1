import re
import config

__all__ = ["Feed"]

class Feed:    
    def __init__(self, inputSource):
        "Feed"
        self.title="None"
        self.description="None"
        self.items=[]
        self.parseFeed(inputSource)      
         
    class Item:
        "Feed Item"
        title="None"
        url="None"
        date="None"
        description="None"
        type="None"
            
    def parseFeed(self, feed):
        headerPattern = re.compile('<channel>.*?</channel>',re.DOTALL)
        itemPattern = re.compile('<item>.*?</item>',re.DOTALL)
        titlePattern = re.compile('<title>.*?</title>',re.DOTALL)
        descriptionPattern = re.compile('<description>.*?</description>',re.DOTALL)
        urlPattern = re.compile('<enclosure url=".*?/>',re.DOTALL)
        btPattern = re.compile('<link>.*?</link>',re.DOTALL)
        datePattern = re.compile('<pubDate>.*?</pubDate>',re.DOTALL)

        def removeExcessSpaces(string):
            string = re.sub('^\s+', '', string)
            return re.sub('\s+',' ',string)
        def removeTags(string):
            string = removeExcessSpaces(string)
            return re.sub('<\S+?>', '', string)
        def removeUrlTag(string):
            string = removeExcessSpaces(string)
            return re.split('"',string)[1]
        def removeDesTag(string):
            string = re.sub('<img src=.*?>','',string) 
            string = re.sub('&lt.*?&gt;','',string)
            string = re.sub('&amp;','and',string)
            string = removeTags(string)
            return re.sub('<a href="\S+">','',string)
        def getType(string):
            for type in config.AUDIO_SUFFIX:
                if string in type:
                   return "audio"
            return "video"

        #PROCESS HEADER
        header = headerPattern.search(feed)
        if header:
           header = header.group()
           title = titlePattern.search(header)
           if title:
              self.title = removeTags(title.group())
           description = descriptionPattern.search(header)
           if description:
              self.description = removeDesTag(description.group())
           #PROCESS ALL ITEMS
           itemList = itemPattern.findall(feed)
           for item in itemList:
               newItem = self.Item()
               title = titlePattern.search(item)
               if title:
                  newItem.title = removeTags(title.group())
               description = descriptionPattern.search(item)
               if description:
                  newItem.description = removeDesTag(description.group())
               url = urlPattern.search(item)
               if url:
                  newItem.url = removeUrlTag(url.group())
                  newItem.type = getType(re.split('"',re.split("\.",newItem.url)[-1])[0])
                  if re.search("^$",newItem.title) or re.search("None",newItem.title):
                     newItem.title = newItem.url
               else:
                  url = btPattern.search(item)
                  if url:
                     newItem.url = removeTags(url.group())
               date = datePattern.search(item)
               if date:
                  newItem.date = removeTags(date.group())
               self.items.append(newItem)
