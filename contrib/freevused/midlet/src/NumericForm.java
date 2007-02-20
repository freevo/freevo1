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
public class NumericForm extends Form implements CommandListener, ItemCommandListener {

	Controller controller;
	Command disconnectCommand;
	Command shutdownCommand;

	Command textCommand;
	Command mainCommand;
	Command moreCommand;
	Command browseCommand;
	Command getItemDataCommand;
	
	StringItem titleItem;
	StringItem statusItem;
	NavigationWidget naviItem;

	Translate t;

	/**
	 * @param arg0
	 */
	public NumericForm(Controller controller) {
		super("Freevused");

		t = Translate.getInstance();

		this.controller = controller;

		
		setCommandListener(this);
		
		naviItem = new NavigationWidget(controller, NavigationWidget.NUMERIC_KEYS, getWidth(), -1);

		naviItem.setLayout(naviItem.getLayout() | Item.LAYOUT_CENTER);

		statusItem = new StringItem(null, t.get("Press any key to control"));
		statusItem.setLayout(statusItem.getLayout() | Item.LAYOUT_CENTER);
		statusItem.setPreferredSize(getWidth(), -1);
		statusItem.setFont(Font.getFont(Font.FACE_SYSTEM, Font.STYLE_BOLD, Font.SIZE_SMALL));

		append(naviItem);
		append(statusItem);
		
		mainCommand = new Command(t.get("Main"), t.get("Main actions"), Command.CANCEL, 0);
		addCommand(mainCommand);
		
		moreCommand = new Command(t.get("More"), t.get("More actions"), Command.SCREEN, 2);
		addCommand(moreCommand);

		browseCommand = new Command(t.get("Browse"), t.get("Browse menu"), Command.SCREEN, 2);
		addCommand(browseCommand);

		textCommand = new Command(t.get("Text"), t.get("Send text"), Command.SCREEN, 2);
		addCommand(textCommand);

		getItemDataCommand = new Command(t.get("Get data"), t.get("Get item data"), Command.SCREEN, 2);
		addCommand(getItemDataCommand); 


	}

	public void setStatus(BemusedProtocol.ItemData itemdata) {
		statusItem.setText(itemdata.data);
	}
	
	public void commandAction(Command cmd, Displayable d) {
		if (cmd == mainCommand) {
			controller.showController();
		}
		else if (cmd == disconnectCommand) {
			controller.disconnect();
		}
		else if (cmd == shutdownCommand) {
			controller.getPlayer().shutdownSystem();
		}
		else if (cmd == mainCommand) {
			controller.showController();
		}
		else if (cmd == moreCommand) {
			controller.showMoreActions();
		}
		else if (cmd == textCommand) {
			controller.showTextForm();
		}
		else if (cmd == browseCommand) {
			controller.showBrowseForm();
		}
		else if (cmd == getItemDataCommand) {
			controller.getPlayer().requestItemData();
		}
	}

	public void commandAction(Command cmd, Item item) {
	}
}
