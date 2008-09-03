# -*- coding: utf-8 -*-

#Canto - ncurses RSS reader
#   Copyright (C) 2008 Jack Miller <jack@codezen.org>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License version 2 as 
#   published by the Free Software Foundation.

import os
import sys
import re
import feed
import utility
import codecs
import curses
import gui
import tag
import signal
import interface_draw
import traceback
import time
import cPickle
class ConfigError(Exception):
    def __str__(self):
        return repr(self.value)

class Cfg:
    """Cfg() is the class encompassing the configuration of Canto. It contains
    all of the options and functions required to drive the actual GUI. Input
    and signals are all routed to here and dispatched as necessary."""

    def __init__(self, conf, sconf, feed_dir):
        self.browser_path = "firefox \"%u\""
        self.text_browser = 0
        self.render = interface_draw.Renderer()

        self.key_list = {"q" : "quit",
                         "KEY_DOWN" : "next_item",
                         "KEY_UP" : "prev_item",
                         "j" : "next_item",
                         "k" : "prev_item",
                         "KEY_RIGHT" : "just_read",
                         "KEY_LEFT" : "just_unread",
                         "KEY_NPAGE" : "next_tag",
                         "KEY_PPAGE" : "prev_tag",
                         "l" : "next_tag",
                         "o" : "prev_tag",
                         "g" : "goto",
                         "." : "next_unread",
                         "," : "prev_unread",
                         "f" : "inline_search",
                         "n" : "next_mark",
                         "p" : "prev_mark",
                         " " : "reader",
                         "c" : "toggle_collapse_tag",
                         "C" : "set_collapse_all",
                         "V" : "unset_collapse_all",
                         "m" : "toggle_mark",
                         "r" : "tag_read",
                         "R" : "all_read",
                         "u" : "tag_unread",
                         "U" : "all_unread",
                         "C-r" : "force_update",
                         "C-l" : "refresh",
                         "h" : "help"}
        
        self.reader_key_list = {"KEY_DOWN" : "scroll_down",
                              "KEY_UP" : "scroll_up",
                              "j" : "scoll_down",
                              "k" : "scroll_up",
                              "KEY_NPAGE" : "page_down",
                              "KEY_PPAGE" : "page_up",
                              "g" : "goto",
                              "l" : "toggle_show_links",
                              "n" : "reader_next",
                              "p" : "reader_prev"}

        self.colors = [("white","black"),("blue","black"),("yellow","black"),
                ("green","black"),("pink","black"),(0,0),(0,0),(0,0)]

        self.default_rate = 5
        self.default_keep = 40
        self.default_title_key = 1

        self.path = conf
        self.sconf = sconf
        self.feed_dir = feed_dir

        self.columns = 1
        self.height = 0
        self.width = 0

        self.resize_hook = None
        self.item_filter = None

        try :
            os.stat(self.path)
        except :
            print "Unable to find config file. Generating and using ~/.canto/conf.example"
            print "You will keep getting this until you create your own ~/.canto/conf"
            print "\nRemember: it's 'h' for help.\n"

            newpath = os.getenv("HOME") + "/.canto/"
            if not os.path.exists(newpath):
                os.mkdir(newpath)

            self.path = newpath + "conf.example"
            f = codecs.open(self.path, "w", "UTF-8")
            f.write("# Auto-generated by canto because you don't have one.\n# Please copy to/create ~/.canto/conf\n\n")
            f.write("""columns = width / 70\n""")
            f.write("""addfeed("Slashdot", "http://rss.slashdot.org/slashdot/Slashdot")\n""")
            f.write("""addfeed("Reddit", "http://reddit.com/.rss")\n""")
            f.write("""addfeed("KernelTrap", "http://kerneltrap.org/node/feed")\n""")
            f.write("""addfeed("Canto", "http://codezen.org/canto/feeds/latest")\n""")
            f.write("\n")
            f.close()

        self.feeds = []
        self.parse()
        self.gen_serverconf()

    def feedwrap(self, tag, URL, **kwargs):

        if kwargs.has_key("keep"):
            keep = kwargs["keep"]
        else:
            keep = self.default_keep

        if kwargs.has_key("rate"):
            rate = kwargs["rate"]
        else:
            rate = self.default_rate

        if kwargs.has_key("title_key"):
            title_key = kwargs["title_key"]
        else:
            title_key = self.default_title_key

        return self.feeds.append(feed.Feed(self, self.feed_dir + tag.replace("/", " "), tag, URL, rate, keep, title_key))

    def set_default_rate(self, rate):
        self.default_rate = rate

    def set_default_keep(self, keep):
        self.default_keep = keep

    def set_default_title_key(self, title_key):
        self.default_title_key = title_key

    def parse(self):

        locals = {"addfeed":self.feedwrap,
            "height" : self.height,
            "width" : self.width,
            "browser" : self.browser_path,
            "text_browser" : self.text_browser,
            "default_rate" : self.set_default_rate,
            "default_keep" : self.set_default_keep,
            "default_title_key" : self.set_default_title_key,
            "render" : self.render,
            "renderer" : interface_draw.Renderer,
            "keys" : self.key_list,
            "reader_keys" : self.reader_key_list,
            "columns" : self.columns,
            "colors" : self.colors}

        data = codecs.open(self.path, "r").read()

        try :
            exec(data, {}, locals)
        except :
            print "Invalid line in config."
            traceback.print_exc()
            raise ConfigError

        # execfile cannot modify basic type
        # locals directly, so we do it by hand.

        self.browser_path = locals["browser"]
        self.text_browser = locals["text_browser"]
        self.render = locals["render"]
        if locals["columns"] > 0:
            self.columns = locals["columns"]

        if locals.has_key("resize_hook"):
            self.resize_hook = locals["resize_hook"]
        if locals.has_key("item_filter"):
            self.item_filter = locals["item_filter"]

    def gen_serverconf(self):
        l = []
        for f in self.feeds:
            l.append((f.tag, f.URL, f.rate, f.keep))

        fsock = codecs.open(self.sconf, "w", "UTF-8", "ignore")
        cPickle.dump(l, fsock)
        fsock.close()
