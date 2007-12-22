import java.io.IOException;

import javax.microedition.lcdui.Canvas;
import javax.microedition.lcdui.CustomItem;
import javax.microedition.lcdui.Graphics;
import javax.microedition.lcdui.Image;

import protocol.MusicPlayer;

public class NavigationWidget extends CustomItem {

	public static final int CONTROL_KEYS = 0;
	public static final int NUMERIC_KEYS = 1;
	public static final int MORE_KEYS    = 2;

	Controller controller;
	Image clickIcon;
	Image[][] icons;
	boolean[][] keyPressed;
	final int rows = 4;
	final int columns = 3;
	int[] xOffset;
	int[] yOffset;
	int[] xSize;
	int[] ySize;
	int currentPlaylistPos;
	int currentTrackPos;
	int currentVolume;
	int maxPlaylistPos;
	int maxTrackPos;

	int controlType = CONTROL_KEYS;

	int formWidth = -1;
	int formHeight = -1;

	String imageName[][];

	String imagesControlActions[][] = {
		{ "previous", "play", "next" },
		{ "rewind", "pause", "forward" },
		{ "vol_down", "stop", "vol_up" },
		{ "vol_mute", "select", "main" }
	};

	String imagesNumericActions[][] = {
		{ "number_1", "number_2", "number_3" },
		{ "number_4", "number_5", "number_6" },
		{ "number_7", "number_8", "number_9" },
		{ "play", "number_0", "stop" }
	};

	String imagesMoreActions[][] = {
		{ "previous", "play", "next" },
		{ "rewind", "guide", "forward" },
		{ "chanplus", "stop", "chanminus" },
		{ "eject", "display", "record" }
	};

	public NavigationWidget(Controller controller, int controlType, int fWidth, int fHeight) {
		super(null);
		this.controller = controller;

		this.controlType = controlType;

		this.formWidth  = fWidth;
		this.formHeight = fHeight;
		
		clickIcon = loadImage("click_icon");
		
		icons = new Image[rows][];
		keyPressed = new boolean[rows][];
		for (int n=0; n<rows; ++n) {
			icons[n] = new Image[columns];
			keyPressed[n] = new boolean[columns];
		}
				
		switch ( controlType ) {
			case 1:
				imageName = imagesNumericActions;
				break;
			case 2:
				imageName = imagesMoreActions;
				break;
			default:
				imageName = imagesControlActions;
				break;
		}

		for (int x=0; x < imageName.length; x++) {
			for (int y=0; y < imageName[x].length; y++) {
        		icons[x][y] = loadImage( imageName[x][y] );
			}
		}

		xSize = new int[columns];
		ySize = new int[rows];
		for (int col=0; col<columns; ++col) {
			int maxColWidth = 0;
			for (int row=0; row<rows; ++row) {
				if (icons[row][col] != null && icons[row][col].getWidth() > maxColWidth) {
					 maxColWidth = icons[row][col].getWidth();
				}
				// reuse the loop to initialize the keypressed matrix
				keyPressed[row][col] = false;
			}
			xSize[col] = maxColWidth;
		}
		for (int row=0; row<rows; ++row) {
			int maxRowHeight = 0;
			for (int col=0; col<columns; ++col) {
				if (icons[row][col] != null && icons[row][col].getHeight() > maxRowHeight) {
					 maxRowHeight = icons[row][col].getHeight();
				}
			}
			ySize[row] = maxRowHeight;
		}

		xOffset = new int[columns];
		yOffset = new int[rows];
		
		xOffset[0] = 0;
		for (int n=1; n<columns; ++n) {
			xOffset[n] = xOffset[n-1] + xSize[n-1];
		}

		yOffset[0] = 0;
		for (int n=1; n<rows; ++n) {
			yOffset[n] = yOffset[n-1] + ySize[n-1];
		}
		
	}
	
	public void setVolume(int vol) {
		currentVolume = vol;
		repaint();
	}
	
