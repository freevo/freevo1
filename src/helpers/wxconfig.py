# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Helper modules to configure freevo using wxPython
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
#   Work-in-progress
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

import sys, os
import re
from pprint import pprint, pformat

import config
import event
from helpers import plugins

#print('config=%s' % pformat(dir(config)))
#print('our_locals=%s' % (pformat(config.our_locals),))

print('freevo_config is %r' % (os.environ['FREEVO_CONFIG'],))
print('local_conf is %r' % (config.overridefile,))

def parse_freevo_config(filename):
    """
    Parse the file for variables.
    """
    items = {}
    try:
        fd = open(filename)
    except IOError, why:
        print why
        raise SystemExit

    # create a list of non-blank lines
    #lines = [i.strip() for i in fd.readlines() if i.strip() ]
    # create a list of stripped lines
    lines = [i.rstrip() for i in fd.readlines() ]
    fd.close()

    # skip change set
    for i in range(len(lines)):
        if lines[i] == '# ======================================================================':
            i += 1
            break

    #print i
    #print lines[i:i+1]
    for j in range(len(lines[i:])):
        if lines[i+j] == '# ======================================================================':
            i += j + 1
            break
    #print j
    #print i

    note_pat = re.compile('^#\s*(.*)$')
    tip_pat = re.compile('^([A-Z]\w+)\s*=\s*[^#]+#\s*(.*)$')
    tipmore_pat = re.compile('^\s+#\s*(.*)$')
    var_pat = re.compile('^\s*([A-Z]\w+)\s*=\s*[^#]+$')
    comment_pat = re.compile('^\s*#\s*[=-]+$')
    plugin_pat = re.compile('^\s*plugin.*$')

    # now we should be at the first config line
    notes = []
    tips = []
    for j in range(len(lines[i:])):
        line = lines[i+j]
        if not line:
            continue
        #print 'line=%s' % line
        comment_mat = comment_pat.match(line)
        plugin_mat = plugin_pat.match(line)
        if comment_mat or plugin_mat:
            continue

        # what do we do with if/else blocks?

        note_mat = note_pat.match(line)
        tip_mat = tip_pat.match(line)
        tipmore_mat = tipmore_pat.match(line)
        var_mat = var_pat.match(line)
        #print('note_mat=%r tip_mat=%r tipmore_mat=%r var_mat=%r' % (note_mat, tip_mat, tipmore_mat, var_mat))
        if note_mat:
            note = note_mat.group(1)
            if note:
                notes.append(note)
        elif tipmore_mat:
            tip = tipmore_mat.group(1)
            if tip:
                tips.append(tip)
        elif tip_mat:
            if tips:
                if var:
                    tip, note = items[var]
                    note = ' '.join([tip] + tips)
                    tip = ''
                    items[var] = (tip, note)
                else:
                    print 'no var for %r' % (tips,)
            var = tip_mat.group(1)
            tip = tip_mat.group(2)
            if tip and not notes:
                notes = [tip]
                tip = ''
            items[var] = (tip, ' '.join(notes))
            notes = []
            tips = []
        elif var_mat:
            if tips:
                if var:
                    tip, note = items[var]
                    note = ' '.join([tip] + tips)
                    tip = ''
                    items[var] = (tip, note)
                else:
                    print 'no var for %r' % (tips,)
            var = var_mat.group(1)
            items[var] = ('', ' '.join(notes))
            notes = []
            tips = []
        else:
            #print('***=%s' % line)
            pass
    return items


def build_config(doc_items):
    config_var_pat = re.compile('^[A-Z].*$')
    items = []
    for var in dir(config):
        if config_var_pat.match(var) is None:
            continue
        if var in ('LOCAL_CONF_CHANGES', 'EVENTS'):
            continue

        #print 'var=%r' % (var,)
        if var in doc_items:
            tip = doc_items[var][0]
            note = doc_items[var][1]
        else:
            tip = ''
            note = ''
        if var in config.our_locals:
            overridden = True
            value = config.our_locals[var]
        else:
            overridden = False
            try:
                value = eval('config.%s' % var)
            except AttributeError, why:
                print '%r: %s' % (var, why)
                value = None

        if isinstance(value, event.Event):
            continue
        #print('%s%r=%r' % ('*** ' if overridden else '    ', var, value))
        items.append((var, value, overridden, tip, note))
    return items
            

def build_plugin_list():
    return plugins.parse_plugins()


def main():
    print 'building documentation from freevo_config...'
    doc_items = parse_freevo_config(os.environ['FREEVO_CONFIG'])
    #print('doc_items=\n%s' % pformat(doc_items))
    print 'building configuration...'
    cfg_items = build_config(doc_items)
    #print('cfg_items=\n%s' % pformat(cfg_items))
    print 'building plug-in configuration...'
    plugin_items = build_plugin_list()


if __name__ == '__main__':
    try:
        main()
    except StandardException, why:
        print why
