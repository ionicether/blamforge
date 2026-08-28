#!/usr/bin/env python3
"""
findmags.py - hunt for magazine blocks in weapon tags

the block is five u16s in a row:
    total_initial, total_maximum, loaded_maximum, runtime_inventory, rounds_reloaded
and runtime_inventory always equals total_maximum - loaded_maximum.

that relationship on its own gives you a load of rubbish, because other
structs in the tag satisfy the same arithmetic by accident. first version of
this told me the sniper rifle had a 1024 round magazine. so there's a pile of
sanity checks below - things a real magazine passes and a coincidence usually
doesn't.

usage:
    python3 findmags.py out/chunks
"""

import os
import re
import struct
import sys


def u16(b, o):
    return struct.unpack_from("<H", b, o)[0]


def is_pow2(n):
    return n > 0 and (n & (n - 1)) == 0


def find_blocks(b):
    hits = []
    for off in range(0, len(b) - 10):
        ti, tm, lm, inv, rr = (u16(b, off + i * 2) for i in range(5))

        if inv != tm - lm or inv == 0 or tm == lm:
            continue
        # nothing in this game holds more than a couple hundred rounds a clip
        if not (1 <= lm <= 200):
            continue
        if not (lm <= tm <= 4000):
            continue
        if not (0 <= ti <= tm):
            continue
        # you reload at most a full mag, at least one round (shotgun does 1)
        if not (1 <= rr <= lm):
            continue
        # this is what killed the 1024-round sniper rifle
        if is_pow2(lm) and is_pow2(tm) and lm >= 64:
            continue
        # reserve is normally a whole number of magazines
        if tm % lm not in (0, lm - 1) and ti % lm != 0:
            continue
        hits.append((off, (ti, tm, lm, inv, rr)))
    return hits


def tag_name(b):
    # weapon tags reference their own animation graph, which has the name in it
    m = re.search(rb"damj(objects[ -~]{4,90}?)(?=tsgt|lbgt|frgt|isgt)", b)
    if not m:
        return "?"
    return m.group(1).decode("latin1").split("\\")[-1]


def main():
    d = sys.argv[1] if len(sys.argv) > 1 else "."

    rows = []
    for f in sorted(os.listdir(d)):
        p = os.path.join(d, f)
        if not os.path.isfile(p):
            continue
        try:
            with open(p, "rb") as fh:
                head = fh.read(64)
                if len(head) < 64:
                    continue
                if head[0x3C:0x40] != b"MALB":
                    continue
                if head[0x30:0x34] != b"paew":
                    continue
                fh.seek(0)
                b = fh.read()
        except OSError:
            continue
        rows.append((f, tag_name(b), find_blocks(b)))

    clean = [r for r in rows if len(r[2]) == 1]
    messy = [r for r in rows if len(r[2]) > 1]
    empty = [r for r in rows if not r[2]]

    print("found one block (%d)" % len(clean))
    for f, n, c in clean:
        off, (ti, tm, lm, inv, rr) = c[0]
        print("  %-34s %-26s 0x%05X  mag=%-4d res=%-5d start=%-5d reload=%d"
              % (f, n, off, lm, tm, ti, rr))

    if messy:
        print("\nmore than one candidate, needs a look (%d)" % len(messy))
        for f, n, c in messy:
            print("  %s %s" % (f, n))
            for off, (ti, tm, lm, inv, rr) in c[:4]:
                print("      0x%05X  mag=%-4d res=%-5d start=%-5d reload=%d"
                      % (off, lm, tm, ti, rr))

    print("\nno magazine (%d)" % len(empty))
    print("expected for the plasma weapons, sword and hammer - they run on a")
    print("battery instead, like the sentinel beam does\n")
    for f, n, _ in empty:
        print("  %-34s %s" % (f, n))


if __name__ == "__main__":
    sys.exit(main())
