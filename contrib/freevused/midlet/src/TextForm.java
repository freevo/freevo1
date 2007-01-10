import java.io.IOException;

import javax.microedition.lcdui.Command;
import javax.microedition.lcdui.CommandListener;
import javax.microedition.lcdui.Displayable;
import javax.microedition.lcdui.Font;
import javax.microedition.lcdui.Form;
import javax.microedition.lcdui.Item;
import javax.microedition.lcdui.List;
import javax.microedition.lcdui.TextBox;
import javax.microedition.lcdui.TextField;


/*
 * Created February 2006
 */

/**
 * @author gorka olaizola
 */
public class TextForm extends TextBox implements CommandListener  {

	Controller controller;

	Command mainCommand;
	Command sendCommand;
	Command moreCommand;
	Command numericCommand;
	Command browseCommand;

	TextBox textBox;

	public TextForm(Controller controller) {
		super("Enter text", "", 40, TextField.ANY);
		this.controller = controller;
		setCommandListener(this);

		sendCommand = new Command("Send", "Send text to Freevo", Command.SCREEN, 0);
		addCommand(sendCommand);

		numericCommand = new Command("Numeric", "Numeric keys", Command.SCREEN, 2);
		addCommand(numericCommand);

		moreCommand = new Command("More", "More actions", Command.SCREEN, 2);
		addCommand(moreCommand);

		browseCommand = new Command("Browse", "Browse Menu", Command.SCREEN, 2);
		addCommand(browseCommand);
		
		mainCommand = new Command("Main", "Main actions", Command.CANCEL, 0);
		addCommand(mainCommand);

		textBox = new TextBox("Send this to Freevo", "", 20, 0);

		
	}
	
	public void commandAction(Command cmd, Displayable display) {
		if (cmd == mainCommand) {
			controller.showController();
		}
		else if (cmd == sendCommand) {
			controller.protocol.sendText(this.getString());
			controller.showController();
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
	}

}
