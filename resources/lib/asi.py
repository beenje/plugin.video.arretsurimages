# -*- coding: utf-8 -*-
import sys
import os
import urllib
import asi_scraper
import xbmc
import xbmcplugin
import xbmcgui
from videoDownloader import Download

# Main URLs and sort method list
URLEMISSION = 'http://www.arretsurimages.net/toutes-les-emissions.php'
URLALLEMISSION = 'http://www.arretsurimages.net/emissions.php'
SORTMETHOD = ['date_publication', 'nb_vues', 'nb_comments']
QUALITY = ['stream_h264_hq_url', 'stream_h264_url']

ASI = asi_scraper.ArretSurImages()

__addon__ = sys.modules['__main__'].__addon__

def getLS(i):
    return __addon__.getLocalizedString(i).encode('utf-8')

class updateArgs:

    def __init__(self, *args, **kwargs):
        for key, value in kwargs.iteritems():
            if value == 'None':
                kwargs[key] = None
            else:
                kwargs[key] = urllib.unquote_plus(kwargs[key])
        self.__dict__.update(kwargs)


class UI:

    def __init__(self):
        self.main = Main(checkMode = False)
        xbmcplugin.setContent(int(sys.argv[1]), 'movies')

    def endofdirectory(self):
        # If name is next or previous, then the script arrived here from a navItem, and won't add to the hierarchy
        if self.main.args.name in [getLS(30020), getLS(30021)]:
            dontAddToHierarchy = True
        else:
            dontAddToHierarchy = False
        # Let xbmc know the script is done adding items to the list.
        xbmcplugin.endOfDirectory(handle = int(sys.argv[1]), updateListing = dontAddToHierarchy)

    def addItem(self, info, itemType='folder'):
        # Defaults in dict. Use 'None' instead of None so it is compatible for quote_plus in parseArgs
        info.setdefault('url', 'None')
        info.setdefault('Thumb', 'None')
        info.setdefault('Icon', info['Thumb'])
        # Create params for xbmcplugin module
        u = sys.argv[0]+\
            '?url='+urllib.quote_plus(info['url'])+\
            '&mode='+urllib.quote_plus(info['mode'])+\
            '&name='+urllib.quote_plus(info['Title'])+\
            '&icon='+urllib.quote_plus(info['Thumb'])
        # Create list item
        li=xbmcgui.ListItem(label = info['Title'], iconImage = info['Icon'], thumbnailImage = info['Thumb'])
        li.setInfo(type='Video', infoLabels=info)
        # For videos, replace context menu
        if itemType == 'video':
            # Let xbmc know this can be played
            isFolder = False
            li.setProperty("IsPlayable", "true")
        elif itemType == 'program':
            # 'program' is a folder including video files
            # Program can be downloaded -> add option to contextmenu
            isFolder = True
            contextmenu = [(getLS(30180), 'XBMC.RunPlugin(%s?download=%s)' % (sys.argv[0], urllib.quote_plus(info['url'])))]
            li.addContextMenuItems(contextmenu, replaceItems=True)
        else:
            # itemType == 'folder'
            isFolder = True
        # Add item to list
        ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=u, listitem=li, isFolder=isFolder)

    def playVideo(self, quality):
        """Play the video"""
        video = ASI.getVideoDetails(self.main.args.url, quality)
        li=xbmcgui.ListItem(video['Title'],
                            iconImage = self.main.args.icon,
                            thumbnailImage = self.main.args.icon,
                            path = video['url'])
        li.setInfo(type='Video', infoLabels=video)
        xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, li)

    def navItems(self, navItems, mode):
        """Display navigation items"""
        if navItems['next']:
            self.addItem({'Title': getLS(30020), 'url':navItems['next'], 'mode':mode})
        if navItems['previous']:
            self.addItem({'Title': getLS(30021), 'url':navItems['previous'], 'mode':mode})

    def showCategories(self):
        """Display the categories"""
        self.addItem({'Title':'Toutes les émissions', 'mode':'toutesLesEmissions'})
        self.addItem({'Title':'@rrêt sur images', 'mode':'arretSurImages', 'Plot':getLS(30031)})
        self.addItem({'Title':'Ligne j@une', 'mode':'ligneJaune', 'Plot':getLS(30032)})
        self.addItem({'Title':'D@ns le texte', 'mode':'dansLeTexte', 'Plot':getLS(30033)})
        self.endofdirectory()

    def programs(self, defaultUrl=None):
        """Display all programs from self.main.args.url or defaultUrl"""
        newMode = 'parts'
        if self.main.args.url:
            programs = ASI.Programs(self.main.args.url)
        else:
            programs = ASI.Programs(defaultUrl)
        # Add nav items to the list
        self.navItems(programs.navItems, self.main.args.mode)
        # Add programs to the list
        for program in programs.getPrograms():
            program['mode'] = newMode
            self.addItem(program, 'program')
        # End the list
        self.endofdirectory()

    def programParts(self):
        """Display all parts of the selected program"""
        newMode = 'playVideo'
        # Add program parts to the list
        for part in ASI.getProgramParts(self.main.args.url, self.main.args.name, self.main.args.icon):
            part['mode'] = newMode
            self.addItem(part, 'video')
        # End the list
        self.endofdirectory()


