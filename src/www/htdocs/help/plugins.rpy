#!/usr/bin/python
# -----------------------------------------------------------------------
# plugins.rpy - Show all plugins
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
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

import sys, time

from www.web_types import HTMLResource, FreevoResource
import util, config

from helpers.plugins import parse_plugins
from helpers.plugins import info_html

TRUE = 1
FALSE = 0

class PluginResource(FreevoResource):

    def _render(self, request):

        fv = HTMLResource()
        form = request.args

        if not hasattr(config, 'all_plugins'):
            config.all_plugins = parse_plugins()

        all_plugins = config.all_plugins
        special_plugins = ('tv', 'video', 'audio', 'image', 'idlebar')

        type = fv.formValue(form, 'type')
        if not type:
            plugin_link = '<li><a href="plugins.rpy?type=%s#%s">%s</a></li>'
            page_link = '<li><a href="plugins.rpy?type=%s">%s plugins</a></li>\n<ol>'

            fv.printHeader(_('Freevo Plugin List'), '/styles/main.css',prefix=request.path.count('/')-1)
            fv.res += '<div id="content">\n'
            fv.res += '<p><b>Index</b><ol>'

            fv.res += page_link % ( 'global', 'Global')
            for p in all_plugins:
                if not p[0][:p[0].find('.')] in special_plugins:
                    fv.res += plugin_link % ('global', p[0], p[0])
            fv.res += '</ol> '
            for type in special_plugins:
                fv.res += page_link % (type, type.capitalize())
                for p in all_plugins:
                    if p[0][:p[0].find('.')] == type:
                        fv.res += plugin_link % (type, p[0], p[0])
                fv.res += '</ol>\n'

            fv.res += '</ol>\n'

        else:
            fv.printHeader(_('Freevo Plugin List')+' - %s Plugins' % type.capitalize(),
                           '/styles/main.css',prefix=request.path.count('/')-1)
            fv.res += '<div id="content">\n'
            fv.res += '<a name="top"></a>'

            if type == 'global':
                for p in all_plugins:
                    if not p[0][:p[0].find('.')] in special_plugins:
                        fv.res +=  '<a name="%s"></a>' % p[0]
                        fv.res += info_html(p[0], [p])
                        fv.res += '[&nbsp;<a href="#top">'+_('top')+'</a>&nbsp;|&nbsp;'
                        fv.res += '<a href="plugins.rpy">'+_('index')+'</a>&nbsp;|&nbsp\n'
                        fv.res += '<a href="/pluginconfig.rpy?expAll#%s">configure</a>]<hr>\n' % p[0]
            else:
                for p in all_plugins:
                    if p[0][:p[0].find('.')] == type:
                        fv.res +=  '<a name="%s"></a>' % p[0]
                        fv.res += info_html(p[0], [p])
                        fv.res += '[&nbsp;<a href="#top">'+_('top')+'</a>&nbsp;|&nbsp;'
                        fv.res += '<a href="plugins.rpy">'+_('index')+'</a>&nbsp;|&nbsp\n'
                        fv.res += '<a href="/pluginconfig.rpy?expAll#%s">configure</a>]<hr>\n' % p[0]

        fv.res += '</div>\n'
        fv.res += '<br><br>'
        fv.printLinks(request.path.count('/')-1)
        fv.printFooter()
        fv.res+=('</ul>')
        return String( fv.res )


resource = PluginResource()
