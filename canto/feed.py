# -*- coding: utf-8 -*-

#Canto - ncurses RSS reader
#   Copyright (C) 2008 Jack Miller <jack@codezen.org>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License version 2 as 
#   published by the Free Software Foundation.

# The Feed() object is the canto client's interface to the files written by
# canto-fetch. In essence, it's only purpose is to load stories and keep the
# state synced on disk.

# The Feed() object is entirely separate from the Tag() objects that are displayed
# in the interface, despite the fact that (by default) there is a single tag per
# feed.

# The only entry points of feed (other than __init__ when it's created) are
# update() for updating from disk and todisk() to commit the current state when
# Canto shuts down.

from const import STORY_QD, STORY_SAVED, STORY_UPDATED
import story

import cPickle
import fcntl

class Feed(list):
    def __init__(self, cfg, dirpath, URL, tags, rate, keep, \
            filter, username, password):

        # We pay attention to whether the base was set at creation time (i.e.
        # via the config) so that setting tags=["sometag"] on two feeds merges
        # them whereas tags=[None, ...] resolving to the same base tag can have
        # their base tags resolved to "Base" and "Base (2)" (see canto.py)

        self.tags = tags
        if self.tags[0] == None:
            self.base_set = 0
            self.base_explicit = 0
        else:
            self.base_set = 1
            self.base_explicit = 1

        self.URL = URL
        self.rate = rate
        self.keep = keep
        self.username = username
        self.password = password

        # Queue status
        self.qd = False

        # Hard filter
        self.filter = filter

        self.path = dirpath
        self.cfg = cfg

    def __eq__(self, other):
        return self.URL == other.URL

    def get_ufp(self):
        lockflags = fcntl.LOCK_SH
        if self.base_set:
            lockflags |= fcntl.LOCK_NB

        try:
            f = open(self.path, "r")
            try:
                fcntl.flock(f.fileno(), lockflags)
                ufp = cPickle.load(f)
            except ImportError:
                try:

                    # Fortunately, I don't think forcing the cpickle
                    # to use feedparser_builtin is harmful, since they're
                    # basically the same class, feedparser_builtin is just the
                    # only way to properly look up the toplevel module now.

                    f.seek(0)
                    data = f.read()
                    data = data.replace("feedparser\n","feedparser_builtin\n",1)
                    ufp = cPickle.loads(data)
                except:
                    return 0
            except:
                return 0
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                f.close()
        except:
            return 0
        return ufp

    def update(self):
        ufp = self.get_ufp()
        if not ufp:
            return 0

        # If the base hasn't been set, attempt to set it from the data we just
        # picked up. get_ufp() blocks if base isn't set so it's impossible that
        # we'll just bail out unless there's a cPickle.load exception, but at
        # that point we're totally fucked anyway.

        if not self.base_set:
            self.base_set = 1
            if "feed" in ufp and "title" in ufp["feed"]:
                replace = lambda x: x or ufp["feed"]["title"]
            else:
                # Using URL for tag, no guarantees
                replace = lambda x: x or self.URL
            self.tags = [ replace(x) for x in self.tags]

        self.extend(ufp["entries"])
        self.todisk(ufp)
        return 1

    # Extend's job is to take items from disk, strip them down to the items that
    # we want to keep in memory (i.e. stuff that's used often) and add them to
    # the feed, applying the hard filter if necessary.

    def extend(self, entries):
        newlist = []
        for entry in entries:

            # This checks existence in newlist as well to avoid
            # duplicate items on feeds with duplicates in them.
            # (i.e. broken)

            if entry in self and entry not in newlist:
                centry = self[self.index(entry)]
                if (not centry.updated) and\
                    (centry["canto_state"] != entry["canto_state"]):
                    centry["canto_state"] = entry["canto_state"]
                newlist.append(centry)
                continue

            # nentry is the new, stripped down version of the item
            nentry = {}
            nentry["id"] = entry["id"]
            nentry["feed"] = self.URL
            nentry["canto_state"] = entry["canto_state"]

            if "title" not in entry:
                nentry["title"] = ""
            else:
                nentry["title"] = entry["title"]

            if "title_detail" in entry:
                nentry["title_detail"] = entry["title_detail"]

            for pc in self.cfg.precache:
                if pc in entry:
                    nentry[pc] = entry[pc]
                else:
                    nentry[pc] = None

            if "link" in entry:
                nentry["link"] = entry["link"]
            elif "href" in entry:
                nentry["link"] = entry["href"]

            # If tags were added in the configuration, c-f won't
            # notice (doesn't care about tags), so we check and
            # append as needed.

            updated = STORY_SAVED
            if self.tags[0] != nentry["canto_state"][0]:
                nentry["canto_state"][0] = self.tags[0]
                updated = STORY_UPDATED

            for tag in self.tags[1:]:
                if tag not in nentry["canto_state"]:
                    nentry["canto_state"].append(tag)
                    updated = STORY_UPDATED

            if nentry not in newlist:
                newlist.append(story.Story(nentry, self.path, updated))

        del self[:]
        for item in newlist:
            if not self.filter or self.filter(self, item):
                list.append(self, item)

    # Merging items means that they're unvalidated and unfiltered. This is
    # used when story objects are read in from a pipe.

    def merge(self, iter):
        for i, item in enumerate(iter):
            if item in self:
                cur = self[self.index(item)]
                if cur.updated in [STORY_SAVED, STORY_QD]:
                    cur["canto_state"] = item["canto_state"]
                    cur.updated = 0
                iter[i] = cur

        del self[:]
        list.extend(self, iter)

    # todisk is the complement to get_ufp, however, since the state may have
    # changed on any of the items, it has to intelligently merge the changes
    # before writing to disk.

    def todisk(self, ufp=None):
        if ufp == None:
            ufp = self.get_ufp()
        if not ufp:
            return

        changed = self.changed()
        if not changed :
            return

        for entry in changed:
            # We've stopped caring about this item
            if entry not in ufp["entries"]:
                continue

            old = ufp["entries"][ufp["entries"].index(entry)]
            if old["canto_state"] != entry["canto_state"]:
                # States differ, and we've recorded an update, that means we
                # probably have the newer information, so we handle the
                # state_change_hook in a batch and overwrite the old data

                if entry.updated:
                    if self.cfg.state_change_hook:
                        add = [t for t in entry["canto_state"] if\
                               t not in old["canto_state"]]
                        rem = [t for t in old["canto_state"] if\
                               t not in entry["canto_state"]]
                        self.cfg.state_change_hook(self, entry, add, rem)
                    old["canto_state"] = entry["canto_state"]


                # States differ, but we have no change, most likely the on disk
                # info is newer (i.e. changed by another running canto
                # instance). We count on the other canto instance handling the
                # state_change_hook.

                else:
                    entry["canto_state"] = old["canto_state"]

        # Dump the feed to disk.
        f = open(self.path, "r+")
        try:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            f.seek(0, 0)
            f.truncate()
            cPickle.dump(ufp, f)
            f.flush()
            for x in changed:
                x.updated = STORY_SAVED
        except:
            return 0
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            f.close()
        del ufp
        return 1

    def changed(self):
        return [ x for x in self if x.updated ]
