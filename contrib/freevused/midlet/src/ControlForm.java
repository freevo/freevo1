import java.util.Date;

import javax.microedition.lcdui.ChoiceGroup;
import javax.microedition.lcdui.Command;
import javax.microedition.lcdui.CommandListener;
import javax.microedition.lcdui.CustomItem;
import javax.microedition.lcdui.Displayable;
import javax.microedition.lcdui.Font;
import javax.microedition.lcdui.Form;
import javax.microedition.lcdui.Item;
import javax.microedition.lcdui.ItemCommandListener;
import javax.microedition.lcdui.StringItem;

import bemused.BemusedProtocol;

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
	
	StringItem titleItem;
	StringItem statusItem;
	NavigationWidget naviItem;
	
	String[] lastPlaylistItems;
	int lastPlaylistPos;
	
	/**
	 * @param arg0
	 */
	public ControlForm(Controller controller) {
		super("Freevused");
		this.controller = controller;
		
		setCommandListener(this);
		
		naviItem = new NavigationWidget(controller);
		titleItem = new StringItem(null, "---");
		statusItem = new StringItem(null, "Press any key to control");

		//titleItem.setLayout(titleItem.getLayout() | ChoiceGroup.HYPERLINK);
		//titleItem.setLayout(titleItem.getLayout() | 
		//		Item.LAYOUT_CENTER | Item.LAYOUT_NEWLINE_AFTER);
		
		statusItem.setLayout(statusItem.getLayout() | 
				Item.LAYOUT_CENTER | Item.LAYOUT_NEWLINE_AFTER);
		
		//append(titleItem);
		append(naviItem);
		append(statusItem);
		
		exitCommand = new Command("Exit", Command.EXIT, 2);
		addCommand(exitCommand);

		numericCommand = new Command("Numeric", "Numeric keys", Command.SCREEN, 2);
		addCommand(numericCommand);

		moreCommand = new Command("More", "More actions", Command.SCREEN, 2);
		addCommand(moreCommand);

		textCommand = new Command("Text", "Send Text", Command.SCREEN, 2);
		addCommand(textCommand);

		browseCommand = new Command("Browse", "Browse Menu", Command.SCREEN, 2);
		addCommand(browseCommand); 

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
	
	public void setStatus(BemusedProtocol.PlaybackStatus s) {
		titleItem.setText(s.title);
		
		String lenText;
		if (s.songLengthSecs >= 60) {
			lenText = "" + ((s.songLengthSecs/60 > 9) ? ("" + s.songLengthSecs/60) : ("0" + s.songLengthSecs/60)) + ":"
			+ ((s.songLengthSecs%60 > 9) ? ("" + s.songLengthSecs%60) : ("0" + s.songLengthSecs%60));
		}
		else {
			lenText = ""+s.songLengthSecs;
		}
		
		long songPosSecs = (new Date().getTime() - s.startTime.getTime())/1000;
		String posText;
		if (s.songLengthSecs >= 60) {
			posText = "" + ((songPosSecs/60 > 9) ? ("" + songPosSecs/60) : ("0" + songPosSecs/60)) + ":"
			+ ((songPosSecs%60 > 9) ? ("" + songPosSecs%60) : ("0" + songPosSecs%60));
		}
		else {
			posText = ""+songPosSecs;
		}
		
		String statusText = (s.playing?"playing":"not playing")+ 
			" " +  posText + " of " + lenText + 
			(s.shuffle?" [shuf]":"") + (s.repeat?" [repeat]":"")/*+" v:"+s.volume+
			" pp:"+s.playlistPos+" pl:"+s.playlist.length+" sp:"+songPosSecs+" sl:"+
			s.songLengthSecs*/;
		statusText = "";
		statusItem.setText(statusText);
		
		naviItem.setPlaylistPos(s.playlistPos, s.playlist.length-1);
		naviItem.setTrackPos((int)songPosSecs, (int)s.songLengthSecs);
		naviItem.setVolume(s.volume);
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
