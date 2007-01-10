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

	Command moreCommand;
	Command numericCommand;
	Command textCommand;
	Command mainCommand;

	Command submenuCommand;
	Command refreshCommand;
	Command menuBackCommand;

	Image folderImage;
	Image fileImage;
	
	public BrowseForm(Controller controller) {
		super("Menu", List.IMPLICIT);
		this.controller = controller;
		setCommandListener(this);

		menuBackCommand = new Command("Back Menu", Command.CANCEL, 0);
		addCommand(menuBackCommand);

		submenuCommand = new Command("Submenu", "Options submenu", Command.SCREEN, 2);
		addCommand(submenuCommand);

		refreshCommand = new Command("Refresh", "Refresh menu", Command.SCREEN, 2);
		addCommand(refreshCommand);
		
		mainCommand = new Command("Main", "Main actions", Command.SCREEN, 2);
		addCommand(mainCommand);

		numericCommand = new Command("Numeric", "Numeric keys", Command.SCREEN, 2);
		addCommand(numericCommand);
		
		moreCommand = new Command("More", "More actions", Command.SCREEN, 2);
		addCommand(moreCommand);

		textCommand = new Command("Text", "Send Text", Command.SCREEN, 2);
		addCommand(textCommand);
		
		try {
			folderImage = Image.createImage("/entry.png");
			fileImage = Image.createImage("/file.png");
		} catch (IOException e) {
			// no image found... hm
		}
	}
	
	void updateDirList(String[] dirs, boolean dirChanged) {
		
		int index = 0;

		index = size();
		while ( index-- > 0 )
		    delete(index);

		for (index=0; index < dirs.length; index++) {
			String name = dirs[index];
			insert(index, name, folderImage);
			setFont(index, Font.getFont(Font.FACE_SYSTEM, Font.STYLE_PLAIN, Font.SIZE_SMALL));
		}
		
	}
	
	public void commandAction(Command cmd, Displayable display) {
		if (cmd == menuBackCommand) {
			controller.protocol.fileBrowser.menuBack();
		}
		else if (cmd == refreshCommand) {
			controller.protocol.fileBrowser.requestMenu();
		}
		else if (cmd == submenuCommand) {
			controller.protocol.fileBrowser.menuSubmenu();
		}
		else if (cmd == mainCommand) {
			controller.showController();
		}
		else if (cmd == numericCommand) {
			controller.showNumericForm();
		}
		else if (cmd == moreCommand) {
			controller.showMoreActions();
		}
		else if (cmd == textCommand) {
			controller.showTextForm();
		}
		else if (cmd == List.SELECT_COMMAND) {
            String str = Integer.toString(getSelectedIndex(), 10);
		    controller.protocol.fileBrowser.sendMenuItemSelected(str);
		}


	}

}
