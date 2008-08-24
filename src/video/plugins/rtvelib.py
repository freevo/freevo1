# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Plugin for streaming programs from rtve.es
# -----------------------------------------------------------------------
# $Id$
# -----------------------------------------------------------------------
# Freevo - A Home Theater PC framework
# Copyright (C) 2008 Krister Lagerstrom, et al.
# Please see the file freevo/Docs/CREDITS for a complete list of authors.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MER-
# CHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General
# Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#
# -----------------------------------------------------------------------

import sys
import os
import re
import socket
import urllib2
import urlparse
import pickle
import random

from time import time,sleep
from threading import Thread,Lock,Semaphore

progs = {}
progsAnalizados = 0
totalProgramas = 0
lockCB = Lock()
lockProgs = Lock()
conexiones = Semaphore(10)
threads = []

def dl(url):
    #print url
    for i in range(2): #n intentos
        try:
            conexiones.acquire()
            f = urllib2.urlopen(url)
            html = f.read()
            return html
        except IOError:
            print "retrying wget '%s'" % (url,)
            pass
        finally:
            conexiones.release()


def decodeAcute(cadena):
    return cadena.replace('&aacute;','á') \
                 .replace('&eacute;','é') \
                 .replace('&iacute;','í') \
                 .replace('&oacute;','ó') \
                 .replace('&uacute;','ú') \
                 .replace('&ordf;'  ,'º') \
                 .replace('&ntilde;','ñ') \
                 .replace('&iexcl;' ,'¡') \
                 .replace('&Aacute;','Á') \
                 .replace('&Eacute;','É') \
                 .replace('&Iacute;','Í') \
                 .replace('&Oacute;','Ó') \
                 .replace('&Uacute;','Ú') \
                 .replace('&Ntilde;','Ñ')



class ParsePrograma(Thread):

    def __init__(self,callback,idProg,image,descripcion,fecha):
        Thread.__init__(self)
        self.idProg = idProg
        self.image = image
        self.descripcion = descripcion
        self.fecha = fecha
        self.callback = callback

    def run(self):

        try:

            progHTML = dl('http://www.rtve.es/alacarta/player/%s.html' % self.idProg)

            if progHTML.find('h3')>0:
                return # page is being refreshed

            #channel
            progHTML = progHTML[progHTML.find('h2'):]
            if progHTML.find('. La 1. ')>0:
                canal = 'La Primera'
            else:
                canal = 'La 2'

            #description
            if progHTML.find('<p>')>0:
                progHTML = progHTML[progHTML.find('<p>')+3:]
                self.descripcion = progHTML[:progHTML.find('</p>')]

            progXML = dl('http://www.rtve.es/alacarta/player/%s.xml' % self.idProg)

            #name
            progXML = progXML[progXML.find('<title>')+7:]
            name = progXML[:progXML.find('</title>')]

            #flv
            progXML = progXML[progXML.find('<location>')+10:]
            flv = 'http://www.rtve.es'+progXML[:progXML.find('</location>')]

            key = name #names may be duplicated
            while progs.has_key(key):
                key = key + "*"

            try:
                lockProgs.acquire()
                progs[key] = {
                    "nombre":name.encode("latin-1"),
                    "fecha":self.fecha,
                    "descripcion":decodeAcute(self.descripcion),
                    "image":self.image,
                    "canal":canal,
                    "flv":flv
                }
            finally:
                lockProgs.release()
            
        finally:

            global progsAnalizados,totalProgramas
            progsAnalizados += 1
            #print "Programas analizados: %s de %s " % (progsAnalizados,totalProgramas)
            avance = 100 * progsAnalizados / totalProgramas
            try:
                lockCB.acquire()
                self.callback(avance)
            finally:
                lockCB.release()

class ParseLetra(Thread):

    def __init__(self,callback,letra,blackList):
        Thread.__init__(self)
        self.letra = letra
        self.callback = callback
        self.blackList = blackList

    def run(self):

        global totalProgramas

        for numero in range(1,99):

            try: 
                url = 'http://www.rtve.es/alacarta/todos/abecedario/%s.html?page=%s' % (self.letra,numero)
                pagina = dl(url)
            except:
                continue

            totalProgramas += len(pagina.split('<li id="video-'))-1

            contador = pagina.find('<span id="contador">')
            if contador>0:
                contador = pagina[contador+20:]
                contador = contador[:contador.find("<")]
                actual = int(contador[:contador.find(" ")])
                total = int(contador[len(contador)-2:])
            else:
                #print "la url %s no tiene contenidos" % url
                break

            while pagina.find('<li id="video-')>=0:
 
                pagina = pagina[pagina.find('<li id="video-')+14:]
                
                if self.blackList:
                    pTitulo = pagina[pagina.find('<h3>')+4:pagina.find('</h3>')]
                    pTitulo = decodeAcute(pTitulo).lower()
                    encontrado = False
                    global progsAnalizados
                    for titulo in self.blackList:
                        if pTitulo.find(titulo.lower())>-1:
                            encontrado = True
                            progsAnalizados += 1
                    if encontrado: continue
                    
                idProg = pagina[:pagina.find('"')]
 
                pagina = pagina[pagina.find('<img src="')+10:]
                image = 'http://www.rtve.es/' + pagina[:pagina.find('"')]
 
                pagina = pagina[pagina.find('<p>')+3:]
                descripcion = pagina[:pagina.find('</p>')]
 
                pagina = pagina[pagina.find('<span>')+6:]
                fecha = pagina[:pagina.find('<br>')].replace('\n','').replace('\t','').replace(' ','')[8:].replace('[',' [')
                
                #parses program pages
                t = ParsePrograma(self.callback,idProg,image,descripcion,fecha)
                t.start()
                threads.append(t)
                
            if actual == total:
                break 


class Programacion:
    def __init__(self):
        self.programas = {}
        global progs, progsAnalizados, totalProgramas, threads
        progs = {}
        progsAnalizados = 0
        totalProgramas = 0
        threads = []

    def parse(self, callback = None, blackList = None):
        
        #iterate thru letters
        letras = ['A','B','C','D','E','F','G','H','I','J','K','L','M','N','O','P','Q','R','S','T','U','V','W','X','Y','Z']
        #letras = ['B']
        for letra in letras:
            t = ParseLetra(callback,letra,blackList)
            t.start()
            threads.append(t)
        
        for thread in threads:
            thread.join()
        
        self.programas = progs

    def sort_by_title(self):
        keys = self.programas.keys()
        keys.sort()
        return keys

    def only_canal(self, canal):
        keys = self.programas.keys()
        for programa in keys:
            if canal != self.programas[programa]["canal"]:
                del self.programas[programa]

def progress(perc):
    print "\rProgress: %d%%\r" % perc,

if __name__ == '__main__':

    programacion = Programacion()
    programacion.parse(progress,['berni'])
    print "Programas parseados: %s " % len(programacion.programas.keys())
 
    pickle.dump(programacion.programas, file("rtve.dump", "w"))
