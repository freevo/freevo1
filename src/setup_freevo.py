# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Autoconfigure Freevo
#
# This is an application that is executed by the "./freevo" script
# after checking for python.
# -----------------------------------------------------------------------
# $Id$
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
Autoconfigure Freevo

This is an application that is executed by the "./freevo" script
after checking for python.
"""

import sys
import os
import string
from optparse import Option, OptionParser, IndentedHelpFormatter

# For Internationalization purpose
# an exception is raised with Python 2.1 if LANG is unavailable.
import gettext
try:
    gettext.install('freevo', os.environ['FREEVO_LOCALE'])
except: # unavailable, define '_' for all modules
    import __builtin__
    __builtin__.__dict__['_']= lambda m: m


CONFIG_VERSION = 2.2

EXTERNAL_PROGRAMS = (
    ("mplayer", "mplayer", 1),
    ("mencoder", "mencoder", 0),
    ("tvtime", "tvtime", 0),
    ("xine", "xine", 0),
    ("fbxine", "fbxine", 0),
    ("df_xine", "df_xine", 0),
    ("lsdvd", "lsdvd", 0),
    ("jpegtran", "jpegtran", 0),
    ("xmame.x11", "xmame", 0),
    ("xmame.SDL", "xmame", 0),
    ("xmame", "xmame", 0),
    ("ssnes9x", "snes", 0),
    ("zsnes", "snes", 0 ),
    ("lame", "lame", 0),
    ("flac", "flac", 0),
    ("cdparanoia", "cdparanoia", 0),
    ("oggenc", "oggenc", 0),
    ("renice", "renice", 0),
    ("setterm", "setterm", 0),
    ("mpav", "mpav", 0),
    ("vlc", "vlc", 0),
    ("dvdbackup", "dvdbackup", 0),
    ("unzip", "unzip", 0),
    ("livepause","livepause",0)
)


def parse_options(defaults):
    """
    Parse command line options
    """
    import version
    geometry_choices = ['800x600', '768x576', '640x480']
    display_choices = ['x11', 'fbdev', 'dxr3', 'mga', 'directfb', 'dfbmga', 'dga']
    tv_choices = ['ntsc', 'pal', 'secam']
    chanlist_choices = [
        'us-cable', 'us-cable-hrc', 'australia', 'italy', 'canada-cable', 'china-bcast', 'japan-bcast',
        'japan-cable', 'newzealand', 'switzerland', 'southafrica', 'us-bcast', 'ireland', 'europe-west',
        'argentina', 'france', 'russia', 'europe-east'
    ]

    formatter = IndentedHelpFormatter(indent_increment=2, max_help_position=32, width=100, short_first=0)
    parser = OptionParser(conflict_handler='resolve', formatter=formatter, usage="""freevo %prog [options]
    
For more information see:
    freevo %prog -- --help""",
        version='%prog ' + version._version)
    parser.prog = 'setup'
    parser.description = """Set up Freevo for your specific environment.

