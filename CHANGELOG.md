# Changelog

Versions here are Blamforge's own. The game build these were verified against
is separate and lives in `registry.json` under `build`. That's the one that
decides whether any of this works.

## 0.4.0

Everything in here came out of using 0.3 for an afternoon.

- Slider ranges scale with stock now. Sniper holds 4 rounds and the track ran
  to 600. You could not land on 8.
- Reload follows the magazine. Set an 80 round mag, forget the reload, get a
  gun that fires 80 and loads 4. Did that twice.
- Not the shotgun though, it loads one shell at a time. Locked.
- Mod folders get a `blamforge.txt` saying what changed. Six months from now
  a folder called `bf_sniper_rifle` full of hex-named containers might not be as clear.
- `uninstall.py`. Finds those folders and deletes them, ignores everything
  else.
- Sentinel beam confirmed. Battery drain works. Heat settings work.
- Starting ammo goes red above the reserve ceiling. Still lets you do it. No
  idea what the game does with a weapon that starts with more ammo than it
  can hold, probably clamps it, haven't checked.
- Mod folders are called `bf_something` now instead of just `something`, so
  it's obvious which ones are mine when you're looking at Content/Paks.
- Blamforge will use a retoc sitting next to it if there isn't one on PATH.
  The readme has been telling people that works for a while. It did not.
- Setup instructions actually cover Windows now. `winget` for Python, the
  PowerShell one-liner for retoc, both of which sort out PATH themselves. Also
  noted that the command is `python` and not `python3` over there, which the
  docs had wrong everywhere.
- This file.

### Fixed

- Assault rifle was pointing at the wrong tag. There are two. I picked the
  one from a mod file and called it stock without checking the actual game.
  It verified. It installed. It did nothing. Fixed.
- Dropped the field at 0x0B53B. Had it down as 4.0. It's 0.04. I never read
  the byte, I just assumed it matched its neighbour, and every Chief tag
  failed verification because of it. Also it doesn't change between stock and
  modded so it's probably not even a delay. Gone.

## 0.3.0

Rewrote the front end. Local server and a browser page instead of the
command line, so there's no shuffling files between a terminal, a downloads
folder and the game directory.

- Run `blamforge.py`, browser opens, sliders. Finds the game itself, unpacks
  what it needs, installs straight into `Content/Paks`.
- Install and Remove buttons. Each mod is its own folder, so removing one is
  deleting a folder.
- Derived fields (the ammo reserve count) show read-only and update as you
  drag the thing they depend on.
- `offsets.json` became `registry.json`, with labels and ranges for the UI.
- Dropped `patch.py`, `mkmod.py` and `findmags.py`. The first two are what
  the app does now. `findmags.py` needs a full extraction that the app no
  longer keeps around, so it'll come back when it works again.

## 0.2.0

- Ten more weapons: battle rifle, DMR, spike rifle, shotgun, needler, sniper
  rifle, rocket launcher, grenade launcher, fuel rod cannon, concussion
  rifle. Magazine, reserve and starting ammo on each.
- `findmags.py`, which finds magazine blocks by their shape rather than by
  known offsets. Five u16s where inventory equals total minus magazine.
- `mkmod.py` builds an installable mod. Packs the container and sorts out
  the `.pak`, which retoc won't generate but the engine insists on. Copies
  an existing one, matching on size so it picks up the right sort.

## 0.1.0

First one that worked.

- `offsets.json`, four targets.
- `patch.py`. Checks the stock values before writing so it fails loudly
  instead of corrupting something.
- Ammo reserve count has to equal ceiling minus magazine or the weapon eats
  its own ammo. Took an embarrassing amount of time to work that out.
