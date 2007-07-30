include Makefile.config

all: midlet

midlet:
	cd midlet && make

midlet-install:
	cd midlet && make install

clean:
	cd midlet && make clean

dist:
	-rm ../${PACKAGE}-$(VERSION).tar.bz2
	-rm -rf midlet/classes
	cd .. && tar -cjvf ${PACKAGE}-$(VERSION).tar.bz2 ${PACKAGE}-$(VERSION)/