Depending on the display and the tv standard the geometry may be automatically changed."""
    parser.add_option('-v', '--verbose', action='count', default=0,
        help='set the level of verbosity [default:%default]')
    parser.add_option('--geometry', default='800x600', metavar='GEOMETRY',
        help='set the screen geometry [default:%default]')
    parser.add_option('--display', choices=display_choices, default=display_choices[0], metavar='DISPLAY',
        help='set the display, choose from: ' + ', '.join(display_choices) + ' [default:%default]')
    parser.add_option('--tv', choices=tv_choices, default=tv_choices[0], metavar='STANDARD',
        help='set the TV standard, choose from: ' + ', '.join(tv_choices) + ' [default:%default]')
    parser.add_option('--chanlist', choices=chanlist_choices, default=chanlist_choices[0], metavar='LIST',
        help='set the channel list, choose from: ' + ', '.join(chanlist_choices) + ' [default:%default]')
    parser.add_option('--sysfirst', action='store_true', default=False,
        help='search for from system path first [default:%default]')
    parser.add_option('--compile', action='store', default=None,
        help='compile the modules [default:%default]')
    parser.add_option('--prefix', action='store', default='.',
        help='destination prefix the modules [default:%default]')

    opts, args = parser.parse_args()
    try:
        w, h = opts.geometry.split('x')
        width = int(w)
        height = int(h)
    except:
        parser.error('geometry %r is not "<width>x<height>"' % opts.geometry)
    if opts.compile is not None:
        try:
            int(opts.compile)
        except:
            parser.error('compile %r is not one of (0, 1, 2)' % opts.geometry)

    return opts, args


class FreevoConf:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def match_files_recursively_helper(result, dirname, names):
    #print 'match_files_recursively_helper(result=%r, dirname=%r, names=%r)' % (result, dirname, names)
    if dirname == '.' or dirname[:5].upper() == './WIP':
        return result
    for name in names:
        if os.path.splitext(name)[1].lower()[1:] == 'py':
            fullpath = os.path.join(dirname, name)
            result.append(fullpath)
    return result


def create_config(conf):

    outfile = '/etc/freevo/freevo.conf'
    try:
        fd = open(outfile, 'w')
    except:
        if not os.path.isdir(os.path.expanduser('~/.freevo')):
            os.mkdir(os.path.expanduser('~/.freevo'))
        outfile = os.path.expanduser('~/.freevo/freevo.conf')
        fd = open(outfile, 'w')

    for val in dir(conf):
        if val[0:2] == '__': continue

        # Some Python magic to get all members of the struct
        fd.write('%s = %s\n' % (val, conf.__dict__[val]))

    print
    print 'wrote %s' % outfile


def check_program(conf, name, variable, necessary, opts=None):

    # Check for programs both in the path and the runtime apps dir
    sysfirst = opts is not None and opts.sysfirst
    verbose = opts is not None and opts.verbose

    search_dirs_runtime = ['./runtime/apps', './runtime/apps/mplayer', './runtime/apps/tvtime']
    if sysfirst:
        search_dirs = os.environ['PATH'].split(':') + search_dirs_runtime
    else:
        search_dirs = search_dirs_runtime + os.environ['PATH'].split(':')

    if verbose:
        print _('checking for %-13s') % (name+'...'),

    for dirname in search_dirs:
        filename = os.path.join(dirname, name)
        if os.path.exists(filename) and os.path.isfile(filename):
            if verbose:
                print filename
            conf.__dict__[variable] = filename
            break
    else:
        if necessary:
            print
            print "********************************************************************"
            print _('ERROR: can\'t find %s') % name
            print _('Please install the application respectively put it in your path.')
            print _('Freevo won\'t work without it.')
            print "********************************************************************"
            print
            print
            sys.exit(1)
        elif verbose:
            print _('not found (deactivated)')




if __name__ == '__main__':
    from pprint import pprint

    opts, args = parse_options({})

    conf = FreevoConf(
        geometry=opts.geometry,
        display=opts.display,
        tv=opts.tv,
        chanlist=opts.chanlist,
        version=CONFIG_VERSION
    )

    # this is called by the Makefile, don't call it directly
    if opts.compile is not None:
        # Compile python files:
        import distutils.util
        try:
            optimize = min(opts.compile, 2)
        except Exception, why:
            sys.exit(why)

        files = []
        os.path.walk('.', match_files_recursively_helper, files)
        distutils.util.byte_compile(files, prefix='.', base_dir=opts.prefix, optimize=optimize)
        sys.exit(0)


    print _('System path first=%s') % ( [_('No'), _('Yes')][opts.sysfirst])

    for program, valname, needed in EXTERNAL_PROGRAMS:
        check_program(conf, program, valname, needed, opts)

    # set geometry for display/tv combinations without a choice
    if conf.display in ( 'directfb', 'dfbmga' ):
        if conf.tv == 'ntsc':
            conf.geometry = '720x480'
        else:
            conf.geometry = '720x576'

    print
    print
    print _('Settings:')
    print '  %20s = %s' % ('geometry', conf.geometry)
    print '  %20s = %s' % ('display', conf.display)
    print '  %20s = %s' % ('tv', conf.tv)
    print '  %20s = %s' % ('chanlist', conf.chanlist)


    # Build everything
    create_config(conf)
    print

    sys.exit()
