#!/usr/bin/env python3
"""
mkmod.py - turn a patched tag into something you can actually install

patch.py gives you a modified chunk. this packs it into a container and sorts
out the .pak, which retoc doesn't generate.

    python3 mkmod.py ar.tag --chunk 422244d93c8d5f7300000002
    python3 mkmod.py ar.tag --chunk <id> --install "/path/to/Halo Campaign Evolved"

about the .pak: the engine wants one sitting next to the .utoc and .ucas or it
won't mount the container. retoc has no way to make one. turns out every mod
ships an identical 339 byte file, so we just copy one from wherever we can
find it. checked a few and they're byte for byte the same.
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PAK_SIZE = 339


def find_stub(*where):
    """any .pak of exactly 339 bytes will do"""
    for d in where:
        if not d or not os.path.isdir(d):
            continue
        for root, _, files in os.walk(d):
            for f in files:
                p = os.path.join(root, f)
                try:
                    if f.endswith(".pak") and os.path.getsize(p) == PAK_SIZE:
                        return p
                except OSError:
                    pass
    return None


def find_manifest(*where):
    for d in where:
        if d and os.path.exists(os.path.join(d, "manifest.json")):
            return os.path.join(d, "manifest.json")
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tag", help="the patched chunk from patch.py")
    ap.add_argument("--chunk", help="chunk id (defaults to the filename)")
    ap.add_argument("--name", help="what to call the mod")
    ap.add_argument("--manifest", help="manifest.json from the extraction")
    ap.add_argument("--stub", help="a .pak to copy, if it can't find one")
    ap.add_argument("-o", "--out", default=os.path.join(HERE, "dist"))
    ap.add_argument("--install", metavar="GAME",
                    help="drop it straight into Content/Paks")
    a = ap.parse_args()

    if not shutil.which("retoc"):
        sys.exit("retoc isn't on PATH")
    if not os.path.exists(a.tag):
        sys.exit("no such file: " + a.tag)

    cid = a.chunk
    if not cid:
        base = os.path.basename(a.tag)
        m = re.search(r"([0-9a-f]{16,32})", base)
        if not m:
            sys.exit("can't tell the chunk id from the filename, use --chunk")
        cid = m.group(1)

    name = a.name or re.sub(r"[^A-Za-z0-9_]", "_",
                            os.path.splitext(os.path.basename(a.tag))[0])
    stem = "zzz_%s_P" % name

    here = os.path.dirname(os.path.abspath(a.tag))
    paks = None
    if a.install:
        g = os.path.expanduser(a.install)
        c = os.path.join(g, "Meteorite", "Content", "Paks")
        paks = c if os.path.isdir(c) else (g if os.path.isdir(g) else None)
        if not paks:
            sys.exit("can't find Content/Paks under " + a.install)

    manifest = a.manifest or find_manifest(here, HERE, os.getcwd(),
                                           os.path.join(os.getcwd(), "out"))
    if not manifest:
        sys.exit("need manifest.json (retoc writes it when you unpack).\n"
                 "pass it with --manifest")

    stub = a.stub or find_stub(here, a.out, HERE, paks)
    if not stub:
        sys.exit("need a .pak stub. any mod folder has one, they're all the\n"
                 "same 339 bytes. copy one here or pass --stub")

    scratch = tempfile.mkdtemp(prefix="mkmod-")
    try:
        src = os.path.join(scratch, "src")
        os.makedirs(os.path.join(src, "chunks"))
        shutil.copy2(a.tag, os.path.join(src, "chunks", cid))
        shutil.copy2(manifest, os.path.join(src, "manifest.json"))

        os.makedirs(a.out, exist_ok=True)
        utoc = os.path.join(a.out, stem + ".utoc")
        for e in (".utoc", ".ucas", ".pak"):
            p = os.path.join(a.out, stem + e)
            if os.path.exists(p):
                os.remove(p)

        r = subprocess.run(["retoc", "pack-raw", src, utoc])
        if r.returncode != 0:
            sys.exit("retoc pack-raw failed")
        if os.path.getsize(utoc) == 0:
            # happened when i tried to cram 51 chunks into one container
            sys.exit("retoc wrote an empty .utoc. too many chunks?")
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

    shutil.copy2(stub, os.path.join(a.out, stem + ".pak"))

    print("built:")
    for e in (".utoc", ".ucas", ".pak"):
        p = os.path.join(a.out, stem + e)
        print("  %s  (%d bytes)" % (p, os.path.getsize(p)))

    if paks:
        dest = os.path.join(paks, name)
        os.makedirs(dest, exist_ok=True)
        for e in (".utoc", ".ucas", ".pak"):
            shutil.copy2(os.path.join(a.out, stem + e),
                         os.path.join(dest, stem + e))
        print("\ninstalled to", dest)
        print("rm -rf that folder to undo")
    else:
        print("\ncopy those three into their own folder under Content/Paks/")

    return 0


if __name__ == "__main__":
    sys.exit(main())
