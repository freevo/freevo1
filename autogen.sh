#!/usr/bin/env bash

# autogen.sh 
#
# Dirk Meyer  <dmeyer@tzi.de>
# $Id$

gen_i18n() {
    for file in `find i18n -name freevo.po`; do
     out=`echo $file | sed 's/\.po$/.mo/'`
     echo generating $out
     msgfmt -o $out $file 2> /dev/null
    done
}

docbook () {
    echo
    echo generating $1 howto html files

    cd Docs/$1
    docbook2html -o html howto.sgml
    cd ../..
    echo
    echo
}
    
howto() {
    docbook installation
    docbook plugin_writing
}

# Main
case "$1" in
    nodocs)
        gen_i18n
        ;;
    howto)
        howto
        ;;
    help)
        echo -n "Usage:   "
        echo $0
        echo "          nodocs     -  Just generate translations"
        echo "          howto      -  Just generate the docbook howto"
        echo "          <default>  -  Generate translations and generate Howto"
        ;;
    *)
        gen_i18n
        howto
        ;;
esac


# end of autogen.sh 
