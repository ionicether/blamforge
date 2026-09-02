#!/usr/bin/env python3
"""
Blamforge.

Run it, a browser opens, you get sliders. Behind that it finds the game,
digs the tags out with retoc, writes your numbers in and packs the result
back into a mod folder.

Localhost only. It reads the game folder and writes into Content/Paks and
its own .cache, and touches nothing else.

Python 3.8+, and retoc needs to be on PATH: github.com/trumank/retoc
"""

import http.server
import json
import os
import re
import shutil
import socket
import socketserver
import struct
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse
import webbrowser

APP = "blamforge"
VERSION = "0.4.0"

HERE = os.path.dirname(os.path.abspath(__file__))


def retoc_path():
    """Find retoc. PATH first, then next to this script.

    The second case matters on Windows, where getting something onto PATH is
    enough of a faff that people would rather drop the exe in the folder.
    """
    found = shutil.which("retoc")
    if found:
        return found
    for name in ("retoc", "retoc.exe"):
        p = os.path.join(HERE, name)
        if os.path.isfile(p):
            return p
    return None
CACHE = os.path.join(HERE, ".cache")
CONTAINER = "pakchunk0-Windows.utoc"

# The .pak that has to sit next to a .utoc/.ucas or the engine won't mount the
# container. retoc doesn't produce one, so we copy an existing one.
#
# 339 is the size when the mount point is "/", which is what retoc-built
# containers want - they don't write a mount point of their own, so the pak's
# is what gets used. Mods that ship real asset paths instead of raw chunk
# overrides use "../../../" and come out at 347. Those aren't interchangeable
# with these, hence matching on the exact size rather than just any .pak.
PAK_SIZE = 339

GAME_HINTS = [
    "~/.local/share/Steam/steamapps/common/Halo Campaign Evolved",
    "~/.steam/steam/steamapps/common/Halo Campaign Evolved",
    "C:/Program Files (x86)/Steam/steamapps/common/Halo Campaign Evolved",
    "D:/SteamLibrary/steamapps/common/Halo Campaign Evolved",
    "E:/SteamLibrary/steamapps/common/Halo Campaign Evolved",
]


# ----------------------------------------------------------------- registry

def load_registry():
    path = os.path.join(HERE, "registry.json")
    if os.path.exists(path):
        return json.load(open(path, encoding="utf-8"))
    # Older checkouts kept this as a .js file. Convert on the fly rather than
    # making people re-download.
    js = os.path.join(HERE, "registry.js")
    if not os.path.exists(js):
        sys.exit("registry.json not found next to blamforge.py")
    src = open(js, encoding="utf-8").read()
    src = src[src.index("{"):src.rindex("}") + 1]
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    src = re.sub(r"//.*", "", src)
    src = re.sub(r"(\w+):", r'"\1":', src)          # bare keys need quoting
    src = re.sub(r"0x([0-9a-fA-F]+)", lambda m: str(int(m.group(1), 16)), src)
    src = re.sub(r",(\s*[}\]])", r"\1", src)        # JSON hates trailing commas
    return json.loads(src)


REG = load_registry()
TARGETS = {t["id"]: t for t in REG["targets"]}


# --------------------------------------------------------------- game files

def find_game(given=None):
    roots = [given] if given else [os.path.expanduser(p) for p in GAME_HINTS]
    for r in roots:
        if not r:
            continue
        r = os.path.expanduser(r)
        for cand in (os.path.join(r, "Meteorite", "Content", "Paks"), r):
            if os.path.exists(os.path.join(cand, CONTAINER)):
                return r, cand
    return None, None


def find_stub(paks):
    for root, _, files in os.walk(paks):
        for f in files:
            p = os.path.join(root, f)
            try:
                if f.endswith(".pak") and os.path.getsize(p) == PAK_SIZE:
                    return p
            except OSError:
                pass
    return None


def read_field(b, f):
    if f["type"] == "u16":
        return struct.unpack_from("<H", b, f["off"])[0]
    return struct.unpack_from("<f", b, f["off"])[0]


