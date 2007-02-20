import java.io.IOException;

import javax.microedition.io.StreamConnection;
import javax.microedition.lcdui.Display;

import protocol.MusicPlayer;
import protocol.ProtocolStatus;
import protocol.StatusUpdateListener;

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
public class Controller implements StatusUpdateListener {
	Main owner;
	SearchForm searchForm;
	ControlForm controlForm;
	BrowseForm browseForm;
	TextForm textForm;
	MoreActionsForm moreActionsForm;
	NumericForm numericForm;

	Settings settings;
	StreamConnection currentConnection;
	BemusedProtocol protocol;
	
	public Controller(Main owner) {
		this.owner = owner;
		protocol = new BemusedProtocol(Display.getDisplay(owner));
		protocol.registerStatusUpdateListener(this);
		settings = new Settings();
		searchForm = new SearchForm(this);
		controlForm = new ControlForm(this);
		browseForm = new BrowseForm(this);
		textForm = new TextForm(this);
		moreActionsForm = new MoreActionsForm(this);
		numericForm = new NumericForm(this);
	}

	Settings getSettings() {
		return settings;
	}

	public void start() {
		Display.getDisplay(owner).setCurrent(searchForm);
	}

	public void showController() {
		Display.getDisplay(owner).setCurrent(controlForm);				
	}

	public void showTextForm() {
		textForm.setString("");	
		Display.getDisplay(owner).setCurrent(textForm);
	}

	public void showMoreActions() {
		Display.getDisplay(owner).setCurrent(moreActionsForm);
	}

	public void showNumericForm() {
		Display.getDisplay(owner).setCurrent(numericForm);
	}

	public void showBrowseForm() {
		showBrowser(true);
	}

	public void showBrowser(boolean refresh) {
		if (refresh) protocol.fileBrowser.requestMenu();
		Display.getDisplay(owner).setCurrent(browseForm);
	}

	
	public void exit() {
		owner.destroyApp(false);
		owner.notifyDestroyed();
	}
	
	void destroy() {
		disconnect();
		settings.save();
		if (protocol != null) {
			//protocol.destroy();
			protocol = null;
		}
	}
	
	void connectTo(String url, String name) {
		settings.setLastUsedDevice(url, name);
		settings.save();
		protocol.setConnectionURL(url);
	}
	
	void disconnect() {	
		protocol.closeConnection();
	}
	
	/* (non-Javadoc)
	 * @see bemused.StatusUpdateListener#bemusedStatusChanged(bemused.BemusedProtocol)
	 */
	public void bemusedStatusChanged(ProtocolStatus status) {
		Display display = Display.getDisplay(owner);
		if (status.connected && (display.getCurrent() == searchForm)) {
			display.setCurrent(controlForm);
		}
		else if (status.connected == false && (display.getCurrent() != searchForm)) {
			display.setCurrent(searchForm);
		}
		
		browseForm.updateDirList(protocol.fileBrowser.dirs(), protocol.fileBrowser.dirChanged());

		controlForm.setStatus(protocol.itemdata);
		numericForm.setStatus(protocol.itemdata);
		moreActionsForm.setStatus(protocol.itemdata);
	}

	MusicPlayer getPlayer() {
		return protocol;
	}
	
}
