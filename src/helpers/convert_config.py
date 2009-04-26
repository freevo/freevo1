# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Helper modules to convert a local_conf.py to the latest standard
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
#   Run with freevo convert_config
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

import sys
import os
import re
from optparse import IndentedHelpFormatter, OptionParser

change_map = {
    'DIR_MOVIES': 'VIDEO_ITEMS',
    'DIR_AUDIO' : 'AUDIO_ITEMS',
    'DIR_IMAGES': 'IMAGE_ITEMS',
    'DIR_GAMES' : 'GAMES_ITEMS',
    'DIR_RECORD': 'TV_RECORD_DIR',
    'SUFFIX_VIDEO_FILES': 'VIDEO_SUFFIX',
    'SUFFIX_VIDEO_MPLAYER_FILES': 'VIDEO_MPLAYER_SUFFIX',
    'SUFFIX_VIDEO_XINE_FILES': 'VIDEO_XINE_SUFFIX',
    'ONLY_SCAN_DATADIR': 'VIDEO_ONLY_SCAN_DATADIR',
    'SUFFIX_AUDIO_FILES': 'AUDIO_SUFFIX',
    'SUFFIX_AUDIO_PLAYLISTS': 'PLAYLIST_SUFFIX',
    'SUFFIX_IMAGE_FILES': 'IMAGE_SUFFIX',
    'SUFFIX_IMAGE_SSHOW': 'IMAGE_SSHOW_SUFFIX',
    'MAME_CACHE': 'GAMES_MAME_CACHE',
    'OSD_SKIN': 'SKIN_MODULE',
    'FORCE_SKIN_LAYOUT': 'DIRECTORY_FORCE_SKIN_LAYOUT',
    'AUDIO_FORMAT_STRING': 'DIRECTORY_AUDIO_FORMAT_STRING',
    'USE_MEDIAID_TAG_NAMES': 'DIRECTORY_USE_MEDIAID_TAG_NAMES',
    'OVERSCAN_X': 'OSD_OVERSCAN_LEFT',
    'OVERSCAN_Y': 'OSD_OVERSCAN_TOP',
    'TV_SHOW_DATA_DIR': 'VIDEO_SHOW_DATA_DIR',
    'TV_SHOW_REGEXP': 'VIDEO_SHOW_REGEXP',
    'TV_SHOW_REGEXP_MATCH': 'VIDEO_SHOW_REGEXP_MATCH',
    'TV_SHOW_REGEXP_SPLIT': 'VIDEO_SHOW_REGEXP_SPLIT',
    'STOP_OSD_WHEN_PLAYING': 'OSD_STOP_WHEN_PLAYING',
    'TV_RECORD_SERVER_IP': 'RECORDSERVER_IP',
    'TV_RECORD_SERVER_PORT': 'RECORDSERVER_PORT',
    'RECORD_SCHEDULE': 'TV_RECORD_SCHEDULE',
    'RECORD_PADDING': 'TV_RECORD_PADDING',
    'IVTV_OPTIONS': 'TV_IVTV_OPTIONS',
    'VCR_SETTINGS': 'TV_VCR_SETTINGS',
    'WWW_SERVER_UID': 'WEBSERVER_UID',
    'WWW_SERVER_GID': 'WEBSERVER_GID',
    'WWW_PORT': 'WEBSERVER_PORT',
    'recordable=True': 'record_group=None',
    'recordable=False': 'record_group=None',
    'recordable = True': 'record_group=None',
    'recordable = False': 'record_group=None',
    'OSD_OVERSCAN_X': 'OSD_OVERSCAN_LEFT = OSD_OVERSCAN_RIGHT',
    'OSD_OVERSCAN_Y': 'OSD_OVERSCAN_TOP = OSD_OVERSCAN_BOTTOM',
    'PERSONAL_WWW_PAGE': 'WWW_PERSONAL_PAGE',
    'TIME_DEBUG': 'DEBUG_TIME',
    'SKIN_DEBUG': 'DEBUG_SKIN',
    'CHILDAPP_DEBUG': 'DEBUG_CHILDAPP',
    'RECORDSERVER_DEBUG': 'DEBUG_RECORDSERVER',
    'ENCODINGSERVER_DEBUG': 'DEBUG_ENCODINGSERVER',
    'RSSSERVER_DEBUG': 'DEBUG_RSSSERVER',
    'WEBSERVER_DEBUG': 'DEBUG_WEBSERVER',
    'RECORDSERVER_LOGGING': 'LOGGING_RECORDSERVER',
    'ENCODINGSERVER_LOGGING': 'LOGGING_ENCODINGSERVER',
    'RSSSERVER_LOGGING': 'LOGGING_RSSSERVER',
    'WEBSERVER_LOGGING': 'LOGGING_WEBSERVER',
    'DEFAULT_VOLUME': 'MIXER_VOLUME_DEFAULT',
    'TV_IN_VOLUME': 'MIXER_VOLUME_TV_IN',
    'VCR_IN_VOLUME': 'MIXER_VOLUME_VCR_IN',
    'RADIO_IN_VOLUME': 'MIXER_VOLUME_RADIO_IN',
    'MAX_VOLUME': 'MIXER_VOLUME_MAX',
    'DEV_MIXER': 'MIXER_DEVICE',
    'MIXER_DEFAULT_STEP': 'MIXER_VOLUME_STEP',
    'CONTROL_ALL_AUDIO': 'MIXER_CONTROL_ALL',
    'VOLUME_DEFAULT': 'MIXER_VOLUME_DEFAULT',
    'VOLUME_VCR_IN': 'MIXER_VOLUME_VCR_IN',
    'VOLUME_TV_IN': 'MIXER_VOLUME_TV_IN',
    'VOLUME_MIXER_STEP': 'MIXER_VOLUME_STEP',
    'VOLUME_RADIO_IN': 'MIXER_VOLUME_RADIO_IN',
    'VOLUME_MAX': 'MIXER_VOLUME_MAX',
    'VOLUME_MIXER_DEV': 'MIXER_DEVICE',
    'MAJOR_AUDIO_CTRL': 'MIXER_MAJOR_CTRL',
    'MAJOR_AUDIO_CTRL_MUTE': 'MIXER_MAJOR_MUTE_CTRL',
    'ENABLE_SHUTDOWN_SYS': 'SHUTDOWN_SYS_ENABLE',
    'FREQUENCY_TABLE': 'TV_FREQUENCY_TABLE',
    'CONFIRM_SHUTDOWN': 'SHUTDOWN_CONFIRM',
    'DUPLICATE_DETECTION': 'TV_RECORD_DUPLICATE_DETECTION',
    'ONLY_NEW_DETECTION': 'TV_RECORD_ONLY_NEW_DETECTION',
    'CONFLICT_RESOLUTION': 'TV_RECORD_CONFLICT_RESOLUTION',
    'REMOVE_COMMERCIALS': 'TV_RECORD_REMOVE_COMMERCIALS',
    'TV_DATEFORMAT': 'TV_DATE_FORMAT',
    'TV_TIMEFORMAT': 'TV_TIME_FORMAT',
    'TV_DATETIMEFORMAT': 'TV_DATETIME_FORMAT',
    'TV_RECORDFILE_MASK': 'TV_RECORD_FILE_MASK',
    'TV_RECORDFILE_SUFFIX': 'TV_RECORD_FILE_SUFFIX',
    'TV_RECORDFILE_OKLETTERS': 'TV_RECORD_FILE_OKLETTERS',
    'VIDEO_GROUPS': 'TV_VIDEO_GROUPS',
    'upsoon': 'tv.upsoon',
    'audio\.playlist': 'audio.playlists',
    'TV_TV_': 'TV_',
    'MIXER_MIXER_': 'MIXER_',
    'SHUTDOWN_CONFIRM': 'SYS_SHUTDOWN_CONFIRM',
    'SHUTDOWN_SYS_CMD': 'SYS_SHUTDOWN_CMD',
    'RESTART_SYS_CMD': 'SYS_RESTART_CMD',
    'SHUTDOWN_SYS_ENABLE': 'SYS_SHUTDOWN_ENABLE',
    'AUTOSYS_SHUTDOWN_CONFIRM': 'AUTOSHUTDOWN_CONFIRM',
    'ICECAST_WWW_PAGE': 'WWW_ICECAST_PAGE',
    'USE_SDL_KEYBOARD': 'SYS_USE_KEYBOARD',
    'USE_NETWORK': 'SYS_USE_NETWORK',
    'SYS_SYS_USE_NETWORK': 'SYS_USE_NETWORK',
}