def write_field(b, f, v):
    for off in [f["off"]] + ([f["mirror"]] if f.get("mirror") else []):
        if f["type"] == "u16":
            struct.pack_into("<H", b, off, int(round(v)))
        else:
            struct.pack_into("<f", b, off, float(v))


def verify(b, t):
    """Check the tag is untouched.

    Every field has to read back the value a clean install has. If even one
    doesn't, we're looking at something else: a tag someone already modded,
    a file we've patched before, or a game update that shifted the layout.
    Better to stop than write into the wrong offset.
    """
    bad = []
    for f in t["fields"]:
        if f["off"] + 4 > len(b):
            bad.append((f["key"], None, f["stock"]))
            continue
        got = read_field(b, f)
        ok = (got == f["stock"] if f["type"] == "u16"
              else abs(got - f["stock"]) <= max(1e-6, abs(f["stock"]) * 1e-4))
        if not ok:
            bad.append((f["key"], got, f["stock"]))
    return bad


# ------------------------------------------------------------------ actions

STATE = {"game": None, "paks": None, "status": "", "busy": False}


STAMP = "extracted.txt"


def cache_state():
    """Is the cache usable, and if not, why not.

    Returns (ok, why). The registry grows over time, so a cache that was
    complete last month can be missing chunks today. Without this you just
    get bounced back to the setup screen with no idea what changed.

    This deliberately doesn't compare game build numbers. There was a version
    that did, and it was comparing the registry against a copy of itself, so
    it fired when I edited registry.json and stayed quiet when the game
    actually updated. The stock value check catches a real game update, by
    noticing the bytes aren't where they should be.
    """
    if not os.path.isdir(CACHE):
        return False, "nothing extracted yet"

    missing = [t["name"] for t in REG["targets"]
               if t.get("chunk")
               and not os.path.exists(os.path.join(CACHE, t["chunk"]))]
    if missing:
        if len(missing) > 3:
            what = "%s and %d others" % (missing[0], len(missing) - 1)
        else:
            what = ", ".join(missing)
        return False, "no tag cached for " + what

    for f in ("manifest.json", "stub.pak"):
        if not os.path.exists(os.path.join(CACHE, f)):
            return False, f + " missing from the cache"

    return True, ""


def cache_ok():
    return cache_state()[0]


def extract(paks, progress):
    """Unpack the container and keep the dozen chunks we can edit.

    retoc has no way to pull a single chunk, so this extracts all ~106,000
    of them, copies out what's in the registry, and throws the rest away.
    Wasteful for a minute, but it only happens once.
    """
    os.makedirs(CACHE, exist_ok=True)
    scratch = tempfile.mkdtemp(prefix="blamforge-", dir=HERE)
    out = os.path.join(scratch, "all")
    try:
        progress("Unpacking the game container. This takes a minute or two "
                 "and only happens once.")
        r = subprocess.run([retoc_path(), "unpack-raw",
                            os.path.join(paks, CONTAINER), out],
                           capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError((r.stderr or "retoc failed").strip())

        chunks = os.path.join(out, "chunks")
        progress("Keeping the tags, discarding the rest.")
        for t in REG["targets"]:
            cid = t.get("chunk")
            if not cid:
                continue
            src = os.path.join(chunks, cid)
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(CACHE, cid))

        m = os.path.join(out, "manifest.json")
        if os.path.exists(m):
            shutil.copy2(m, os.path.join(CACHE, "manifest.json"))

        stub = find_stub(paks)
        if stub:
            shutil.copy2(stub, os.path.join(CACHE, "stub.pak"))

        with open(os.path.join(CACHE, STAMP), "w", encoding="utf-8") as fh:
            fh.write("extracted %s\n" % time.strftime("%Y-%m-%d %H:%M"))
            fh.write("registry %s\n" % REG.get("version", "?"))
            fh.write("build %s\n" % REG.get("build", "?"))
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


NOTE = "blamforge.txt"
PREFIX = "bf_"


def mod_dirs(target_id):
    """Where this mod could be. New installs use the prefix; older ones
    didn't, and there's no reason to strand them."""
    return [os.path.join(STATE["paks"], PREFIX + target_id),
            os.path.join(STATE["paks"], target_id)]


