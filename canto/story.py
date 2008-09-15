# -*- coding: utf-8 -*-

#Canto - ncurses RSS reader
#   Copyright (C) 2008 Jack Miller <jack@codezen.org>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License version 2 as 
#   published by the Free Software Foundation.

import sys
import utility
import struct
import re
import codecs

class Story():
    def __init__(self, ufp, feed, renderer):
        self.feed_idx = 0
        self.idx = 0
        self.last = 0

        self.row = 0
        self.lines = 0
        
        self.prev_feed = None
        self.next_feed = None

        self.next = None
        self.prev = None

        self.ufp = ufp
        self.feed = feed
        self.sel = 0
        self.renderer = renderer

    def __eq__(self, other):
        if self.ufp["id"] != other.ufp["id"]:
            return 0
        return 1

    def __getitem__(self, key):
        if self.ufp.has_key(key):
            return self.ufp[key]
        else:
            return ""

    def has_key(self, key):
        return self.ufp.has_key(key)

    def __tagwrap(self, tag, i):
        if i == 0:
            return tag in self.ufp["canto_state"]
        elif i == 1 and not tag in self.ufp["canto_state"]:
            self.ufp["canto_state"].append(tag)
        elif i == -1 and tag in self.ufp["canto_state"]:
            self.ufp["canto_state"].remove(tag)
        self.feed.has_changed()

    def wasread(self):
        return self.__tagwrap("read", 0)

    def read(self):
        self.__tagwrap("read", 1)

    def unread(self):
        self.__tagwrap("read", -1)

    def marked(self):
        return self.__tagwrap("marked", 0)

    def mark(self):
        self.__tagwrap("marked", 1)

    def unmark(self):
        self.__tagwrap("marked", -1)

    def isnew(self):
        return self.__tagwrap("new", 0)

    def new(self):
        self.__tagwrap("new", 1)

    def old(self):
        self.__tagwrap("new", -1)

    def selected(self):
        return self.sel

    def select(self):
        self.sel = 1

    def unselect(self):
        self.sel = 0

    def print_item(self, tag, row, i):
        return self.renderer.story(tag, self, row, \
                i.cfg.height, i.cfg.width / i.cfg.columns, i.window_list)
