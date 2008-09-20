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
import extra
import chardet

class ConfigError(Exception):
    def __str__(self):
        return repr(self.value)

class Cfg:
    def __init__(self, conf, log_file, feed_dir):
        self.browser = "firefox \"%u\""
        self.text_browser = 0
        self.render = interface_draw.Renderer()
        self.log_file = log_file

        self.key_list = {"q" : "quit",
                         "KEY_DOWN" : "next_item",
                         "KEY_UP" : "prev_item",
                         "j" : "next_item",
                         "k" : "prev_item",
                         "KEY_RIGHT" : "just_read",
                         "KEY_LEFT" : "just_unread",
                         "KEY_NPAGE" : "next_tag",
                         "KEY_PPAGE" : "prev_tag",
                         "[" : "prev_filter",
                         "]" : "next_filter",
                         "{" : "prev_feed_filter",
                         "}" : "next_feed_filter",
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
                         "M" : "all_unmarked",
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
                              "n" : ["destroy","next_item","reader"],
                              "p" : ["destroy","prev_item","reader"],
                              "h" : ["destroy","help"],
                              "q" : ["destroy","quit"],
                              " " : "quit"}

        self.colors = [("white","black"),("blue","black"),("yellow","black"),
                ("green","black"),("pink","black"),(0,0),(0,0),(0,0)]

        self.default_rate = 5
        self.default_keep = 40
        self.default_title_key = 1

        self.path = conf
        self.feed_dir = feed_dir

        self.columns = 1
        self.height = 0
        self.width = 0

        self.resize_hook = None
        self.new_hook = None
        self.select_hook = None
        self.unselect_hook = None
        self.start_hook = None
        self.end_hook = None
        self.update_hook = None

        self.filterlist = [None]
        self.filter_idx = 0

        self.no_conf = 0

        # If we can't stat self.path, generate a default config
        # and toss a message about making your own.

        try :
            os.stat(self.path)
        except :
            print "Unable to find config file. Generating and "\
                  "using ~/.canto/conf.example"
            print "You will keep getting this until you create your "\
                  "own ~/.canto/conf"
            print "\nRemember: it's 'h' for help.\n"

            newpath = os.getenv("HOME") + "/.canto/"
            if not os.path.exists(newpath):
                os.mkdir(newpath)

            self.path = newpath + "conf.example"
            f = codecs.open(self.path, "w", "UTF-8")
            f.write("# Auto-generated by canto because you don't have one.\n"
                    "# Please copy to/create ~/.canto/conf\n\n")
            f.write("""columns = width / 70\n""")
            f.write("""addfeed("Slashdot", """\
                    """"http://rss.slashdot.org/slashdot/Slashdot")\n""")
            f.write("""addfeed("Reddit", """\
                    """"http://reddit.com/.rss")\n""")
            f.write("""addfeed("KernelTrap", """\
                    """"http://kerneltrap.org/node/feed")\n""")
            f.write("""addfeed("Canto", """\
                    """"http://codezen.org/canto/feeds/latest")\n""")
            f.write("\n")
            f.close()
            self.no_conf = 1

        self.feeds = []
        self.parse()

        # Convert all of the C-M-blah (human readable) keys into
        # key tuples used in the main loop.

        self.key_list = utility.conv_key_list(self.key_list)
        self.reader_key_list = utility.conv_key_list(self.reader_key_list)

    # Simple append log.

    def log(self, message, mode="a"):
        try:
            f = open(self.log_file, mode)
            f.write(message + "\n")
            f.close()
        except:
            pass

    # Addfeed is a wrapper that's called as the config is exec'd
    # so that subsequent commands can reference it ASAP, and
    # so that set defaults are applied at that point.

    def addfeed(self, tag, URL, **kwargs):

        if kwargs.has_key("keep"):
            keep = kwargs["keep"]
        else:
            keep = self.default_keep

        if kwargs.has_key("rate"):
            rate = kwargs["rate"]
        else:
            rate = self.default_rate

        if kwargs.has_key("renderer"):
            renderer = kwargs["renderer"]
        else:
            renderer = self.render

        if kwargs.has_key("filterlist"):
            filterlist = [self.filter_dec(x) for x in kwargs["filterlist"]]
        else:
            filterlist = [None]

        # The tag is the only thing that has to be unique, so we ignore
        # any duplicate feed names, or everything  will break.

        if not tag in [f.tag for f in self.feeds]:
            return self.feeds.append(feed.Feed(self, self.feed_dir +\
                    tag.replace("/", " "), tag, URL, rate, keep, renderer,
                    filterlist))
        return -1

    def set_default_rate(self, rate):
        self.default_rate = rate

    def set_default_keep(self, keep):
        self.default_keep = keep

    def set_default_title_key(self, title_key):
        self.default_title_key = title_key

    # This decorator-like function is used to wrap
    # all of the hooks, so that user exceptions don't
    # take Canto down.

    def hook_dec(self, fn):
        def hdec(*args):
            try:
                r = fn(*args)
            except:
                self.log("\nException in hook:")
                self.log("%s" % traceback.format_exc())
        return hdec

    def filter_dec(self, c):
        if not c:
            return None

        class fdec():
            def __init__(self, instance, log):
                self.instance = instance
                self.log = log

            def __str__ (self):
                return self.instance.__str__()

            def __call__(self, *args):
                try:
                    return self.instance(*args)
                except:
                    self.log("\nException in filter:")
                    self.log("%s" % traceback.format_exc())
        return fdec(c, self.log)

    def parse(self):

        locals = {"addfeed":self.addfeed,

            # height and width are kept for legacy reasons
            # and will always be 0 at config time. Configs
            # should use resize_hook instead.

            "height" : self.height,
            "width" : self.width,
            "browser" : self.browser,
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

        # The entirety of the config is read in first (rather
        # than using execfile) because the config could be in
        # some strange encoding, and execfile would choke attempting
        # to coerce some character into ASCII.

        try:
            data = codecs.open(self.path, "r", "UTF-8").read()
        except UnicodeDecodeError:
            # If the Python built-in decoders can't figure it
            # out, it might need some help from chardet.
            data = codecs.open(self.path, "r").read()
            enc = chardet.detect(data)["encoding"]
            data = unicode(data, enc).encode("UTF-8")
            self.log("Chardet detected conf encoding: %s" % enc)

        try :
            exec(data, {}, locals)
        except :
            print "Invalid line in config."
            traceback.print_exc()
            raise ConfigError

        # exec cannot modify basic type
        # locals directly, so we do it by hand.

        for attr in ["filterlist", "filter_idx", "browser",\
                "text_browser", "render", "columns"]:
            if locals.has_key(attr):
                setattr(self, attr, locals[attr])

        # Wrap hooks in the exception handler
        for hook in ["resize_hook","new_hook","select_hook","update_hook",\
                "unselect_hook","start_hook","end_hook"]:
            if locals.has_key(hook):
                setattr(self, hook, self.hook_dec(locals[hook]))

        # Wrap filters in exception handler
        self.filterlist = [self.filter_dec(x) for x in self.filterlist]

        # Ensure we have at least one column
        if not self.columns:
            self.log("columns <1, set to 1")
            self.columns = 1

        # And that the user didn't set filter_idx invalidly.
        if self.filter_idx >= len(self.filterlist):
            self.log("filter_idx not in range, set to 0")
            self.filter_idx = 0

    # Key-binds for feed based filtering.
    def next_filter(self):
        if self.filter_idx < len(self.filterlist) - 1:
            self.filter_idx += 1
            return 1
        return 0

    def prev_filter(self):
        if self.filter_idx > 0:
            self.filter_idx -= 1
            return 1
        return 0