class Main:

    def __init__(self, checkMode = True):
        print sys.argv
        self.parseArgs()
        self.getSettings()
        # Check username and password have been set
        if self.settings['username'] and self.settings['password']:
            if checkMode:
                self.checkMode()
        else:
            xbmcgui.Dialog().ok(getLS(30050), getLS(30051), getLS(30052))

    def parseArgs(self):
        # call updateArgs() with our formatted argv to create the self.args object
        if (sys.argv[2]):
            exec "self.args = updateArgs(%s')" % (sys.argv[2][1:].replace('&', "',").replace('=', "='"))
        else:
            # updateArgs will turn the 'None' into None.
            # Don't simply define it as None because unquote_plus in updateArgs will throw an exception.
            self.args = updateArgs(mode = 'None', url = 'None', name = 'None')

    def getSettings(self):
        self.settings = dict()
        self.settings['username'] = __addon__.getSetting('username')
        self.settings['password'] = __addon__.getSetting('password')
        self.settings['sortMethod'] = int(__addon__.getSetting('sortMethod'))
        self.settings['downloadMode'] = __addon__.getSetting('downloadMode')
        self.settings['downloadPath'] = __addon__.getSetting('downloadPath')
        self.quality = QUALITY[int(__addon__.getSetting('quality'))]

    def downloadVideo(self, url):
        if self.settings['downloadMode'] == 'true':
            downloadPath = xbmcgui.Dialog().browse(3, getLS(30090), 'video')
        else:
            downloadPath = self.settings['downloadPath']
        if downloadPath:
            video = ASI.getVideoDownloadLink(url)
            Download(video['Title'], video['url'], downloadPath)

    def checkMode(self):
        mode = self.args.mode
        if mode is None:
            # Try to login only if username isn't already logged in
            # (we don't have to login everytime as we use a cookie)
            # We only need to check that when starting the plugin
            if ASI.isLoggedIn(self.settings['username']) or ASI.login(self.settings['username'], self.settings['password']):
                UI().showCategories()
            else:
                xbmcgui.Dialog().ok(getLS(30050), getLS(30053))
        elif mode == 'toutesLesEmissions':
            url = URLALLEMISSION + '?orderby=' + SORTMETHOD[self.settings['sortMethod']]  
            UI().programs(url)
        elif mode == 'arretSurImages':
            url = URLEMISSION + '?id=1' + '&orderby=' + SORTMETHOD[self.settings['sortMethod']]  
            UI().programs(url)
        elif mode == 'ligneJaune':
            url = URLEMISSION + '?id=2' + '&orderby=' + SORTMETHOD[self.settings['sortMethod']]
            UI().programs(url)
        elif mode == 'dansLeTexte':
            url = URLEMISSION + '?id=3' + '&orderby=' + SORTMETHOD[self.settings['sortMethod']]
            UI().programs(url)
        elif mode == 'parts':
            UI().programParts()
        elif mode == 'playVideo':
            UI().playVideo(self.quality)

