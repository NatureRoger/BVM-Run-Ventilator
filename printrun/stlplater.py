#!/usr/bin/env python3

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

import os

# Set up Internationalization using gettext
# searching for installed locales on /usr/share; uses relative folder if not found (windows)
from .utils import install_locale
install_locale('pronterface')

import wx
import time
import logging
import threading
import math
import sys
import re
#import traceback
#import subprocess
#from copy import copy

from printrun import stltool
from printrun.objectplater import make_plater, PlaterPanel1



class showstl(wx.Window):
    def __init__(self, parent, size, pos):
        wx.Window.__init__(self, parent, size = size, pos = pos)
        self.i = 0
        self.parent = parent
        self.previ = 0
        #self.Bind(wx.EVT_MOUSEWHEEL, self.rot)
        #self.Bind(wx.EVT_MOUSE_EVENTS, self.move)
        #self.Bind(wx.EVT_PAINT, self.repaint)
        #self.Bind(wx.EVT_KEY_DOWN, self.keypress)
        self.triggered = 0
        self.initpos = None
        self.prevsel = -1

    def prepare_model(self, m, scale):
        m.bitmap = wx.Bitmap(800, 800, 32)
        dc = wx.MemoryDC()
        dc.SelectObject(m.bitmap)
        dc.SetBackground(wx.Brush((0, 0, 0, 0)))
        dc.SetBrush(wx.Brush((0, 0, 0, 255)))
        dc.SetBrush(wx.Brush(wx.Colour(128, 255, 128)))
        dc.SetPen(wx.Pen(wx.Colour(128, 128, 128)))
        for i in m.facets:
            dc.DrawPolygon([wx.Point(400 + scale * p[0], (400 - scale * p[1])) for p in i[1]])
        dc.SelectObject(wx.NullBitmap)
        m.bitmap.SetMask(wx.Mask(m.bitmap, wx.Colour(0, 0, 0, 255)))


class StlPlaterPanel(PlaterPanel1):

    load_wildcard = _("STL files (*.stl;*.STL)|*.stl;*.STL|OpenSCAD files (*.scad)|*.scad")
    save_wildcard = _("STL files (*.stl;*.STL)|*.stl;*.STL")

    def prepare_ui(self, filenames = [], callback = None,
                   parent = None, build_dimensions = None, circular_platform = False,
                   simarrange_path = None, antialias_samples = 0):
        super(StlPlaterPanel, self).prepare_ui(filenames, callback, parent, build_dimensions)
        self.cutting = False
        self.cutting_axis = None
        self.cutting_dist = None

        viewer = showstl(self, (580, 580), (0, 0))

        self.simarrange_path = simarrange_path
        #self.set_viewer(viewer)


StlPlater = make_plater(StlPlaterPanel)
