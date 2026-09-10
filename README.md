# Blamforge

Sliders for Halo: Campaign Evolved. Magazine sizes, energy weapon drain/heat, shield strength, shield recovery, health, health recovery. Things you'd otherwise be changing with a hex editor.

![Blamforge](docs/screenshot.png)

## What you need

**Python.** That's the only thing you have to install.

Blamforge also needs (and automatically downloads) [retoc](https://github.com/trumank/retoc), which does the actual reading and writing of the game's containers. Blamforge offers to download it the first time you run it. It tells you exactly what file it's fetching and from where, puts it in its own folder, and checks it runs before carrying on.

Blamforge itself is the offsets (which took a while to find) and a web UI to wrangle them with.

### Getting Python

**Windows.** Open PowerShell:

```
winget install --id Python.Python.3 --source winget --accept-package-agreements --accept-source-agreements
```

**Close PowerShell and open it again** afterwards, or it won't be found.

>If `winget` isn't recognised, your App Installer is out of date. Get Python from python.org instead and tick "Add Python to PATH" during the install.

>If typing `python` opens the Microsoft Store instead of running anything, that's Windows' app execution aliases getting in the way. Settings -> Apps -> Advanced app settings -> App execution aliases -> turn off the `python.exe` and `python3.exe` entries.

**Linux.** Usually already there. Check:

```
python3 --version
```

If that errors, install it with whatever your distro uses. `sudo pacman -S python` on Arch, `sudo apt install python3` on Debian or Ubuntu, `sudo dnf install python3` on Fedora.

## Running it

Grab the latest zip from the [releases page](https://github.com/ionicether/blamforge/releases) or [NexusMods](https://www.nexusmods.com/halocampaignevolved/mods/322) and unzip it wherever you like.

Then open a terminal in the folder that contains blamforge.py. On Windows, right-click the folder and pick "Open in Terminal", or shift-right-click and "Open PowerShell window here" if you're on 10. On Linux most file managers have "Open Terminal Here" in the right-click menu, or just `cd` to it.

Windows: `python blamforge.py`

Linux: `python3 blamforge.py`

A browser tab opens, then...

1. It looks for your Steam install. If it can't find it, paste the folder that has `Meteorite/Content/Paks` in it.
2. First time only, it unpacks the game container to get at the tags. A minute or two. It keeps about a dozen files and bins the rest. Your install isn't modified, this only reads from it.
3. Pick something and drag the sliders. Each one shows what the value was before you touched it.
4. Install. That builds the mod and puts it in its own folder under `Content/Paks`.

Remove removes the associated mod it created and resets the interface to the default value for that selection.

Launch the game and enjoy. Blamforge doesn't need to be running.

## What's in it

| | | |
|---|---|---|
| Master Chief | recharge delay and time | tested |
| Master Chief | shield strength, health | value changes, no effect in game |
| Assault rifle | mag, reserve, set-dressing pickup ammo, RPM, spread | tested |
| SMG | mag, reserve, set-dressing pickup ammo, rate of fire | tested |
| Sentinel beam | battery drain, heat | tested |
| BR, magnum, needle rifle, needler, spiker | mag, reserve, set-dressing pickup ammo, rate of fire | offsets check out, haven't played them |
| Shotgun, sniper, rockets, fuel rod | mag, reserve, set-dressing pickup ammo | same |
| Plasma rifle, brute plasma rifle | battery per shot, heat per shot, rate of fire | same |
| Plasma pistol, beam rifle | battery per shot, heat per shot | same |
| Grenades | how many of each you can carry | same |

Battery weapons have no magazine. A shot costs a fraction of the battery, and stock values work out to somewhere between 20 shots for the beam rifle and 770 for the sentinel beam. The plasma pistol has two sets because it has two triggers.

Still missing: energy sword, which has neither a magazine nor a battery, so there may not be anything to change.

>There are tags in the game files for weapons that aren't in the campaign (because apparently they worked off of a build of Halo: Reach) at all, like a DMR, a spartan laser, and a focus rifle. I had six of them in here because they show up in the game data and I hadn't played the bonus missions, so I couldn't say for certain they weren't tucked away somewhere. They're not. Halo Studios publish the weapon list and none of them are on it.

## About rate of fire

The AR's rate of fire reads 12 in the tag. The devs say (in [their blurb](https://store.steampowered.com/news/app/2806050/view/669499588924673054) where they talk about how they fixed it in the latest update) the intended rate is 10 rounds a second. Higher is faster, I checked by setting both 1 and 48. What the number measures, not a clue at this time. 
It will probably take someone smarter than me to figure it out.

## Co-op

Not a stinkin' clue. Nobody has tried any of this in co-op and I don't know whether it's host file driven or not. If you try it, please reach out to me.

## Cleansing

Each mod is its own folder under `Content/Paks`, named `bf_` and then whatever you changed, with a `blamforge.txt` (don't delete this file, cleanse.py requires it) in it saying what was changed and when. The Remove button deletes the folder, and so does deleting it yourself.

If you've binned Blamforge and still have mods installed:

Windows: `python cleanse.py`

Linux: `python3 cleanse.py`

That lists what's there. Add a name to remove one, or `--all` for everything. It only touches folders with that text file in them, so nobody else's mods get caught up in it.

Close the game first. Windows won't let you delete files something else has open.

## Platforms

Written and tested on Linux. It should run anywhere python and retoc do, and it looks in the usual Windows/Linux Steam locations, but I've only ever used it on Linux myself. If something breaks elsewhere, say so.

## How it works, roughly

Gameplay values live in Blam engine tags packed inside Unreal's IoStore containers. Once a tag's out, the numbers are ints and floats at fixed offsets. `registry.json` is a list of those offsets and the value each one holds in a clean install, and Blamforge checks that value matches before it writes anything. If it doesn't, you've got a mod installed already, or you've patched the file before, or the game updated and everything moved.

Finding new offsets is written up in CONTRIBUTING.md.

## Potential hazards

Offsets were checked against build 2026.08.11.1121610. I cannot promis it will work beyond that.

A fair bit isn't reachable from tags at all. Damage resistance, the difficulty skulls, anything to do with player traits. That stuff lives in Unreal-side code and, as far as I'm aware, no amount of tag editing gets near it. [UE4SS](https://github.com/UE4SS-RE/RE-UE4SS) is the tool for that, not this one. Checkout NexusMods for UE4SS mods.

Linux users - You prob know better, but I didn't think about this at the time. If you go extracting containers yourself, don't do it into `/tmp`. On a lot of setups that's a RAM disk, and pakchunk0 is 106,000 files. It'll fill up and truncate silently, and you'll spend an evening convinced the file you're looking for doesn't exist. Ask me how I know.

## Files

Offsets, not game data. Bring your own copy of the game. I cannot upload the game data. That's a 'tsk tsk'

## Privacy

Server binds to a free port on `127.0.0.1` and makes no outbound requests. Nothing leaves your machine.

## Version

See CHANGELOG.md. The version in `registry.json` is Blamforge's own. The `build` field next to it is the game build the offsets came from.

## Thanks

retoc and repak are [trumank's](https://github.com/trumank), and this doesn't work without them.

The Chief recharge values were difficult to find, thankfully [Chance_25](https://www.nexusmods.com/profile/Chance255) set them in [Chief Shield and Health Recharge Overhaul](https://www.nexusmods.com/halocampaignevolved/mods/226)

MIT licensed.
