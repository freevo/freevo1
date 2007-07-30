import java.util.Date;

import javax.microedition.lcdui.ChoiceGroup;
import javax.microedition.lcdui.Command;
import javax.microedition.lcdui.CommandListener;
import javax.microedition.lcdui.CustomItem;
import javax.microedition.lcdui.Displayable;
import javax.microedition.lcdui.Font;
import javax.microedition.lcdui.Form;
import javax.microedition.lcdui.Item;
import javax.microedition.lcdui.Spacer;
import javax.microedition.lcdui.ItemCommandListener;
import javax.microedition.lcdui.StringItem;

import bemused.BemusedProtocol;
import translate.Translate;

/*
 * Created on May 24, 2004
 *
 * To change the template for this generated file go to
 * Window&gt;Preferences&gt;Java&gt;Code Generation&gt;Code and Comments
 */

/**
 * @author fred
 *
 * To change the template for this generated type comment go to
 * Window&gt;Preferences&gt;Java&gt;Code Generation&gt;Code and Comments
 */
public class ControlForm extends Form implements CommandListener, ItemCommandListener {

	Controller controller;
	Command exitCommand;
	Command disconnectCommand;
	Command shutdownCommand;

	Command textCommand;
	Command numericCommand;
	Command moreCommand;
	Command browseCommand;
	Command getItemDataCommand;
	
	StringItem statusItem;
	NavigationWidget naviItem;
	
	String[] lastPlaylistItems;
	int lastPlaylistPos;

	Translate t = Translate.getInstance();
	
	/**
	 * @param arg0
	 */
	public ControlForm(Controller controller) {
		super("Freevused");

		this.controller = controller;

		setCommandListener(this);
		
		naviItem = new NavigationWidget(controller, NavigationWidget.CONTROL_KEYS, getWidth(), -1);
		naviItem.setLayout(naviItem.getLayout() | Item.LAYOUT_CENTER);

		statusItem = new StringItem(null, t.get("Press any key to control"));
		statusItem.setLayout(statusItem.getLayout() | Item.LAYOUT_CENTER);
		statusItem.setPreferredSize(getWidth(), -1);
		statusItem.setFont(Font.getFont(Font.FACE_SYSTEM, Font.STYLE_BOLD, Font.SIZE_SMALL));
		
		append(naviItem);
		append(statusItem);
		
		exitCommand = new Command(t.get("Exit"), Command.EXIT, 2);
		addCommand(exitCommand);

		numericCommand = new Command(t.get("Numeric"), t.get("Numeric keys"), Command.SCREEN, 2);
		addCommand(numericCommand);

		moreCommand = new Command(t.get("More"), t.get("More actions"), Command.SCREEN, 2);
		addCommand(moreCommand);

		textCommand = new Command(t.get("Text"), t.get("Send text"), Command.SCREEN, 2);
		addCommand(textCommand);

		browseCommand = new Command(t.get("Browse"), t.get("Browse menu"), Command.SCREEN, 2);
		addCommand(browseCommand); 

		getItemDataCommand = new Command(t.get("Get data"), t.get("Get item data"), Command.SCREEN, 2);
		addCommand(getItemDataCommand); 

		/*

		shutdownCommand = new Command("Shutdown", "System shutdown", Command.SCREEN, 5);
		addCommand(shutdownCommand);

		playlistCommand = new Command("Playlist", "Show playlist", Command.SCREEN, 1);
		addCommand(playlistCommand);
		
		disconnectCommand = new Command("Disconnect", Command.SCREEN, 4);
		addCommand(disconnectCommand);
		
		browseCommand = new Command("Browse", "Browse Music", Command.SCREEN, 2);
		addCommand(browseCommand);
		
		shuffleCommand = new Command("Shuffle", "Toggle shuffle", Command.SCREEN, 3);
		addCommand(shuffleCommand);
		
		repeatCommand = new Command("Repeat", "Toggle repeat", Command.SCREEN, 3);
		addCommand(repeatCommand);
		
		

		controller.getPlayer().refreshPlaylist();
		*/
	}
	
	public void setStatus(BemusedProtocol.ItemData itemdata) {
		statusItem.setText(itemdata.data);
	}
	
	public void commandAction(Command cmd, Displayable d) {
		if (cmd == exitCommand) {
			controller.exit();
		}
		else if (cmd == disconnectCommand) {
			controller.disconnect();
		}
		else if (cmd == shutdownCommand) {
			controller.getPlayer().shutdownSystem();
		}
		else if (cmd == textCommand) {
			controller.showTextForm();
		}
		else if (cmd == moreCommand) {
			controller.showMoreActions();
		}
		else if (cmd == numericCommand) {
			controller.showNumericForm();
		}
		else if (cmd == browseCommand) {
			controller.showBrowseForm();
		}
		else if (cmd == getItemDataCommand) {
			controller.getPlayer().requestItemData();
		}
		/*
		else if (cmd == playlistCommand) {
			controller.showPlaylist();
		}
		else if (cmd == shuffleCommand) {
			controller.protocol.toggleShuffle();
		}
		else if (cmd == repeatCommand) {
			controller.protocol.toggleRepeat();
		}
		*/
	}

	public void commandAction(Command cmd, Item item) {
	}
}
