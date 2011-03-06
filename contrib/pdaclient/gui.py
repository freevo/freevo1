
from socket import *
from thread import start_new_thread
from Tkinter import *
from os import name, getcwd

class App:
    def __init__(self,master,CONFIG):
        self.s = None
        self.freevo = CONFIG["freevo"]
        self.freevoport = CONFIG["freevoport"]
        self.wo = CONFIG["iconpath"]
        self.iconsize = CONFIG["iconsize"]
        self.width = CONFIG["width"]
        self.textsize = CONFIG["textsize"]
        master["bg"] = "black"
        self.network()

        self.reihe1 = Frame(master)
        self.reihe1.pack()

        self.img_mute = PhotoImage(file=self.wo+"mute.gif")
        self.mute=Button(self.reihe1,width=self.iconsize,height=self.iconsize,image=self.img_mute,relief="flat",command=lambda:self.send("MUTE"),bg="#353434")
        self.mute.pack(side="left")

        self.img_up = PhotoImage(file=self.wo+"up.gif")
        self.up=Button(self.reihe1,width=self.iconsize,height=self.iconsize,image=self.img_up,relief="flat",command=lambda:self.send("UP"),bg="#353434")
        self.up.pack(side="left")

        self.img_down = PhotoImage(file=self.wo+"down.gif")
        self.down=Button(self.reihe1,width=self.iconsize,height=self.iconsize,image=self.img_down,relief="flat",command=lambda:self.send("DOWN"),bg="#353434")
        self.down.pack(side="left")

        self.img_shutdown = PhotoImage(file=self.wo+"shutdown.gif")
        self.shutdown=Button(self.reihe1,width=self.iconsize,height=self.iconsize,image=self.img_shutdown,relief="flat",command=lambda:self.send("LEFT"),bg="#353434")
        self.shutdown.pack(side="left")

        self.reihe2 = Frame(master)
        self.reihe2.pack()

        self.img_ok = PhotoImage(file=self.wo+"ok.gif")
        self.ok=Button(self.reihe2,width=self.iconsize,height=self.iconsize,image=self.img_ok,relief="flat",command=lambda:self.send("SELECT"),bg="#353434")
        self.ok.pack(side="left")

        self.img_left = PhotoImage(file=self.wo+"left.gif")
        self.left=Button(self.reihe2,width=self.iconsize,height=self.iconsize,image=self.img_left,relief="flat",command=lambda:self.send("LEFT"),bg="#353434")
        self.left.pack(side="left")

        self.img_right = PhotoImage(file=self.wo+"right.gif")
        self.right=Button(self.reihe2,width=self.iconsize,height=self.iconsize,image=self.img_right,relief="flat",command=lambda:self.send("RIGHT"),bg="#353434")
        self.right.pack(side="left")

        self.img_quit = PhotoImage(file=self.wo+"quit.gif")
        self.quit=Button(self.reihe2,width=self.iconsize,height=self.iconsize,image=self.img_quit,relief="flat",command=lambda:self.send("EXIT"),bg="#353434")
        self.quit.pack(side="left")

        self.reihe3 = Frame(master)
        self.reihe3.pack()

        self.img_display = PhotoImage(file=self.wo+"display.gif")
        self.display=Button(self.reihe3,width=self.iconsize,height=self.iconsize,image=self.img_display,relief="flat",command=lambda:self.send("DISPLAY"),bg="#353434")
        self.display.pack(side="left")

        self.img_volm = PhotoImage(file=self.wo+"vol-.gif")
        self.volm=Button(self.reihe3,width=self.iconsize,height=self.iconsize,image=self.img_volm,relief="flat",command=lambda:self.send("VOL-"),bg="#353434")
        self.volm.pack(side="left")

        self.img_volp = PhotoImage(file=self.wo+"vol+.gif")
        self.volp=Button(self.reihe3,width=self.iconsize,height=self.iconsize,image=self.img_volp,relief="flat",command=lambda:self.send("VOL+"),bg="#353434")
        self.volp.pack(side="left")

        self.img_exit = PhotoImage(file=self.wo+"exit.gif")
        self.exit=Button(self.reihe3,width=self.iconsize,height=self.iconsize,image=self.img_exit,relief="flat",command=master.quit,bg="#353434")
        self.exit.pack(side="left")

        self.reihe4 = Frame(master)
        self.reihe4.pack()

        self.canvas=Canvas(self.reihe4, width=self.width, height=300, highlightthickness=1, bg="#353434")
        self.canvas.pack()

        self.pfad = self.canvas.create_text(10,10,text="not connected, yet", font=("Arial", self.textsize), fill="gray", anchor=NW)

        self.change_path(self.freevo)

    def receive_loop(self):
        while 1:
            rec = self.s.recvfrom(1024)[0]
            if rec:
                self.change_path(rec)
            else:
                break;

    def network(self):
        if not self.s:
            self.s = socket(AF_INET, SOCK_DGRAM)
            self.s.bind(("", 5555))
            self.s.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
            start_new_thread(self.receive_loop,())

    def send(self, cmd):
        print "sendig ", cmd

        self.s.sendto(cmd, self.freevo)

    def change_path(self, path):
        self.canvas.itemconfigure(self.pfad, text=path)


CONFIG = {}

# PythonCE just support a QVGA resolution. So i have to switch
# between a linux client and the PPC one.

if name == "posix":
    CONFIG["width"] = 500
    CONFIG["height"] = 640
    CONFIG["iconsize"] = 120
    CONFIG["textsize"] = 18
    CONFIG["iconpath"] = getcwd() + "/icons/"
    CONFIG["freevo"] = ("192.168.1.9", 16310)
    CONFIG["freevoport"] = 5555

else:
    CONFIG["width"] = 240
    CONFIG["height"] = 320
    CONFIG["iconsize"] = 40
    CONFIG["textsize"] = 8
    CONFIG["iconpath"] = getcwd() + "\\smallicons\\"
    CONFIG["freevo"] = ("192.168.1.9", 16310)
    CONFIG["freevoport"] = 5555

root=Tk()
root.geometry("%dx%d+%d+%d" % (CONFIG["width"],CONFIG["height"],0,0))
#root.overrideredirect(1)
app=App(root, CONFIG)
root.mainloop()
