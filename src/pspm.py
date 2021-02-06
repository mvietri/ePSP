#!/usr/bin/env python

#    This file is part of PSPm Project
#
#    Mauro - github@mvietri.dev
#
#    PSPm is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    any later version.
#
#    PSPm is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with PSPm; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import os
import sys
import gtk
import math
import time
import pygtk
import Image           ## python-imaging must be installed.
#import gobject
import gettext
#import language
import gtk.glade
import ImageFilter
import ConfigParser
import ImageEnhance
from threading import Thread


try:
	pygtk.require("2.0")
except:
	print _("PyGTK >= 2.0 needed!")
	sys.exit(1)

try:
	import pynotify		##libnotify-bin is optional
	haveosd = True
except:
	haveosd = False

#Load translation 
TRANSLATION_DOMAIN = "pspm"
LOCALE_DIR = os.path.join(os.path.dirname(__file__), "locale")
gettext.install(TRANSLATION_DOMAIN, LOCALE_DIR)

projectname = "PSPm"
projectvers = "0.3a"
URL = "http://code.google.com/p/pspm/"
About = _("\"PSP\", \"PlayStation\", \"Memory Stick Pro Duo\"\n" \
	  "and their logos are trademark of Sony Computer Entertainment Inc.\n" \
	  "PSP Headphones icon by Nelson\n" \
	  "PSP icon by Asher.")



#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

