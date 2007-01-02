import java.io.IOException;

import javax.microedition.lcdui.Canvas;
import javax.microedition.lcdui.CustomItem;
import javax.microedition.lcdui.Graphics;
import javax.microedition.lcdui.Image;

import protocol.MusicPlayer;

/*
 * Created on Jun 7, 2004
 *
 * TODO To change the template for this generated file go to
 * Window - Preferences - Java - Code Style - Code Templates
 */

/**
 * @author fred
 *
 * TODO To change the template for this generated type comment go to
 * Window - Preferences - Java - Code Style - Code Templates
 */
public class NumericNavigationWidget extends CustomItem {

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
	
	
	public NumericNavigationWidget(Controller controller) {
		super(null);
		this.controller = controller;
		
		clickIcon = loadImage("click_icon");
		
		icons = new Image[rows][];
		keyPressed = new boolean[rows][];
		for (int n=0; n<rows; ++n) {
			icons[n] = new Image[columns];
			keyPressed[n] = new boolean[columns];
		}
				
		icons[0][0] = loadImage("number_1");
		icons[0][1] = loadImage("number_2");
		icons[0][2] = loadImage("number_3");
		
		icons[1][0] = loadImage("number_4");
		icons[1][1] = loadImage("number_5");
		icons[1][2] = loadImage("number_6");
		
		icons[2][0] = loadImage("number_7");
		icons[2][1] = loadImage("number_8");
		icons[2][2] = loadImage("number_9");

		icons[3][0] = loadImage("play");
		icons[3][1] = loadImage("number_0");
		icons[3][2] = loadImage("stop");

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
					 maxRowHeight = icons[row][col].getWidth();
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
		return getMinContentWidth();
	}

	protected int getPrefContentHeight(int width) {
		return getMinContentHeight();
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
		keyPressed[getRowForKey(keyCode)][getColForKey(keyCode)] = false;
		repaint();
	}
}
