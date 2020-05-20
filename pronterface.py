#!/usr/bin/env python3

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

import os
import sys
import getopt

from pathlib import Path  ## added by Roger 2020-04-22

try:
    import wx  # NOQA
    if wx.VERSION < (4,):
        raise ImportError()
except:
    print("wxPython >= 4 is not installed. This program requires wxPython >=4 to run.")
    raise

from printrun.pronterface import PronterApp

if __name__ == '__main__':

    from printrun.printcore import __version__ as printcore_version

    os.environ['GDK_BACKEND'] = 'x11'

    usage = "Usage:\n"+\
            "  pronterface [OPTIONS] [FILE]\n\n"+\
            "Options:\n"+\
            "  -h, --help\t\t\tPrint this help message and exit\n"+\
            "  -V, --version\t\t\tPrint program's version number and exit\n"+\
            "  -v, --verbose\t\t\tIncrease verbosity\n"+\
            "  -a, --autoconnect\t\tAutomatically try to connect to printer on startup\n"+\
            "  -c, --conf, --config=CONFIG_FILE\tLoad this file on startup instead of .pronsolerc; you may chain config files, if so settings auto-save will use the last specified file\n"+\
            "  -e, --execute=COMMAND\t\tExecutes command after configuration/.pronsolerc is loaded; macros/settings from these commands are not autosaved"
    

    path = Path(__file__).parent.absolute()  ## added by Roger 2020-04-22
    os.chdir( path )
    
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hVvac:e:", ["help", "version", "verbose", "autoconnect", "conf=", "config=", "execute="])
    except getopt.GetoptError as err:
        print(str(err))
        print(usage)
        sys.exit(2)
    for o, a in opts:
        if o in ('-V','--version'):
            print("printrun "+printcore_version)
            sys.exit(0)
        elif o in ('-h', '--help'):
            print(usage)
            sys.exit(0)

    app = PronterApp(False)
    try:
        app.MainLoop()
    except KeyboardInterrupt:
        pass
    del app
