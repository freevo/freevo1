package bemused;

import protocol.*;
import java.util.Vector;

/*
 * Created August 2004
 */

/**
 * @author johan köhne
 */

public class Browser {

	BemusedProtocol protocol;
	String[] dirs;
	String[] files;
	String activeDir;
	
	boolean updateVisible;
	boolean dirChanged;
	
	
	public Browser(BemusedProtocol prot) {
		protocol = prot;
		activeDir = "";
		
		int tempsize = 1;
		dirs = new String[0];
		files = new String[0];
		
		updateVisible = true;
		
		dirChanged = false;
	}
	
	public String activeDir() {
		int lastSlash = 0, newLastSlash = 0;

		while (newLastSlash > -1) {
			lastSlash = newLastSlash;
			newLastSlash = activeDir.indexOf("\\", lastSlash + 1);
		}
		return activeDir.substring(lastSlash, activeDir.length());
	}
	
	public String[] dirs() {
		return dirs;
	}
	
	public String[] files() {
		return files;
	}
	
	public void requestMenu() {
		protocol.requestMenu();
	}
	
	public int fetchIndex(String jumpTo) {
		int len = jumpTo.length();
		jumpTo = jumpTo.toLowerCase();
		
		for (int n = 0; n < dirs.length; n++) {
			if (dirs[n].substring(0, len).toLowerCase().equals(jumpTo)) {
				return n;
			}
		}
		for (int n = 0; n < files.length; n++) {
			if (files[n].substring(0, len).toLowerCase().equals(jumpTo)) {
				return (n + dirs.length);
			}
		}
		return 0;
	}

	public void setDirInfo(String[] structure) {
		Vector dirList = new Vector();
		
		for (int n = 0; n < structure.length; n++) 	{
			dirList.addElement( structure[n] );
		}
		
		int listSize = dirList.size();
		dirs = new String[listSize < 1 ? 0 : listSize];
		for (int n = 0; n < listSize; n++) {
			dirs[n] = (String) dirList.elementAt(n);
		}
		
		if (updateVisible) {
			protocol.notifyStatusUpdate();
		}
	}
	
	public boolean dirChanged() {
		if (dirChanged) {
			dirChanged = false;
			return true;
		}
		return dirChanged;
	}
	
/*
	public void addToPlaylist(String f) {
		protocol.addToPlaylist(f);
	}
	
	public void enqueue(int index) {
		if (index == -1) return;
		if (index >= dirs.length) {
			addToPlaylist(activeDir.equals("") ? files[index - dirs.length] : activeDir + "\\" + files[index - dirs.length]);
			protocol.infoAlert("Adding", "File added to playlist!", 1500);
		}
		else {
			addToPlaylist(activeDir.equals("") ? dirs[index] : activeDir + "\\" + dirs[index]);
			protocol.infoAlert("Adding", "Dir added to playlist!", 2000);
		}
	}
	public void openItem(int index) {
		if (index == -1) return;
		if (index >= dirs.length) {
			protocol.playFile(activeDir.equals("") ? files[index - dirs.length] : activeDir + "\\" + files[index - dirs.length]);
		}
		else {
			changeDir(dirs[index]);
		}
	}
*/	
	
	private static void quicksort(String[] data) {
		quicksort(data, 0, data.length-1);
	}
	
	private static void quicksort(String[] data, int lb, int ub) {
		if (ub <= lb) return;
		int part = partition(data, lb, ub);
		quicksort(data, lb, part-1);
		quicksort(data, part+1, ub);
	}
	
	private static int partition(String[] data, int lb, int ub) {
		while (true) {
			while (lb < ub && data[lb].toLowerCase().compareTo(data[ub].toLowerCase()) < 0) ub--;
			if (lb < ub) swap(data, lb++, ub);
			else return lb;
			
			while (lb < ub && data[lb].toLowerCase().compareTo(data[ub].toLowerCase()) < 0) lb++;
			if (lb < ub) swap(data, lb, ub--);
			else return ub;
		}
	}
	
	private static void swap(String[] data, int x, int y) {
		String tmp = data[x];
		data[x] = data[y];
		data[y] = tmp;
	}

	public void sendMenuItemSelected(String idx) {
		protocol.sendMenuItemSelected( idx );
		requestMenu();
	}

	public void menuSubmenu() {
		protocol.submenu();
	    requestMenu();
	}

	public void menuMain() {
		protocol.mainMenu();
	}

	public void menuBack() {
		protocol.stop();
		requestMenu();
	}

}
