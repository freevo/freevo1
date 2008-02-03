/*
 * Created on Apr 6, 2004
 *
 * To change the template for this generated file go to
 * Window&gt;Preferences&gt;Java&gt;Code Generation&gt;Code and Comments
 */

import javax.microedition.lcdui.*;
import javax.microedition.midlet.*;

//import java.util.TimerTask;
//import java.util.Timer;

/**
 * @author fred
 *
 * To change the template for this generated type comment go to
 * Window&gt;Preferences&gt;Java&gt;Code Generation&gt;Code and Comments
 */

public class Main 
extends MIDlet {

	//private Form mMainForm;
	private StringItem stateItem;
	private Command exitCommand;
	private Command connectCommand;
	private Command disconnectCommand;
	//private Timer updateTimer;
	private Controller controller;
	
	public Main() {
		System.out.println("Main.Main()");
		controller = new Controller(this);
		
		//mForm = new Form("Bemused");

		// Add commands
		//mMainForm.setCommandListener(this);		
		//exitCommand = new Command("Exit", Command.EXIT, 1);
		//mMainForm.addCommand(exitCommand);
		//connectCommand = new Command("Connect", Command.ITEM, 0);
		//mMainForm.addCommand(connectCommand);
		//disconnectCommand = new Command("Disconnect", Command.ITEM, 0);
		//mMainForm.addCommand(disconnectCommand);

		// Add widgets
		//stateItem = new StringItem(null, " ");
		//mMainForm.append(stateItem);

		//updateStateDisplay();
	}

	/*private void updateStateDisplay() {
		stateItem.setText("Disconnected");
	}*/

	public void startApp() {
		System.out.println("Main.startApp()");
		controller.start();
	}

	public void pauseApp() {
		System.out.println("Main.pauseApp()");
	}

	public void destroyApp(boolean unconditional) {
		controller.destroy();
	}

	/*public void commandAction(Command c, Displayable s) {
		if (c == exitCommand) {
			notifyDestroyed();
		}
		else if (c == connectCommand) {
			connect();
		}
		else if (c == disconnectCommand) {
			disconnect();
		}
	}*/

	/*private void connect() {
		DiscoveryAgent agent;
		String connectURL = "null";
		try {
			agent = LocalDevice.getLocalDevice().getDiscoveryAgent();
			connectURL = agent.selectService(
				new UUID("1101", true),
				ServiceRecord.NOAUTHENTICATE_NOENCRYPT, false);
		} catch (BluetoothStateException e) {
			e.printStackTrace();
		}
		System.out.println("Connect URL: "+connectURL);

		if (connectURL != null) {			
			try {
				//StreamConnection c = (StreamConnection)Connector.open(connectURL);
				protocol = new BemusedProtocol();
				protocol.setConnectionURL(connectURL);
			} catch (IOException e1) {
				e1.printStackTrace();
			}
	
			
			TimerTask updateTimerTask = new TimerTask() {
				public void run() {
					Main.this.updateStatus();
				}
			};
			updateTimer = new Timer();
			updateTimer.schedule(updateTimerTask, 0, 2000);
		}

	}*/


	private void destroy() {
		//if (updateTimer != null) updateTimer.cancel();
		//updateTimer = null;
	}
	
	private void updateStatus() {
		
	}

}
