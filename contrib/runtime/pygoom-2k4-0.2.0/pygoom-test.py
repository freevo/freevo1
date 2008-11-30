# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Small test harness for pygoom
# -----------------------------------------------------------------------
# Controls:
# escape quits
# left mouse button changes the song title
# middle mouse button changes the frame rate
# right mouse button changes the message
# numbers change the effects mode

import os, sys
import pygame
from pygame.locals import *

if not pygame.font: print 'Warning, fonts disabled'
if not pygame.mixer: print 'Warning, sound disabled'

import pygoom

if pygoom.HEXVERSION < 0x000200f0:
    sys.exit('Error, pygoom too old')
print '0x%08x' % pygoom.HEXVERSION, pygoom.VERSION
pygoom.debug(1)

width, height = (320, 240)

pygame.init()
screen = pygame.display.set_mode((width, height))
pygame.display.set_caption('PyGoom Test')
pygame.mouse.set_visible(0)

clock = pygame.time.Clock()

background = pygame.Surface(screen.get_size())
background = background.convert()
background.fill((250, 250, 250))

exportfile = '/tmp/mpav'
if not os.path.exists(exportfile):
    open(exportfile, 'w').write('\0' * 2048)

goom = pygoom.PyGoom(width, height, exportfile, songtitle='song title')

def main():
    songtitles = [ 'First Song', 'Second Song', 'newling\ndoes not work' ]
    songtitle_idx = 0
    framerates = [ 60, 25, 20, 15, 10, 5, 1 ]
    framerate_idx = 0
    messages = [ 'This is pygoom %s' % pygoom.VERSION, 'written by Duncan Webb' ]
    message_idx = 0
    while True:
        fps = clock.get_fps()
        msecs = clock.tick(framerates[framerate_idx])
        #print 'fps=%.1f mescs=%s' % (fps, msecs)
        goom.fps = fps

        #Handle Input Events
        for event in pygame.event.get():
            #print event
            if event.type == QUIT:
                return
            elif event.type == KEYDOWN:
                fxmodes = ''
                if event.key == K_ESCAPE:
                    return
                elif event.key == K_0 or event.key == K_KP0:
                    goom.fxmode = 0; fxmodes = 'NORMAL_MODE'
                elif event.key == K_1 or event.key == K_KP1:
                    goom.fxmode = 1; fxmodes = 'WAVE_MODE'
                elif event.key == K_2 or event.key == K_KP2:
                    goom.fxmode = 2; fxmodes = 'CRYSTAL_BALL_MODE'
                elif event.key == K_3 or event.key == K_KP3:
                    goom.fxmode = 3; fxmodes = 'SCRUNCH_MODE'
                elif event.key == K_4 or event.key == K_KP4:
                    goom.fxmode = 4; fxmodes = 'AMULETTE_MODE'
                elif event.key == K_5 or event.key == K_KP5:
                    goom.fxmode = 5; fxmodes = 'WATER_MODE'
                elif event.key == K_6 or event.key == K_KP6:
                    goom.fxmode = 6; fxmodes = 'HYPERCOS1_MODE'
                elif event.key == K_7 or event.key == K_KP7:
                    goom.fxmode = 7; fxmodes = 'HYPERCOS2_MODE'
                elif event.key == K_8 or event.key == K_KP8:
                    goom.fxmode = 8; fxmodes = 'YONLY_MODE'
                elif event.key == K_9 or event.key == K_KP9:
                    goom.fxmode = 9; fxmodes = 'SPEEDWAY_MODE'
                else:
                    goom.fxmode = -1;
                print 'goom.fxmode=%r %s' % (goom.fxmode, fxmodes)

            elif event.type == MOUSEBUTTONDOWN:
                if event.button == 1:
                    goom.songtitle = songtitles[songtitle_idx]
                    print 'goom.songtitle=%r' % goom.songtitle
                    songtitle_idx = (songtitle_idx + 1) % len(songtitles)
                elif event.button == 2:
                    framerate_idx = (framerate_idx + 1) % len(framerates)
                    print 'goom.framerate=%r' % framerates[framerate_idx]
                elif event.button == 3:
                    goom.message = messages[message_idx]
                    print 'goom.message=%r' % goom.message
                    message_idx = (message_idx + 1) % len(messages)

        #Draw Everything
        screen.blit(background, (0, 0))
        surf = goom.process()
        screen.blit(surf, (0, 0))
        pygame.display.flip()


if __name__ == '__main__': main()
