#!/usr/bin/python3
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# Copyright (C) 2022 Luke Horwell <code@horwell.me>
#
"""
This is the GUI to convienent apply or revert the patch to improve
the user interface for The Sims 2 on 4K resolutions.
"""
import sys
import wx

# import dbpf

__version__ = "0.1.0"


class MainWindow(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self, None, title="The Sims 2 4K UI Mod", size=(350,200))
        self.Bind(wx.EVT_CLOSE, self.on_close)

        self.statusbar = self.CreateStatusBar()

        panel = wx.Panel(self)
        box = wx.BoxSizer(wx.VERTICAL)

        title = wx.StaticText(panel, -1, "Hello World!")
        title.SetFont(wx.Font(14, wx.SWISS, wx.NORMAL, wx.BOLD))
        title.SetSize(title.GetBestSize())
        box.Add(title, 0, wx.ALL, 10)

        close_btn = wx.Button(panel, wx.ID_CLOSE, "Close")
        close_btn.Bind(wx.EVT_BUTTON, self.on_close)
        box.Add(close_btn, 0, wx.ALL, 10)

        panel.SetSizer(box)
        panel.Layout()

    def on_close(self, event):
        dialog = wx.MessageDialog(self, "Do you really want to close this application?", "Confirm Exit", wx.OK|wx.CANCEL|wx.ICON_QUESTION)
        result = dialog.ShowModal()
        dialog.Destroy()
        if result == wx.ID_OK:
            self.Destroy()


app = wx.App(redirect=True)
top = MainWindow()
top.Show()
app.MainLoop()
