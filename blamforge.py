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

import contextlib
import http.server
import json
import os
import platform
import re
import shutil
import socket
import socketserver
import struct
import subprocess
import sys
import tarfile
import tempfile
import threading
import time
import urllib.parse
import urllib.request
import webbrowser
import zipfile

APP = "blamforge"

HERE = os.path.dirname(os.path.abspath(__file__))


def need_retoc():
    """retoc's path, or a readable complaint.

    Everything checks for retoc at startup, but it could go missing between
    then and here, and subprocess raises something unhelpful when handed a
    None.
    """
    p = retoc_path()
    if not p:
        raise RuntimeError(
            "Can't find retoc any more. It was there when Blamforge started, "
            "so it's been moved or deleted since."
        )
    return p


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
# Steam and the Xbox app ship the same container under different names, so
# finding the game means checking for both. Thanks to NagatoZeta for working
# this out, the Game Pass one had me stuck.
CONTAINERS = (
    ("pakchunk0-Windows.utoc", "Steam"),
    ("pakchunk0-WinGDK.utoc", "Game Pass"),
)

# Pinned rather than "latest" so the download can't quietly become something
# else. Bump it when there's a reason to.
RETOC_VERSION = "v0.1.5"
RETOC_BASE = "https://github.com/trumank/retoc/releases/download/" + RETOC_VERSION + "/"
RETOC_ASSETS = {
    ("Linux", "x86_64"): "retoc_cli-x86_64-unknown-linux-gnu.tar.xz",
    ("Linux", "aarch64"): "retoc_cli-aarch64-unknown-linux-gnu.tar.xz",
    ("Windows", "AMD64"): "retoc_cli-x86_64-pc-windows-msvc.zip",
    ("Windows", "x86_64"): "retoc_cli-x86_64-pc-windows-msvc.zip",
}


def retoc_asset():
    """Which release file suits this machine, if we know."""
    return RETOC_ASSETS.get((platform.system(), platform.machine()))


