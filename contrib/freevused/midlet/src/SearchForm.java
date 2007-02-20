import java.io.IOException;
import java.util.Vector;

import javax.bluetooth.BluetoothStateException;
import javax.bluetooth.DataElement;
import javax.bluetooth.DeviceClass;
import javax.bluetooth.DiscoveryAgent;
import javax.bluetooth.DiscoveryListener;
import javax.bluetooth.LocalDevice;
import javax.bluetooth.RemoteDevice;
import javax.bluetooth.ServiceRecord;
import javax.bluetooth.UUID;
import javax.microedition.lcdui.Command;
import javax.microedition.lcdui.CommandListener;
import javax.microedition.lcdui.Displayable;
import javax.microedition.lcdui.List;

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
public class SearchForm 
extends List 
implements CommandListener, DiscoveryListener {

	private Controller controller;
	private Command exitCommand;
	private Command connectCommand;
	private Command searchCommand;
	private Command lastUsedCommand;
	private int foundDevicesCount;
	private RemoteDevice[] foundDevices;

	private Translate t;

	class ServiceInfo {
		public boolean equals(Object o) {
			ServiceInfo other = (ServiceInfo)o;
			 return connectURL.equals(other.connectURL) && name.equals(other.name);
		}
		public String connectURL;
		public String name;
	}
	private Vector serviceList;

	/**
	 * @param arg0
	 */
	public SearchForm(Controller controller) {
		super("Search", List.IMPLICIT);

		t = Translate.getInstance();

		serviceList = new Vector();
		this.controller = controller;
		setCommandListener(this);
		connectCommand = new Command(t.get("Connect"), Command.ITEM, 2);
		exitCommand = new Command(t.get("Exit"), Command.EXIT, 1);
		addCommand(exitCommand);
		searchCommand = new Command(t.get("Search"), Command.SCREEN, 1);
		//addCommand(searchCommand);
		
		setSelectCommand(connectCommand);

		foundDevices = new RemoteDevice[7];
		startSearch();
	}

	void setStatusText(String s) {
		setTitle(s);
	}

	void startSearch() {
		removeCommand(searchCommand);
		foundDevicesCount = 0;
		deleteAll();
		serviceList.removeAllElements();
		setStatusText(t.get("Searching for devices..."));
		String lastURL = controller.getSettings().getLastUsedDeviceURL();			
		String lastName = controller.getSettings().getLastUsedDeviceName();
		if (lastURL != null && lastName != null) {
			ServiceInfo info = new ServiceInfo();
			info.connectURL = lastURL;
			info.name = lastName;
			addInfo(info);
		}
		try {
			DiscoveryAgent agent = LocalDevice.getLocalDevice().getDiscoveryAgent();
			UUID[] serialUUID = new UUID[1];
			serialUUID[0] = new UUID("1101", true);
			agent.startInquiry(DiscoveryAgent.GIAC, this);
		} catch (BluetoothStateException e) {
			e.printStackTrace();
			setStatusText(t.get("Error - stopped"));
			addCommand(searchCommand);
		}
	}

	public void commandAction(Command c, Displayable d) {
		if (c == exitCommand) {
			controller.exit();
		}
		else if (c == connectCommand) {
			if (getSelectedIndex() >= 0) {
				ServiceInfo info = (ServiceInfo)serviceList.elementAt(getSelectedIndex());
				controller.connectTo(info.connectURL, info.name);				
			}
		}
		else if (c == searchCommand) {
			startSearch();
		}
	}

	public void deviceDiscovered(RemoteDevice dev, DeviceClass dummy) {
		DiscoveryAgent agent;
		if (foundDevicesCount < foundDevices.length) {
			foundDevices[foundDevicesCount] = dev;
			foundDevicesCount++;
			if (foundDevicesCount == 1) {
				setStatusText(""+foundDevicesCount+" "+t.get("device. Searching..."));
			} else {
				setStatusText(""+foundDevicesCount+" "+t.get("devices. Searching..."));
			}
		}
	}

	public void servicesDiscovered(int transID, ServiceRecord[] services) {
		for (int n=0; n<services.length; ++n) {
			String url = services[n].getConnectionURL(ServiceRecord.NOAUTHENTICATE_NOENCRYPT, false);
			ServiceInfo info = new ServiceInfo();
			info.connectURL = url;
			String devName = null;
			try {
				String tmpDevName = services[n].getHostDevice().getFriendlyName(false);
				if (tmpDevName != null && tmpDevName.length() > 0) {
					devName = tmpDevName;
				}
			} catch (IOException e) {
				e.printStackTrace();
			}			
			int serviceNameOffset = 0x0000;
			int primaryLanguageBase = 0x0100;
			DataElement de = services[n].getAttributeValue(primaryLanguageBase + serviceNameOffset);
			String srvName = null;
			if (de != null && de.getDataType() == DataElement.STRING) {
				srvName = (String)de.getValue();
			}
			if (devName != null && srvName != null) {
				info.name = devName + " - "+srvName;
			}
			else if (devName != null) {
				info.name = devName;
			}
			else if (srvName != null) {
				info.name = services[n].getHostDevice().getBluetoothAddress() + "/" + srvName;
			}
			else {
				info.name = "???";
			}
			addInfo(info);
			setStatusText(t.get("Freevused server found. Searching..."));
		}
	}
	
	void addInfo(ServiceInfo info) {
		boolean bFound = false;
		for (int n=0; n<serviceList.size(); ++n) {
			ServiceInfo nInfo = (ServiceInfo)serviceList.elementAt(n);
			if (nInfo.equals(info)) {
				bFound = true;			
			}
		}
		if (bFound == false) {
			serviceList.addElement(info);
			append(info.name, null);
		}
	}

	public void serviceSearchCompleted(int arg0, int arg1) {
		setStatusText(t.get("Done."));
		searchNextDeviceForServices();
	}

	void searchNextDeviceForServices() {
		if (foundDevicesCount > 0) {
			foundDevicesCount--;
			RemoteDevice dev = foundDevices[foundDevicesCount];
			foundDevices[foundDevicesCount] = null;
			try {
				DiscoveryAgent agent = LocalDevice.getLocalDevice().getDiscoveryAgent();
				UUID[] serialUUID = new UUID[1];
				serialUUID[0] = new UUID("1101", true);
				int attrSet[] = new int[1];
				attrSet[0] = 0x0100; // service name (primary language)
				setStatusText(t.get("Retrieving service list..."));
				agent.searchServices(attrSet, serialUUID, dev, this);
			} catch (BluetoothStateException e) {
				e.printStackTrace();
				setStatusText(t.get("Error - stopped."));
			}
		}
		else {
			addCommand(searchCommand);
		}
	}

	public void inquiryCompleted(int arg0) {
		setStatusText(t.get("Done."));
		searchNextDeviceForServices();
	}

}
