include ../Makefile.config

CLASS_PATH="/usr/local/nokia/j2me/Devices/Series_60_MIDP_Concept_SDK_Beta_0_3_1_Nokia_edition/lib/classes.zip:/usr/local/nokia/j2me/Devices/Series_60_MIDP_Concept_SDK_Beta_0_3_1_Nokia_edition/lib/ext/bluetooth.zip:./classes"

ifndef RESOLUTION
	RESOLUTION=128x128
endif

JAVAC=/usr/bin/javac
PREVERIFY=/usr/local/nokia/j2me/Devices/Series_60_MIDP_Concept_SDK_Beta_0_3_1_Nokia_edition/bin/preverify
JAR=/usr/bin/jar

ifndef LINGUA
  LINGUA=ES
endif

PROGNAME=$(PACKAGE)_$(RESOLUTION)_$(LINGUA)

all: link

clean:
	-rm -rf classes bin

compile:
	-mkdir classes bin
	-ln -sf Translation-${LINGUA}.java src/translate/Translation.java

	$(JAVAC) -d classes/ -classpath $(CLASS_PATH) src/protocol/*.java src/translate/Translate.java src/translate/Translation.java
	$(JAVAC) -d classes/ -classpath $(CLASS_PATH) src/bemused/*.java src/Browser.java src/translate/Translate.java src/translate/Translation.java
	$(JAVAC) -d classes/ -classpath $(CLASS_PATH) src/*.java src/translate/Translate.java src/translate/Translation.java

link: compile

	$(PREVERIFY) -classpath $(CLASS_PATH) -d classes/ -cldc classes/

	cp res/$(RESOLUTION)/* classes/
	cp MANIFEST.MF classes/
	cp MANIFEST.MF bin/$(PROGNAME).jad

	$(JAR) -cmf MANIFEST.MF bin/$(PROGNAME).jar -C classes .

	echo "MIDlet-Jar-URL: $(PROGNAME).jar" >> bin/$(PROGNAME).jad
	echo "MIDlet-Jar-Size: `du -b bin/$(PROGNAME).jar | awk '{print $$1}'`" >> bin/$(PROGNAME).jad

install:
	scp bin/$(PROGNAME).jad bin/$(PROGNAME).jar macario:~/tmp/
	ssh macario gammu 1 --nokiaaddfile Application ~/tmp/$(PROGNAME)

install2:
	scp bin/$(PROGNAME).jad bin/$(PROGNAME).jar macario:~/tmp/
	ssh macario gammu --nokiaaddfile Application ~/tmp/$(PROGNAME)
