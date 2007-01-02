import java.io.IOException;

import javax.microedition.lcdui.Command;
import javax.microedition.lcdui.CommandListener;
import javax.microedition.lcdui.Displayable;
import javax.microedition.lcdui.Font;
import javax.microedition.lcdui.Form;
import javax.microedition.lcdui.Item;
import javax.microedition.lcdui.List;
import javax.microedition.lcdui.Image;

/*
 * Created August 2004
 */

/**
 * @author johan köhne
 */
public class BrowseForm extends List implements CommandListener  {

	Controller controller;
	Command menuSelectCommand;
	Command menuSubmenuCommand;
	Command menuMainCommand;
	Command menuBackCommand;
	Command menuQuitCommand;
	Image folderImage;
	Image fileImage;
	
	public BrowseForm(Controller controller) {
		super("Browser", List.IMPLICIT);
		this.controller = controller;
		setCommandListener(this);
		
		menuSelectCommand = new Command("Select", Command.ITEM, 1);
		addCommand(menuSelectCommand);
		
		menuSubmenuCommand = new Command("Submenu", "Submenu", Command.ITEM, 2);
		addCommand(menuSubmenuCommand);

		menuMainCommand = new Command("Mainmenu", "Go to Main", Command.ITEM, 3);
		addCommand(menuMainCommand);
		
		menuBackCommand = new Command("Back", Command.BACK, 1);
		addCommand(menuBackCommand);

		menuQuitCommand = new Command("Quit", "Quit Browser", Command.SCREEN, 1);
		addCommand(menuQuitCommand);
		
		
		try {
			folderImage = Image.createImage("/folder.png");
			fileImage = Image.createImage("/file.png");
		} catch (IOException e) {
			// no image found... hm
		}
	}
	
	void updateDirList(String[] dirs, boolean dirChanged) {
		
		int n, i, index = 0;
		
		for (n=0; n < dirs.length; ++n) {
			String name = dirs[n];
			if (index < size()) {
				set(index, name, folderImage);
			}
			else {
				insert(index, name, folderImage);
			}
			setFont(index, Font.getFont(Font.FACE_SYSTEM, Font.STYLE_PLAIN, Font.SIZE_SMALL));
			index++;
		}
		
		// setTitle
		// setTitle(controller.protocol.fileBrowser.activeDir());

		// if we just changed dir, set selected item to the first again		
		/*
		if (size() > 0 && dirChanged) {
			setSelectedIndex(0, true);
		}
		*/
	}
	
	public void commandAction(Command cmd, Displayable display) {
		if (cmd == menuBackCommand) {
			controller.protocol.fileBrowser.menuBack();
		}
		else if (cmd == menuSelectCommand) {
			controller.protocol.fileBrowser.menuSelect();
		}
		else if (cmd == menuSubmenuCommand) {
			controller.protocol.fileBrowser.menuSubmenu();
		}
		else if (cmd == menuMainCommand) {
			controller.protocol.fileBrowser.menuMain();
		}
		else if (cmd == menuQuitCommand) {
			controller.showController();
		}
	}

}
