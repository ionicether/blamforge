# Changelog

Versions here are Blamforge's own. The game build these were verified against
is separate and lives in `registry.json` under `build`. That's the one that
decides whether any of this works.

## 0.6.0

Rate of fire on eight more weapons. SMG, battle rifle, spiker, needle rifle, magnum, needler, plasma rifle, brute plasma rifle.

Three of them ramp (needler, plasma rifle, brute plasma rifle), so those get two sliders instead of one.

Single shot weapons don't get one. 

Added grenade count

The text file in each mod folder was saying 0.4.0 no matter what version you were on. It reads the real one now.

uninstall.py is cleanse.py now.

## 0.5.2

Shield strength and health don't do anything. The value writes fine, the stock
check passes, and you still die at exactly the same rate. Damage seems to come
off as a percentage rather than a flat number, so doubling your shield also
doubles what each hit takes and it cancels out.

Left the sliders in with a note saying so, since the offsets are right and
someone may work out what they're for. The four recharge fields underneath
them do work.

## 0.5.1

The DMR isn't in this game. Neither is the spartan laser, the focus rifle,
the plasma launcher, the concussion rifle or the grenade launcher. All six
have tags sitting in the game files with perfectly reasonable data in them,
which is why they were in 0.5.0. I hadn't played the bonus missions and
couldn't rule out that they turned up somewhere I hadn't been. Halo Studios
publish the weapon list. None of them are on it. Gone.

While checking that against the official list I found three that should have
been in and weren't: the magnum, the needle rifle and the brute plasma rifle.

The brute one is a separate tag from the plasma rifle, red, and there are two
chunks both calling themselves plasma_rifle. The one that references
plasma_rifle_red assets is the brute. I had the wrong one of the two in as the
plain plasma rifle, so anyone who edited a plasma rifle in 0.5.0 was editing
the red one and wondering why nothing happened.

Also:

- Spike rifle is called the Spiker.
- Battery weapons had two drain sliders, one the tag calls CAMPAIGN and one
  it doesn't. This game is campaign and co-op only so I don't know what reads
  the second one. It's one slider now that writes both, which sidesteps the
  question. Plasma pistol goes from six sliders to four.
- The energy sword is the last thing on the official list that isn't in here.
  It has neither a magazine nor a battery, so there may be nothing to change.

## 0.5.0

Covenant weapons. Plasma rifle, plasma pistol, plasma launcher, beam rifle,
focus rifle, spartan laser. They don't have magazines, they spend a fraction
of the battery per shot like the sentinel beam, so it's battery per shot and
heat per shot instead of ammo.

Plasma pistol gets six sliders because it has two triggers and each one is its
own barrel with its own values.

None of them have been played yet.

Focus rifle has two tags, same as the assault rifle did. Went with the one
whose asset paths are all focus rifle and left a note in the app pointing at
the other.

Other things:

- Retoc downloads itself if you don't have it. Says what it's fetching first,
  puts it next to blamforge.py rather than on PATH, and runs it once to check
  it works. The linux builds link against system glibc, so on an old distro it
  lands fine and then dies halfway through extracting the game. Better to find
  out at the download.
- It remembers what you installed. Saved on install, not while you're
  dragging. Reset goes back to stock, Remove forgets it.
- Help text on every field. Most of them had none.
- Battle rifle magazine steps in threes. Three round bursts.
- AR and BR go red past 99. The counter on the side of the gun is two digits,
  so 123 rounds shows as 23. The ammo is really there.
- Cache tells you what's missing instead of dumping you back at setup.

### Fixed

- "Starting ammo" is how much ammo a weapon or ammo pack comes with when it's
  placed in the level. Not what you start a level holding, and not what drops
  off an enemy. Renamed. I took the name from the tag calling it "total
  initial" and never checked, and it took someone noticing the needler behaved
  differently from the assault rifle to work out what it really is.

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
