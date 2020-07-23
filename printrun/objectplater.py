# This file is part of the BVM-run Ventilator suite, it's based on 
# Printrun.
#
# BVM-run and Printrun is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Printrun is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Printrun.  If not, see <http://www.gnu.org/licenses/>.


from .utils import install_locale, iconfile
install_locale('plater')

import logging
import os
import platform
import types
import wx

import time
from numba import jit
import math

import matplotlib
##matplotlib.use('GTK3Agg') 
import numpy as np
import matplotlib.figure as mfigure
import matplotlib.animation as manim
import matplotlib.pyplot as plt #import matplotlib library

from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg

import serial # import Serial Library
import random
random.seed()

def patch_method(obj, method, replacement):
    orig_handler = getattr(obj, method)

    def wrapped(*a, **kwargs):
        kwargs['orig_handler'] = orig_handler
        return replacement(*a, **kwargs)
    setattr(obj, method, types.MethodType(wrapped, obj))

class PlaterPanel(wx.Panel):
    def __init__(self, **kwargs):
        self.destroy_on_done = False
        parent = kwargs.get("parent", None)
        super(PlaterPanel, self).__init__(parent = parent)
        self.prepare_ui(**kwargs)

    def prepare_ui(self, filenames = [], callback = None, parent = None, build_dimensions = None):
        self.filenames = filenames
        self.mainsizer = wx.BoxSizer(wx.HORIZONTAL)
        panel = self.menupanel = wx.Panel(self, -1)
        sizer = self.menusizer = wx.GridBagSizer()
        self.l = wx.ListBox(panel)
        sizer.Add(self.l, pos = (1, 0), span = (1, 2), flag = wx.EXPAND)
        sizer.AddGrowableRow(1, 1)
        # Clear button
        clearbutton = wx.Button(panel, label = _("Clear"))
        clearbutton.Bind(wx.EVT_BUTTON, self.clear)
        sizer.Add(clearbutton, pos = (2, 0), span = (1, 2), flag = wx.EXPAND)
        # Load button
        loadbutton = wx.Button(panel, label = _("Load"))
        loadbutton.Bind(wx.EVT_BUTTON, self.load)
        sizer.Add(loadbutton, pos = (0, 0), span = (1, 1), flag = wx.EXPAND)
        # Snap to Z = 0 button
        snapbutton = wx.Button(panel, label = _("Snap to Z = 0"))
        snapbutton.Bind(wx.EVT_BUTTON, self.snap)
        sizer.Add(snapbutton, pos = (3, 0), span = (1, 1), flag = wx.EXPAND)
        # Put at center button
        centerbutton = wx.Button(panel, label = _("Put at center"))
        centerbutton.Bind(wx.EVT_BUTTON, self.center)
        sizer.Add(centerbutton, pos = (3, 1), span = (1, 1), flag = wx.EXPAND)
        # Delete button
        deletebutton = wx.Button(panel, label = _("Delete"))
        deletebutton.Bind(wx.EVT_BUTTON, self.delete)
        sizer.Add(deletebutton, pos = (4, 0), span = (1, 1), flag = wx.EXPAND)
        # Auto arrange button
        autobutton = wx.Button(panel, label = _("Auto arrange"))
        autobutton.Bind(wx.EVT_BUTTON, self.autoplate)
        sizer.Add(autobutton, pos = (5, 0), span = (1, 2), flag = wx.EXPAND)
        # Export button
        exportbutton = wx.Button(panel, label = _("Export"))
        exportbutton.Bind(wx.EVT_BUTTON, self.export)
        sizer.Add(exportbutton, pos = (0, 1), span = (1, 1), flag = wx.EXPAND)
        if callback != None:
            donebutton = wx.Button(panel, label = _("Done"))
            donebutton.Bind(wx.EVT_BUTTON, lambda e: self.done(e, callback))
            sizer.Add(donebutton, pos = (6, 0), span = (1, 1), flag = wx.EXPAND)
            cancelbutton = wx.Button(panel, label = _("Cancel"))
            cancelbutton.Bind(wx.EVT_BUTTON, lambda e: self.Destroy())
            sizer.Add(cancelbutton, pos = (6, 1), span = (1, 1), flag = wx.EXPAND)
        self.basedir = "."
        self.models = {}
        panel.SetSizerAndFit(sizer)
        self.mainsizer.Add(panel, flag = wx.EXPAND)
        self.SetSizer(self.mainsizer)
        if build_dimensions:
            self.build_dimensions = build_dimensions
        else:
            self.build_dimensions = [200, 200, 100, 0, 0, 0]

    def set_viewer(self, viewer):
        # Patch handle_rotation on the fly
        if hasattr(viewer, "handle_rotation"):
            def handle_rotation(self, event, orig_handler):
                if self.initpos is None:
                    self.initpos = event.GetPosition()
                else:
                    if event.ShiftDown():
                        p1 = self.initpos
                        p2 = event.GetPosition()
                        x1, y1, _ = self.mouse_to_3d(p1[0], p1[1])
                        x2, y2, _ = self.mouse_to_3d(p2[0], p2[1])
                        self.parent.move_shape((x2 - x1, y2 - y1))
                        self.initpos = p2
                    else:
                        orig_handler(event)
            patch_method(viewer, "handle_rotation", handle_rotation)
        # Patch handle_wheel on the fly
        if hasattr(viewer, "handle_wheel"):
            def handle_wheel(self, event, orig_handler):
                if event.ShiftDown():
                    delta = event.GetWheelRotation()
                    angle = 10
                    if delta > 0:
                        self.parent.rotate_shape(angle / 2)
                    else:
                        self.parent.rotate_shape(-angle / 2)
                else:
                    orig_handler(event)
            patch_method(viewer, "handle_wheel", handle_wheel)
        self.s = viewer
        self.mainsizer.Add(self.s, 1, wx.EXPAND)

    def move_shape(self, delta):
        """moves shape (selected in l, which is list ListBox of shapes)
        by an offset specified in tuple delta.
        Positive numbers move to (rigt, down)"""
        name = self.l.GetSelection()
        if name == wx.NOT_FOUND:
            return False

        name = self.l.GetString(name)

        model = self.models[name]
        model.offsets = [model.offsets[0] + delta[0],
                         model.offsets[1] + delta[1],
                         model.offsets[2]
                         ]
        return True

    def rotate_shape(self, angle):
        """rotates acive shape
        positive angle is clockwise
        """
        name = self.l.GetSelection()
        if name == wx.NOT_FOUND:
            return False
        name = self.l.GetString(name)
        model = self.models[name]
        model.rot += angle

    def autoplate(self, event = None):
        logging.info(_("Autoplating"))
        separation = 2
        try:
            from printrun import packer
            p = packer.Packer()
            for i in self.models:
                width = abs(self.models[i].dims[0] - self.models[i].dims[1])
                height = abs(self.models[i].dims[2] - self.models[i].dims[3])
                p.add_rect(width, height, data = i)
            centerx = self.build_dimensions[0] / 2 + self.build_dimensions[3]
            centery = self.build_dimensions[1] / 2 + self.build_dimensions[4]
            rects = p.pack(padding = separation,
                           center = packer.Vector2(centerx, centery))
            for rect in rects:
                i = rect.data
                position = rect.center()
                self.models[i].offsets[0] = position.x
                self.models[i].offsets[1] = position.y
        except ImportError:
            bedsize = self.build_dimensions[0:3]
            cursor = [0, 0, 0]
            newrow = 0
            max = [0, 0]
            for i in self.models:
                self.models[i].offsets[2] = -1.0 * self.models[i].dims[4]
                x = abs(self.models[i].dims[0] - self.models[i].dims[1])
                y = abs(self.models[i].dims[2] - self.models[i].dims[3])
                centre = [x / 2, y / 2]
                centreoffset = [self.models[i].dims[0] + centre[0],
                                self.models[i].dims[2] + centre[1]]
                if (cursor[0] + x + separation) >= bedsize[0]:
                    cursor[0] = 0
                    cursor[1] += newrow + separation
                    newrow = 0
                if (newrow == 0) or (newrow < y):
                    newrow = y
                # To the person who works out why the offsets are applied
                # differently here:
                #    Good job, it confused the hell out of me.
                self.models[i].offsets[0] = cursor[0] + centre[0] - centreoffset[0]
                self.models[i].offsets[1] = cursor[1] + centre[1] - centreoffset[1]
                if (max[0] == 0) or (max[0] < (cursor[0] + x)):
                    max[0] = cursor[0] + x
                if (max[1] == 0) or (max[1] < (cursor[1] + x)):
                    max[1] = cursor[1] + x
                cursor[0] += x + separation
                if (cursor[1] + y) >= bedsize[1]:
                    logging.info(_("Bed full, sorry sir :("))
                    self.Refresh()
                    return
            centerx = self.build_dimensions[0] / 2 + self.build_dimensions[3]
            centery = self.build_dimensions[1] / 2 + self.build_dimensions[4]
            centreoffset = [centerx - max[0] / 2, centery - max[1] / 2]
            for i in self.models:
                self.models[i].offsets[0] += centreoffset[0]
                self.models[i].offsets[1] += centreoffset[1]
        self.Refresh()

    def clear(self, event):
        result = wx.MessageBox(_('Are you sure you want to clear the grid? All unsaved changes will be lost.'),
                               _('Clear the grid?'),
                               wx.YES_NO | wx.ICON_QUESTION)
        if result == 2:
            self.models = {}
            self.l.Clear()
            self.Refresh()

    def center(self, event):
        i = self.l.GetSelection()
        if i != -1:
            m = self.models[self.l.GetString(i)]
            centerx = self.build_dimensions[0] / 2 + self.build_dimensions[3]
            centery = self.build_dimensions[1] / 2 + self.build_dimensions[4]
            m.offsets = [centerx, centery, m.offsets[2]]
            self.Refresh()

    def snap(self, event):
        i = self.l.GetSelection()
        if i != -1:
            m = self.models[self.l.GetString(i)]
            m.offsets[2] = -m.dims[4]
            self.Refresh()

    def delete(self, event):
        i = self.l.GetSelection()
        if i != -1:
            del self.models[self.l.GetString(i)]
            self.l.Delete(i)
            self.l.Select(self.l.GetCount() - 1)
            self.Refresh()

    def add_model(self, name, model):
        newname = os.path.split(name.lower())[1]
        if not isinstance(newname, str):
            newname = str(newname, "utf-8")
        c = 1
        while newname in self.models:
            newname = os.path.split(name.lower())[1]
            newname = newname + "(%d)" % c
            c += 1
        self.models[newname] = model

        self.l.Append(newname)
        i = self.l.GetSelection()
        if i == wx.NOT_FOUND:
            self.l.Select(0)

        self.l.Select(self.l.GetCount() - 1)

    def load(self, event):
        dlg = wx.FileDialog(self, _("Pick file to load"), self.basedir, style = wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
        dlg.SetWildcard(self.load_wildcard)
        if dlg.ShowModal() == wx.ID_OK:
            name = dlg.GetPath()
            self.load_file(name)
        dlg.Destroy()

    def load_file(self, filename):
        raise NotImplementedError

    def export(self, event):
        dlg = wx.FileDialog(self, _("Pick file to save to"), self.basedir, style = wx.FD_SAVE)
        dlg.SetWildcard(self.save_wildcard)
        if dlg.ShowModal() == wx.ID_OK:
            name = dlg.GetPath()
            self.export_to(name)
        dlg.Destroy()

    def export_to(self, name):
        raise NotImplementedError

class PlaterPanel1(wx.Panel):
    def __init__(self, **kwargs):
        self.destroy_on_done = False
        parent = kwargs.get("parent", None)
        style = wx.DEFAULT_FRAME_STYLE & (~wx.CLOSE_BOX) & (~wx.MAXIMIZE_BOX)
        super(PlaterPanel, self).__init__(parent = parent, style=style)
        #self.prepare_ui(**kwargs)


@jit(nopython=True)  # Set "nopython" mode for best performance, equivalent to @njit
def calc_P(p_value): # Function is compiled to machine code when called the first time
    return p_value * 1.0197442889221 

@jit(nopython=True) # Set "nopython" mode for best performance, equivalent to @njit
def calc_Velocity(diff_P, r_density): 
    return math.sqrt( 2 *  diff_P / r_density  )

@jit(nopython=True) # Set "nopython" mode for best performance, equivalent to @njit
def calc_Flow_value(Radius,radius_tube, Velocity):
    return 3.141592653589793 * (Radius**2- radius_tube**2) *  Velocity * 1000 * 60


class plotPanel(wx.Panel):
    def __init__(self, parent, strPort, Baudrate, id=-1, dpi=None, **kwargs):
    #    super().__init__(parent, id=id, **kwargs)    
    #def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        

        #self.fig, (self.ax1,self.ax2) = plt.subplots(nrows=2)

        self.fig = mfigure.Figure()
        #self.fig = plt.figure(figsize=(16,8))
        #self.ax1 = self.fig.add_subplot(211)
        #self.ax2 = self.fig.add_subplot(311)
        self.ax1 = self.fig.add_axes([0.1, 0.5, 0.8, 0.4],
                   xticklabels=[], ylim=(-2, 55))
        self.ax2 = self.fig.add_axes([0.1, 0.1, 0.8, 0.4],
                   ylim=(-2, 350))       
        self.canv = FigureCanvasWxAgg(self, wx.ID_ANY, self.fig)

        if strPort!='None':
            self.arduinoData = serial.Serial(strPort, Baudrate) #Creating our serial object named arduinoData
            time.sleep(1)

        self.PORT=strPort
        self.values1 = []
        self.values2 = []             
        self.arduinoString =''

        self.base_P_TEST_TIMES=16
        self.cnt=0
        self.Total_P=0
        self.base_P=0
        self.Delta_P=0
        self.Total_temp=0
        self.base_temp=0

        platform_str=platform.platform()

        self.x_time=0     
        

        self.r_density      = 1.204    ## density of fluid (kg/m3)
        self.pi             = 3.141592653589793
        self.Radius         = 0.012    ## "Radius" : inner diameter of the 3d print pipe 
                             ##            12mm ->  0.012m / 2 = 0.006m   
        self.radius_tube    = 0.002    ## "radius_tube" : diameter of the Pitot Tube
                                  ##       4mm ->  0.004m / 2 = 0.002m 

        if 'raspi' in platform_str:  ## raspberry pi slow down the refresh interval
            self.x_width=100
            v_interval=120
            self.recv_time=0.12
            self.plot_time=0.24
            self.blockFactor=6
        else:
            self.x_width=100
            v_interval=80
            self.recv_time=0.1
            self.plot_time=0.1
            self.blockFactor=3

            """
            self.x_width=100
            v_interval=80
            self.recv_time=0.1
            self.plot_time=0.1
            self.blockFactor=3
            """

        #self.ax1.clear()
        self.ax1.set_xlim([0,self.x_width])
        self.ax1.set_ylim([-2,55]) 
        self.ax1.set_xlabel('X time') 
        #self.ax1.yaxis.set_label_position("right")
        self.ax1.set_ylabel('Pressure (cmH2O)')  

        #self.ax2.clear()
        self.ax2.set_xlim([0,self.x_width])
        self.ax2.set_ylim([-2,350]) 
        self.ax2.set_xlabel('X time') 

        #self.ax2.yaxis.set_label_position("right")
        self.ax2.set_ylabel('Flow (L/Min)')  

        self.tget=0
        self.t1 = time.time()
        #self.animator = manim.FuncAnimation(self.fig, self.anim, interval=v_interval, repeat=False) 
        self.animator = manim.FuncAnimation(self.fig, self.anim, interval=v_interval) 

        # Now put all into a sizer
        sizer = wx.BoxSizer(wx.VERTICAL)
        # This way of adding to sizer allows resizing
        sizer.Add(self.canv, 1, wx.LEFT | wx.TOP | wx.GROW)
        ## Best to allow the toolbar to resize!
        #sizer.Add(self.toolbar, 0, wx.GROW)
        self.SetSizer(sizer)
        self.Fit()        

    def anim(self,i):
        arduinoString_ok=False
        dataArray=[9,0,0,0,0]
        
        if (self.tget==0 or self.tget>self.plot_time):
          self.t1 = time.time()

        ### read serial line
        if self.PORT!='None':
            while (self.arduinoData.inWaiting()==0): #Wait here until there is data
                pass #do nothing

            arduinoString = self.arduinoData.readline() #read the line of text from the serial port
            #print(arduinoString)
            #print(arduinoString.decode()[0])
            if(arduinoString[0]==48 and (self.tget==0 or self.tget>self.recv_time)):  
              dataArray = arduinoString.decode().strip().split(',')  #Split it into an array called dataArray 
              if (float( dataArray[4] )>0.2 or float( dataArray[2] )> self.base_P+1) or random.randint(1, 10)>self.blockFactor :
                arduinoString_ok=True                                          
                                                           # str→bytes：encode()方法。str通过encode()方法可以转换为bytes。
                                                           #bytes→str：decode()方法。如果我们从网络或磁盘上读取了字节流，那么读到的数据就是bytes。要把bytes变为str，就需要用decode()方法。
                  #line 115, in <module> if ('SDP810-500PA' in arduinoString.decode()  or 'BMP180' in arduinoString.decode()):
                  #UnicodeDecodeError: 'utf-8' codec can't decode byte 0xfe in position 0: invalid start byte
              
            if "Windows" in platform.platform() and arduinoString_ok==True :
               if (self.tget> self.plot_time) :
                   self.ax1.clear()
                   self.ax1.set_xlim([0,self.x_width])
                   self.ax1.set_ylim([-2,55]) 
                   self.ax1.set_ylabel('Pressure (cmH2O)') 
                   self.ax2.clear()          
                   self.ax2.set_xlim([0,self.x_width])
                   self.ax2.set_ylim([-2,350])
                   self.ax2.set_ylabel('Flow (L/Min)')  

            elif ('SDP810-500PA' in arduinoString.decode()  or 'BMP180' in arduinoString.decode()):
               print(arduinoString.decode())
               arduinoString_ok==False
            else:
               arduinoString_ok==False                  

            #print(arduinoString)
            #print ('arduinoString[0] %s' % (arduinoString[0]))
            #if(arduinoString[0]!=0xfe and arduinoString[0]!=0xb7):
            ###if ('SDP810-500PA' in arduinoString.decode()  or 'BMP180' in arduinoString.decode()):
                ###print(arduinoString.decode())
                ###arduinoString_ok==False
        else:

            dataArray[0] = '0'
            dataArray[1] = random.randint(27, 32)       ## bmp180 temp
            dataArray[2] = random.randint(1007, 1042)   ## bmp180 Pressure (hPa)
            dataArray[3] = random.randint(27, 32)       ## SDP810-500PA SDP_temp
            dataArray[4] = random.randint(0, 28)        ## SDP810-500PA diff_P 0->400
            arduinoString_ok=True

            if "Windows" in platform.platform():
              if (self.tget> self.plot_time) :
                  self.ax1.clear()
                  self.ax1.set_xlim([0,self.x_width])
                  self.ax1.set_ylim([-2,55]) 
                  self.ax1.set_ylabel('Pressure (cmH2O)') 
                  self.ax2.clear()          
                  self.ax2.set_xlim([0,self.x_width])
                  self.ax2.set_ylim([-2,350])
                  self.ax2.set_ylabel('Flow (L/Min)')              


        t3 = time.time()

        if (arduinoString_ok==True):
            Flow_value = 0

            #T(°C) = (T(°F) - 32) / 1.8
            #temp = (float( dataArray[0] ) - 32 ) /1.8 #Convert first element to floating number and put in temp C
            temp = float( dataArray[1] )               # Get (°C) 
            P =    round(calc_P(float( dataArray[2])),3)    #Convert second element to floating number and put in P  cmH2O
                                                       #Hectopascals to centimeters of water conversion formula
                                                       #Pressure(cmH2O) = Pressure (hPa) × 1.0197442889221
            SDP_temp= float( dataArray[3] )            # Get SDP810-500PA TEMPRATURE (°C) 
            diff_P =  float( dataArray[4] ) 

            if diff_P<=0 :
               Velocity = 0
               Flow_value = 0
            else:
              #Velocity   = np.sqrt( 2 *  diff_P / self.r_density  ) 
              Velocity   = calc_Velocity(diff_P, self.r_density )
              #Flow_value = round(self.pi * (self.Radius*self.Radius-self.radius_tube*self.radius_tube) *  Velocity * 1000, 3)
              #Flow_value = Flow_value * 60
              Flow_value = calc_Flow_value(self.Radius,self.radius_tube, Velocity)
              #print ("; BMP180 TempC, cmH2O ; DP810-50radius_tube0PA TempC, Pitot Tube Diff Pressrue : %s, %s, %s, %s, %s" % (temp, P,SDP_temp, diff_P, Flow_value))
            

            if i < self.base_P_TEST_TIMES and P>0:
              self.Total_P = self.Total_P + P
              self.Total_temp = self.Total_temp + temp
              self.cnt=self.cnt+1
            elif i == self.base_P_TEST_TIMES: 
              self.base_P = self.Total_P / (self.cnt)
              self.base_temp = self.Total_temp / (self.cnt)
              if self.PORT=='None':
                self.base_P = 1027
                self.base_temp = 28
              #print ('base_P = %s , base_temp = %s' % (self.base_P, self.base_temp))
              self.values1 = []
              self.values2 = []
              #self.Delta_P= round(P - self.base_P, 3)
              #self.values1.append(self.Delta_P)
              #self.values2.append(Flow_value)
              self.x_time=0
            else:  
              if self.base_P==0:
                self.base_P =  P
              self.Delta_P= round(P - self.base_P, 3)
              #print ('Delta pressure: = %s , Flow_value = %s' % (self.Delta_P, Flow_value))
              
              if (self.tget> self.plot_time) :
                  self.x_time=self.x_time+1 
                  self.values1.append(self.Delta_P) 
                  self.values2.append(Flow_value)
                  #print ('base_P = %s , Delta_P = %s' % (self.base_P, self.Delta_P))
                  ##print(self.values1)
                  ##print(self.values2)
                  self.ax2.plot(np.arange(1,self.x_time+1),self.values2,'.-g') ## 'ro-'
                  self.ax1.plot(np.arange(1,self.x_time+1),self.values1,'.-b') ## 'b^-'  'd-'
     

        t2 = time.time()
        t = t2 - self.t1
        #t3r = t2 - t3
        self.tget= t
        #print("t %.20f , t3r %.20f" % (t, t3r))
        #print("   t %.20f" % t)
        #print("tget %.20f" % self.tget)

        if (self.x_time%self.x_width==0) :
          if len(self.values1)>0:

            if "Windows" in platform.platform():
                self.values1.pop(0)
                self.values2.pop(0)
                self.x_time = self.x_time-1 
            else:   
                self.values1 = []
                self.values2 = []
                self.x_time = 0 

                self.ax1.clear()
                self.ax1.set_xlim([0,self.x_width])
                self.ax1.set_ylim([-2,55]) 
                self.ax1.set_ylabel('Pressure (cmH2O)') 
                self.ax2.clear()          
                self.ax2.set_xlim([0,self.x_width])
                self.ax2.set_ylim([-2,350])
                self.ax2.set_ylabel('Flow (L/Min)')         
        return  
  

    def prepare_ui(self, filenames = [], callback = None, parent = None, build_dimensions = None):
        self.filenames = filenames
        self.mainsizer = wx.BoxSizer(wx.HORIZONTAL)
        panel = self.menupanel = wx.Panel(self, -1)
        sizer = self.menusizer = wx.GridBagSizer()
        self.l = wx.ListBox(panel)
        sizer.Add(self.l, pos = (1, 0), span = (1, 2), flag = wx.EXPAND)


class Plater(wx.Frame):
    def __init__(self, **kwargs):
        self.destroy_on_done = True
        parent = kwargs.get("parent", None)
        size = kwargs.get("size", (800, 580))
        if "size" in kwargs:
            del kwargs["size"]
        platform_str=platform.platform()
        Title_str= "Matplot Chat - %s" % (platform_str)
        #style = wx.DEFAULT_FRAME_STYLE & (~wx.CLOSE_BOX) | wx.STAY_ON_TOP
        style = wx.DEFAULT_FRAME_STYLE & (~wx.CLOSE_BOX) | wx.FRAME_FLOAT_ON_PARENT
        wx.Frame.__init__(self, parent, title = _(Title_str), size = size, style=style)
        self.SetIcon(wx.Icon(iconfile("plater.png"), wx.BITMAP_TYPE_PNG))
        #self.prepare_ui(**kwargs)
        panel = wx.Panel(self)
        #if kwargs: # If kwargs != empty.
        #  print(kwargs)
        """
          {'callback': <bound method PronterWindow.platecb of <printrun.pronterface.PronterWindow object at 0x0000000003720C18>>, 'parent': <printrun.pronterface.PronterWindow object at 0x0000000003720C18>, 'build_dimensions': [200.0, 200.0, 100.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'circular_platform': False, 'simarrange_path': '', 
          'antialias_samples': 0, 'com_port': 'com6', 'com_baudrate': '9600'}
        """
        print ('Connect Flow Meter & Pressure sensor Device')
        self.SerialPort = kwargs.get("com_port", None) 
        self.SerialBaudrate = kwargs.get("com_baudrate", 9600) 
        print ('SerialPort: %s , Baudrate: %s' % (self.SerialPort, self.SerialBaudrate))
        if (self.SerialPort=='None'):
            print('Random Value of Flow & Pressure for DEMO.')
        self.panel = plotPanel(panel, self.SerialPort, self.SerialBaudrate)
        #self.panel = plotPanel(panel, 'Com6')

        """
        style = wx.DEFAULT_FRAME_STYLE & (~wx.CLOSE_BOX) & (~wx.MAXIMIZE_BOX)
        super(PlaterPanel, self).__init__(parent = parent, style=style)

        ## wxpython-how-to-hide-the-x-and-expand-button-on-window
        ## https://stackoverflow.com/questions/25024129/wxpython-how-to-hide-the-x-and-expand-button-on-window
        style = self.GetWindowStyle()
        self.SetWindowStyle(style & (~wx.CLOSE_BOX) & (~wx.MAXIMIZE_BOX))
        self.Refresh()
        """

    def closewindow(self, event):
        self.Destroy()

def make_plater(panel_class):
    name = panel_class.__name__.replace("Panel", "")
    return type(name, (Plater, panel_class), {})
