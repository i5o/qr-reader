#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2014  Ignacio Rodríguez <ignacio@sugarlabs.org>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  021101301, USA.

import commands
import gi
import os
import random
import sys

gi.require_version('Gst', "1.0")

from gettext import gettext as _

from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import GObject
from gi.repository import Gst
from gi.repository import GstVideo
from gi.repository import Gtk

from sugar3.activity import activity
from sugar3.activity.widgets import ActivityButton
from sugar3.activity.widgets import StopButton
from sugar3.graphics import style
from sugar3.graphics.alert import NotifyAlert
from sugar3.graphics.toggletoolbutton import ToggleToolButton as ToogleButton
from sugar3.graphics.toolbarbox import ToolbarBox
from sugar3.graphics.toolbutton import ToolButton
from sugar3.graphics.toolcombobox import ToolComboBox


DATA = os.path.join(activity.get_bundle_path(), "tools")
data = commands.getoutput("uname -m")
if 'arm' in data:
    DATA = os.path.join(DATA, "arm")
elif '64' in data:
    DATA = os.path.join(DATA, "64")
else:
    DATA = Os.path.join(DATA, "32")

LIB = os.path.join(DATA, "lib")
sys.path.append(DATA)
from qrtools import QR

GObject.threads_init()
Gst.init([])


class QrReader(activity.Activity):
    def __init__(self, handle):
        activity.Activity.__init__(self, handle)

        self.realize()
        self.qr_window = Gtk.DrawingArea()
        self.qr_window.set_double_buffered(False)
        self.qr_window.set_app_paintable(True)

        self.image = Gtk.Image()

        self.box = Gtk.VBox()
        self.box.pack_start(self.qr_window, True, True, 0)
        self.box.pack_end(self.image, True, True, 0)

        self.set_canvas(self.box)

        self.build_toolbar()
        self.show_all()
        self.image.hide()
        GObject.idle_add(self.setup_init)

    def build_toolbar(self):
        toolbox = ToolbarBox()
        toolbar = toolbox.toolbar

        activity_button = ActivityButton(self)
        toolbar.insert(activity_button, -1)
        toolbar.insert(Gtk.SeparatorToolItem(), -1)

        self.stop_play = ToogleButton('media-playback-start')
        self.stop_play.set_tooltip(_("Turn on/off the camera"))
        self.stop_play.props.active = True

        self.copylink = copy_to = ToolButton('text-uri-list')
        self.copylink.set_tooltip(_("Copy link to clipboard"))
        self.copylink.set_sensitive(False)

        toolbar.insert(self.stop_play, -1)
        toolbar.insert(self.copylink, -1)

        separator = Gtk.SeparatorToolItem()
        separator.props.draw = False
        separator.set_expand(True)
        toolbar.insert(separator, -1)

        stopbtn = StopButton(self)
        toolbar.insert(stopbtn, -1)
        toolbar.show_all()

        self.set_toolbar_box(toolbox)

    def setup_init(self):
        xid = self.qr_window.get_property('window').get_xid()
        visor = QrVisor(xid, self.stop_play, self, self.qr_window, self.copylink, self.image)
        visor.play()


class QrVisor:
    def __init__(self, xid, stop_play, activity, drawing, copylink, image):
        self.stop_play = stop_play
        self.stop_play.connect("toggled", self.stopplay)
        self.activity = activity
        self.window_id = xid
        self.draw_area = drawing
        self.copy_link = copylink
        self.copy_link.connect("clicked", self.copy_to_clipboard)
        self.image = image
        self.qr_link = None

        self.camerabin = Gst.ElementFactory.make("camerabin", "cam")
        self.sink = Gst.ElementFactory.make("xvimagesink", "sink")
        src = Gst.ElementFactory.make("v4l2src","src")
        self.camerabin.set_property("viewfinder-sink", self.sink)

        wrapper = Gst.ElementFactory.make("wrappercamerabinsrc", "wrapper")
        wrapper.set_property("video-source", src)
        self.camerabin.set_property("camera-source", wrapper)

        bus = self.camerabin.get_bus()
        bus.add_signal_watch()
        bus.connect('message', self.sync_message)

    def play(self):
        self.camerabin.set_state(Gst.State.PLAYING)

    def pause(self):
        self.camerabin.set_state(Gst.State.PAUSED)

    def stop(self):
        self.camerabin.set_state(Gst.State.NULL)

    def sync_message(self, bus, message):
        try:
            if message.get_structure().get_name() == 'prepare-window-handle':
                message.src.set_window_handle(self.window_id)
                return
        except:
            pass

    def stopplay(self, widget):
        active = widget.props.active
        if active:
            if hasattr(widget, "set_named_icon"):
                widget.set_named_icon("media-playback-start")
            self.image.hide()
            def internalcallback():
                self.draw_area.show()
                self.activity.show()
            GObject.timeout_add(100, internalcallback)
        else:
            if hasattr(widget, "set_named_icon"):
                widget.set_named_icon("media-playback-pause")
            widget.set_icon_name("media-playback-pause")
            image = self.get_qr()
            def internal_callback():
                while 1:
                    if not os.path.exists(image):
                        return True
                    else:
                        self.look_qr(image, widget)
                        return False

            widget.set_sensitive(False)
            cursor = Gdk.Cursor.new(Gdk.CursorType.WATCH)
            self.activity.get_window().set_cursor(cursor)
            GObject.idle_add(internal_callback)

        widget.show()

    def get_qr(self):
        photo_filename = os.path.join(activity.get_activity_root(),
                    "instance", "qr.png")
        if os.path.exists(photo_filename):
            os.remove(photo_filename)

        self.camerabin.set_property("location", photo_filename)
        self.camerabin.emit("start-capture")
        return photo_filename

    def look_qr(self, image_path, button):
        self.camerabin.set_state(Gst.State.NULL)
        h = Gdk.Screen.height() - style.GRID_CELL_SIZE
        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(image_path, -1, h)
        self.image.set_from_pixbuf(pixbuf)
        self.image.set_halign(Gtk.Align.CENTER)
        self.check_image_qr(image_path)
        self.draw_area.hide()
        self.image.show()
        self.activity.get_window().set_cursor(None)

    def check_image_qr(self, path):
        myCode = QR(filename=path)
        if myCode.decode():
            self.qr_link = myCode.data_to_string()
            self.copy_link.set_sensitive(True)
            alert = NotifyAlert(10)
            alert.props.title = _("Code found")
            alert.props.msg = _("Click on toolbar button for copy link to clipboard.")
            alert.connect("response", lambda x, y: self.activity.remove_alert(x))
            self.activity.add_alert(alert)
        else:
            self.qr_link = None
            self.copy_link.set_sensitive(False)
            alert = NotifyAlert(10)
            alert.props.title = _("Code not found")
            alert.props.msg = _("Try again, please focus the Qr Code in the camera.")
            alert.connect("response", lambda x, y: self.activity.remove_alert(x))
            self.activity.add_alert(alert)

        self.stop_play.set_sensitive(False)

    def copy_to_clipboard(self, widget):
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        clipboard.set_text(self.qr_link, -1)