	public void setTrackPos(int pos, int maxPos) {
		currentTrackPos = pos;
		maxTrackPos = maxPos;
		repaint();
	}
	
	public void setPlaylistPos(int pos, int maxPos) {
		currentPlaylistPos = pos;
		maxPlaylistPos = maxPos;
		repaint();
	}
	
	private Image loadImage(String name) {
		Image ret;
		try {
			ret = Image.createImage("/"+name+".png");
		} catch (IOException e) {
			ret = null;
		}
		return ret;
	}
	
	protected int getMinContentWidth() {
		int width = 0;
		for (int col=0; col<columns; ++col) {
			width += xSize[col];
		}
		return width;
	}

	protected int getMinContentHeight() {
		int height = 0;
		for (int row=0; row<rows; ++row) {
			height += ySize[row];
		}
		return height;
	}

	protected int getPrefContentWidth(int height) {
		int w;

		if ( formWidth == -1 ) {
			w = getMinContentWidth();
		} else {
			w = formWidth;
		}

		return w;
	}

	protected int getPrefContentHeight(int width) {
		int h;

		if ( formHeight == -1 ) {
			h = getMinContentHeight();
		} else {
			h = formHeight;
		}

		return h;
	}

	public int getWidth() {
		return getPrefContentWidth( formHeight );
	}

	public int getHeight() {
		return getPrefContentHeight( formWidth );
	}

	void drawBar(Graphics g, int w, int row, int val, int maxVal) {
		if (maxVal==0) maxVal = 1;
		if (val<0) val=0;
		if (val>maxVal) val=maxVal;
		g.setColor(188,200,235);
		g.fillRect(0, yOffset[row], (w*val)/maxVal, ySize[row]);
		g.setColor(245,250,255);
		g.fillRect((w*val)/maxVal, yOffset[row], w-(w*val)/maxVal, ySize[row]);		
	}
	
	protected void paint(Graphics g, int w, int h) {
		/*
		drawBar(g, w, 0, currentPlaylistPos, maxPlaylistPos);
		drawBar(g, w, 1, currentTrackPos, maxTrackPos);
		drawBar(g, w, 2, currentVolume, 255);
		*/
		for (int row=0; row<rows; ++row) {
			for (int col=0; col<columns; ++col) {
				Image icon = icons[row][col];
				if (icon != null) {
					g.drawImage(icon, xOffset[col], yOffset[row], 
							Graphics.LEFT | Graphics.TOP);
					if (keyPressed[row][col]) {
						g.drawImage(clickIcon, xOffset[col]+xSize[col]/2,
								yOffset[row]+ySize[row]/2, 
								Graphics.HCENTER | Graphics.VCENTER);
					}
				}
			}
		}
	}

	private int getRowForKey(int keycode) {
		switch (keycode) {
			case Canvas.KEY_NUM1:
			case Canvas.KEY_NUM2:
			case Canvas.KEY_NUM3:
				return 0;
			case Canvas.KEY_NUM4:
			case Canvas.KEY_NUM5:
			case Canvas.KEY_NUM6:
				return 1;
			case Canvas.KEY_NUM7:
			case Canvas.KEY_NUM8:
			case Canvas.KEY_NUM9:
				return 2;
			case Canvas.KEY_STAR:
			case Canvas.KEY_NUM0:
			case Canvas.KEY_POUND:
				return 3;
			default:
				return 0;
		}
	}
	
	private int getColForKey(int keycode) {
		switch (keycode) {
			case Canvas.KEY_NUM1:
			case Canvas.KEY_NUM4:
			case Canvas.KEY_NUM7:
			case Canvas.KEY_STAR:
				return 0;
			case Canvas.KEY_NUM2:
			case Canvas.KEY_NUM5:
			case Canvas.KEY_NUM8:
			case Canvas.KEY_NUM0:
				return 1;
			case Canvas.KEY_NUM3:
			case Canvas.KEY_NUM6:
			case Canvas.KEY_NUM9:
			case Canvas.KEY_POUND:
				return 2;
			default:
				return 0;
		}
	}
	
