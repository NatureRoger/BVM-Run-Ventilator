
# https://www.tutorialspoint.com/wxpython/wx_combobox_choice_class.htm

import os
import platform
import queue
import sys
import time
import threading
import traceback
import io as StringIO
import subprocess
import glob
import logging
import re

try: import simplejson as json
except ImportError: import json

#from . import pronsole
#from . import printcore
#from printrun.spoolmanager import spoolmanager_gui


try:
    import wx
    import wx.adv
    if wx.VERSION < (4,):
        raise ImportError()
except:
    logging.error(_("WX >= 4 is not installed. This program requires WX >= 4 to run."))
    raise

class Mywin(wx.Frame): 
   def __init__(self, parent, title): 
      super(Mywin, self).__init__(parent, title = title,size = (300,200)) 
		
      panel = wx.Panel(self) 
      box = wx.BoxSizer(wx.VERTICAL) 
      self.label = wx.StaticText(panel,label = "Your choice:" ,style = wx.ALIGN_CENTRE) 
      box.Add(self.label, 0 , wx.EXPAND |wx.ALIGN_CENTER_HORIZONTAL |wx.ALL, 20) 
      cblbl = wx.StaticText(panel,label = "Combo box",style = wx.ALIGN_CENTRE) 
		
      box.Add(cblbl,0,wx.EXPAND|wx.ALIGN_CENTER_HORIZONTAL|wx.ALL,5) 
      languages = ['C', 'C++', 'Python', 'Java', 'Perl'] 
      com_list = ['Com1', 'Com2', 'Com3', 'Com4', 'Com5', 'Com6', 'Com7', 'Com8']  # self.scanserial()
      #combo='Com5'
      self.combo = wx.ComboBox(panel, choices =  com_list ,
                                  style = wx.CB_DROPDOWN)
		
      box.Add(self.combo,1,wx.EXPAND|wx.ALIGN_CENTER_HORIZONTAL|wx.ALL,5) 
      chlbl = wx.StaticText(panel,label = "Choice control",style = wx.ALIGN_CENTRE) 
		
      box.Add(chlbl,0,wx.EXPAND|wx.ALIGN_CENTER_HORIZONTAL|wx.ALL,5) 
      self.choice = wx.Choice(panel,choices = languages) 
      box.Add(self.choice,1,wx.EXPAND|wx.ALIGN_CENTER_HORIZONTAL|wx.ALL,5) 
         
      box.AddStretchSpacer() 
      self.combo.Bind(wx.EVT_COMBOBOX, self.OnCombo) 
      self.choice.Bind(wx.EVT_CHOICE, self.OnChoice)
		
      panel.SetSizer(box) 
      self.Centre() 
      self.Show() 
		  
   def OnCombo(self, event): 
      self.label.SetLabel("You selected"+self.combo.GetValue()+" from Combobox") 
		
   def OnChoice(self,event): 
      self.label.SetLabel("You selected "+ self.choice.GetString
         (self.choice.GetSelection())+" from Choice") 

   def scanserial(self):
      """scan for available ports. return a list of device names."""
      baselist = []
      if os.name == "nt":
          try:
              key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, "HARDWARE\\DEVICEMAP\\SERIALCOMM")
              i = 0
              while(1):
                  baselist += [winreg.EnumValue(key, i)[1]]
                  i += 1
          except:
              pass

      for g in ['/dev/ttyUSB*', '/dev/ttyACM*', "/dev/tty.*", "/dev/cu.*", "/dev/rfcomm*"]:
          baselist += glob.glob(g)
      if(sys.platform!="win32" and self.settings.devicepath):
          baselist += glob.glob(self.settings.devicepath)
      return [p for p in baselist if self._bluetoothSerialFilter(p)]      
                             
app = wx.App() 
Mywin(None,  'ComboBox and Choice demo') 
app.MainLoop()