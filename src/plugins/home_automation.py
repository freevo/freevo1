import os  
import plugin
import config

from item import Item

class PluginInterface(plugin.MainMenuPlugin):
    """
    Home Automation Plugin
    
    Activate:
    plugin.activate('home_automation')
    
    This plugin is for controlling home automation items, such as X10 devices.
    It uses external programs to control the hardware.
    
    Configuration is as follows:
    ('ROOM NAME/LOCATION'('FUNCTION','COMMAND TO RUN'))

    In the following example I demonstrate using this plugin with the heyu application.

    Example local_conf.py configuration:

     AUTOMATION_ITEMS = [('Living Room',
                         (
                         ('Lights',('On','heyu on a2','Off','heyu off a2','Brighten','heyu bright a2 1','Dim','heyu dim a2 1')),
                         ('TV',('On','heyu','Off','heyu'))
                         )),
                         ('Porch',
                         (
                         ('Light',('On','heyu','Off','heyu'))
                         ))]
    
 
    """

    def __init__(self):
        if not hasattr(config, 'AUTOMATION_ITEMS'):
            self.reason = 'AUTOMATION_ITEMS not defined'
            return
        plugin.MainMenuPlugin.__init__(self)


    def items(self, parent):
        return [ HomeAutomationMainMenu(parent) ]

class AutomationItem(Item):
    """
    Item for the menu for one room
    """
    def __init__(self, parent):
        Item.__init__(self, parent)
    
    def actions(self):
        """
        return a list of actions for this item
        """
        items = [ ( self.getroomdevices, _('Room Items') ) ]
        return items

    def getroomdevices(self, arg=None, menuw=None):
        room_devices = []
        for device in self.room_items:
            room_device = RoomDevice(self)
            room_device.name = device[0]            
            room_device.functions = device[1]
            room_devices += [ room_device ]
        room_devices_menu = menu.Menu(_('Home Automation Devices'), room_devices)
        menuw.pushmenu(room_devices_menu)
        menuw.refresh()

class RoomDevice(Item):
    """
    Item for the menu for one room
    """
    def __init__(self, parent):
        Item.__init__(self, parent)

    def actions(self):
        """
        return a list of actions for this item
        """
        items = [ ( self.getdeviceoptions, _('Device Options') ) ]
        return items

    def getdeviceoptions(self, arg=None, menuw=None):
        device_options = []
        device_name = []
        device_index = 0
        for option in self.functions:
            device_option = DeviceOptions(self)
            device_index = device_index + 1
            if device_index % 2:
                device_name = option
            else: 
                device_option.name = device_name
                device_option.cmd = option
                device_options += [ device_option ]
        device_options_menu = menu.Menu(_('Device Options'), device_options)
        menuw.pushmenu(device_options_menu)
        menuw.refresh()

class DeviceOptions(Item):
    """
    Item for the menu for one room
    """
    def __init__(self, parent):
        Item.__init__(self, parent)

    def actions(self):
        """
        return a list of actions for this item
        """
        return [ ( self.runcmd , _('Run Command') ) ]
        
    def runcmd(self, arg=None, menuw=None):
        """
        Run Command
        """
        os.system(self.cmd)

class HomeAutomationMainMenu(Item):
    """
    this is the item for the main menu and creates the list of rooms.
    """
    def __init__(self, parent):
        Item.__init__(self, parent, skin_type='homeautomation')
        self.name = _('Home Automation')
    

    def actions(self):
        """
        return a list of actions for this item
        """
        items = [ ( self.create_automation_items_menu , _('Home Automation' )) ]
        return items

    def create_automation_items_menu(self, arg=None, menuw=None):
        automation_items = []
        for room in config.AUTOMATION_ITEMS:
            automation_item = AutomationItem(self)
            automation_item.name = room[0]
            automation_item.room_items = room[1]
            automation_items += [ automation_item ]
        if (len(automation_items) == 0):
            automation_items += [menu.MenuItem(_('No Home Automation items found'), menuw.goto_prev_page, 0)]
        automation_items_menu = menu.Menu(_('Home Automation'), automation_items)
        menuw.pushmenu(automation_items_menu)
        menuw.refresh()



 	  	 
