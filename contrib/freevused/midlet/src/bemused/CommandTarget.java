/*
 * Created on May 25, 2004
 *
 * To change the template for this generated file go to
 * Window&gt;Preferences&gt;Java&gt;Code Generation&gt;Code and Comments
 */
package bemused;

import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.util.Date;


/**
 * @author fred
 *
 * To change the template for this generated type comment go to
 * Window&gt;Preferences&gt;Java&gt;Code Generation&gt;Code and Comments
 */
interface CommandTarget {
	DataInputStream getInputStream();
	DataOutputStream getOutputStream();
	void setDirInfo(String[] structure);
	void setStatus(String data);

}