def mod_dir(target_id):
    """The one that's actually there, if any."""
    for d in mod_dirs(target_id):
        if os.path.isdir(d) and os.path.exists(os.path.join(d, NOTE)):
            return d
    return None


def write_note(dest, t, values, patched):
    """Leave a plain text record in the mod folder.

    Mostly so that in six months you can look at a folder and know what's in
    it.
    """
    lines = [
        "%s %s" % (APP, VERSION),
        t["name"],
        "installed %s" % time.strftime("%Y-%m-%d %H:%M"),
        "game build %s" % REG.get("build", "unknown"),
        "chunk %s" % t["chunk"],
        "",
    ]
    rows = []
    for f in t["fields"]:
        now = read_field(patched, f)
        if f["type"] == "u16":
            now, was = int(now), int(f["stock"])
            same = now == was
        else:
            was = f["stock"]
            # same tolerance the stock check uses, so a value that round
            # trips through float32 doesn't read as a change
            same = abs(now - was) <= max(1e-6, abs(was) * 1e-4)
            now = round(now, 6)
        if same:
            continue
        rows.append((f.get("label", f["key"]), was, now))

    if rows:
        width = max(len(r[0]) for r in rows)
        for label, was, now in rows:
            lines.append("%-*s  %s -> %s" % (width, label, was, now))
    else:
        lines.append("nothing changed from stock")

    lines += [
        "",
        "Delete this whole folder to put it back the way it was, or run",
        "uninstall.py to find and remove every folder with one of these in it.",
        "",
    ]
    with open(os.path.join(dest, NOTE), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def install(target_id, values, progress):
    t = TARGETS[target_id]
    cid = t["chunk"]
    src = os.path.join(CACHE, cid)
    if not os.path.exists(src):
        raise RuntimeError("that tag isn't in the cache; try Refresh")

    b = bytearray(open(src, "rb").read())

    bad = verify(b, t)
    if bad:
        raise RuntimeError(
            "The cached tag isn't stock: " +
            ", ".join("%s reads %s, expected %s" % x for x in bad) +
            ". A mod may already be installed, or the game has updated.")

    for f in t["fields"]:
        if f["key"] in values:
            write_field(b, f, values[f["key"]])

    name = t["id"]
    stem = "zzz_%s_P" % name
    scratch = tempfile.mkdtemp(prefix="blamforge-build-", dir=HERE)
    try:
        srcdir = os.path.join(scratch, "src")
        os.makedirs(os.path.join(srcdir, "chunks"))
        open(os.path.join(srcdir, "chunks", cid), "wb").write(bytes(b))
        shutil.copy2(os.path.join(CACHE, "manifest.json"),
                     os.path.join(srcdir, "manifest.json"))

        dist = os.path.join(scratch, "dist")
        os.makedirs(dist)
        utoc = os.path.join(dist, stem + ".utoc")

        progress("Packing the mod.")
        r = subprocess.run([retoc_path(), "pack-raw", srcdir, utoc],
                           capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError((r.stderr or "retoc pack-raw failed").strip())
        if not os.path.exists(utoc) or os.path.getsize(utoc) == 0:
            raise RuntimeError("retoc produced an empty container")

        stub = os.path.join(CACHE, "stub.pak")
        if not os.path.exists(stub):
            raise RuntimeError("stub.pak missing from the cache; try Refresh")
        shutil.copy2(stub, os.path.join(dist, stem + ".pak"))

        # if it's already installed under the old unprefixed name, take that
        # folder out rather than leaving two containers fighting over the
        # same chunk
        old = mod_dir(name)
        if old and os.path.basename(old) == name:
            shutil.rmtree(old, ignore_errors=True)

        dest = os.path.join(STATE["paks"], PREFIX + name)
        os.makedirs(dest, exist_ok=True)
        for ext in (".utoc", ".ucas", ".pak"):
            shutil.copy2(os.path.join(dist, stem + ext),
                         os.path.join(dest, stem + ext))
        write_note(dest, t, values, b)
        return dest
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def uninstall(target_id):
    d = mod_dir(TARGETS[target_id]["id"])
    if d:
        shutil.rmtree(d)
        return True
    return False


def installed_ids():
    out = []
    if not STATE["paks"]:
        return out
    for t in REG["targets"]:
        if mod_dir(t["id"]):
            out.append(t["id"])
    return out


# ------------------------------------------------------------------- server

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=HERE, **kw)

    def log_message(self, *a):
        pass

    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)

        if u.path == "/api/state":
            ok, why = cache_state()
            return self._json({
                "registry": REG,
                "game": STATE["game"],
                "ready": ok,
                "stale": why,
                "status": STATE["status"],
                "busy": STATE["busy"],
                "installed": installed_ids(),
                "retoc": retoc_path() is not None,
            })

        if u.path == "/api/values":
            tid = urllib.parse.parse_qs(u.query).get("target", [""])[0]
            t = TARGETS.get(tid)
            if not t:
                return self._json({"error": "unknown target"}, 404)
            p = os.path.join(CACHE, t.get("chunk") or "")
            if not os.path.exists(p):
                return self._json({"error": "not extracted"}, 404)
            b = open(p, "rb").read()
            bad = verify(b, t)
            return self._json({
                "values": {f["key"]: read_field(b, f) for f in t["fields"]},
                "mismatch": [{"key": k, "got": g, "want": w} for k, g, w in bad],
            })

        return super().do_GET()

    def do_POST(self):
        u = urllib.parse.urlparse(self.path)
        n = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(n) or "{}")

        if u.path == "/api/game":
            game, paks = find_game(body.get("path"))
            if not game:
                return self._json({"error":
                    "No Halo: Campaign Evolved there. Look for the folder "
                    "containing Meteorite/Content/Paks."}, 400)
            STATE["game"], STATE["paks"] = game, paks
            return self._json({"game": game, "ready": cache_ok()})

        if u.path == "/api/extract":
            if not STATE["paks"]:
                return self._json({"error": "no game folder set"}, 400)
            if STATE["busy"]:
                return self._json({"error": "already working"}, 409)

            def run():
                STATE["busy"] = True
                try:
                    extract(STATE["paks"], lambda s: STATE.update(status=s))
                    STATE["status"] = "Ready."
                except Exception as e:
                    STATE["status"] = "Failed: %s" % e
                finally:
                    STATE["busy"] = False

            threading.Thread(target=run, daemon=True).start()
            return self._json({"started": True})

        if u.path == "/api/install":
            if not STATE["paks"]:
                return self._json({"error": "no game folder set"}, 400)
            try:
                dest = install(body["target"], body.get("values", {}),
                               lambda s: STATE.update(status=s))
                STATE["status"] = "Installed."
                return self._json({"installed": dest})
            except Exception as e:
                STATE["status"] = ""
                return self._json({"error": str(e)}, 400)

        if u.path == "/api/uninstall":
            try:
                return self._json({"removed": uninstall(body["target"])})
            except Exception as e:
                return self._json({"error": str(e)}, 400)

        return self._json({"error": "unknown endpoint"}, 404)


def free_port(start=8777):
    """First port in the range nobody else is sitting on."""
    for p in range(start, start + 40):
        with socket.socket() as s:
            try:
                s.bind(("127.0.0.1", p))
                return p
            except OSError:
                continue
    sys.exit("no free port")


def main():
    if not retoc_path():
        print("retoc isn't on your PATH.")
        print("Get it from https://github.com/trumank/retoc. Blamforge needs")
        print("it to read and write the game's containers.\n")

    game, paks = find_game(sys.argv[1] if len(sys.argv) > 1 else None)
    if game:
        STATE["game"], STATE["paks"] = game, paks
        print("game:", game)
    else:
        print("Couldn't find the game automatically; you can point at it in "
              "the browser.")

    port = free_port()
    url = "http://127.0.0.1:%d/app.html" % port
    print("Blamforge running at", url)
    print("Close this window when you're done.\n")

    srv = socketserver.ThreadingTCPServer(("127.0.0.1", port), Handler)
    srv.daemon_threads = True
    threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")


if __name__ == "__main__":
    main()
