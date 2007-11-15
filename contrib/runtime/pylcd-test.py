#!/usr/bin/python -tt
# -*- coding: iso-8859-1 -*-
import sys,pylcd,os

p=pylcd.client()
print 'Connect message:', p.connect()
print 'Info as know by the module:'
p.getinfo()
print 'Setting some info to the display.'

(sysname, nodename, release, version, machine)=os.uname()

s='s'
w1='w1'
w2='w2'
w3='w3'

p.screen_add(s)
p.widget_add(s,w1,'string')
p.widget_add(s,w2,'string')
p.widget_add(s,w3,'string')
p.widget_set(s,w1,'1 1 "Hello, LCD world!"')
print 'printing "Hello, LCD world!"'
p.widget_set(s,w2,'1 2 "%s: %s"'%(nodename, release))
print 'printing "%s: %s"'%(nodename, release)
p.widget_set(s,w3,'1 3 "äöüß"')
print 'printing "äöüß"'

print 'All done.'

try:
    raw_input('Press a key to continue')
except EOFError:
    print '\nEOF'

print 'Exit.'