class PSP:

	## Don't know why ???
	if haveosd == True:
		osd_available = True
	else:
		osd_available = False

	def __init__(self):
		gtk.gdk.threads_init()	
				
		if self.osd_available == True:
			if not pynotify.init( projectname ):
				self.osd_available = False
				## Debug info ...
				print _("Even though you have installed libnotify-bin, something went wrong and it couldn't be initialized")
				print _("Gtk dialogs will be use as fallback notification system")
				self.notify(_("Ups! OSD won't come up. I will be in charge"))
				

	        self.build("main")		


	def build(self, id, data=None):
		"""load the right GUI according to id and data"""
		if id == "main":
			Handler = gtk.glade.XML("GUI/psp.glade") 
		
			window = Handler.get_widget("window1")
			window.connect("destroy", self.canILeave, window)
			window.set_title(_("%s [Main Menu]") %projectname)
			self.setWindow(window)

			btnGames = Handler.get_widget("btnGames")
			btnGames.connect("clicked", self.buildGames)
			btnGames.set_tooltip_text(_("Copy/Delete games to/from your PSP"))
			lblGames = Handler.get_widget("lblGames")
			lblGames.set_text(_("Manage games' backup"))


			btnSavegames = Handler.get_widget("btnSavegames")
			btnSavegames.connect("clicked", self.buildPSPSavegames)
			btnSavegames.set_tooltip_text(_("View, Backup or Delete Savegames saved in your Memory Stick"))
			lblSGP = Handler.get_widget("lblSGP")
			lblSGP.set_text(_("Savegames on PSP"))

			btnLocalsg = Handler.get_widget("btnLocalsg")
			btnLocalsg.connect("clicked", self.buildLocalSavegames)
			btnLocalsg.set_tooltip_text(_("View, Restore or Delete Savegames saved in your PC"))
			lblSGH = Handler.get_widget("lblSGH")
			lblSGH.set_text(_("Savegames on HDD"))

			btnCiso = Handler.get_widget("btnCiso")
			btnCiso.connect("clicked", self.buildCiso)
			btnCiso.set_tooltip_text(_("(Dis)compress your iso/cso images"))
			lblCISO = Handler.get_widget("lblCISO")
			lblCISO.set_text(_("CISO Tool"))

			btnExplore = Handler.get_widget("btnExplore")
			btnExplore.connect("clicked", self.callExploreMS)
			btnExplore.set_tooltip_text(_("Explore the content of the Memory Stick using a file browser of choice"))
			lblExplore = Handler.get_widget("lblExplore")
			lblExplore.set_text(_("Explore Memory Stick"))

			btnConf = Handler.get_widget("btnConf")
			btnConf.connect("clicked", self.buildConf)
			btnConf.set_tooltip_text(_("Configuration Stuff"))
			lblConf = Handler.get_widget("lblConf")
			lblConf.set_text(_("Configuration"))

			btnAbout = Handler.get_widget("btnAbout")
			btnAbout.connect("clicked", self.buildAbout)
			btnAbout.set_tooltip_text(_("Know about us"))
			lblAbout = Handler.get_widget("lblAbout")
			lblAbout.set_text(_("About %s") %projectname)

			self.loadConf()

		if id == "games":

			def remext(file):
				"""Remove the extension form any file"""
				tmp = (len(file) - 4)
				return file[0:tmp]

			def loadGames(path, lstore, data):
				"""Reads a directory and fills treeview with formated data"""
				files = os.listdir(path)
		
				format = '<b>%s</b> <span foreground="#A5A5A5" font_size="small">[%.2f GB]</span>'

				if files != []:
				   for item in files:
					if item.lower().endswith('.iso') or item.lower().endswith('.cso'):
						size = float(os.path.getsize(path + "/%s" %item))
						lstore.append([format %(remext(item), size / 2**30), item])
						if data == 'local':
							self.LGames.append(item)
						else:
							self.PGames.append(item)

			
			Handler = gtk.glade.XML("GUI/psp_games.glade") 
		
			winGames = Handler.get_widget("window1")
			winGames.set_title(_("%s [Games manager]") %projectname)

			HBox = Handler.get_widget("hbox1")
			self.PB = Handler.get_widget("progressbar1")

			winGames.set_size_request(600,400)
			self.setWindow(winGames)

			self.btnOK = Handler.get_widget("btnAplicar")
			self.btnOK.connect("clicked", self.excuteToDoList)
			self.btnOK.set_tooltip_text(_("Execute all pending tasks"))

			self.lock = False
			self.ready = True
			self.space = True
			self.LGames = []
			self.PGames = []
			self.bytes = 0			
			self.actions = []
			self.updateSpaceBar()		

			## PC's Treeview
			scrolledwindow = gtk.ScrolledWindow()
			self.liststore = gtk.ListStore(str, str)
			self.treeview = gtk.TreeView(self.liststore)
			cell = gtk.CellRendererText()
			cell2 = gtk.CellRendererText()
			tvcolumn = gtk.TreeViewColumn(self.localiso, cell, markup=0)
			tvcolumn2 = gtk.TreeViewColumn("Hidden", cell2, text=1)
			tvcolumn2.set_visible(False)

			try:
				loadGames(self.localiso, self.liststore, 'local')
			except:
				self.liststore.append([_('Cannot access %s') %self.localiso,''])
				self.ready = False
			
			self.treeview.append_column(tvcolumn)
			self.treeview.append_column(tvcolumn2)
			self.treeview.set_search_column(0)
			tvcolumn.set_sort_column_id(0)
		        scrolledwindow.add(self.treeview)
			scrolledwindow.set_size_request(200, 250)
			HBox.pack_start(scrolledwindow)

			## Buttons w/ arrows
			VBox1 = gtk.VBox()
			
			image = gtk.Image()
			image.set_from_file("icons/R.png")
			image.show()
			btnder = gtk.Button()
			btnder.add(image)
			btnder.set_relief(gtk.RELIEF_NONE)
			btnder.connect("clicked", self.putGameIn)
			btnder.set_tooltip_text(_("Copy file from PC to PSP"))

			image = gtk.Image()
			image.set_from_file("icons/L.png")
			image.show()
			btnizq = gtk.Button()
			btnizq.add(image)
			btnizq.set_relief(gtk.RELIEF_NONE)
			btnizq.connect("clicked", self.takeGameOut)
			btnizq.set_tooltip_text(_("Delete file from PSP only"))

			VBox1.pack_start(btnder)
			VBox1.pack_start(btnizq)
			
			HBox.pack_start(VBox1)

			## PSP's TreeView
			scrolledwindow2 = gtk.ScrolledWindow()
			self.liststore2 = gtk.ListStore(str, str)
			self.treeview2 = gtk.TreeView(self.liststore2)
			cell = gtk.CellRendererText()
			cell2 = gtk.CellRendererText()
			tvcolumn = gtk.TreeViewColumn(self.mspsp, cell, markup=0)
			tvcolumn2 = gtk.TreeViewColumn("Hidden", cell2, text=1)
			tvcolumn2.set_visible(False)

			try:
				loadGames(self.mspsp, self.liststore2, 'psp')
			except:
				self.liststore2.append([_('Cannot access %s') %self.mspsp,''])
				self.ready = False

			self.treeview2.append_column(tvcolumn)
			self.treeview2.append_column(tvcolumn2)
			self.treeview2.set_search_column(0)
			tvcolumn2.set_sort_column_id(0)
		        scrolledwindow2.add(self.treeview2)
			scrolledwindow2.set_size_request(200, 250)
			HBox.pack_start(scrolledwindow2)

			if self.ready == False:
				self.notify(_("Neither PSP nor MS was found. Check configuration and try again"),"warn")
			
			HBox.show()
			winGames.show_all()	


		
		if id == "ciso":
			if os.path.isfile("/usr/bin/ciso") == False:
				self.notify(_("CISO app is not installed. Cannot continue."),"error")
				return

			Handler = gtk.glade.XML("GUI/psp_ciso.glade") 

			winCiso = Handler.get_widget("window1")
			winCiso.set_title(_("%s [CISO by Booster]") %projectname)

			self.setWindow(winCiso)

			lblBrowse = Handler.get_widget("lblBrowse")
			lblBrowse.set_text(_("Browse ..."))

			fbrowser = Handler.get_widget("selector")
			fbrowser.connect("clicked", self.browseFile)
			fbrowser.set_tooltip_text(_("Browser a iso/cso file"))

			self.lblinfo = Handler.get_widget("lblInfo")
			self.lblinfo.set_markup(_("<b>First, select a file</b>"))
			self.cDelete = Handler.get_widget("cDelete")
			self.cDelete.set_label(_("Delete original file when finish"))
			self.spinner = Handler.get_widget("spin")

			btnCiso = Handler.get_widget("btnCiso")
			btnCiso.connect("clicked", self.process)
			btnCiso.set_tooltip_text(_("Let's Go!"))

			winCiso.show_all()

		if id == "explore":
			os.system(self.Expl + " " + self.mspath)

		if id == "about":
			Handler = gtk.glade.XML("GUI/psp_about.glade") 

			winAbout = Handler.get_widget("window1")
			winAbout.set_title(_("%s [About]") %projectname)

			self.setWindow(winAbout)

			lblversion = Handler.get_widget("lblversion")
			lblversion.set_markup("<b>%s %s</b>" %(projectname, projectvers))

			lblcredits = Handler.get_widget("lblcredits")
			lblcredits.set_text(About)

			btnlink = Handler.get_widget("btnlink")
			btnlink.set_label(_("%s Website") %projectname)
			btnlink.set_uri(URL)

			winAbout.show_all()

		if id == "sg":
			Handler = gtk.glade.XML("GUI/psp_sg.glade") 

			self.winSG = Handler.get_widget("window1")
			self.winSG.set_size_request(480,272)
			self.winSG.set_title(_("%s [Savegames] Press 'H' for help") %projectname)

			self.winSG.connect("key-press-event", self.keySignal)
			self.setWindow(self.winSG)
			
			self.ltitulo = Handler.get_widget("ltitulo")
			self.lfecha = Handler.get_widget("lfecha")	
			self.llvl = Handler.get_widget("llvl")
			self.lporc = Handler.get_widget("lporc")

			self.mini = Handler.get_widget("mini")
			self.mini.set_size_request(144,80)
			is_available = True

			if data == 'local':
					try:
						flist = os.listdir(self.tSave)
						root = self.tSave
					except:
						is_available = False
						self.notify(_("Cannot access %s") %self.tSave, "error")
						self.winSG.destroy()
			else:
					if os.path.isdir(self.mssave):
						flist = os.listdir(self.mssave)
						root = self.mssave
					else:
						is_available = False
				 		self.notify(_("Cannot access %s") %self.mssave,"error")
						self.winSG.destroy()

			self.array = []
			self.index = 0

			if is_available:

				for item in flist:

					path = root + '/' + item + '/'
					f = open(path + 'PARAM.SFO', 'r')
					ts = os.path.getmtime(path + 'PARAM.SFO') 

					f.seek(272)  
					desc = f.read(751)

					f.seek(4656)
					desc2 = f.read(127)			
	
					f.seek(4784)
					gamename = f.read(127)

					f.close()

					n1 = gamename.replace('\x00','')
					d11 = desc.replace('\x00','')
					d22 = desc2.replace('\x00','')

					t = time.gmtime(int(ts))

					fecha = '%.2d/%.2d/%.2d  %.2d:%.2d' %(t[2],t[1],t[0],23 -(t[3] - 3),t[4])

					self.array.append([path, n1, d11, d22,fecha])
				
					f.close()


				self.winSG.show_all()
				self.Direction( None, 'first')

		if id == "conf":
			Handler = gtk.glade.XML("GUI/psp_conf.glade") 

			winConf = Handler.get_widget("window1")
			winConf.set_size_request(550,200)
			winConf.set_title(_("%s [Configuration]") %projectname)

			self.setWindow(winConf)

			lblOptions = Handler.get_widget("lblOptions")
			lblOptions.set_text(_("Options"))

			lblPath = Handler.get_widget("lblPath")
			lblPath.set_text(_("Paths"))

			lblExit = Handler.get_widget("lblExit")
			lblExit.set_text(_("Exit"))

			lblmount = Handler.get_widget("lblmount")
			lblmount.set_text(_("Path to PSP mount point (i.e /media/disk)"))
		
			lbliso = Handler.get_widget("lbliso")
			lbliso.set_text(_("I keep my iso/cso files in:"))

			lblsg = Handler.get_widget("lblsg")
			lblsg.set_text(_("and my savegames backup in:"))

			lbluseex = Handler.get_widget("lbluseex")
			lbluseex.set_text(_("Use my favourite file browser: (i.e nautilus)"))

			lblOSD = Handler.get_widget("lblOSD")
			lblOSD.set_markup(_("Notify events using OSD\n<b>libnotify-bin must be installed</b>"))

			self.ePSP = Handler.get_widget("ePSP")
			self.eISO = Handler.get_widget("eISO")
			self.eSave = Handler.get_widget("eSave")
			self.cOSD = Handler.get_widget("cOSD")
			self.cBell = Handler.get_widget("cBell")
			self.eExplorer = Handler.get_widget("eExplorer")

			self.ePSP.set_text(self.mspath)
			self.eISO.set_text(self.localiso)
			self.eSave.set_text(self.tSave)
			self.eExplorer.set_text(self.Expl)
			
			self.cOSD.set_active(self.oOSD)
			self.cBell.set_active(self.oBell)

			bApply = Handler.get_widget("bApply")
			bApply.connect("clicked", self.saveConf)

			bCancel = Handler.get_widget("bCancel")
			bCancel.connect("clicked", self.destroy, winConf)
		
			winConf.show_all()