def fetch_retoc(progress):
    """Download retoc and drop the binary next to this script.

    Deliberately not touching PATH. A running process keeps the PATH it
    started with, so installing there would need a restart, whereas a file
    in our own directory is found the moment it exists.
    """
    asset = retoc_asset()
    if not asset:
        raise RuntimeError(
            f"No prebuilt retoc for {platform.system()} {platform.machine()} that I know of. Grab one from {RETOC_BASE} "
            "and put it next to blamforge.py."
        )

    url = RETOC_BASE + asset
    progress("Downloading " + asset)

    scratch = tempfile.mkdtemp(prefix="retoc-", dir=HERE)
    try:
        archive = os.path.join(scratch, asset)
        try:
            with urllib.request.urlopen(url, timeout=60) as r, open(archive, "wb") as f:
                shutil.copyfileobj(r, f)
        except Exception as e:
            raise RuntimeError(f"Couldn't download it: {e}") from e

        progress("Unpacking")
        if asset.endswith(".zip"):
            with zipfile.ZipFile(archive) as z:
                z.extractall(scratch)
        else:
            with tarfile.open(archive) as t:
                t.extractall(scratch)

        # the binary sits in a subdirectory whose name changes between
        # releases, so go looking for it
        found = None
        for root, _, files in os.walk(scratch):
            for f in files:
                if f in ("retoc", "retoc.exe"):
                    found = os.path.join(root, f)
                    break
            if found:
                break
        if not found:
            raise RuntimeError("Downloaded it but there's no retoc inside")

        dest = os.path.join(HERE, os.path.basename(found))
        shutil.copy2(found, dest)
        os.chmod(dest, 0o755)

        # A file being there doesn't mean it runs. The linux builds link
        # against system glibc, so on an older distro this lands fine and
        # then dies with a linker error the first time it's used, halfway
        # through extracting the game. Better to find out now.
        progress("Checking it runs")
        try:
            r = subprocess.run(
                [dest, "--version"],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
        except OSError as e:
            os.remove(dest)
            raise RuntimeError(
                f"Downloaded it but it won't run on this system: {e}. Try a "
                f"different build from {RETOC_BASE}, or build it yourself."
            ) from e
        if r.returncode != 0:
            err = (r.stderr or r.stdout or "").strip().splitlines()
            os.remove(dest)
            raise RuntimeError(
                "Downloaded it but it won't run: {}. Try a different build "
                "from {}, or build it yourself.".format(
                    err[0] if err else "no output", RETOC_BASE
                )
            )

        return dest
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


# The .pak that has to sit next to a .utoc/.ucas or the engine won't mount the
# container. retoc doesn't produce one, so we copy an existing one.
#
# 339 is the size when the mount point is "/", which is what retoc-built
# containers want - they don't write a mount point of their own, so the pak's
# is what gets used. Mods that ship real asset paths instead of raw chunk
# overrides use "../../../" and come out at 347. Those aren't interchangeable
# with these, hence matching on the exact size rather than just any .pak.
PAK_SIZE = 339

# Where the Paks folder sits relative to whatever you point at. Steam puts
# Meteorite straight in the game folder; the Xbox app wraps it in another
# Content directory.
PAKS_SHAPES = [
    ("Meteorite", "Content", "Paks"),
    ("Content", "Meteorite", "Content", "Paks"),
    (),
]

LINUX_HINTS = [
    "~/.local/share/Steam/steamapps/common/Halo Campaign Evolved",
    "~/.steam/steam/steamapps/common/Halo Campaign Evolved",
]

# Tried under every drive letter that actually exists, rather than guessing
# at C, D and E and giving up. The Xbox app writes the game name with a
# hyphen because a colon isn't allowed in a path.
WINDOWS_HINTS = [
    "Program Files (x86)/Steam/steamapps/common/Halo Campaign Evolved",
    "Program Files/Steam/steamapps/common/Halo Campaign Evolved",
    "SteamLibrary/steamapps/common/Halo Campaign Evolved",
    "Games/Steam/steamapps/common/Halo Campaign Evolved",
    "XboxGames/Halo- Campaign Evolved",
    "XboxGames/Halo Campaign Evolved",
]


def drives():
    """Drive letters that exist. Empty on anything that isn't Windows."""
    if os.name != "nt":
        return []
    out = []
    for c in "CDEFGHIJKLMNOPQRSTUVWXYZ":
        if os.path.isdir(c + ":\\"):
            out.append(c + ":")
    return out


def game_hints():
    hints = [os.path.expanduser(p) for p in LINUX_HINTS]
    for d in drives():
        for p in WINDOWS_HINTS:
            hints.append(os.path.join(d + os.sep, *p.split("/")))
    return hints


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
    with open(js, encoding="utf-8") as f:
        src = f.read()
    src = src[src.index("{") : src.rindex("}") + 1]
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.DOTALL)
    src = re.sub(r"//.*", "", src)
    src = re.sub(r"(\w+):", r'"\1":', src)  # bare keys need quoting
    src = re.sub(r"0x([0-9a-fA-F]+)", lambda m: str(int(m.group(1), 16)), src)
    src = re.sub(r",(\s*[}\]])", r"\1", src)  # JSON hates trailing commas
    return json.loads(src)


REG = load_registry()
TARGETS = {t["id"]: t for t in REG["targets"]}


# --------------------------------------------------------------- game files


def find_game(given=None):
    """Work out where the game is and which edition it is.

    Takes either the game folder or the Paks folder itself, and copes with
    both the Steam and Xbox app layouts, which differ in where the Paks
    folder sits and in what the container is called.

    Returns (game folder, paks folder, container name, edition).
    """
    roots = [given] if given else game_hints()
    for raw in roots:
        if not raw:
            continue
        r = os.path.expanduser(raw)
        for shape in PAKS_SHAPES:
            cand = os.path.join(r, *shape) if shape else r
            for container, edition in CONTAINERS:
                if os.path.exists(os.path.join(cand, container)):
                    return r, cand, container, edition
    return None, None, None, None


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
            struct.pack_into("<H", b, off, round(v))
        else:
            struct.pack_into("<f", b, off, float(v))


