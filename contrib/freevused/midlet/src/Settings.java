import javax.microedition.rms.InvalidRecordIDException;
import javax.microedition.rms.RecordStore;
import javax.microedition.rms.RecordStoreException;
import javax.microedition.rms.RecordStoreFullException;
import javax.microedition.rms.RecordStoreNotFoundException;
import javax.microedition.rms.RecordStoreNotOpenException;

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
public class Settings {

	String lastUsedDeviceURL;
	String lastUsedDeviceName;
	
	public Settings() {
		super();
		load();
	}
	
	void load() {
		RecordStore store = null;
		lastUsedDeviceName = null;
		lastUsedDeviceURL = null;
		try {
			store = RecordStore.openRecordStore("Settings", false);
			if (store != null) {
				lastUsedDeviceURL = new String(store.getRecord(1));
				lastUsedDeviceName = new String(store.getRecord(2));				
			}
		} catch (RecordStoreFullException e) {
			e.printStackTrace();
		} catch (InvalidRecordIDException e) {
		} catch (RecordStoreNotFoundException e) {
		}	catch (RecordStoreNotOpenException e) {
			e.printStackTrace();
		} catch (RecordStoreException e) {
			e.printStackTrace();
		} finally {
			if (store != null) try {
				store.closeRecordStore();
			} catch (RecordStoreException e1) { }
		}

	}
	
	void save()  {
		RecordStore store = null;
		try {
			try {
				RecordStore.deleteRecordStore("Settings");
			} catch (RecordStoreNotFoundException e1) { }
			
			if (lastUsedDeviceURL != null && lastUsedDeviceName != null) {
				store = RecordStore.openRecordStore("Settings", true);
				byte[] data;
				data = lastUsedDeviceURL.getBytes();
				store.addRecord(data, 0, data.length);
				data = lastUsedDeviceName.getBytes();
				store.addRecord(data, 0, data.length);
			}
		} catch (RecordStoreFullException e) {
			e.printStackTrace();
		} catch (RecordStoreNotFoundException e) {
			e.printStackTrace();
		}	catch (RecordStoreNotOpenException e) {
			e.printStackTrace();
		} catch (RecordStoreException e) {
			e.printStackTrace();
		}	finally {
			if (store != null) try {
				store.closeRecordStore();
			} catch (RecordStoreException e1) { }
		}
	}
	
	String getLastUsedDeviceURL() {
		return lastUsedDeviceURL; 
	}
	
	String getLastUsedDeviceName() {
		return lastUsedDeviceName; 
	}
	
	void setLastUsedDevice(String url, String name) {
		lastUsedDeviceName = name;
		lastUsedDeviceURL = url;
	}
}
