package bemused;

import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.io.IOException;
// import java.io.UnsupportedEncodingException;
import java.util.Date;
import java.util.Enumeration;
import java.util.Timer;
import java.util.TimerTask;
import java.util.Vector;
import java.lang.Byte;

import javax.microedition.io.Connector;
import javax.microedition.io.StreamConnection;
import javax.microedition.lcdui.Display;
import javax.microedition.lcdui.Alert;
import javax.microedition.lcdui.AlertType;

import protocol.*;
import protocol.MusicPlayer;

import translate.Translate;

/*
 * Created on Apr 20, 2004
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
public class BemusedProtocol implements MusicPlayer {
	String connectionURL;
	StreamConnection connection;
	DataInputStream iStream;
	DataOutputStream oStream;
	Display display;
	Thread readWriteThread;
	boolean reconnect;
	Integer runSignal;
	Vector statusUpdateListeners;
	ProtocolStatus status;
	Vector cmdQueue;
	MyCommandTarget commandTarget;
	Timer statusUpdateTimer;

	public Browser fileBrowser;
	
	public class PlaybackStatus {
		public PlaybackStatus() {
			playing = false;
			repeat = false;
			shuffle = false;
			startTime = new Date();
			songLengthSecs = 0;
			title = "<no title>";
		}
		public boolean playing;
		public boolean shuffle;
		public boolean repeat;
		public Date startTime;
		public long songLengthSecs;
		public String title;
		public String[] playlist;
		public int playlistPos;
		public int volume;
	}
	PlaybackStatus currentStatus;

	public class ItemData {
		public String data;
		private Translate t;

		public ItemData() {
			t = Translate.getInstance();
			data =  t.get("Press any key to control");
		}
	}
	public ItemData itemdata;
	
	public BemusedProtocol(Display display) {
		status = new ProtocolStatus();
		statusUpdateTimer = new Timer();
		currentStatus = new PlaybackStatus();
		commandTarget = new MyCommandTarget();
		currentStatus.playlist = new String[0];

		itemdata = new ItemData();

		this.display = display;
		runSignal = new Integer(0);
		statusUpdateListeners = new Vector();
		cmdQueue = new Vector();

		fileBrowser = new Browser(this);
		
		Runnable runnable = new Runnable() {
			public void run() {
				BemusedProtocol.this.run();	
			}
		};
		reconnect = true;
		readWriteThread = new Thread(runnable);
		readWriteThread.start();

	}
	
	public void infoAlert(String title, String msg, int timeout) {
		Alert alert = new Alert (title, msg, null, AlertType.INFO);
		alert.setTimeout (timeout);
		display.setCurrent(alert);
	}
	
	private void run() {
		while (reconnect == true) {
			try {
				synchronized (runSignal) {
					runSignal.wait();					
				}
				openConnection();
				do {
					doNextCommand();
					synchronized (runSignal) {
						runSignal.wait();
					}
				} while (reconnect == true);
			} catch (IOException e) {
				closeConnection();
				continue;			
			} catch (InterruptedException e) {
				e.printStackTrace();
				throw new RuntimeException("InterruptedExcpetion caught: "+e.getMessage());	
			}
		}
	}
	
	void openConnection() throws IOException {
		closeConnection();
		if (connectionURL != null) {
			connection = (StreamConnection)Connector.open(connectionURL);
			iStream = connection.openDataInputStream();
			oStream = connection.openDataOutputStream();
			status.connected = true;
			notifyStatusUpdate();
		}
		else {
			throw new IOException("Bemused connection URL is null");
		}
	}
	
	public void setConnectionURL(String url) {
		closeConnection();
		synchronized (runSignal) {
			runSignal.notifyAll();
		}		
		this.connectionURL = url;
	}
	
	public void closeConnection() {
		try {
			if (iStream != null) iStream.close();
			if (oStream != null) oStream.close();
			if (connection != null) connection.close();
		} catch (IOException e) {
			// Might be closed already, doesn't matter.
		}
		connection = null;
		iStream = null;
		oStream = null;
		synchronized (runSignal) {
			runSignal.notifyAll();
		}		
		status.connected = false;
		notifyStatusUpdate();
	}
	
	void doNextCommand() throws IOException {
		for (Command cmd = getNextCommand(); cmd != null; cmd = getNextCommand()) {
			try {
				cmd.execute(commandTarget);
			} catch (BemusedProtocolException e) {
				throw new IOException("Bemused Exception: "+e.getMessage());
			}
		}
	}
	
	Command getNextCommand() {
		synchronized (cmdQueue) {
			if (cmdQueue.isEmpty() == false) {
				Command ret = (Command)cmdQueue.elementAt(0);
				cmdQueue.removeElementAt(0);
				return ret;
			}
			else return null;
		}
	}
	
	public void destroy() {
    	closeConnection();
    	statusUpdateTimer.cancel();
    	synchronized (runSignal) {
			runSignal.notifyAll();
		}
		try {
			readWriteThread.join();
		} catch (InterruptedException e) {
			e.printStackTrace();
			throw new RuntimeException("InterruptedException caught: "+e.getMessage());	
		}
		statusUpdateListeners.removeAllElements();
	}
	
	public void registerStatusUpdateListener(StatusUpdateListener listener) {
		statusUpdateListeners.addElement(listener);
	}
	
	void notifyStatusUpdate() {
		display.callSerially(new Runnable() { public void run() {
			for (Enumeration e = statusUpdateListeners.elements(); e.hasMoreElements();) {
				StatusUpdateListener listener = (StatusUpdateListener)e.nextElement();
				listener.bemusedStatusChanged(BemusedProtocol.this.status);
			}
		}});
	}
	
	class MyCommandTarget implements CommandTarget {
	
		public DataInputStream getInputStream() {
			return iStream;
		}
	
		public DataOutputStream getOutputStream() {
			return oStream;
		}

		public void setDirInfo(String[] contents) {
			fileBrowser.setDirInfo(contents);
		}

		public void setStatus(String data) {
			itemdata.data = data;

			notifyStatusUpdate();
		}

	}

	void appendCommand(Command cmd) {
		synchronized (cmdQueue) {
			cmdQueue.addElement(cmd);
		}
		synchronized (runSignal) {
			runSignal.notifyAll();
		}		
	}

	public void play() {
		appendCommand(new Command("STRT"));
	}

	public void stop() {
		appendCommand(new Command("STOP"));
	}
	
	public void pause() {
		appendCommand(new Command("PAUS"));
	}

	public void next() {
		appendCommand(new Command("NEXT"));
	}

	public void previous() {
		appendCommand(new Command("PREV"));
	}

	public void shutdownSystem() {
		appendCommand(new Command("SHUT"));
	}

	public void rewind() {
		appendCommand(new Command("RWND"));
	}
	
	public void forward() {
		appendCommand(new Command("FFWD"));
	}
	
	public void submenu() {
		appendCommand(new Command("SLCT"));
	}

	public void mainMenu() {
		appendCommand(new Command("MAIN"));
	}
	
	public void volumeLouder() {
		appendCommand(new Command("VOL+"));
	}

	public void volumeQuieter() {
		appendCommand(new Command("VOL-"));
	}

	public void volumeMute() {
		appendCommand(new Command("VOLM"));
	}

	public void sendText(String txt) {
		appendCommand(new Command("TEXT", txt));
	}

	public void sendAction(String action) {
		appendCommand(new Command(action));
	}

	public void sendMenuItemSelected(String idx) {
		appendCommand(new Command("MITM", idx));
	}

	public void requestMenu() {
		appendCommand(new Command("MSND"));
	}

	public void requestItemData() {
		appendCommand(new Command("STAT"));
	}

}