#	def RemoveCPtask ( self, widget ):
#		pass
#
#	def RemoveRMtask ( self, widget ):
#		pass

	def destroy ( self, widget, win, sr=None):
		"""Destroy this window"""
		win.destroy()

	def loadConf ( self ):
		"""Read configuration from conf.dat"""
		cp2 = ConfigParser.ConfigParser()

		self.workingpath = self.validateDir( os.getcwd() )
		self.userpath = self.validateDir( os.path.expanduser("~") )

		self.currentFile = None
		new = False

		if os.path.isfile('conf.dat') == False:
			#First time using PSPMan or just new conf
			new = True
			cp2.add_section(_('Options'))
			cp2.set(_('Options'),'PSP_Path','/media/disk/')
			cp2.set(_('Options'),'ISO_Path',self.userpath + 'ISO/')
			cp2.set(_('Options'),'Save_Path',self.userpath + 'SAVEDATA/')
			cp2.set(_('Options'),'OSD', 0)
			cp2.set(_('Options'),'Bell', 0)
			cp2.set(_('Options'),'Expl', 'nautilus')

			with open('conf.dat','w') as file:
			    cp2.write(file)
			    

		cp2.read('conf.dat')

		self.mspath = cp2.get(_('Options'), 'PSP_Path')
		self.localiso = cp2.get(_('Options'), 'ISO_Path')
		self.tSave = cp2.get(_('Options'),'Save_Path')
		self.oOSD = cp2.get(_('Options'),'OSD')
		self.oBell = cp2.get(_('Options'),'Bell')
		self.Expl = cp2.get(_('Options'), 'Expl')
		
		self.oOSD = bool(int(self.oOSD))
		self.oBell = bool(int(self.oBell))

		self.mspsp = self.mspath + 'ISO'
		self.mssave = self.mspath + 'PSP/SAVEDATA'
		self.busy = False

		if new:
			self.notify(_("This is your first run. Please, go to configuration first."))

	def saveConf ( self, widget):
		"""Save Configuration on a file"""
		cp = ConfigParser.ConfigParser()

	
		cp.add_section(_('Options'))
		cp.set(_('Options'),'PSP_Path', self.validateDir( self.ePSP.get_text() ) )
		cp.set(_('Options'),'ISO_Path', self.validateDir( self.eISO.get_text() ) )
		cp.set(_('Options'),'Save_Path',self.validateDir( self.eSave.get_text()) )
		cp.set(_('Options'),'Expl', self.eExplorer.get_text() )

		#TODO Should a better workaround
		if self.cOSD.get_active() == True:
			cp.set(_('Options'),'OSD',1)
		else:
			cp.set(_('Options'),'OSD',0)

		if self.cBell.get_active() == True:
			cp.set(_('Options'),'Bell',1)
		else:
			cp.set(_('Options'),'Bell',0)

		with open('conf.dat','w') as file:
		    cp.write(file)
				
		# Refresh configuration
		self.loadConf()

