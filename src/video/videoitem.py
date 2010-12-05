# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Item for video objects
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
#
# Todo:
#
# -----------------------------------------------------------------------
# Freevo - A Home Theater PC framework
# Copyright (C) 2002 Krister Lagerstrom, et al.
# Please see the file freevo/Docs/CREDITS for a complete list of authors.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MER-
# CHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General
# Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#
# -----------------------------------------------------------------------


"""
Item for video objects.
"""

import os
import re
import md5
import time
import copy
from pprint import pformat

import config
import util
import rc
import menu
import configure
import plugin
import kaa.metadata as metadata
import dialog

from gui   import PopupBox, AlertBox, ConfirmBox
from item  import Item, FileInformation
from event import *
from skin.widgets import ScrollableTextScreen


class VideoItem(Item):
    """
    A class describing a video item.

    @ivar autovars: a list of variables.
    @ivar type: the item type, video for this item.
    @ivar variants: a list of audio variants.
    @ivar subitems: a list of files or tracks to play.
    @ivar current_subitem: the current video item.
    @ivar media_id: media id when the item is on removable media
    @ivar subtitle_file: file name of a file containing subtitles.
    @ivar audio_file: file name of a file containing audio.
    @ivar mplayer_options: additional options for mplayer.
    @ivar tv_show: if the item is a tv programme.
    @ivar video_width: width of the video.
    @ivar video_height: height of the video.
    @ivar selected_subtitle: current subtitle track.
    @ivar selected_audio: current audio track.
    @ivar elapsed: seconds that the item has played.
    @ivar possible_players: a list of possible players.
    @ivar player: current player.
    @ivar player_rating: rating of the current player.
    """

    def __init__(self, url, parent, info=None, parse=True):
        """
        Create an instance of a VideoItem

        @param url: the pysudo URL for the VideoItem
        @param parent: the parent of the VideoItem
        @param info: controls if additional information is found
        @type info: boolean
        @param parse: controls if the url is parsed
        @type parse: boolean
        """
        self.autovars = []
        Item.__init__(self, parent)
        self.type = 'video'

        self.variants          = []
        self.subitems          = []
        self.current_subitem   = None
        self.media_id          = ''

        self.subtitle_file     = {}
        self.audio_file        = {}

        self.mplayer_options   = ''
        self.tv_show           = False

        self.video_width       = 0
        self.video_height      = 0

        self.selected_subtitle = None
        self.selected_audio    = None
        self.elapsed           = 0

        self.possible_players  = []
        self.player        = None
        self.player_rating = 0

        # set the url (this influences the list of possible players!)
        self.set_url(url, info=parse)
        if info:
            self.info.set_variables(info)

        # deinterlacing and related things
        video_deinterlace = config.VIDEO_DEINTERLACE != None and config.VIDEO_DEINTERLACE or False
        self['deinterlace'] = video_deinterlace

        video_use_xvmc = config.VIDEO_USE_XVMC != None and config.VIDEO_USE_XVMC or False
        self['xvmc'] = video_use_xvmc

        video_field_dominance = config.VIDEO_FIELD_DOMINANCE != None and config.VIDEO_FIELD_DOMINANCE or False
        self['field-dominance'] = video_field_dominance

        # find image for tv show and build new title
        if config.VIDEO_SHOW_REGEXP_MATCH(self.name) and not self.network_play and config.VIDEO_SHOW_DATA_DIR:

            show_name = config.VIDEO_SHOW_REGEXP_SPLIT(self.name)
            if show_name[0] and show_name[1] and show_name[2] and show_name[3]:
                self.name = show_name[0] + u' ' + show_name[1] + u'x' + show_name[2] + u' - ' + show_name[3]
                image = util.getimage((config.VIDEO_SHOW_DATA_DIR + show_name[0].lower()))
                if self.filename and not image:
                    image = util.getimage(os.path.join(os.path.dirname(self.filename), show_name[0].lower()))

                if image:
                    self.image = image

                from video import tv_show_information
                if tv_show_information.has_key(show_name[0].lower()):
                    tvinfo = tv_show_information[show_name[0].lower()]
                    self.info.set_variables(tvinfo[1])
                    if not self.image:
                        self.image = tvinfo[0]
                    self.skin_fxd = tvinfo[3]
                    self.mplayer_options = tvinfo[2]

                self.tv_show       = True
                self.show_name     = show_name
                self.tv_show_name  = show_name[0]
                self.tv_show_ep    = show_name[3]

        # extra info in discset_information
        if parent and parent.media:
            fid = String(parent.media.id) + self.filename[len(os.path.join(parent.media.mountdir,'')):]
            from video import discset_information
            if discset_information.has_key(fid):
                self.mplayer_options = discset_information[fid]

        if config.VIDEO_DEINTERLACE and self.info['interlaced']:
            # force deinterlacing
            self['deinterlace'] = True
        else:
            self['deinterlace'] = False


    def __str__(self):
        """
        Create a string for a VideoItem instance.
        @returns: string representation
        """
        s = pformat(self, depth=2)
        return s


    def __repr__(self):
        """
        Create a raw string for a VideoItem instance.
        @returns: string representation
        """
        if hasattr(self, 'name'):
            s = '%s: %r' % (self.name, self.__class__)
        else:
            s = '%r' % (self.__class__)
        return s


    def set_url(self, url, info=True):
        """
        Sets a new url to the item. This functions also changes other
        attributes, like file name, mode, network_play and the list of possible
        players.

        B{WARNING}: This is called whenever self.url is set, therefore it is
        strictly forbidden to set self.url directly in this function, (infinite
        recursion!). Use self.__dict__['url'] instead!
        """
        Item.set_url(self, url, info)

        # additional types of urls
        if url.startswith('dvd://') or url.startswith('vcd://'):
            self.network_play = False
            self.mimetype = self.url[:self.url.find('://')].lower()
            if self.url.find('/VIDEO_TS/') > 0:
                # dvd on harddisc
                self.filename = self.url[5:self.url.rfind('/VIDEO_TS/')]
                self.info     = util.mediainfo.get(self.filename)
                self.files    = FileInformation()
                self.name     = self.info['title:filename']
                if not self.name:
                    self.name = util.getname(self.filename)
                self.files.append(self.filename)
            elif self.url.rfind('.iso') + 4 == self.url.rfind('/'):
                # iso
                self.filename = self.url[5:self.url.rfind('/')]
            else:
                self.filename = ''

        elif url.endswith('.iso') and self.info['mime'] == 'video/dvd':
            self.mimetype = 'dvd'
            self.mode     = 'dvd'
            self.__dict__['url'] = 'dvd' + self.url[4:] + '/'

        # cover image
        if not self.image or (self.parent and self.image == self.parent.image):
            image = vfs.getoverlay(self.filename + '.raw')
            if os.path.exists(image):
                self.image = image
                self.files.image = image

        # do a new player rating based on the new url
        self.rating()


    def rating(self):
        """
        Calculate a new player rating for this item.

        The decision which player to use for a VideoItem is based on this
        rating.  First each player plugins is asked for a rate, on how good it
        can play this VideoItem. There are three possible rates: good (=2),
        possible (=1) and unplayable(=0). This rate is then weighted by a
        factor of ten.  Next the user's choice of prefered players is checked.
        The user can define a rank list of players with the variable
        VIDEO_PREFERED_PLAYER in local_conf.py. The rank that is calculated
        from this config variable is then added to the current rate. Last but
        not least there is the possibility that for some reason the use of a
        special player is forced.  In that case a value of 100 is added to the
        rate.

        In the end a sorted list of possible_players is created. All players in
        this list have a rating for this special VideoItem of not less than 10.
        The first one is the default one, the others are offered to the user as
        choices in the "Alternate Player" menu.
        """
        # create a new player rating
        self.possible_players =[]
        self.player = None
        self.player_rating = 0
        # some debug info
        try:
            _debug_('rating: url=%r' % (self.url), 2)
            _debug_('rating: mode=%r' % (self.mode), 2)
            _debug_('rating: mimetype=%r' % (self.mimetype), 2)
            _debug_('rating: network_play=%r' % (self.network_play), 2)
        except Exception, e:
            print 'videoitem.py: %s' %e
        for p in plugin.getbyname(plugin.VIDEO_PLAYER, True):
            rating = p.rate(self) * 10
            if p.name in config.VIDEO_PREFERED_PLAYER:
                # do we have a rank list for all possible players?
                if type(config.VIDEO_PREFERED_PLAYER) in [list, tuple]:
                    # get the rank of this player
                    rank = config.VIDEO_PREFERED_PLAYER.index(p.name)
                    # lower index means higher rank, therefor more calculations
                    rank = len(config.VIDEO_PREFERED_PLAYER)-rank
                    # finally increade the rating
                    rating += rank
                else: # it is more simple if just one player is prefered
                    rating +=1
            if hasattr(self, 'force_player') and p.name == self.force_player:
                rating += 100
            if (rating, p) not in self.possible_players:
                self.possible_players += [(rating, p)]
        # just use players with a rating of at last 10
        self.possible_players = filter(lambda l: l[0] >= 10, self.possible_players)
        # sort the players in the order of the rating
        self.possible_players.sort(lambda l, o: -cmp(l[0], o[0]))
        if len(self.possible_players) > 0:
            # choose the best player as default player
            self.player_rating, self.player = self.possible_players[0]
        _debug_("rating: url=%r possible_players=%r" % (self.url, self.possible_players,), 2)


    def id(self):
        """
        This id should be the same when the item is rebuild later with the same
        information.

        @returns: a unique id of the item.
        """
        ret = self.url
        if self.subitems:
            for s in self.subitems:
                ret += s.id()
        if self.variants:
            for v in self.variants:
                ret += v.id()
        return ret


    def __getitem__(self, key):
        """
        Get the item's attribute.

        @returns: the specific attribute
        """
        if not self.info:
            return ''

        if key == 'geometry' and self.info['width'] and self.info['height']:
            return '%sx%s' % (self.info['width'], self.info['height'])

        if key == 'aspect':
            aspect = None
            if self.info['aspect']:
                aspect = str(self.info['aspect'])
                aspect[:aspect.find(' ')].replace('/', ':')
            else:
                if self.info['width'] and self.info['height']:
                    aspect = util.misc.human_aspect_ratio(self.info['width'], self.info['height'])

            if aspect:
                return aspect

        if key == 'mplayer_aspect':
            aspect = None
            if self.info['aspect']:
                aspect = str(self.info['aspect'])
                aspect[:aspect.find(' ')].replace('/', ':')
            else:
                if self.info['width'] and self.info['height']:
                    ratio = float(self.info['width']) / self.info['height']
                    aspect = "%f" % ratio

            if aspect:
                return aspect

        if key == 'rating':
            if self.info['rating']:
                return self.info['rating']
            else:
                return ''

        if key == 'runtime':
            if self.info['runtime']:
                if self.info['runtime'] != 'None':
                    return self.info['runtime']

            total = 0
            if self.subitems:
                for s in self.subitems:
                    length = 0
                    if s.info['length']:
                        length = s.info['length']
                    if not length and hasattr(s, 'length'):
                        length = s.length
                    if not length:
                        continue
                    try:
                        total += length
                    except TypeError:
                        _debug_('Invalid length: %r' % (length,))
                total = '%s min' % str(int(total) / 60)
            else:
                if self.info['length']:
                    total = self.info['length']
                elif hasattr(self, 'length'):
                    total = self.length

                try:
                    total = '%s min' % str(int(total) / 60)
                except ValueError:
                    try:
                        runtime = self.info['runtime']
                    except:
                        total = ''

            return total

        return Item.__getitem__(self, key)


    def sort(self, mode=None):
        """
        Sort the video items.

        @returns: the string how to sort this item
        """
        if mode == 'date' and self.mode == 'file' and os.path.isfile(self.filename):
            return u'%s%s' % (os.stat(self.filename).st_ctime, Unicode(self.filename))

        if self.name.find(u'The ') == 0:
            return self.name[4:]
        return self.name


    def actions(self):
        """
        Menu actions for a video item.

        @returns: a list of possible actions on this item.
        """
        if not self.possible_players:
            return []

        # DVD actions
        if self.url.startswith('dvd://') and self.url[-1] == '/':
            if self.player_rating >= 20:
                items = [
                    (self.play, _('Play DVD')),
                    (self.dvd_vcd_title_menu, _('DVD title list'))
                ]
            else:
                # this player is not able to deal with menus
                items = [
                    (self.dvd_vcd_title_menu, _('DVD title list')),
                    (self.play, _('Play default track'))
                ]

        # VCD actions
        elif self.url == 'vcd://':
            if self.player_rating >= 20:
                items = [
                    (self.play, _('Play VCD')),
                    (self.dvd_vcd_title_menu, _('VCD title list'))
                ]
            else:
                items = [
                    (self.dvd_vcd_title_menu, _('VCD title list')),
                    (self.play, _('Play default track'))
                ]

        # youtube
        elif self.url.startswith('youtube:'):
            popup=PopupBox('Resolving YouTube video URL....')
            popup.show()
            if hasattr(config,'YOUTUBE_USER'):
                cmdline='youtube-dl -g -u '+config.YOUTUBE_USER+' -p '+config.YOUTUBE_PASSWORD+' '
            else:
                cmdline='youtube-dl -g '
            pipe=os.popen(cmdline+self.url[8:])
            self.url=pipe.readline()
            pipe.close()
            popup.hide()
            items = [ (self.play, _('Play')) ]

        else:
            items = [ (self.play, _('Play')) ]

        items.append((self.show_details, _('Full description')))

        if self.network_play:
            items.append((self.play_max_cache, _('Play with maximum cache')))

        items += configure.get_items(self)

        if self.variants and len(self.variants) > 1:
            items = [ (self.show_variants, _('Show variants')) ] + items

        if self.mode == 'file' and not self.variants and (not self.image or not self.image.endswith('raw')):
            items.append((self.create_thumbnail, _('Create Thumbnail'), 'create_thumbnail'))

        return items


    def show_details(self, arg=None, menuw=None):
        """
        Show more details
        """
        ShowDetails(menuw, self)


    def show_variants(self, arg=None, menuw=None):
        """
        Show a list of variants in a menu
        """
        if not self.menuw:
            self.menuw = menuw
        m = menu.Menu(self.name, self.variants, reload_func=None, fxd_file=self.skin_fxd)
        m.item_types = 'video'
        self.menuw.pushmenu(m)


    def create_thumbnail(self, arg=None, menuw=None):
        """
        Create a thumbnail as image icon
        """
        import util.videothumb
        pop = PopupBox(text=_('Please wait....'))
        pop.show()

        util.videothumb.snapshot(self.filename)
        pop.destroy()
        menuw.delete_submenu()


    def play_max_cache(self, arg=None, menuw=None):
        """
        Play and use maximum cache with mplayer
        """
        self.play(menuw=menuw, arg='-cache 65536')


    def set_next_available_subitem(self):
        """
        Select the next available subitem. Loops on each subitem and checks if
        the needed media is really there.  If the media is there, sets
        self.current_subitem to the given subitem and returns True.

        If no media has been found, we set self.current_subitem to None.  If
        the search for the next available subitem did start from the beginning
        of the list, then we consider that no media at all was available for
        any subitem: we return False.  If the search for the next available subitem
        did not start from the beginning of the list, then we consider that at
        least one media had been found in the past: we return True.
        """
        if hasattr(self, 'conf_select_this_item'):
            # XXX bad hack, clean me up
            self.current_subitem = self.conf_select_this_item
            del self.conf_select_this_item
            return True

        si = self.current_subitem
        from_start = False
        cont = True
        while cont:
            if not si:
                # No subitem selected yet: take the first one
                si = self.subitems[0]
                from_start = True
            else:
                pos = self.subitems.index(si)
                # Else take the next one
                if pos < len(self.subitems)-1:
                    # Let's get the next subitem
                    si = self.subitems[pos+1]
                else:
                    # No next subitem
                    si = None
                    cont = False
            if si:
                if (si.media_id or si.media):
                    # If the file is on a removeable media
                    if util.check_media(si.media_id):
                        self.current_subitem = si
                        return True
                    elif si.media and util.check_media(si.media.id):
                        self.current_subitem = si
                        return True
                else:
                    # if not, it is always available
                    self.current_subitem = si
                    return True

        self.current_subitem = None
        return not from_start


    def play(self, arg=None, menuw=None):
        """
        Play the item.
        """
        if not self.player or self.player_rating < 10:
            AlertBox(text=_('No player for this item found')).show()
            return

        if not self['resume'] and self['autobookmark_resume']:
            self.__play_args = (arg, menuw)
            dialog.show_confirmation(_('Do you want to resume play back or play from the start?'),
                    cancel_handler=self.resume_play, cancel_text=_('From Start'),
                    proceed_handler=self.resume_resume, proceed_text=_('Resume'))
        else:
            self.__play(arg, menuw)

    def resume_play(self):
        self.__play(*self.__play_args)

    def resume_resume(self):
        self['resume']  = max(0, self['autobookmark_resume'] - 10)
        self.__play(*self.__play_args)

    def __play(self, arg=None, menuw=None):
        # execute commands if defined
        if config.VIDEO_PRE_PLAY:
            os.system(config.VIDEO_PRE_PLAY)

        if self.parent:
            self.parent.current_item = self

        if not self.menuw:
            self.menuw = menuw

        # if we have variants, play the first one as default
        if self.variants:
            self.variants[0].play(arg, menuw)
            return

        # if we have subitems (a movie with more than one file),
        # we start playing the first that is physically available
        if self.subitems:
            self.error_in_subitem = 0
            self.last_error_msg   = ''
            self.current_subitem  = None

            result = self.set_next_available_subitem()
            if self.current_subitem: # 'result' is always 1 in this case
                # The media is available now for playing
                # Pass along the options, without loosing the subitem's own
                # options
                if self.current_subitem.mplayer_options:
                    if self.mplayer_options:
                        # With this set the player options are incorrect when there is more than 1 item
                        #self.current_subitem.mplayer_options += ' ' + self.mplayer_options
                        pass
                else:
                    self.current_subitem.mplayer_options = self.mplayer_options
                # When playing a subitem, the menu must be hidden. If it is not,
                # the playing will stop after the first subitem, since the
                # PLAY_END/USER_END event is not forwarded to the parent
                # videoitem.
                # And besides, we don't need the menu between two subitems.
                self.menuw.hide()
                self.last_error_msg = self.current_subitem.play(arg, self.menuw)
                if self.last_error_msg:
                    self.error_in_subitem = 1
                    # Go to the next playable subitem, using the loop in
                    # eventhandler()
                    self.eventhandler(PLAY_END)

            elif not result:
                # No media at all was found: error
                ConfirmBox(text=(_('No media found for "%(name)s".\nPlease insert the media "%(media_id)s".')) %
                     ({'name': self.name, 'media_id': self.media_id}), handler=self.play).show()
            return

        # normal plackback of one file
        if self.url.startswith('file://'):
            file = self.filename
            if self.media_id:
                mountdir, file = util.resolve_media_mountdir(self.media_id,file)
                if mountdir:
                    util.mount(mountdir)
                else:
                    self.menuw.show()
                    ConfirmBox(text=(_('No media found for "%(file)s".\nPlease insert the media "%(media_id)s".')) % \
                        ({'file': file, 'media_id': self.media_id}), handler=self.play).show()
                    return

            elif self.media:
                util.mount(os.path.dirname(self.filename))

        # dvd and vcd
        elif self.mode in ('dvd', 'vcd') and not self.filename and not self.media:
            media = util.check_media(self.media_id)
            if media:
                self.media = media
            else:
                self.menuw.show()
                ConfirmBox(text=(_('No media found for "%(media_id)s".\nPlease insert the media "%(url)s".')) % ({
                    'media_id': self.media_id, 'url': self.url}), handler=self.play).show()
                return

        mplayer_options = self.mplayer_options.split(' ')
        if not mplayer_options:
            mplayer_options = []

        if arg:
            mplayer_options += arg.split(' ')

        if self.menuw.visible:
            self.menuw.hide()

        self.plugin_eventhandler(PLAY, menuw)

        self.menuw.delete_submenu()

        error = self.player.play(mplayer_options, self)

        # Clear any resume settings
        self['resume'] = ''

        if error:
            # If we are a subitem we don't show any error message before
            # having tried all the subitems
            if hasattr(self.parent, 'subitems') and self.parent.subitems:
                return error
            else:
                AlertBox(text=error, handler=self.error_handler).show()


    def error_handler(self):
        """
        error handler if play doesn't work to send the end event and stop
        the player
        """
        rc.post_event(PLAY_END)
        self.stop()


    def stop(self, arg=None, menuw=None):
        """
        execute commands if defined
        """
        if config.VIDEO_POST_PLAY:
            os.system(config.VIDEO_POST_PLAY)

        if self.player:
            self.player.stop()


    def dvd_vcd_title_menu(self, arg=None, menuw=None):
        """
        Generate special menu for DVD/VCD/SVCD content
        """
        if not self.menuw:
            self.menuw = menuw

        # delete the submenu that got us here
        self.menuw.delete_submenu(False)

        # XXX only one track, play it
        # XXX disabled, it makes it impossible to set languages
        # if len(self.info['tracks']) == 1:
        #     i=copy.copy(self)
        #     i.parent = self
        #     i.set_url(self.url + '1', False)
        #     i.play(menuw = self.menuw)
        #     return

        # build a menu
        items = []
        for titlenum in range(len(self.info['tracks'])):
            i = copy.copy(self)
            i.parent = self
            i.set_url(self.url + str(titlenum+1), False)
            i.info = copy.copy(self.info)
            # copy the attributes from mmpython about this track
            i.info.discinfo = self.info.discinfo['tracks'][titlenum]
            i.info.set_variables(self.info.get_variables())
            i.info_type       = 'track'
            i.files           = None
            i.name            = Unicode(_('Play Title %d') % (titlenum+1))
            items.append(i)


        moviemenu = menu.Menu(self.name, items, umount_all=1, fxd_file=self.skin_fxd)
        moviemenu.item_types = 'video'
        self.menuw.pushmenu(moviemenu)


    def settings(self, arg=None, menuw=None):
        """
        Create a menu with 'settings'
        """
        if not self.menuw:
            self.menuw = menuw
        confmenu = configure.get_menu(self, self.menuw)
        self.menuw.pushmenu(confmenu)


    def eventhandler(self, event, menuw=None):
        """
        Eventhandler for this item
        """
        # when called from mplayer.py, there is no menuw
        if not menuw:
            menuw = self.menuw

        if self.plugin_eventhandler(event, menuw):
            return True

        # PLAY_END: do we have to play another file?
        if self.subitems and not self.variants:
            if event == PLAY_END:
                if not hasattr(self, 'error_in_subitem'):
                    # I have no idea how this can happen, but it does
                    self.error_in_subitem = 0
                self.set_next_available_subitem()
                # Loop until we find a subitem which plays without error
                while self.current_subitem:
                    _debug_('playing next item')
                    error = self.current_subitem.play(menuw=menuw)
                    if error:
                        self.last_error_msg = error
                        self.error_in_subitem = 1
                        self.set_next_available_subitem()
                    else:
                        return True
                if self.error_in_subitem:
                    # No more subitems to play, and an error occured
                    self.menuw.show()
                    AlertBox(text=self.last_error_msg).show()

            elif event == USER_END:
                pass

        # show configure menu
        if event == MENU:
            if self.player:
                self.player.stop()
            self.settings(menuw=menuw)
            menuw.show()
            return True

        # give the event to the next eventhandler in the list
        if isstring(self.parent):
            self.parent = None
        return Item.eventhandler(self, event, menuw)


    def rename_possible(self):
        """
        Returns True if the video item can be renamed.
        """
        try:
            if self.info and self.parent.DIRECTORY_USE_MEDIAID_TAG_NAMES and self.info['title']:
                # sorry, unable to edit media tag info
                return False
        except:
            pass
        return self.files and not self.files.read_only
        

    def rename(self, newname):
        """
        Try and rename the video item.
        If there is a .fxd file associated, the title is renamed in the .fxd file.
        If there is no .fxd file, and the video is a single file, that file and
        associated files are renamed .
        If there is no .fxd file, and the video is composed by a set of files, the
        whole set is renamed.
        """
        if not self.files.fxd_file:
            # no .fxd file
            if len(self.subitems) > 1:
                # rename each file of the set
                # search for the numeric pattern to get its length
                pat = re.compile(config.VIDEO_AUTOJOIN_REGEX)
                firstfile = self.subitems[0].files.files[0]
                mat = pat.search(firstfile)
                if mat is not None:
                    start = firstfile.find(mat.group(1), mat.start())
                    end = start + len(mat.group(1))
                    numlen = end - start
                else:
                    # sould not append, but default numeric pattern length is 2
                    numlen = 2
                # first file is number 1
                num = 1
                for subitem in self.subitems:
                    if not subitem.files.rename('%s%0*d' % (newname, numlen, num), False, True, True):
                        return False
                    num += 1
                self.name=newname
                return True
            else:
                # simple file rename
                if self.files.rename(newname):
                    self.name=newname
                    return True
                return False
        else:
            # change the title in the .fxd file
            self.fxd_rename_newname = newname
            try:
                parser = util.fxdparser.FXD(self.files.fxd_file)
                parser.set_handler('movie', self.fxd_rename, mode='w')
                parser.parse()
                parser.save()
            except Exception, e:
                return False
            return True


    def fxd_rename(self, fxd, node):
        fxd.setattr(node, 'title', self.fxd_rename_newname)
        self.name=self.fxd_rename_newname



