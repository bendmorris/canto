# -*- coding: utf-8 -*-

#Canto - ncurses RSS reader
#   Copyright (C) 2008 Jack Miller <jack@codezen.org>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License version 2 as 
#   published by the Free Software Foundation.

import tempfile
import urllib2
import signal 
import curses
import locale
import sys
import re
import os
import subprocess
import main

# The Cycle class has proved to be useful. It's used
# to encapsulate every cycle in canto, global filters,
# tag filters, global and tag sorts, tags. It's
# essentially a list with a current pointer and
# exception proof next/prev function and the ability
# to temporarily override a particular value.

class Cycle():
    def __init__(self, list, idx = 0):
        self.overridden = False
        self.over = None
        self.list = list
        if 0 <= idx < len(self.list):
            self.idx = idx
        else:
            self.idx = 0

    def next(self):
        self.overridden = False
        if self.idx >= len(self.list) - 1:
            return 0
        self.idx += 1
        return 1

    def prev(self):
        self.overridden = False
        if self.idx <= 0:
            return 0
        self.idx -= 1
        return 1

    def override(self, cur):
        if not self.overridden or self.over != cur:
            self.overridden = True
            self.over = cur
            return 1
        return 0

    def cur(self):
        if self.overridden:
            return self.over
        return self.list[self.idx]

def silentfork(path, href, text, fetch):

    enc = locale.getpreferredencoding()
    href = href.encode(enc, "ignore")

    # A lot of programs don't appreciate
    # having their fds closed, so instead
    # we dup them to /dev/null.

    curses.endwin()

    if fetch:
        response = urllib2.urlopen(href)
        data = response.read()
        fd, name = tempfile.mkstemp()
        os.write(fd, data)
        os.close(fd)
        path = path.replace("%u", name)
    else:
        path = path.replace("%u", href)

    subprocess.call(["/bin/sh", "-c", path])

    main.Main.instance.refresh(restart=True)


def goto(link, cfg):
    title,href,handler = link
    if handler in cfg.handlers:
        for k in [h for h in cfg.handlers[handler].keys() if h]:
            if href.endswith(k):
                binary, text, fetch = cfg.handlers[handler][k]
                break
        else:
            if None in cfg.handlers[handler]:
                binary, text, fetch = cfg.handlers[handler][None]
            else:
                cfg.log("No default %s handler defined!" % handler)
                return


        # Escape all "s in the URL, to avoid malicious use
        # of crafted feeds. Thanks to Andreas.
        href = href.replace("\"","%22")

        if text:
            cfg.wait_for_pid = silentfork(binary, href, 1, fetch)
        else:
            silentfork(binary, href, 0, fetch)
    else:
        cfg.log("No handler set for %s" % handler)

def stripchars(string):
    string = string.replace("\\","\\\\")
    string = string.replace("%", "\\%")
    return string

def strip_escape_chars(strings):
    return (re.sub("\\\\(.)", "\\1", string) for string in strings)
