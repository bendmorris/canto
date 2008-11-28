# -*- coding: utf-8 -*-

#Canto - ncurses RSS reader
#   Copyright (C) 2008 Jack Miller <jack@codezen.org>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License version 2 as 
#   published by the Free Software Foundation.

from textpad import Textbox
import curses
import signal
import re

def input(cfg, prompt):
    cfg.message(prompt + ": ")

    temp = signal.getsignal(signal.SIGALRM)
    signal.signal(signal.SIGALRM, signal.SIG_IGN)
    
    term = Textbox(cfg.msg).edit()
    term = term.split(": ",1)[-1].strip()

    signal.signal(signal.SIGALRM, temp)
    signal.alarm(1)

    cfg.msg.erase()
    cfg.msg.refresh()

    return term

def search(cfg, prompt):
    term = input(cfg, prompt)
    if not term :
        return

    elif term.startswith("rgx:"):
        str = term[4:]
    else:
        str = ".*" + re.escape(term) + ".*"
    
    try:
        m = re.compile(str)
    except:
        return None

    return m
