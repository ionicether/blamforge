#!/usr/bin/env python3
"""
cleanse.py - remove mods Blamforge installed

Every folder Blamforge writes gets a blamforge.txt in it. This looks for
those and deletes the folders they're in. Nothing else is touched, so mods
from anywhere else are left alone.

Folders are named bf_<something>, but older versions didn't use the prefix,
so this goes by the text file rather than the name.

Also clears the matching saved slider values out of settings.json next to
this script, same as the Cleanse button in the app. With --all that's the
whole file.

    python3 cleanse.py                    # list what's installed
    python3 cleanse.py --all              # remove all of it
    python3 cleanse.py assault_rifle      # remove one

You can also just delete the folders yourself. That's all this does.
"""

import argparse
import json
import os
import shutil
import sys

NOTE = "blamforge.txt"
SETTINGS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")


def forget(target_ids=None):
    """Drop saved slider values.

    All of them when target_ids is None, otherwise just those. Same as the
    Cleanse button in the app, so removing a mod here doesn't leave the app
    offering to put back something you got rid of on purpose.
    """
    if target_ids is None:
        try:
            os.remove(SETTINGS)
            return True
        except OSError:
            return False
    try:
        with open(SETTINGS, encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, ValueError):
        return False
    gone = [t for t in target_ids if d.pop(t, None) is not None]
    if not gone:
        return False
    try:
        with open(SETTINGS, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=2)
        return True
    except OSError:
        return False


HINTS = [
    "~/.local/share/Steam/steamapps/common/Halo Campaign Evolved",
    "~/.steam/steam/steamapps/common/Halo Campaign Evolved",
    "C:/Program Files (x86)/Steam/steamapps/common/Halo Campaign Evolved",
    "D:/SteamLibrary/steamapps/common/Halo Campaign Evolved",
    "E:/SteamLibrary/steamapps/common/Halo Campaign Evolved",
]


def find_paks(given=None):
    roots = [given] if given else [os.path.expanduser(p) for p in HINTS]
    for raw in roots:
        if not raw:
            continue
        r = os.path.expanduser(raw)
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
                with open(note, encoding="utf-8") as f:
                    first = f.read().splitlines()
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
            for line in lines[:5]:
                if line.strip():
                    print("   ", line)
            print()
        print("Pass a name to remove one, or --all for everything.")
        return 0

    if a.all:
        targets = mods
    else:
        by_name = {n: (n, d, lines) for n, d, lines in mods}
        targets = []
        for w in a.which:
            if w not in by_name:
                print("not installed:", w)
                continue
            targets.append(by_name[w])

    if not targets:
        return 1

    print("about to delete:")
    for _, d, _ in targets:
        print("   ", d)

    if not a.yes and input("\ngo ahead? [y/N] ").strip().lower() not in ("y", "yes"):
        print("left alone")
        return 0

    for name, d, _ in targets:
        shutil.rmtree(d)
        print("removed", name)

    if a.all:
        if forget():
            print("cleared your saved slider values too")
    else:
        # folders are bf_<id>, settings are keyed on the id
        ids = [n.removeprefix("bf_") for n, _, _ in targets]
        if forget(ids):
            print("forgot the saved values for those")
    return 0


if __name__ == "__main__":
    sys.exit(main())
