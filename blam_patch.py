#!/usr/bin/env python3
"""
patch.py - edit values in Halo CE (2026) blam tags

usage:
    python3 patch.py --list
    python3 patch.py chief.tag --show
    python3 patch.py chief.tag out.tag --set shield_delay=0.5 --set shield_vitality=200

offsets are in offsets.json. they're for whatever build i have installed
right now (2026.07.25 CU3), no idea how stable they are across patches.
it checks the stock value before writing so at least it'll fail loudly
instead of corrupting something.
"""

import argparse
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OFFSETS = json.load(open(os.path.join(HERE, "offsets.json")))


def read(buf, f):
    if f["type"] == "u16":
        return struct.unpack_from("<H", buf, f["off"])[0]
    return struct.unpack_from("<f", buf, f["off"])[0]


def write(buf, f, v):
    targets = [f["off"]]
    if f.get("mirror"):
        targets.append(f["mirror"])
    for off in targets:
        if f["type"] == "u16":
            struct.pack_into("<H", buf, off, int(round(v)))
        else:
            struct.pack_into("<f", buf, off, float(v))


def close_enough(f, got):
    if f["type"] == "u16":
        return got == f["stock"]
    return abs(got - f["stock"]) <= max(1e-6, abs(f["stock"]) * 1e-4)


def identify(buf):
    """work out which tag this is by checking the values against known stock

    only counts as a match if every field lines up. otherwise you get silly
    results - a patched AR was matching as the sentinel beam because it
    happened to fail fewer checks.
    """
    if len(buf) < 0x40:
        return None, []
    if bytes(buf[0x3C:0x40]) != b"MALB":
        return None, []
    group = bytes(buf[0x30:0x34]).decode("latin1")

    partial, partial_bad = None, None
    for t in OFFSETS["targets"]:
        if t["group"] != group:
            continue
        bad = [f for f in t["fields"]
               if f["off"] + 4 > len(buf) or not close_enough(f, read(buf, f))]
        if not bad:
            return t, []
        # keep the closest one around so the error message can name it
        if partial is None or len(bad) / len(t["fields"]) < len(partial_bad) / len(partial["fields"]):
            partial, partial_bad = t, bad
    return partial, partial_bad


def main():
    p = argparse.ArgumentParser()
    p.add_argument("infile", nargs="?")
    p.add_argument("outfile", nargs="?")
    p.add_argument("--list", action="store_true", help="what i've mapped so far")
    p.add_argument("--show", action="store_true", help="print current values")
    p.add_argument("--set", action="append", default=[], metavar="KEY=VAL")
    p.add_argument("--force", action="store_true",
                   help="write even if the stock check fails (don't)")
    a = p.parse_args()

    if a.list:
        print("build:", OFFSETS["build"])
        for t in OFFSETS["targets"]:
            print("\n%s  (%s, chunk %s)" % (t["name"], t["group"], t["chunk"]))
            for f in t["fields"]:
                note = ""
                if f.get("derived"):
                    note = "  [auto, don't set]"
                if f.get("locked"):
                    note = "  [leave alone]"
                print("    %-22s 0x%05X  %s%s"
                      % (f["key"], f["off"], f["stock"], note))
        return 0

    if not a.infile:
        p.error("need a file (or --list)")

    buf = bytearray(open(a.infile, "rb").read())
    t, bad = identify(buf)

    if t is None:
        sys.exit("that's not a blam tag, or not one i know about")

    print("%s (%d bytes)" % (t["name"], len(buf)))
    if bad:
        print("\nstock check failed:")
        for f in bad:
            print("  %-22s reads %-14s expected %s"
                  % (f["key"], read(buf, f), f["stock"]))
        print("\nprobably means: already patched, a mod is installed, or the")
        print("game updated and everything moved.")
        if not a.force:
            return 1

    if a.show or not a.set:
        print()
        for f in t["fields"]:
            print("  %-22s %s" % (f["key"], read(buf, f)))
        if not a.set:
            return 0

    # apply
    changes = {}
    keys = {f["key"]: f for f in t["fields"]}
    for s in a.set:
        if "=" not in s:
            sys.exit("--set wants key=value, got %r" % s)
        k, v = s.split("=", 1)
        if k not in keys:
            sys.exit("no field %r on %s. try --list" % (k, t["name"]))
        if keys[k].get("derived"):
            sys.exit("%s is derived from other fields, don't set it directly" % k)
        if keys[k].get("locked"):
            sys.exit("%s is locked - changing it breaks things" % k)
        changes[k] = float(v)

    vals = {f["key"]: read(buf, f) for f in t["fields"]}
    vals.update(changes)

    # keep the derived fields in step
    for l in t.get("linked", []):
        x = vals[l["source"]]
        if l.get("minus"):
            x -= vals[l["minus"]]
        vals[l["target"]] = max(0, round(x))

    for f in t["fields"]:
        write(buf, f, vals[f["key"]])

    if not a.outfile:
        print("\nno output file given, nothing written")
        return 1

    open(a.outfile, "wb").write(bytes(buf))
    print("\nwrote", a.outfile)
    for f in t["fields"]:
        old = f["stock"]
        new = read(buf, f)
        if not close_enough(f, new):
            print("  %-22s %s -> %s" % (f["key"], old, new))

    print("\nnow:")
    print("  mkdir -p mod/chunks")
    print("  cp %s mod/chunks/%s" % (a.outfile, t["chunk"]))
    print("  cp manifest.json mod/")
    print("  retoc pack-raw mod out/zzz_%s_P.utoc" % t["id"])
    print("  # then copy the utoc+ucas into Content/Paks/<something>/")
    print("  # along with a .pak stub nicked from another mod folder")
    return 0


if __name__ == "__main__":
    sys.exit(main())
