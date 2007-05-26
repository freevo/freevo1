# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# remind.py - a simple plugin show reminders, or the output of a command
# -----------------------------------------------------------------------
# activate:
# plugin.activate('reminders', level=45)
# REMINDERS = [ ("cmd", "name", <wrap 0|N >, "string") ]
# -----------------------------------------------------------------------
# Freevo - A Home Theater PC framework
# Copyright (C) 2003 Krister Lagerstrom, et al.
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


__author__ = "Christian Lyra"
__version__ = "0.1"
__svnversion__ = "$Revision$"[11:-2]
__date__ = "$Date$"[7:-2]
__copyright__ = "Copyright (c) 2007 Christian Lyra"
__license__ = "GPL"
__doc__ = '''A plugin to list reminders, but can be used to
show the output of a user command.

To activate, put the following lines in local_conf.py:
plugin.activate('reminders', level=45)
REMINDERS = [ ("cmd", "name", <wrap 0|N>, "string") ]
wrap should be the maximum number of columns, and string if defined would be used to
indent the output. ("/usr/bin/remind -h", "Today", 47, "Reminders for") should output something like:
Reminders for Saturday, 26th May, 2007 (today):
Uncle Bob birthday
'''

#python modules
import os, time, stat, re, copy

#freevo modules
import config, menu, rc, plugin, skin, osd, util
from item import Item


#get the singletons so we get skin info and access the osd
skin = skin.get_singleton()
osd  = osd.get_singleton()

skin.register('headlines', ('screen', 'title', 'info', 'plugin'))


class PluginInterface(plugin.MainMenuPlugin):
    """
    A plugin to list reminders, but can be used to
    show the output of a user command.

    To activate, put the following lines in local_conf.py:
    plugin.activate('reminders', level=45)
    REMINDERS = [ ("cmd", "name", <wrap 0|N>, "string") ]
    wrap should be the maximum number of columns, and string if defined would be used to
    indent the output. ("/usr/bin/remind -h", "Today", 47, "Reminders for") should output something like:
    Reminders for Saturday, 26th May, 2007 (today):
        Uncle Bob birthday

    """
    # make an init func that creates the cache dir if it don't exist
    def __init__(self):
        plugin.MainMenuPlugin.__init__(self)

    def items(self, parent):
        return [ RemindMainMenuItem(parent) ]



class RemindItem(Item):
    """
    Item for the menu for one Reminder Type
    """
    def __init__(self, parent):
        self.cmd = None
        self.name = None
        self.wrap = None
        Item.__init__(self, parent)

    def actions(self):
        """
        return a list of actions for this item
        """
        items = [ ( self.remindlines , _('Show Reminders') ) ]
        return items

    def remindlines(self, arg=None, menuw=None):
        lines = []
        for f in self.run_remind(self.cmd, self.wrap):
            mi = menu.MenuItem('%s' % f)
            mi.arg = (mi, menuw)
            lines.append(mi)

        if (len(lines) == 0):
            lines += [menu.MenuItem(_('No Reminders Found'), menuw.goto_prev_page, 0)]

        lines_menu = menu.Menu(_('Reminders'), lines)
        rc.app(None)
        menuw.pushmenu(lines_menu)
        menuw.refresh()

    def run_remind(self, cmd, wrap=47):
        """execute the remind command and pretify the output"""

        output = []

        try:
            inst = os.popen(self.cmd)
            f = inst.readlines()
            inst.close()
        except:
            pass
        if int(wrap) > 1:
            for line in f:
                if line !='\n':
                    if self.str and line.rfind(self.str) == 0:
                        pad = ''
                    else:
                        pad = '   '
                    for tmp in self.wraper(line, int(wrap)).rstrip('\n').split('\n'):
                        output += [ pad + tmp ]
        else:
            output = f
        return output

    # from http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/148061
    def wraper(self, text, width):
        """
        A word-wrap function that preserves existing line breaks
        and most spaces in the text. Expects that existing line
        breaks are posix newlines (\n).
        """
        return reduce(lambda line, word, width=width: '%s%s%s' %
            (line,
            ' \n'[(len(line)-line.rfind('\n')-1
                 + len(word.split('\n',1)[0]) >= width)], word),
            text.split(' '))


class RemindMainMenuItem(Item):
    """
    this is the item for the main menu and creates the list
    of Reminders in a submenu.
    """
    def __init__(self, parent):
        Item.__init__(self, parent, skin_type='headlines')
        self.name = _('Reminders')
        self.reminders = config.REMINDERS

    def config(self):
        return [
            ( 'REMINDERS', None, 'list of tuples containing (command, group, width, header prefix)' )
        ]

    def actions(self):
        """
        return a list of actions for this item
        """
        items = [ ( self.create_reminderstype_menu , _('Reminders types' )) ]
        return items

    def create_reminderstype_menu(self, arg=None, menuw=None):
        remind_types = []

        for (cmd, name, wrap, string) in self.reminders:
            remind_type_item = RemindItem(self)
            remind_type_item.name = name
            remind_type_item.str = string
            remind_type_item.cmd = cmd
            remind_type_item.wrap = wrap
            remind_types += [ remind_type_item ]

        remind_menu = menu.Menu(_('Remind type'), remind_types)
        menuw.pushmenu(remind_menu)
        menuw.refresh()