def field_chunk(t, f):
    """Which chunk a field lives in.

    Most fields are in the target's own tag. Weapon damage isn't: it sits in
    a separate damage effect tag, three hops from the weapon, so those fields
    carry their own chunk id.
    """
    return f.get("chunk") or t["chunk"]


def load_chunks(t):
    """Every chunk this target touches, keyed by id."""
    out = {}
    for cid in {field_chunk(t, f) for f in t["fields"]}:
        p = os.path.join(CACHE, cid)
        if not os.path.exists(p):
            raise RuntimeError(
                f"tag {cid} isn't in the cache, try re-reading the game files"
            )
        with open(p, "rb") as f:
            out[cid] = bytearray(f.read())
    return out


def verify_all(bufs, t):
    """Same as verify, but across every chunk the target uses."""
    bad = []
    for f in t["fields"]:
        b = bufs[field_chunk(t, f)]
        if f["off"] + 4 > len(b):
            bad.append((f["key"], None, f["stock"]))
            continue
        got = read_field(b, f)
        ok = (
            got == f["stock"]
            if f["type"] == "u16"
            else abs(got - f["stock"]) <= max(1e-6, abs(f["stock"]) * 1e-4)
        )
        if not ok:
            bad.append((f["key"], got, f["stock"]))
    return bad


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
        ok = (
            got == f["stock"]
            if f["type"] == "u16"
            else abs(got - f["stock"]) <= max(1e-6, abs(f["stock"]) * 1e-4)
        )
        if not ok:
            bad.append((f["key"], got, f["stock"]))
    return bad


# ------------------------------------------------------------------ actions

STATE = {
    "game": None,
    "paks": None,
    "container": None,
    "edition": None,
    "status": "",
    "busy": False,
}


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

    missing = []
    for t in REG["targets"]:
        for cid in {f.get("chunk") or t.get("chunk") for f in t["fields"]}:
            if cid and not os.path.exists(os.path.join(CACHE, cid)):
                missing.append(t["name"])
                break
    if missing:
        if len(missing) > 3:
            what = f"{missing[0]} and {len(missing) - 1} others"
        else:
            what = ", ".join(missing)
        return False, "no tag cached for " + what

    for f in ("manifest.json", "stub.pak"):
        if not os.path.exists(os.path.join(CACHE, f)):
            return False, f + " missing from the cache"

    return True, ""


def cache_ok():
    return cache_state()[0]


def extract(paks, container, progress):
    """Unpack the container and keep the dozen chunks we can edit.

    retoc has no way to pull a single chunk, so this extracts all ~106,000
    of them, copies out what's in the registry, and throws the rest away.
    Wasteful for a minute, but it only happens once.
    """
    os.makedirs(CACHE, exist_ok=True)
    scratch = tempfile.mkdtemp(prefix="blamforge-", dir=HERE)
    out = os.path.join(scratch, "all")
    try:
        progress(
            "Unpacking the game container. This takes a minute or two "
            "and only happens once."
        )
        r = subprocess.run(
            [need_retoc(), "unpack-raw", os.path.join(paks, container), out],
            capture_output=True,
            text=True,
            check=False,
        )
        if r.returncode != 0:
            raise RuntimeError((r.stderr or "retoc failed").strip())

        chunks = os.path.join(out, "chunks")
        progress("Keeping the tags, discarding the rest.")
        wanted = set()
        for t in REG["targets"]:
            for f in t["fields"]:
                cid = f.get("chunk") or t.get("chunk")
                if cid:
                    wanted.add(cid)
        for cid in wanted:
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
            fh.write("extracted {}\n".format(time.strftime("%Y-%m-%d %H:%M")))
            fh.write("registry {}\n".format(REG.get("version", "?")))
            fh.write("build {}\n".format(REG.get("build", "?")))
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


