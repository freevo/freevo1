import sys
from xml.dom import *
import xml.dom.minidom
import traceback

class OSDObject(object):
    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height= height

    def get_common_attr(self):
        return 'x="%d" y="%d" width="%d" height="%d"' % (self.x,self.y,self.width, self.height)

class Dialog(OSDObject):
    def __init__(self, name, objects, x, y, width, height):
        super(Dialog,self).__init__(x, y, width, height)
        self.name = name
        self.objects = objects

    def to_xml(self, indent, level):
        xml_str = '%s<osd name="%s" %s >\n' % (indent * level, self.name, self.get_common_attr())

        for object in self.objects:
            xml_str += object.to_xml(indent, level + 1)
        xml_str += '%s</osd>\n' % (indent * level)
        return xml_str

class Text(OSDObject):
    def __init__(self, expr, x, y, width, height):
        super(Text,self).__init__(x, y, width, height)
        self.expr = expr

    def to_xml(self, indent, level):
        return '%s<text expression="%s" font="<Name>/<Size>" fgcolor="<R,G,B>" align="(left|center|right)" valign="(top|center|bottom)" %s/>\n'% (indent * level,self.expr, self.get_common_attr())

class Image(OSDObject):
    def __init__(self, expr, x, y, width, height):
        super(Image,self).__init__(x, y, width, height)
        self.expr = expr

    def to_xml(self, indent, level):
        if self.expr:
            expr = 'expression="%s"'% self.expr
        else:
            expr = ''

        return '%s<image %s src="FILL IN" scale="One of (noscale | horizontal | vertical | both | aspect) %s/>\n'% (indent * level,expr, self.get_common_attr())

class Percent(OSDObject):
    def __init__(self, expr, x, y, width, height):
        super(Percent,self).__init__(x, y, width, height)
        self.expr = expr

    def to_xml(self, indent, level):
        return '%s<percent expression="%s" src="FILL IN" vertical="(True|False)" %s/>\n'% (indent * level, self.expr, self.get_common_attr())


class Button(OSDObject):
    def __init__(self, name, x, y, width, height):
        super(Button,self).__init__(x, y, width, height)
        self.name = name

    def to_xml(self, indent, level):
        return '%s<button name="%s" style="FILL IN" %s/>\n'% (indent * level, self.name, self.get_common_attr())

class ToggleButton(OSDObject):
    def __init__(self, name, x, y, width, height):
        super(ToggleButton,self).__init__(x, y, width, height)
        self.name = name

    def to_xml(self, indent, level):
        return '%s<togglebutton name="%s" style="FILL IN" %s/>\n'% (indent * level, self.name, self.get_common_attr())

class Menu(OSDObject):
    def __init__(self, details, x, y, width, height):
        super(Menu,self).__init__(x, y, width, height)
        name, items = details.split(',', 1)
        if name:
            self.name = name
        else:
            self.name = 'menu'
        self.items = items

    def to_xml(self, indent, level):
        return '%s<menu name="%s" style="FILL IN" itemsperpage="%s" %s/>\n'% (indent * level, self.name, self.items, self.get_common_attr())

def process_dialog(name, node):
    min_x = 0xffff
    min_y = 0xffff
    max_x = 0
    max_y = 0
    objects = []
    for node in node.childNodes:
        if node.nodeType == node.ELEMENT_NODE:
            try:
                label = node.getAttribute('inkscape:label')
                if label:
                    x = int(eval(node.getAttribute('x')))
                    y = int(eval(node.getAttribute('y')))
                    w = int(eval(node.getAttribute('width')))
                    h = int(eval(node.getAttribute('height')))
                    min_x = min(x, min_x)
                    min_y = min(y, min_y)
                    max_x = max(x+w, max_x)
                    max_y = max(y+h, max_y)

                    details = label.split(':', 1)
                    if len(details) == 1:
                        details = (details[0], '')

                    if details[0].lower() == 'text':
                        objects.append(Text(details[1], x, y, w, h))
                    elif details[0].lower() == 'image':
                        objects.append(Image(details[1], x, y, w, h))
                    elif details[0].lower() == 'percent':
                        objects.append(Percent(details[1], x, y, w, h))
                    elif details[0].lower() == 'button':
                        objects.append(Button(details[1], x, y, w, h))
                    elif details[0].lower() == 'togglebutton':
                        objects.append(ToggleButton(details[1], x, y, w, h))
                    elif details[0].lower() == 'menu':
                        objects.append(Menu(details[1], x, y, w, h))
            except:
                print >>sys.stderr, 'Failed to process %s' % node.localName
                traceback.print_exc()



    for object in objects:
        object.x = object.x - min_x
        object.y = object.y - min_y
    return Dialog(name, objects, min_x, min_y, max_x - min_x, max_y-min_y)


if len(sys.argv) == 1:
    print 'svgtodialog <filename>'
    sys.exit(1)

dom = xml.dom.minidom.parse(sys.argv[1])
elements = dom.getElementsByTagName('g')
dialogs = {}

for element in elements:
    label = element.getAttribute('inkscape:label')
    if label.startswith('dialog:'):
        name = label[7:]
        dialogs[name] = process_dialog(name, element)

elements = dom.getElementsByTagName('svg')
width = int(elements[0].getAttribute('width'))
height= int(elements[0].getAttribute('height'))

print '<freevo>'
indent = '    '
print '%s<osds geometry="%dx%d">' % (indent, width, height)
for name,dialog in dialogs.items():
    print dialog.to_xml(indent, 2)

print '%s</osds>' % indent
print '</freevo>'