########################
# Show Details
import skin
# Create the skin_object object
skin_object = skin.get_singleton()
if skin_object:
    skin_object.register('tvguideinfo', ('screen', 'info', 'scrollabletext', 'plugin'))

# Program Info screen
class ShowDetails(ScrollableTextScreen):
    """
    Screen to show more details
    """
    def __init__(self, menuw, movie):
        if movie is None:
            name = _('No Information Available')
            description = ''
        else:
            self.movie = movie
            name = movie.name
            sub_title = movie['tagline']
            desc = movie['plot']
            # gather the info and construct the description text
            if sub_title:
                # subtitle + newline + description
                description = u'"' + sub_title + u'"\n' + desc + u'\n\n'
            else:
                # or just the description, if there is no subtitle
                description = desc + u'\n\n'
            # add some additional info if they are available
            if movie['genre']:
                description += _('Genre') + u' : '+movie['genre'] + u'\n'
            if movie['length']:
                description +=  _('Length')+ u' : '+movie['length'] + u'\n'
            if movie['year']:
                description +=  _('Year')+u' : '+movie['year'] + u'\n'
            if movie['rating']:
                description +=  _('Rating')+u' : '+movie['rating'] + u'\n'
            if movie['mpaa']:
                description +=  _('MPAA')+u' : '+movie['mpaa'] + u'\n'

        # that's all, we can show this to the user
        ScrollableTextScreen.__init__(self, 'tvguideinfo', description)
        self.name            = name
        self.visible = True

        self.show(menuw)


    def getattr(self, name):
        if name == 'title':
            return self.name

        if name == 'datetime':
            record_start = self.movie['recording_timestamp']
            if record_start:
                return time.strftime(config.TV_DATETIME_FORMAT,
                                        time.localtime(float(record_start)))

        if self.movie:
            return self.movie.getattr(name)

        return u''


    def eventhandler(self, event, menuw=None):
        """
        eventhandler for the programm description display
        """
        event_consumed = ScrollableTextScreen.eventhandler(self, event, menuw)

        if not event_consumed:
            if event == MENU_PLAY_ITEM:
                self.menuw.back_one_menu()
                # try to watch this program
                self.movie.play(menuw=self.menuw)
                event_consumed = True

        return event_consumed