	protected void keyPressed(int keyCode) {
		keyPressed[getRowForKey(keyCode)][getColForKey(keyCode)] = true;
		repaint();
	}
	
	protected void keyReleased(int keyCode) {
		MusicPlayer p = controller.getPlayer();
		switch ( controlType ) {
			case 1:
			    keyReleasedNumericActions(p, keyCode);
				break;
			case 2:
			    keyReleasedMoreActions(p, keyCode);
				break;
			default:
			    keyReleasedControlActions(p, keyCode);
				break;
		}
		keyPressed[getRowForKey(keyCode)][getColForKey(keyCode)] = false;
		repaint();
	}

	private void keyReleasedControlActions(MusicPlayer p, int keyCode) {
		switch (keyCode) {
			case Canvas.KEY_NUM1:
				p.previous();
				break;
			case Canvas.KEY_NUM2:
				p.play();
				break;
			case Canvas.KEY_NUM3:
				p.next();
				break;
			case Canvas.KEY_NUM4:
				p.rewind();
				break;
			case Canvas.KEY_NUM5:
				p.pause();
				break;
			case Canvas.KEY_NUM6:
				p.forward();
				break;
			case Canvas.KEY_NUM7:
				p.volumeQuieter();
				break;
			case Canvas.KEY_NUM8:
				p.stop();
				break;
			case Canvas.KEY_NUM9:
				p.volumeLouder();
				break;
			case Canvas.KEY_NUM0:
				p.submenu();
				break;
			case Canvas.KEY_STAR:
				p.volumeMute();
				break;
			case Canvas.KEY_POUND:
				p.mainMenu();
				break;
		}
	}

	private void keyReleasedNumericActions(MusicPlayer p, int keyCode) {
		switch (keyCode) {
			case Canvas.KEY_NUM1:
				p.sendAction("NUM1");
				break;
			case Canvas.KEY_NUM2:
				p.sendAction("NUM2");
				break;
			case Canvas.KEY_NUM3:
				p.sendAction("NUM3");
				break;
			case Canvas.KEY_NUM4:
				p.sendAction("NUM4");
				break;
			case Canvas.KEY_NUM5:
				p.sendAction("NUM5");
				break;
			case Canvas.KEY_NUM6:
				p.sendAction("NUM6");
				break;
			case Canvas.KEY_NUM7:
				p.sendAction("NUM7");
				break;
			case Canvas.KEY_NUM8:
				p.sendAction("NUM8");
				break;
			case Canvas.KEY_NUM9:
				p.sendAction("NUM9");
				break;
			case Canvas.KEY_NUM0:
				p.sendAction("NUM0");
				break;
			case Canvas.KEY_STAR:
				p.play();
				break;
			case Canvas.KEY_POUND:
				p.stop();
				break;
		}			
	}

	private void keyReleasedMoreActions(MusicPlayer p, int keyCode) {
		switch (keyCode) {
			case Canvas.KEY_NUM1:
				p.previous();
				break;
			case Canvas.KEY_NUM2:
				p.play();
				break;
			case Canvas.KEY_NUM3:
				p.next();
				break;
			case Canvas.KEY_NUM4:
				p.rewind();
				break;
			case Canvas.KEY_NUM5:
				p.sendAction("GUID");
				break;
			case Canvas.KEY_NUM6:
				p.forward();
				break;
			case Canvas.KEY_NUM7:
				p.sendAction("CHA+");
				break;
			case Canvas.KEY_NUM8:
				p.stop();
				break;
			case Canvas.KEY_NUM9:
				p.sendAction("CHA-");
				break;
			case Canvas.KEY_NUM0:
				p.sendAction("DISP");
				break;
			case Canvas.KEY_STAR:
				p.sendAction("EJEC");
				break;
			case Canvas.KEY_POUND:
				p.sendAction("RECO");
				break;
		}			
	}

}