#	def backupSG ( self, savegamepath ):
#		cmd = "cp -r \"" + savegamepath + "\" \"" + self.tSave + "\""
#		os.system(cmd)
#
#	def deleteSG ( self, savegamepath ):
#		cmd = "rm -r \"" + savegamepath + "\""
#		os.system(cmd)

	def setWindow ( self, window ):
		"""Set settings and show it!"""
		settings = window.get_settings()
            	settings.set_property("gtk-button-images", True)

		window.set_modal(True)
		window.set_resizable(False)
		window.present()

	def excuteToDoList ( self, widget ):
		"""Init thread for transfering stuff"""
		if not self.ready:
			return	

		if self.lock:	
			self.lock = False
			self.notify(_("Will stop after current job"),"warn")
		else:	
			self.lock = True
			self.btnOK.set_label('gtk-media-stop')
			self.btnOK.set_tooltip_text(_("Ends current job and then stops"))
			self.PB.set_text(_("Initalizing..."))
			self.busy = True
			Thread(target=self.ToDo).start()

	def ToDo ( self ):
		"""Process ToDo items one by one and check if cancel button was pressed"""
		i = 0

		for action in self.actions:
			if not self.lock:
				break
			else:
				foo = action.split()
				bar = foo[1].split("/")
				
				if foo[0] == "rm":
					self.PB.set_text( _("Erasing %s ...") %bar.split("/")[len(bar) - 1])
				else:
					self.PB.set_text( _("Copying %s ...") %bar.split("/")[len(bar) - 1])
				os.system(action)
				i = i + 1

		by = _("%.2f GB processed") %(self.bytes / 2**30)
		jc = _("\n%d job(s) complete. \nPlease do NOT remove MM or umount PSP immediately.")  %i

		self.notify(by + jc, "ok")
		self.busy = False
		self.lock = False
		self.btnOK.set_label('gtk-execute')
		self.btnOK.set_tooltip_text(_("Execute all pending tasks"))
		self.updateSpaceBar()

	def buildGames ( self, widget ):
		"""Build Games Window"""
		self.build("games")

	def buildPSPSavegames ( self, widget ):
		"""Build Savegame [PSP] Window"""
		self.build("sg", "psp")
	
	def buildLocalSavegames ( self, widget ):
		"""Build Savegame [Local] Window"""
		self.build("sg", "local")

	def buildCiso ( self, widget ):
		"""Build CISO Window"""
		self.build("ciso")

	def callExploreMS ( self, widget ):
		"""Called File explorer"""
		self.build("explore")

	def buildConf ( self, widget ):
		"""Build Configuration Window"""
		self.build("conf")

	def buildAbout ( self, widget ):
		"""Build About Window"""
		self.build("about")

	def getSelected( self, TV):
		"""return item selected in any treeview"""
		selection = TV.get_selection()
		result = selection.get_selected()
		model, iter = selection.get_selected()
		
		try:
			item = model.get_value(iter,1)
			pangoitem = model.get_value(iter,0)
		except:
			return None, None, None

		return item, pangoitem, iter


	def putGameIn ( self, widget ):
		"""Copy the selected item to PSP's treeview"""
		if self.ready == False or self.space == False:
			return		

		item, pangoitem, iter = self.getSelected(self.treeview)

		if item == None:
			return
			
		if item in self.PGames:
			#Already exists
			return 

		size = float(os.path.getsize(self.localiso + "/%s" %item))
		dec = self.checkFreeSpace(size / 2**30)

		if dec != None:
			if not dec:
				self.notify(_("Not enought space in %s" %self.mspsp),"warn")
				return
		else:
			self.notify(_("An error occurred while accessing PSP or MS"),"error")
			return

		self.liststore2.append([pangoitem,item])
		self.PGames.append(item)
		ac = "cp \"" + self.localiso + item + '\" \"' + self.mspsp + "\""
		self.actions.append(ac)
		self.bytes += size
		self.updateSpaceBar()

	def takeGameOut ( self, widget ):
		"""Remove selected item from PSP's treeview"""
		if self.ready == False:
			return		
		
		item, pangoitem, iter = self.getSelected(self.treeview2)

		if item == None:
			return
		
		#self.liststore.append([pangoitem,item])
		self.liststore2.remove(iter)
		self.PGames.remove(item)

		#If game is NOT on PSP, we read the size from pc.
		if os.path.isfile(self.mspsp + "/%s" %item):
			size = float(os.path.getsize(self.mspsp + "/%s" %item))
		else:
			size = float(os.path.getsize(self.localiso + "/%s" %item))
			
		ac = "rm \"" + self.mspsp +'/' + item + "\""
		self.actions.append(ac)
		self.bytes -= size
		self.updateSpaceBar()

	def process ( self, widget ):
		"""Prepare to work with an iso/cso file, choose the right command and execute it"""
		if self.currentFile:
			nivel = self.spinner.get_value()
			origen = self.currentFile
			cmd = ""
			modo = 0

			def MakeCmd(input, id):
				tmp = (len(input) - 4)
				output =  input[0:tmp]
				if id == 1:
					cmd = "ciso " + str(int(nivel)) + " \"" + input + "\" \"" +  output + ".iso\""
				else:
					cmd = "ciso " + str(int(nivel)) + " \"" + input + "\" \"" +  output + ".cso\""

				return cmd


			if int(nivel) == 0:
				#Decompress CSO a ISO
				if origen.lower().endswith('.cso') == False:
					self.lblinfo.set_markup(_("Selected file <b>IS NOT</b> a CSO file, or level is wrong"))
					return

				cmd = MakeCmd(self.currentFile, 1)

			else:
				#Compress ISO a CSO
				if origen.lower().endswith('.iso') == False:
					self.lblinfo.set_markup(_("Selected file <b>IS NOT</b> a ISO file, or level is wrong"))
					return

				cmd = MakeCmd(self.currentFile, 2)

				
			if cmd != "":
				if modo == 1:
					self.lblinfo.set_markup(_("<b>Decompressing </b> %s ..." % os.path.basename(self.currentFile)))

				if modo == 2:
					self.lblinfo.set_markup(_("<b>Compressing </b> %s ..." % os.path.basename(self.currentFile)))
					
				success_msj = _("%s was succesfully created!" % os.path.basename(self.currentFile))

				self.busy = True
				Thread(target=self.convertFile,args=(self.currentFile,cmd,success_msj)).start()

				
	def canILeave ( self, widget, window):
		"""If jobs remain queued, exit is forbidden"""
		if self.busy == False:
			os.system('rm .tmp.png')
			gtk.main_quit () 
		else:
			self.notify(_("Cannot quit. Jobs remain queued.","warn"))

	def convertFile (self, fi, cmd, txt):
		"""Compress or Decompress and ISO/CSO file"""
		os.system(cmd)
		self.notify (txt, "ok")			
		self.lblinfo.set_markup(_("<b>Select a file</b>"))
		
		if self.cDelete.get_active() == True:
			os.system("rm \"%s\"" %fi)

		self.busy = False

		
	def notify (self, msj, clase="info"):
		"""Spawn notifications using setWindow dialogs or OSD notification if available"""
		if self.oOSD == False:
			tipos = {
					'info' : gtk.MESSAGE_INFO, 
					'warn' : gtk.MESSAGE_WARNING,
					'ok'   : gtk.MESSAGE_INFO, 
					'error': gtk.MESSAGE_ERROR,
				}

			tipo = tipos.get(clase)
			dialog = gtk.MessageDialog(type=tipo,message_format=msj,buttons=gtk.BUTTONS_OK)
				
			if dialog.run() == gtk.RESPONSE_OK or dialog.run() == gtk.RESPONSE_DELETE_EVENT:
				dialog.hide()		

		else:
			if self.osd_available:
				n = pynotify.Notification(projectname, msj , self.workingpath + "icons/" + clase + ".png")
				n.set_hint_string ("x-canonical-append", "allowed")
				n.show()
		


	def updateSpaceBar ( self ):
		"""Update the gtk progressbar in game's window"""
		try:
			f = os.statvfs(self.mspsp)
		except:
			f = None

		if f:
			free = float((f.f_bsize * f.f_bavail - self.bytes))
			fspace = "%.2f" %(free / 1073741824)
	
			tot = float(f.f_bsize * f.f_blocks)
			tspace = math.ceil(float("%f" % (tot / 1073741824)))

			ms = _("Memory Stick size: %s GB") %str(tspace)
			fs = _("  (Free: %s GB)") %str(fspace)

			self.PB.set_text( ms + fs )

			frac = 1 - ((free / 1073741824) / (tot / 1073741824))
			self.PB.set_fraction(frac)

			if free <= 0.25:
				self.notify(_("Not enought space"), "warn")
				self.space = False
			else:
				self.space = True

		else:
			self.PB.set_text(_("An error ocurred. Information N/A at this moment."))
			self.PB.set_fraction(0)
	

	def browseFile ( self, widget ):
		 """Open FileChooser Dialog"""
		 self.currentFile = None

		 file_open = gtk.FileChooserDialog(title=_("Please, select an ISO or CSO file")
		             , action=gtk.FILE_CHOOSER_ACTION_OPEN
		            , buttons=(gtk.STOCK_CANCEL
		                         , gtk.RESPONSE_CANCEL
		                         , gtk.STOCK_OPEN
		                         , gtk.RESPONSE_OK))
		 result = ""
		 if file_open.run() == gtk.RESPONSE_OK:
		     result = file_open.get_filename()
		 file_open.destroy()

		 if result:
	                 self.lblinfo.set_markup(_("<b>%s</b> selected!" %os.path.basename(result)))
			 self.currentFile = result


	def cutText ( self, text, max=20, suffix='...' ):
		"""Limit a string lenght, and add a suffix"""
		if len(text) > max:
			return text[0:max] + suffix
		else:
			return text

	def checkFreeSpace( self, new_size ):
		"""Check if PSP have enough size for new_size"""
		try:
			f = os.statvfs(self.mspsp)
		except:
			f = None

		if f:
			free = float((f.f_bsize * f.f_bavail - self.bytes))
			fspace = "%.2f" %(free / 1073741824)

			size = "%.2f" %new_size

			if fspace <= size:
				return False
			else:
				return True

		else:	

			return None


	def Direction ( self, widget, goto):
		if self.array == []:
			self.noMoreSG()

		if goto == "first":
			self.index = 0

		else:
			if goto == "back":
				self.index -= 1
		
				if self.index < 0:
					self.index = (len(self.array)-1)
			else:
				self.index += 1
		
				if self.index > (len(self.array) - 1):
					self.index = 0

		
		try:
			Ruta = self.array[self.index][0] 
			Titulo = self.array[self.index][1].replace("\n"," ")
			Porcentaje = self.array[self.index][2]
			Nivel = self.array[self.index][3]
			Fecha = self.array[self.index][4]
		except:
			self.noMoreSG()
			return


		mini = Ruta + 'ICON0.PNG'

		if os.path.isfile(mini) == False:
			self.mini.set_from_file(self.workingpath + 'icons/NO_ICON0.jpg')
		else:
			self.mini.set_from_file(Ruta + 'ICON0.PNG')

	
		path = Ruta + 'PIC1.PNG'
		
		if os.path.isfile(path) == False:
			path = self.workingpath + 'icons/psp.png'
			use_original = True
		else:
			if self.makeDarker(path) == None:
				use_original = True
			else:
				use_original = False

		self.winSG.set_app_paintable(False)
		if use_original:
			pixbuf = gtk.gdk.pixbuf_new_from_file(path) 
		else:
			pixbuf = gtk.gdk.pixbuf_new_from_file(".tmp.png") 
		pixmap, mask = pixbuf.render_pixmap_and_mask() 
		width, height = pixmap.get_size() 
		del pixbuf 
		self.winSG.set_app_paintable(True) 
		self.winSG.resize(width, height) 
		self.winSG.realize() 
		self.winSG.window.set_back_pixmap(pixmap, False) 
		del pixmap 


		template = '<span foreground="#F0F0F0">%s</span>'
		template2 = '<span foreground="#A9A9A9"><tt><u>%s</u></tt></span>'
						
		Titulo = template2 %self.cutText(Titulo,25,'...')
		Porc = template %self.cutText(Porcentaje,70,"\n...")
		Nivel = template %self.cutText(Nivel,70,"...")
		fecha = template %Fecha

		self.ltitulo.set_markup(Titulo)
		self.lfecha.set_markup(fecha)
		self.lporc.set_markup(Porc)
		self.llvl.set_markup(Nivel)

	def deleteSaveGame ( self, widget, device):
		"""Delete selected savegame"""
		if self.array == []:
			self.noMoreSG()
			return
			
		com = "rm -r \"%s\"" %self.array[self.index][0]
			
		if os.path.isdir(self.array[self.index][0]):
			## no need of a thread for this, it will take 5 seconds tops
			os.system(com)
			self.notify(_("%s deleted!!" %self.array[self.index][1].replace("\n"," ")),"ok")
			del self.array[self.index]
			self.index -= 1
			self.Direction( None, 'ahead')
		else:
			self.notify(_("Error while deleting %s!" %self.array[self.index][1].replace("\n"," ")),"error")


	def copySaveGame ( self, widget, device):
		"""Depending of current window, it will backup or restore current savegame"""
		if self.array == []:
			self.noMoreSG()
			return

		if device == 'local':
			com = "cp -pr \"%s\" \"%s\"" %(self.array[self.index][0], self.mssave)
		else:
			com = "cp -pr \"%s\" \"%s\"" %(self.array[self.index][0], self.tSave)
		
		if os.path.isdir(self.mssave):
			## no need of a thread for this, it will take 5 seconds tops
			os.system(com)
			self.notify(_("%s copied!!" %self.array[self.index][1].replace("\n"," ")),"ok")
		else:
			self.notify(_("Error while copying %s!" %self.array[self.index][1].replace("\n"," ")),"error")

	def noMoreSG( self ):
		"""To be more friendly, we show a "There are no sg" instead of an error"""
		self.mini.set_from_file(self.workingpath + '/icons/NO_ICON0.jpg')
		self.ltitulo.set_markup(_("<b>There are no savegames</b>"))
		self.lfecha.set_text("")
		self.lporc.set_text(_('If any, please check paths in configuration.'))
		self.llvl.set_text('')
		return

	def validateDir ( self, path ):
		"""Force all paths to end with /"""
		if path.endswith('/'):
			return path
		else:
		   	return path + '/'

	def keySignal(self, widget, event):
		"""Called when a key is pressed in Savegame window"""
		if event.keyval == 65363:
			self.Direction(None,'ahead')

		if event.keyval == 65361:
			self.Direction(None,'back')

		if event.keyval == 104 or event.keyval == 72:
			self.notify(_("Left  = Go back\n" \
				    "Right = Go fordward\n" \
				    "  S   = Save/Restore Savegame\n" \
				    "  D   = Delete savegame\n" \
				    "  H   = Show this help"))
			
		if event.keyval == 115 or event.keyval == 83:
			self.copySaveGame(None,None)

		if event.keyval == 100 or event.keyval == 68:
			Titulo = self.array[self.index][1].replace("\n"," ")
			dialog = gtk.MessageDialog(type=gtk.MESSAGE_QUESTION,message_format=_("Delete %s?") %Titulo,buttons=gtk.BUTTONS_OK_CANCEL)
				
			if dialog.run() == gtk.RESPONSE_OK:
				self.deleteSaveGame(None,None)
				dialog.destroy()
			else:
				dialog.destroy()
			

	def makeDarker(self, path):
		"""Receive a image path and make it a little darker.
		   Output is saved as .tmp.png"""
		try:
			im = Image.open(path)
		except:
			return None

		enhancer = ImageEnhance.Brightness(im)
		bright_im = enhancer.enhance(0.3)
		sharp_im = bright_im.filter(ImageFilter.SHARPEN)
		sharp_im.save(".tmp.png")
		return True


if __name__ == "__main__":
	hwg = PSP()
	gtk.main()
