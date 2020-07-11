# This file is part of the Printrun suite.
#
# Printrun is free software: you can redistribute it and/or modify
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

import wx
import re

import time
import logging
import threading
import sys

"""
print ('numpy as np')
import numpy as np
print ('matplotlib.figure')
import matplotlib.figure as mfigure
print ('matplotlib.animation')
import matplotlib.animation as manim
print ('matplotlib.pyplot as plt')
import matplotlib.pyplot as plt #import matplotlib library

from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg
"""

class MacroEditor(wx.Dialog):
    """Really simple editor to edit macro definitions"""

    def __init__(self, macro_name, definition, callback, gcode = False):
        self.indent_chars = "  "
        title = "  macro %s"
        if gcode:
            title = "  %s"
        self.gcode = gcode
        wx.Dialog.__init__(self, None, title = title % macro_name,
                           style = wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.callback = callback
        self.panel = wx.Panel(self, -1)
        titlesizer = wx.BoxSizer(wx.HORIZONTAL)
        self.titletext = wx.StaticText(self.panel, -1, "              _")  # title%macro_name)
        titlesizer.Add(self.titletext, 1)
        self.findb = wx.Button(self.panel, -1, _("Find"), style = wx.BU_EXACTFIT)  # New button for "Find" (Jezmy)
        self.findb.Bind(wx.EVT_BUTTON, self.find)
        self.okb = wx.Button(self.panel, -1, _("Save"), style = wx.BU_EXACTFIT)
        self.okb.Bind(wx.EVT_BUTTON, self.save)
        self.Bind(wx.EVT_CLOSE, self.close)
        titlesizer.Add(self.findb)
        titlesizer.Add(self.okb)
        self.cancelb = wx.Button(self.panel, -1, _("Cancel"), style = wx.BU_EXACTFIT)
        self.cancelb.Bind(wx.EVT_BUTTON, self.close)
        titlesizer.Add(self.cancelb)
        topsizer = wx.BoxSizer(wx.VERTICAL)
        topsizer.Add(titlesizer, 0, wx.EXPAND)
        self.e = wx.TextCtrl(self.panel, style = wx.HSCROLL | wx.TE_MULTILINE | wx.TE_RICH2, size = (400, 400))
        if not self.gcode:
            self.e.SetValue(self.unindent(definition))
        else:
            self.e.SetValue("\n".join(definition))
        topsizer.Add(self.e, 1, wx.ALL | wx.EXPAND)
        self.panel.SetSizer(topsizer)
        topsizer.Layout()
        topsizer.Fit(self)
        self.Show()
        self.e.SetFocus()

    def find(self, ev):
        # Ask user what to look for, find it and point at it ...  (Jezmy)
        S = self.e.GetStringSelection()
        if not S:
            S = "Z"
        FindValue = wx.GetTextFromUser('Please enter a search string:', caption = "Search", default_value = S, parent = None)
        somecode = self.e.GetValue()
        position = somecode.find(FindValue, self.e.GetInsertionPoint())
        if position == -1:
            self.titletext.SetLabel(_("Not Found!"))
        else:
            self.titletext.SetLabel(str(position))

            # ananswer = wx.MessageBox(str(numLines)+" Lines detected in file\n"+str(position), "OK")
            self.e.SetFocus()
            self.e.SetInsertionPoint(position)
            self.e.SetSelection(position, position + len(FindValue))
            self.e.ShowPosition(position)

    def ShowMessage(self, ev, message):
        dlg = wx.MessageDialog(self, message,
                               "Info!", wx.OK | wx.ICON_INFORMATION)
        dlg.ShowModal()
        dlg.Destroy()

    def save(self, ev):
        self.Destroy()
        if not self.gcode:
            self.callback(self.reindent(self.e.GetValue()))
        else:
            self.callback(self.e.GetValue().split("\n"))

    def close(self, ev):
        self.Destroy()

    def unindent(self, text):
        self.indent_chars = text[:len(text) - len(text.lstrip())]
        if len(self.indent_chars) == 0:
            self.indent_chars = "  "
        unindented = ""
        lines = re.split(r"(?:\r\n?|\n)", text)
        if len(lines) <= 1:
            return text
        for line in lines:
            if line.startswith(self.indent_chars):
                unindented += line[len(self.indent_chars):] + "\n"
            else:
                unindented += line + "\n"
        return unindented

    def reindent(self, text):
        lines = re.split(r"(?:\r\n?|\n)", text)
        if len(lines) <= 1:
            return text
        reindented = ""
        for line in lines:
            if line.strip() != "":
                reindented += self.indent_chars + line + "\n"
        return reindented

SETTINGS_GROUPS = {"External": _("Breaths basic settings(呼吸循環基本設定)"),
                   "External1": _("Breaths Advance settings(吸氣進階設定)"),
                   "External2": _("Breaths Advance settings(呼氣進階設定)"),
                   "Printer": _("BVM_Run<Ventilator> settings"),
                   "UI": _("User interface"),
                   "Viewer": _("Viewer"),
                   "Colors": _("Colors"),
                   }

class PronterOptionsDialog(wx.Dialog):
    """Options editor"""
    def __init__(self, pronterface):
        wx.Dialog.__init__(self, parent = None, title = _("Edit settings"),
                           size = (500, 400), style = wx.DEFAULT_DIALOG_STYLE)
        panel = wx.Panel(self)
        header = wx.StaticBox(panel, label = _("Settings"))
        sbox = wx.StaticBoxSizer(header, wx.VERTICAL)
        notebook = wx.Notebook(panel)
        all_settings = pronterface.settings._all_settings()
        group_list = []
        groups = {}
        for group in ["External", "External1", "External2", "Printer", "UI", "Viewer", "Colors"]:
            group_list.append(group)
            groups[group] = []
        for setting in all_settings:
            if setting.group not in group_list:
                group_list.append(setting.group)
                groups[setting.group] = []
            groups[setting.group].append(setting)
        for group in group_list:
            grouppanel = wx.Panel(notebook, -1)
            notebook.AddPage(grouppanel, SETTINGS_GROUPS[group])
            settings = groups[group]
            grid = wx.GridBagSizer(hgap = 8, vgap = 2)
            current_row = 0
            for setting in settings:
                if setting.name.startswith("separator_"):
                    sep = wx.StaticLine(grouppanel, size = (-1, 5), style = wx.LI_HORIZONTAL)
                    grid.Add(sep, pos = (current_row, 0), span = (1, 2),
                             border = 3, flag = wx.ALIGN_CENTER | wx.ALL | wx.EXPAND)
                    current_row += 1
                label, widget = setting.get_label(grouppanel), setting.get_widget(grouppanel)
                if setting.name.startswith("separator_"):
                    font = label.GetFont()
                    font.SetWeight(wx.BOLD)
                    label.SetFont(font)
                grid.Add(label, pos = (current_row, 0),
                         flag = wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
                grid.Add(widget, pos = (current_row, 1),
                         flag = wx.ALIGN_CENTER_VERTICAL | wx.EXPAND)
                if hasattr(label, "set_default"):
                    label.Bind(wx.EVT_MOUSE_EVENTS, label.set_default)
                    if hasattr(widget, "Bind"):
                        widget.Bind(wx.EVT_MOUSE_EVENTS, label.set_default)
                current_row += 1
            grid.AddGrowableCol(1)
            grouppanel.SetSizer(grid)
        sbox.Add(notebook, 1, wx.EXPAND)
        panel.SetSizer(sbox)
        topsizer = wx.BoxSizer(wx.VERTICAL)
        topsizer.Add(panel, 1, wx.ALL | wx.EXPAND)
        topsizer.Add(self.CreateButtonSizer(wx.OK | wx.CANCEL), 0, wx.ALIGN_RIGHT)
        self.SetSizerAndFit(topsizer)
        self.SetMinSize(self.GetSize())

def PronterOptions(pronterface):
    dialog = PronterOptionsDialog(pronterface)
    if dialog.ShowModal() == wx.ID_OK:
        for setting in pronterface.settings._all_settings():
            old_value = setting.value
            setting.update()
            if setting.value != old_value:
                pronterface.set(setting.name, setting.value)
    dialog.Destroy()

"""
Add by Roger 2020/06/30


class plotPanel(wx.Panel):
    def __init__(self, parent, strPort, id=-1, dpi=None, **kwargs):
    #    super().__init__(parent, id=id, **kwargs)    
    #def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        self.fig = mfigure.Figure()
        #self.ax1 = self.fig.add_subplot(211)
        #self.ax2 = self.fig.add_subplot(311)
        self.ax1 = self.fig.add_axes([0.1, 0.5, 0.8, 0.4],
                   xticklabels=[], ylim=(-10, 50))
        self.ax2 = self.fig.add_axes([0.1, 0.1, 0.8, 0.4],
                   ylim=(-10, 70))       
        self.canv = FigureCanvasWxAgg(self, wx.ID_ANY, self.fig)

        #self.arduinoData = serial.Serial(strPort, 9600) #Creating our serial object named arduinoData
        
        self.values1 = []
        self.values2 = []
        self.arduinoString =''
        self.animator = manim.FuncAnimation(self.fig,self.anim, interval=100)

        # Now put all into a sizer
        sizer = wx.BoxSizer(wx.VERTICAL)
        # This way of adding to sizer allows resizing
        sizer.Add(self.canv, 1, wx.LEFT | wx.TOP | wx.GROW)
        ## Best to allow the toolbar to resize!
        #sizer.Add(self.toolbar, 0, wx.GROW)
        self.SetSizer(sizer)
        self.Fit()

    def anim(self,i):
        if i%50 == 0:
            self.values1 = []
            self.values2 = []
        else:
            ### read serial line
            ###data = float(self.ser.readline().decode('utf-8'))
            #while (self.arduinoData.inWaiting()==0): #Wait here until there is data
            #    pass #do nothing
            #self.arduinoString = self.arduinoData.readline() #read the line of text from the serial port
            ##print(arduinoString)
            ##arduinoString = arduinoString.encode()
            #dataArray = arduinoString.decode().strip().split(',')   #Split it into an array called dataArray
                                                   # str→bytes：encode()方法。str通过encode()方法可以转换为bytes。
                                                   #bytes→str：decode()方法。如果我们从网络或磁盘上读取了字节流，那么读到的数据就是bytes。要把bytes变为str，就需要用decode()方法。
            ###T(°C) = (T(°F) - 32) / 1.8
            #temp = (float( dataArray[0] ) - 32 ) /1.8  #Convert first element to floating number and put in temp C
            #P =    float( dataArray[1] ) * 1.0197442889221   #Convert second element to floating number and put in P  cmH2O
                                                       #Hectopascals to centimeters of water conversion formula
                                                       #Pressure(cmH2O) = Pressure (hPa) × 1.0197442889221
            #print ("TempC_cmH2O : " % (temp, P))

            temp = np.random.rand() * 50
            P =    float( np.random.rand() ) * 1.0197442889221 * 40
            self.values1.append(P)
            self.values2.append(temp)

        self.ax1.clear()
        self.ax1.set_xlim([0,50])
        self.ax1.set_ylim([-10,50]) 
        self.ax1.set_xlabel('X time') 
        self.ax1.set_ylabel('Y Pressure (cmH2O)')   
        self.ax2.clear()
        self.ax2.set_xlim([0,50])
        self.ax2.set_ylim([-10,70]) 
        self.ax2.set_xlabel('X time') 
        self.ax2.set_ylabel('Y Flow (Lpm)')                       
        self.ax1.plot(np.arange(1,i%50+1),self.values1,'b^-') ## 'd-'
        self.ax2.plot(np.arange(1,i%50+1),self.values2,'ro-')       
        return 

class PronterMatplotDialog(wx.Dialog):
#class PronterMatplotDialog(wx.Window):
    #Matplot Chat
    def __init__(self, pronterface):
        #wx.Window.__init__(self)
        wx.Dialog.__init__(self, parent = None, title = _("Matplot Chat"),
                           size = (800, 600), style = wx.DEFAULT_DIALOG_STYLE)
        panel = wx.Panel(self)
        #header = wx.StaticBox(panel, label = _("Matplot Chat"))
        #sbox = wx.StaticBoxSizer(header, wx.VERTICAL)
        #notebook = wx.Notebook(panel)
        all_settings = pronterface.settings._all_settings()
        self.panel = plotPanel(panel, 'COM3')
        #self.Show()

    def stop(self):
        self.animator.event_source.stop()   


def PronterMatplot(pronterface):
    dialog = PronterMatplotDialog(pronterface)
    if dialog.ShowModal() == wx.ID_OK:
        for setting in pronterface.settings._all_settings():
            old_value = setting.value
            setting.update()
            if setting.value != old_value:
                pronterface.set(setting.name, setting.value)
    dialog.Destroy()


End Add by Roger 2020/06/30
"""        

class ButtonEdit(wx.Dialog):
    """Custom button edit dialog"""
    def __init__(self, pronterface):
        wx.Dialog.__init__(self, None, title = _("Custom button"),
                           style = wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.pronterface = pronterface
        topsizer = wx.BoxSizer(wx.VERTICAL)
        grid = wx.FlexGridSizer(rows = 0, cols = 2, hgap = 4, vgap = 2)
        grid.AddGrowableCol(1, 1)
        grid.Add(wx.StaticText(self, -1, _("Button title")), 0, wx.BOTTOM | wx.RIGHT)
        self.name = wx.TextCtrl(self, -1, "")
        grid.Add(self.name, 1, wx.EXPAND)
        grid.Add(wx.StaticText(self, -1, _("Command")), 0, wx.BOTTOM | wx.RIGHT)
        self.command = wx.TextCtrl(self, -1, "")
        xbox = wx.BoxSizer(wx.HORIZONTAL)
        xbox.Add(self.command, 1, wx.EXPAND)
        self.command.Bind(wx.EVT_TEXT, self.macrob_enabler)
        self.macrob = wx.Button(self, -1, "..", style = wx.BU_EXACTFIT)
        self.macrob.Bind(wx.EVT_BUTTON, self.macrob_handler)
        xbox.Add(self.macrob, 0)
        grid.Add(xbox, 1, wx.EXPAND)
        grid.Add(wx.StaticText(self, -1, _("Color")), 0, wx.BOTTOM | wx.RIGHT)
        self.color = wx.TextCtrl(self, -1, "")
        grid.Add(self.color, 1, wx.EXPAND)
        topsizer.Add(grid, 0, wx.EXPAND)
        topsizer.Add((0, 0), 1)
        topsizer.Add(self.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL), 0, wx.ALIGN_CENTER)
        self.SetSizer(topsizer)

    def macrob_enabler(self, e):
        macro = self.command.GetValue()
        valid = False
        try:
            if macro == "":
                valid = True
            elif macro in self.pronterface.macros:
                valid = True
            elif hasattr(self.pronterface.__class__, "do_" + macro):
                valid = False
            elif len([c for c in macro if not c.isalnum() and c != "_"]):
                valid = False
            else:
                valid = True
        except:
            if macro == "":
                valid = True
            elif macro in self.pronterface.macros:
                valid = True
            elif len([c for c in macro if not c.isalnum() and c != "_"]):
                valid = False
            else:
                valid = True
        self.macrob.Enable(valid)

    def macrob_handler(self, e):
        macro = self.command.GetValue()
        macro = self.pronterface.edit_macro(macro)
        self.command.SetValue(macro)
        if self.name.GetValue() == "":
            self.name.SetValue(macro)

class TempGauge(wx.Panel):

    def __init__(self, parent, size = (200, 22), title = "",
                 maxval = 240, gaugeColour = None, bgcolor = "#FFFFFF"):
        wx.Panel.__init__(self, parent, -1, size = size)
        self.Bind(wx.EVT_PAINT, self.paint)
        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)
        self.bgcolor = wx.Colour()
        self.bgcolor.Set(bgcolor)
        self.width, self.height = size
        self.title = title
        self.max = maxval
        self.gaugeColour = gaugeColour
        self.value = 0
        self.setpoint = 0
        self.recalc()

    def recalc(self):
        mmax = max(int(self.setpoint * 1.05), self.max)
        self.scale = float(self.width - 2) / float(mmax)
        self.ypt = max(16, int(self.scale * max(self.setpoint, self.max / 6)))

    def SetValue(self, value):
        self.value = value
        wx.CallAfter(self.Refresh)

    def SetTarget(self, value):
        self.setpoint = value
        wx.CallAfter(self.Refresh)

    def interpolatedColour(self, val, vmin, vmid, vmax, cmin, cmid, cmax):
        if val < vmin: return cmin
        if val > vmax: return cmax
        if val <= vmid:
            lo, hi, val, valhi = cmin, cmid, val - vmin, vmid - vmin
        else:
            lo, hi, val, valhi = cmid, cmax, val - vmid, vmax - vmid
        vv = float(val) / valhi
        rgb = lo.Red() + (hi.Red() - lo.Red()) * vv, lo.Green() + (hi.Green() - lo.Green()) * vv, lo.Blue() + (hi.Blue() - lo.Blue()) * vv
        rgb = (int(x * 0.8) for x in rgb)
        return wx.Colour(*rgb)

    def paint(self, ev):
        self.width, self.height = self.GetClientSize()
        self.recalc()
        x0, y0, x1, y1, xE, yE = 1, 1, self.ypt + 1, 1, self.width + 1 - 2, 20
        dc = wx.PaintDC(self)
        dc.SetBackground(wx.Brush(self.bgcolor))
        dc.Clear()
        cold, medium, hot = wx.Colour(0, 167, 223), wx.Colour(239, 233, 119), wx.Colour(210, 50, 0)
        # gauge1, gauge2 = wx.Colour(255, 255, 210), (self.gaugeColour or wx.Colour(234, 82, 0))
        gauge1 = wx.Colour(255, 255, 210)
        shadow1, shadow2 = wx.Colour(110, 110, 110), self.bgcolor
        gc = wx.GraphicsContext.Create(dc)
        # draw shadow first
        # corners
        gc.SetBrush(gc.CreateRadialGradientBrush(xE - 7, 9, xE - 7, 9, 8, shadow1, shadow2))
        gc.DrawRectangle(xE - 7, 1, 8, 8)
        gc.SetBrush(gc.CreateRadialGradientBrush(xE - 7, 17, xE - 7, 17, 8, shadow1, shadow2))
        gc.DrawRectangle(xE - 7, 17, 8, 8)
        gc.SetBrush(gc.CreateRadialGradientBrush(x0 + 6, 17, x0 + 6, 17, 8, shadow1, shadow2))
        gc.DrawRectangle(0, 17, x0 + 6, 8)
        # edges
        gc.SetBrush(gc.CreateLinearGradientBrush(xE - 6, 0, xE + 1, 0, shadow1, shadow2))
        gc.DrawRectangle(xE - 7, 9, 8, 8)
        gc.SetBrush(gc.CreateLinearGradientBrush(x0, yE - 2, x0, yE + 5, shadow1, shadow2))
        gc.DrawRectangle(x0 + 6, yE - 2, xE - 12, 7)
        # draw gauge background
        gc.SetBrush(gc.CreateLinearGradientBrush(x0, y0, x1 + 1, y1, cold, medium))
        gc.DrawRoundedRectangle(x0, y0, x1 + 4, yE, 6)
        gc.SetBrush(gc.CreateLinearGradientBrush(x1 - 2, y1, xE, y1, medium, hot))
        gc.DrawRoundedRectangle(x1 - 2, y1, xE - x1, yE, 6)
        # draw gauge
        width = 12
        w1 = y0 + 9 - width / 2
        w2 = w1 + width
        value = x0 + max(10, min(self.width + 1 - 2, int(self.value * self.scale)))
        # gc.SetBrush(gc.CreateLinearGradientBrush(x0, y0 + 3, x0, y0 + 15, gauge1, gauge2))
        # gc.SetBrush(gc.CreateLinearGradientBrush(0, 3, 0, 15, wx.Colour(255, 255, 255), wx.Colour(255, 90, 32)))
        gc.SetBrush(gc.CreateLinearGradientBrush(x0, y0 + 3, x0, y0 + 15, gauge1, self.interpolatedColour(value, x0, x1, xE, cold, medium, hot)))
        val_path = gc.CreatePath()
        val_path.MoveToPoint(x0, w1)
        val_path.AddLineToPoint(value, w1)
        val_path.AddLineToPoint(value + 2, w1 + width / 4)
        val_path.AddLineToPoint(value + 2, w2 - width / 4)
        val_path.AddLineToPoint(value, w2)
        # val_path.AddLineToPoint(value-4, 10)
        val_path.AddLineToPoint(x0, w2)
        gc.DrawPath(val_path)
        # draw setpoint markers
        setpoint = x0 + max(10, int(self.setpoint * self.scale))
        gc.SetBrush(gc.CreateBrush(wx.Brush(wx.Colour(0, 0, 0))))
        setp_path = gc.CreatePath()
        setp_path.MoveToPoint(setpoint - 4, y0)
        setp_path.AddLineToPoint(setpoint + 4, y0)
        setp_path.AddLineToPoint(setpoint, y0 + 5)
        setp_path.MoveToPoint(setpoint - 4, yE)
        setp_path.AddLineToPoint(setpoint + 4, yE)
        setp_path.AddLineToPoint(setpoint, yE - 5)
        gc.DrawPath(setp_path)
        # draw readout
        text = "T\u00B0 %u/%u" % (self.value, self.setpoint)
        # gc.SetFont(gc.CreateFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD), wx.WHITE))
        # gc.DrawText(text, 29,-2)
        gc.SetFont(gc.CreateFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD), wx.WHITE))
        gc.DrawText(self.title, x0 + 19, y0 + 4)
        gc.DrawText(text, x0 + 119, y0 + 4)
        gc.SetFont(gc.CreateFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)))
        gc.DrawText(self.title, x0 + 18, y0 + 3)
        gc.DrawText(text, x0 + 118, y0 + 3)

class SpecialButton:

    label = None
    command = None
    background = None
    tooltip = None
    custom = None

    def __init__(self, label, command, background = None,
                 tooltip = None, custom = False):
        self.label = label
        self.command = command
        self.background = background
        self.tooltip = tooltip
        self.custom = custom
