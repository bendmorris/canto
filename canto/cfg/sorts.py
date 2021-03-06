# -*- coding: utf-8 -*-

#Canto - ncurses RSS reader
#   Copyright (C) 2008 Jack Miller <jack@codezen.org>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License version 2 as 
#   published by the Free Software Foundation.

from canto.utility import Cycle
import traceback
import types

all_sorts = []

class Sort:
    def __init__(self):
        self.precache = []

    def __str__(self):
        return "Unnamed Sort."

    def __call__(self, item, item2):
        return 0

def sort_dec(c, s):
    if not s:
        return None

    class sdec():
        def __init__(self, instance, log):
            self.instance = instance
            self.precache = self.instance.precache
            self.log = log

        def __eq__(self, other):
            if not other:
                return False
            return str(self) == str(other)

        def __str__(self):
            return self.instance.__str__()

        def __call__(self, *args):
            try:
                return self.instance(*args)
            except:
                self.log("\nException in sort:")
                self.log("%s" % traceback.format_exc())
    return sdec(s, c.log)

def register(c): 
    def set_default_tag_sorts(sorts):
        c.tag_sorts = sorts

    c.all_sorts = []
    c.tag_sorts = [None]

    c.locals.update({
        "Sort" : Sort,
        "default_tag_sorts" : set_default_tag_sorts,
        "tag_sorts" : c.tag_sorts })

def post_parse(c):
    c.all_sorts = all_sorts

def validate_sort(c, s):
    if not s:
        return None
    if type(s) not in [types.ClassType, types.InstanceType]:
        raise Exception, \
            "All sorts must be classes that subclass Sort (%s)" % s
    if not isinstance(s, Sort):
        s = s()
    if not issubclass(s.__class__, Sort):
        raise Exception, "All sorts must subclass Sort class ("\
                + s.__class__.__name__ + ")"

    if c:
        return sort_dec(c, s)
    else:
        return s

def validate(c):
    c.all_sorts = [ validate_sort(c, s) for s in c.all_sorts ]
    for tag in c.cfgtags:
        if type(tag.sorts) != list:
            raise Exception, "Tag sorts for %s must be a list" % tag.tag
        newsorts = [ validate_sort(c, s) for s in tag.sorts ]
        for s in newsorts:
            if s not in c.all_sorts:
                c.all_sorts.append(s)
        tag.sorts = Cycle(newsorts)
        
def test(c):
    pass