NOTE = "blamforge.txt"
SETTINGS = os.path.join(HERE, "settings.json")


def load_settings():
    """What was installed last time, per target.

    Lives next to blamforge.py rather than in .cache so that re-reading the
    game files doesn't throw it away.
    """
    try:
        with open(SETTINGS, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def save_settings(target_id, values):
    d = load_settings()
    d[target_id] = dict(values)
    try:
        with open(SETTINGS, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=2)
    except OSError:
        pass  # not worth failing an install over


PREFIX = "bf_"


def mod_dirs(target_id):
    """Where this mod could be. New installs use the prefix; older ones
    didn't, and there's no reason to strand them."""
    return [
        os.path.join(STATE["paks"], PREFIX + target_id),
        os.path.join(STATE["paks"], target_id),
    ]


def mod_dir(target_id):
    """The one that's actually there, if any."""
    for d in mod_dirs(target_id):
        if os.path.isdir(d) and os.path.exists(os.path.join(d, NOTE)):
            return d
    return None


def write_note(dest, t, values, bufs):
    """Leave a plain text record in the mod folder.

    Mostly so that in six months you can look at a folder and know what's in
    it. cleanse.py only cares that the file exists, not what it says, so
    there's nothing here that has to parse.
    """
    lines = [
        "{} {}".format(APP, REG.get("version", "?")),
        t["name"],
        "installed {}".format(time.strftime("%Y-%m-%d %H:%M")),
        "game build {}".format(REG.get("build", "unknown")),
        "chunk {}".format(", ".join(sorted({field_chunk(t, f) for f in t["fields"]}))),
        "",
    ]
    rows = []
    for f in t["fields"]:
        now = read_field(bufs[field_chunk(t, f)], f)
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
            lines.append(f"{label:<{width}}  {was} -> {now}")
    else:
        lines.append("nothing changed from stock")

    lines += [
        "",
        "Delete this whole folder to put it back the way it was, or run",
        "cleanse.py to find and remove every folder with one of these in it.",
        "",
    ]
    with open(os.path.join(dest, NOTE), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def install(target_id, values, progress):
    t = TARGETS[target_id]
    bufs = load_chunks(t)

    bad = verify_all(bufs, t)
    if bad:
        raise RuntimeError(
            "The cached tag isn't stock: "
            + ", ".join("{} reads {}, expected {}".format(*x) for x in bad)
            + ". A mod may already be installed, or the game has updated."
        )

    for f in t["fields"]:
        if f["key"] in values:
            write_field(bufs[field_chunk(t, f)], f, values[f["key"]])

    name = t["id"]
    stem = f"zzz_{name}_P"
    scratch = tempfile.mkdtemp(prefix="blamforge-build-", dir=HERE)
    try:
        srcdir = os.path.join(scratch, "src")
        os.makedirs(os.path.join(srcdir, "chunks"))
        for cid, buf in bufs.items():
            with open(os.path.join(srcdir, "chunks", cid), "wb") as f:
                f.write(bytes(buf))
        shutil.copy2(
            os.path.join(CACHE, "manifest.json"), os.path.join(srcdir, "manifest.json")
        )

        dist = os.path.join(scratch, "dist")
        os.makedirs(dist)
        utoc = os.path.join(dist, stem + ".utoc")

        progress("Packing the mod.")
        r = subprocess.run(
            [need_retoc(), "pack-raw", srcdir, utoc],
            capture_output=True,
            text=True,
            check=False,
        )
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
            shutil.copy2(os.path.join(dist, stem + ext), os.path.join(dest, stem + ext))
        write_note(dest, t, values, bufs)
        save_settings(target_id, values)
        return dest
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def cleanse():
    """Take every Blamforge mod back out and forget the settings.

    Only folders with our own note file in them, so anyone else's mods are
    left where they are. cleanse.py is the standalone version and only
    removes the folders; this one is a full reset.
    """
    removed = []
    for t in REG["targets"]:
        d = mod_dir(t["id"])
        if d:
            shutil.rmtree(d, ignore_errors=True)
            removed.append(t["name"])
    # clears the saved values too, so this really is back to nothing. Export
    # a preset first if you want your setup back afterwards.
    with contextlib.suppress(OSError):
        os.remove(SETTINGS)
    return removed


def uninstall(target_id):
    d = mod_dir(TARGETS[target_id]["id"])
    if d:
        shutil.rmtree(d)
        s = load_settings()
        if s.pop(target_id, None) is not None:
            try:
                with open(SETTINGS, "w", encoding="utf-8") as f:
                    json.dump(s, f, indent=2)
            except OSError:
                pass
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

    def log_message(self, format, *args):
        pass  # the terminal is for our own output, not a request log

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
            return self._json(
                {
                    "registry": REG,
                    "game": STATE["game"],
                    "edition": STATE["edition"],
                    "ready": ok,
                    "stale": why,
                    "status": STATE["status"],
                    "busy": STATE["busy"],
                    "installed": installed_ids(),
                    "retoc": retoc_path() is not None,
                    "retoc_asset": retoc_asset(),
                    "retoc_url": RETOC_BASE,
                }
            )

        if u.path == "/api/saved":
            saved = load_settings()
            out = []
            for tid, vals in saved.items():
                t = TARGETS.get(tid)
                if not t:
                    continue
                changed = []
                for f in t["fields"]:
                    if f["key"] not in vals or f.get("derived"):
                        continue
                    v = vals[f["key"]]
                    same = (
                        v == f["stock"]
                        if f["type"] == "u16"
                        else abs(v - f["stock"]) <= max(1e-6, abs(f["stock"]) * 1e-4)
                    )
                    if not same:
                        changed.append(
                            {
                                "label": f.get("label", f["key"]),
                                "was": f["stock"],
                                "now": v,
                            }
                        )
                out.append({"id": tid, "name": t["name"], "changed": changed})
            return self._json({"saved": out, "raw": saved})

        if u.path == "/api/values":
            tid = urllib.parse.parse_qs(u.query).get("target", [""])[0]
            t = TARGETS.get(tid)
            if not t:
                return self._json({"error": "unknown target"}, 404)
            try:
                bufs = load_chunks(t)
            except RuntimeError as e:
                return self._json({"error": str(e)}, 404)
            bad = verify_all(bufs, t)
            saved = load_settings().get(tid, {})
            return self._json(
                {
                    "values": {
                        f["key"]: read_field(bufs[field_chunk(t, f)], f)
                        for f in t["fields"]
                    },
                    "saved": {
                        k: v
                        for k, v in saved.items()
                        if any(f["key"] == k for f in t["fields"])
                    },
                    "mismatch": [{"key": k, "got": g, "want": w} for k, g, w in bad],
                }
            )

        return super().do_GET()

    def do_POST(self):
        u = urllib.parse.urlparse(self.path)
        n = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(n) or "{}")

        if u.path == "/api/game":
            game, paks, container, edition = find_game(body.get("path"))
            if not game:
                return self._json(
                    {
                        "error": "No Halo: Campaign Evolved there. Look for the folder "
                        "containing Meteorite/Content/Paks."
                    },
                    400,
                )
            STATE["game"], STATE["paks"] = game, paks
            STATE["container"], STATE["edition"] = container, edition
            return self._json({"game": game, "edition": edition, "ready": cache_ok()})

        if u.path == "/api/cleanse":
            if not STATE["paks"]:
                return self._json({"error": "no game folder set"}, 400)
            return self._json({"removed": cleanse()})

        if u.path == "/api/settings":
            d = body.get("settings")
            if not isinstance(d, dict):
                return self._json({"error": "that file isn't a settings file"}, 400)
            known = {t["id"] for t in REG["targets"]}
            kept = {k: v for k, v in d.items() if k in known}
            try:
                with open(SETTINGS, "w", encoding="utf-8") as f:
                    json.dump(kept, f, indent=2)
            except OSError as e:
                return self._json({"error": str(e)}, 500)
            return self._json(
                {"loaded": sorted(kept), "skipped": sorted(set(d) - set(kept))}
            )

        if u.path == "/api/install_saved":
            if not STATE["paks"]:
                return self._json({"error": "no game folder set"}, 400)
            if STATE["busy"]:
                return self._json({"error": "already working"}, 409)

            saved = load_settings()

            def run():
                STATE["busy"] = True
                done, failed = [], []
                try:
                    for tid, vals in saved.items():
                        if tid not in TARGETS:
                            continue
                        STATE["status"] = "Installing " + TARGETS[tid]["name"]
                        try:
                            install(tid, vals, lambda s: None)
                            done.append(TARGETS[tid]["name"])
                        except Exception as e:  # noqa: BLE001 - one bad
                            # target shouldn't stop the rest installing
                            failed.append(f"{TARGETS[tid]['name']} ({e})")
                    STATE["status"] = f"Installed {len(done)}."
                    if failed:
                        STATE["status"] += " Didn't manage " + ", ".join(failed)
                finally:
                    STATE["busy"] = False

            threading.Thread(target=run, daemon=True).start()
            return self._json({"started": True})

        if u.path == "/api/get_retoc":
            if retoc_path():
                return self._json({"already": True})
            if STATE["busy"]:
                return self._json({"error": "already working"}, 409)

            def run():
                STATE["busy"] = True
                try:
                    p = fetch_retoc(lambda s: STATE.update(status=s))
                    STATE["status"] = "Got it: " + os.path.basename(p)
                except Exception as e:  # noqa: BLE001 - a thread that dies
                    # silently leaves the page waiting forever
                    STATE["status"] = f"Failed: {e}"
                finally:
                    STATE["busy"] = False

            threading.Thread(target=run, daemon=True).start()
            return self._json({"started": True})

        if u.path == "/api/extract":
            if not STATE["paks"]:
                return self._json({"error": "no game folder set"}, 400)
            if STATE["busy"]:
                return self._json({"error": "already working"}, 409)

            def run():
                STATE["busy"] = True
                try:
                    extract(
                        STATE["paks"],
                        STATE["container"],
                        lambda s: STATE.update(status=s),
                    )
                    STATE["status"] = "Ready."
                except Exception as e:  # noqa: BLE001 - same, this runs in a
                    # thread and the only way to report is the status line
                    STATE["status"] = f"Failed: {e}"
                finally:
                    STATE["busy"] = False

            threading.Thread(target=run, daemon=True).start()
            return self._json({"started": True})

        if u.path == "/api/install":
            if not STATE["paks"]:
                return self._json({"error": "no game folder set"}, 400)
            try:
                dest = install(
                    body["target"],
                    body.get("values", {}),
                    lambda s: STATE.update(status=s),
                )
                STATE["status"] = "Installed."
                return self._json({"installed": dest})
            except Exception as e:  # noqa: BLE001 - turn any failure into
                # something the page can show rather than a dead request
                STATE["status"] = ""
                return self._json({"error": str(e)}, 400)

        if u.path == "/api/uninstall":
            try:
                return self._json({"removed": uninstall(body["target"])})
            except Exception as e:  # noqa: BLE001 - same
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

    game, paks, container, edition = find_game(
        sys.argv[1] if len(sys.argv) > 1 else None
    )
    if game:
        STATE["game"], STATE["paks"] = game, paks
        STATE["container"], STATE["edition"] = container, edition
        print("game:", game, f"({edition})")
    else:
        print(
            "Couldn't find the game automatically; you can point at it in the browser."
        )

    port = free_port()
    url = f"http://127.0.0.1:{port}/app.html"
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