def parse_options():
    """
    Parse command line options
    """
    import version
    formatter = IndentedHelpFormatter(indent_increment=2, max_help_position=32, width=100, short_first=0)
    parser = OptionParser(conflict_handler='resolve', formatter=formatter,
        usage="freevo %prog [options]",
        version='%prog ' + str(version._version))
    parser.prog = os.path.splitext(os.path.basename(sys.argv[0]))[0]
    parser.description = "Helper to convert old local_conf.py configuration to current configuration"
    #parser.add_option('-v', '--verbose', action='count', default=0,
    #    help='set the level of verbosity [default:%default]')
    parser.add_option('--scan', action='store_true', default=False,
        help='scan source files for the old variables')
    parser.add_option('--file', metavar='FILE', default=None,
        help='the local_conf.py file [default:%default]')
    parser.add_option('-w', '--write', action='store_true', default=False,
        help='write the local_conf.py file, this will overwrite an existing file!')

    opts, args = parser.parse_args()
    if not opts.file and not opts.scan:
        parser.error('either --scan or --file must be given.')

    return opts, args


opts, args = parse_options()

seperator = ' #=[]{}().:,\n'

def change(file, print_name=False):
    out = None
    try:
        cfg = open(file)
    except:
        help()

    data = cfg.readlines()
    cfg.close()

    if opts.write:
        print 'write output file %s' % file
        out = open(file, 'w')

    change = True
    if file == 'freevo_config.py':
        change = False

    for line in data:
        if line.startswith('FREEVO_CONF_VERSION'):
            change = True

        if not change:
            if out:
                out.write(line)
            continue

        for var in change_map:
            repat = re.compile(var)
            match = repat.match(line)
            if match:
                if print_name:
                    print '**** %s **** ' % file
                    print_name = False
                if out:
                    line = re.sub(repat, change_map[var], line)
                else:
                    print 'changing config file line:'
                    print line[:-1]
                    print re.sub(repat, change_map[var], line)[:-1]
                    print
        if out:
            out.write(line)

    if out:
        out.close()


if opts.scan:
    print 'searching for files using old style variables...'
    # s = ''
    # for var in change_map:
    #     s += '|%s' % var
    # s = '(%s)' % s[1:]
    # pipe = 'xargs egrep \'%s\' | grep -v helpers/convert_config' % s
    # os.system('find . -name \*.py | %s' % pipe)
    # os.system('find . -name \*.rpy | %s' % pipe)
    # print
    # print
    # print 'starting scanning all files in detail:'
    import util
    for f in util.match_files_recursively('src', [ 'py', 'rpy' ]):
        change(f, print_name=True)
    sys.exit(0)


change(opts.file)
