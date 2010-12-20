#!/usr/bin/env bash

# autogen.sh 
#
# Dirk Meyer  <dmeyer@tzi.de>
# $Id$

revision() {
    echo -n generating revision.py
    rev=$(LC_ALL=C svn info --revision=BASE | sed -n '/Revision:/s/Revision: *\([0-9]*\)/\1/p')
    echo '"""' > src/revision.py
    echo 'Freevo revision number' >> src/revision.py
    echo '"""' >> src/revision.py
    echo '' >> src/revision.py
    echo "__revision__ = ${rev}" >> src/revision.py
    echo " ${rev}"
}

gen_i18n() {
    for file in $(find i18n -name freevo.po); do
     out=$(echo $file | sed 's/\.po$/.mo/')
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

mkhtmldir() {
    if [ ! -e Docs/installation/html ]; then mkdir Docs/installation/html; fi
}

# main
case "$1" in
    revision)
        revision
        ;;
    nodocs)
        revision
        gen_i18n
        mkhtmldir
        ;;
    howto)
        howto
        ;;
    -h|--help|help)
        echo -n "usage:   "
        echo $0
        echo "          revision   -  just generate svn revision module"
        echo "          nodocs     -  just generate translations"
        echo "          howto      -  just generate the docbook howto"
        echo "          <default>  -  generate translations and generate howto"
        ;;
    *)
        revision
        gen_i18n
        howto
        ;;
esac


# end of autogen.sh 
