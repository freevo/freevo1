import java.io.IOException;

import javax.microedition.lcdui.Command;
import javax.microedition.lcdui.CommandListener;
import javax.microedition.lcdui.Displayable;
import javax.microedition.lcdui.Form;
import javax.microedition.lcdui.List;
import javax.microedition.lcdui.Choice;


/*
 * Created February 2006
 */

/**
 * @author gorka olaizola
 */
public class MoreActionsListForm extends List implements CommandListener  {

	Controller controller;

	Command backCommand;
	Command sendCommand;

	static final String [] ITEM_NAME = {
	  "Change display", "Eject Disc", "Detach audio", "CH+", "CH-", "1", "2", "3", "4", "5", "6", "7", "8",
	  "9", "0"
	};
	static final String [] ITEM_ID = {
	  "DISP", "EJEC", "DEAU", "CHA+", "CHA-", "NUM1", "NUM2", "NUM3", "NUM4", "NUM5", "NUM6",
	  "NUM7", "NUM8", "NUM9", "NUM0"
	};

	int i;

	public MoreActionsListForm(Controller controller) {
		super("Select action", Choice.IMPLICIT);
		this.controller = controller;
		setCommandListener(this);

		for (i=0; i< ITEM_NAME.length; i++) {
		  append (ITEM_NAME[i], null);
		}	

		backCommand = new Command("Back", "Back to main screen", Command.CANCEL, 0);
		addCommand(backCommand);

	}
	
	public void commandAction(Command cmd, Displayable display) {
		if (cmd == backCommand) {
			controller.showController();
		}
		else if (cmd == List.SELECT_COMMAND) {
			controller.protocol.sendAction( ITEM_ID[getSelectedIndex()] );
		}
	}

}
