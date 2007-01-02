include ../Makefile.config

CLASS_PATH="/usr/local/nokia/j2me/Devices/Series_60_MIDP_Concept_SDK_Beta_0_3_1_Nokia_edition/lib/classes.zip:/usr/local/nokia/j2me/Devices/Series_60_MIDP_Concept_SDK_Beta_0_3_1_Nokia_edition/lib/ext/bluetooth.zip:./classes"

JAVAC=/usr/bin/javac
PREVERIFY=/usr/local/nokia/j2me/Devices/Series_60_MIDP_Concept_SDK_Beta_0_3_1_Nokia_edition/bin/preverify
JAR=/usr/bin/jar

all: clean compile

clean:
	-rm -rf classes midlet

compile:
	-mkdir classes midlet

	$(JAVAC) -d classes/ -classpath $(CLASS_PATH) src/protocol/*.java
	$(JAVAC) -d classes/ -classpath $(CLASS_PATH) src/bemused/*.java src/Browser.java
	$(JAVAC) -d classes/ -classpath $(CLASS_PATH) src/*.java

	$(PREVERIFY) -classpath $(CLASS_PATH) -d classes/ -cldc classes/

	cp res/* classes/
	cp MANIFEST.MF classes/
	cp MANIFEST.MF midlet/$(PACKAGE).jad

	$(JAR) -cmf MANIFEST.MF midlet/$(PACKAGE).jar -C classes .

	echo "MIDlet-Jar-URL: $(PACKAGE).jar" >> midlet/$(PACKAGE).jad
	echo "MIDlet-Jar-Size: `du -b midlet/$(PACKAGE).jar | awk '{print $$1}'`" >> midlet/$(PACKAGE).jad

install:
	scp midlet/* macario:~/tmp/
	ssh macario gammu --nokiaaddfile Application ~/tmp/$(PACKAGE)
