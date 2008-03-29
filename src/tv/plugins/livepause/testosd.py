import pygame
import pygame.image
import PIL.Image

surf = pygame.image.load(r'c:\cygwin\work\python\freevo\share\images\osd\osd.png')

image_str = pygame.image.tostring(surf, 'P')
image = PIL.Image.fromstring('P', surf.get_size(), image_str)
print 'Palette ', surf.get_palette()
print 'Color key ' , surf.get_colorkey()
print 'Color key index', surf.map_rgb(surf.get_colorkey()[:3])

palette = []
use_yuv = True
for r,g,b in surf.get_palette():
    if use_yuv:
        y = int( (0.299 * r) +(0.587 *g) + (0.114 *b))
        y = max(0, min(255, y))
        u = int((b - y) * 0.565)
        u = max(0, min(255, u))
        v = int((r - y) * 0.713)
        v = max(0, min(255, v))
        palette.extend((v,u,y))
    else:
        palette.extend((r,g,b))

while len(palette) < 256:
    palette.extend((0,0,0))
image.putpalette(palette)
image.save(r'c:\temp\osd.png', transparency=0)