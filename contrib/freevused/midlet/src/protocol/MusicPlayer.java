/*
 * Created on May 25, 2004
 *
 * To change the template for this generated file go to
 * Window&gt;Preferences&gt;Java&gt;Code Generation&gt;Code and Comments
 */
package protocol;

/**
 * @author fred
 *
 * To change the template for this generated type comment go to
 * Window&gt;Preferences&gt;Java&gt;Code Generation&gt;Code and Comments
 */
public interface MusicPlayer {
	void play();
	void stop();
	void pause();
	void next();
	void previous();
	void rewind();
	void forward();
	void registerStatusUpdateListener(StatusUpdateListener listener);
	void submenu();
	void mainMenu();
	void shutdownSystem();
	void volumeLouder();
	void volumeQuieter();
	void volumeMute();
	void requestItemData();
	void sendAction(String action);
}
