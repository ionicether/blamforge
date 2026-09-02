#!/usr/bin/env python3
"""
uninstall.py - remove mods Blamforge installed

Every folder Blamforge writes gets a blamforge.txt in it. This looks for
those and deletes the folders they're in. Nothing else is touched, so mods
from anywhere else are left alone.

Folders are named bf_<something>, but older versions didn't use the prefix,
so this goes by the text file rather than the name.

    python3 uninstall.py                    # list what's installed
    python3 uninstall.py --all              # remove all of it
    python3 uninstall.py assault_rifle      # remove one

You can also just delete the folders yourself. That's all this does.
"""

import argparse
import os
import shutil
import sys

NOTE = "blamforge.txt"

HINTS = [
    "~/.local/share/Steam/steamapps/common/Halo Campaign Evolved",
    "~/.steam/steam/steamapps/common/Halo Campaign Evolved",
    "C:/Program Files (x86)/Steam/steamapps/common/Halo Campaign Evolved",
    "D:/SteamLibrary/steamapps/common/Halo Campaign Evolved",
    "E:/SteamLibrary/steamapps/common/Halo Campaign Evolved",
]


def find_paks(given=None):
    roots = [given] if given else [os.path.expanduser(p) for p in HINTS]
    for r in roots:
        if not r:
            continue
        r = os.path.expanduser(r)
        for c in (os.path.join(r, "Meteorite", "Content", "Paks"), r):
            if os.path.isdir(c):
                return c
    return None


def installed(paks):
    found = []
    for name in sorted(os.listdir(paks)):
        d = os.path.join(paks, name)
        note = os.path.join(d, NOTE)
        if os.path.isdir(d) and os.path.exists(note):
            try:
                first = open(note, encoding="utf-8").read().splitlines()
            except OSError:
                first = []
            found.append((name, d, first))
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("which", nargs="*", help="folder names to remove")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--game", help="game folder, if it can't find it")
    ap.add_argument("-y", "--yes", action="store_true", help="don't ask")
    a = ap.parse_args()

    paks = find_paks(a.game)
    if not paks:
        sys.exit("Can't find Content/Paks. Pass --game with the game folder.")

    mods = installed(paks)
    if not mods:
        print("Nothing installed by Blamforge in", paks)
        return 0

    if not a.which and not a.all:
        print(paks, "\n")
        for name, _, lines in mods:
            print(name)
            for l in lines[:5]:
                if l.strip():
                    print("   ", l)
            print()
        print("Pass a name to remove one, or --all for everything.")
        return 0

    if a.all:
        targets = mods
    else:
        by_name = {n: (n, d, l) for n, d, l in mods}
        targets = []
        for w in a.which:
            if w not in by_name:
                print("not installed:", w)
                continue
            targets.append(by_name[w])

    if not targets:
        return 1

    print("about to delete:")
    for name, d, _ in targets:
        print("   ", d)

    if not a.yes:
        if input("\ngo ahead? [y/N] ").strip().lower() not in ("y", "yes"):
            print("left alone")
            return 0

    for name, d, _ in targets:
        shutil.rmtree(d)
        print("removed", name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
