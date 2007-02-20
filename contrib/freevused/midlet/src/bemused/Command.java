/*
 * Created on May 31, 2004
 *
 * TODO To change the template for this generated file go to
 * Window - Preferences - Java - Code Style - Code Templates
 */
package bemused;

import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.io.IOException;
import java.util.Vector;

import protocol.MusicPlayer;
import bemused.BemusedProtocol;

import translate.Translate;

public class Command {

	String name;
	String strArg;
	int intArg;
	byte byteArg;

	Translate t = Translate.getInstance();

	public Command(String name) {
		this.name = name;
	}

	public Command(String name, int intArg) {
		this.name = name;
		this.intArg = intArg;
	}

	public Command(String name, byte byteArg) {
		this.name = name;
		this.byteArg = byteArg;
	}

	public Command(String name, String strArg) {
		this.name = name;
		this.strArg = strArg;
	}

	public void setFilenameArg(String s) {
		strArg = s;
	}

	public String getName() {
		return name;
	}

	private byte readByte(DataInputStream input) throws IOException {
		return (byte) input.readUnsignedByte();
	}

	private void writeShort(DataOutputStream output, short val)
			throws IOException {
		output.writeShort(val);
	}
	
	private void writeString(DataOutputStream output, String s) throws BemusedProtocolException {
		byte[] stream = s.getBytes();
		try {
			for (int n = 0; n < stream.length; ++n) {
				output.writeByte(stream[n]);
			}
		}
		 catch (IOException e) {
			throw new BemusedProtocolException("BemusedCommand:execute: "
					+ e.getMessage());
		}
	}

	public void execute(CommandTarget target) throws BemusedProtocolException {
		DataOutputStream output = target.getOutputStream();
		DataInputStream input = target.getInputStream();
		try {
			// Send the command name 
			output.write(name.getBytes(), 0, 4);

			if (name.equals("TEXT")) {
				writeString(output, strArg);
				output.flush();
			}
			else if (name.equals("MITM")) {
				writeString(output, strArg);
				output.flush();
			}
			else if (name.equals("MSND")) {
				output.flush();
				readMenu(input, target);
			}
			else if (name.equals("STAT")) {
				output.flush();
				readItemData(input, target);
			}
			else {
				output.flush();
			}
		} catch (IOException e) {
			throw new BemusedProtocolException("BemusedCommand:execute: "
					+ e.getMessage());
		}
	}

	private void readMenu(DataInputStream input, CommandTarget target)
		throws IOException {

		byte[] curItemBuf = new byte[128];
		int curItemBufLen = curItemBuf.length;
		int curItemBufPos;
		byte lastByte;
		Vector dirList = new Vector();

		lastByte = readByte(input);
		while ( lastByte != 0 ) {
			curItemBufPos = 0;
			while ( lastByte != (byte) '\n' ) {
				if (curItemBufPos < curItemBufLen) {
					curItemBuf[curItemBufPos++] = lastByte;
				}
				lastByte = readByte(input);
			}
			if ( curItemBufPos > 0 ) {
				String curItemStr = new String(curItemBuf, 0, curItemBufPos, "UTF-8");
				dirList.addElement(curItemStr);
			}
			lastByte = readByte(input);
		}

		int listSize = dirList.size();
		String[] ret_string = new String[listSize < 1 ? 0 : listSize];

		for (int n = 0; n < listSize; n++) {
			ret_string[n] = (String) dirList.elementAt(n);
		}
		target.setDirInfo(ret_string);

	}

	private void requestMenu(DataOutputStream output)
		   	throws BemusedProtocolException {
		writeString(output, "MSND");
	}

	private void readItemData(DataInputStream input, CommandTarget target)
		throws IOException {

		byte[] curItemBuf = new byte[128];
		int curItemBufLen = curItemBuf.length;
		int curItemBufPos;
		byte lastByte;
		StringBuffer ItemStr = new StringBuffer();
		String data;

		lastByte = readByte(input);
		while ( lastByte != 0 ) {

			curItemBufPos = 0;
			while (curItemBufPos < curItemBufLen && lastByte != 0) {
				curItemBuf[curItemBufPos++] = lastByte;
				lastByte = readByte(input);
			}
			String curItemStr = new String(curItemBuf, 0, curItemBufPos, "UTF-8");
			ItemStr.append(curItemStr);
		}

		data = ItemStr.toString();
		if ( data.equals("") ) {
			data = t.get("Press any key to control");
		}
		target.setStatus(data);

	}

}
