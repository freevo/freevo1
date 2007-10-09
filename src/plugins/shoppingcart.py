# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# shoppingcart.py - Example item plugin
# -----------------------------------------------------------------------
# $Id$
#
# Notes: This is a plugin to move and copy files
#
# Activate:
#   plugin.activate('shoppingcart')
#
# Todo:
#   o handle fxd files
#   o also add metafiles like covers to the cart
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


import os
import plugin
import config
import shutil
import util
from gui import PopupBox, AlertBox
import rc
import event as em
import menu

class PluginInterface(plugin.ItemPlugin):
    """
    This plugin copies or moves files to directories. Go to a file hit
    enter pick 'add to cart' and then go to a directory. Press enter
    and pick what you want to do.

    plugin.activate('shoppingcart')

    """
    def __init__(self):
        plugin.ItemPlugin.__init__(self)
        self.item = None
        self.cart = []

    def moveHere(self, arg=None, menuw=None):
        popup = PopupBox(text=_('Moving files...'))
        popup.show()
        try:
            for cartfile in self.cart:
                cartfile.files.move(self.item.dir)
        except OSError, e:
            print 'Mode failed \'%s\'' % e
        popup.destroy()
        self.cart = []
        rc.post_event(em.MENU_BACK_ONE_MENU)


    def copyHere(self, arg=None, menuw=None):
        popup = PopupBox(text=_('Copying files...'))
        popup.show()
        try:
            for cartfile in self.cart:
                cartfile.files.copy(self.item.dir)
        except OSError, e:
            print 'Copy failed \'%s\'' % e
        popup.destroy()
        self.cart = []
        rc.post_event(em.MENU_BACK_ONE_MENU)


    def addToCart(self, arg=None, menuw=None):
        if hasattr(self.item, 'subitems') and self.item.subitems:
            for s in self.item.subitems:
                self.cart.append(s)
        else:
            self.cart.append(self.item)

        if isinstance(menuw.menustack[-1].selected, menu.MenuItem):
            rc.post_event(em.MENU_BACK_ONE_MENU)
        else:
            rc.post_event(em.Event(em.OSD_MESSAGE, arg=_('Added to Cart')))


    def removeFromCart(self, arg=None, menuw=None):
        if hasattr(self.item, 'subitems') and self.item.subitems:
            for s in self.item.subitems:
                self.cart.remove(s)
        else:
            self.cart.remove(self.item)

        if isinstance(menuw.menustack[-1].selected, menu.MenuItem):
            rc.post_event(em.MENU_BACK_ONE_MENU)
        else:
            rc.post_event(em.Event(em.OSD_MESSAGE, arg=_('Removed from Cart')))


    def shuntItemInCart(self, item):
        ''' Move an image item into or out of the shopping cart
        '''
        if self.cart != [] and item in self.cart:
            self.cart.remove(item)
            rc.post_event(em.Event(em.OSD_MESSAGE, arg=_('Removed Item from Cart')))
        else:
            self.cart.append(item)
            rc.post_event(em.Event(em.OSD_MESSAGE, arg=_('Added Item to Cart')))


    def deleteCart(self, arg=None, menuw=None):
        self.cart = []
        rc.post_event(em.MENU_BACK_ONE_MENU)


    def actions(self, item):
        self.item = item
        myactions = []

        if self.item.parent and self.item.parent.type not in ('dir','mediamenu'):
            # only activate this for directory items
            return []

        _debug_('item=%s, type=%s, cart=%s' % (item, item.type, self.cart), 2)
        if item.type == 'dir':
            if len(self.cart) > 0:
                for c in self.cart:
                    if not c.files.move_possible():
                        break
                else:
                    myactions.append((self.moveHere, _('Cart: Move Files Here')))
                myactions.append((self.copyHere, _('Cart: Copy Files Here')))

            if self.item.parent and self.item.parent.type == 'dir':
                if item not in self.cart:
                    myactions.append((self.addToCart, _('Add Directory to Cart'), 'cart:add'))
                elif item in self.cart:
                    myactions.append((self.removeFromCart, _('Remove Directory from Cart'), 'cart:remove'))

        elif hasattr(item, 'files') and item.files:
            if item not in self.cart and item.files.copy_possible():
                myactions.append((self.addToCart, _('Add to Cart'), 'cart:add'))
            elif item in self.cart:
                myactions.append((self.removeFromCart, _('Remove from Cart'), 'cart:remove'))

        if self.cart:
            myactions.append((self.deleteCart, _('Delete Cart')))

        return myactions
