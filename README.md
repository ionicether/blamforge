# Blamforge

Sliders for Halo: Campaign Evolved. Magazine sizes, energy weapon drain/heat, shield strength, shield recovery, health, health recovery. Things you'd otherwise be changing with a hex editor.

![Blamforge](docs/screenshot.png)

## What you need

**Python.** That's the only thing you have to install.

>Blamforge also needs (but downloads it itself) [retoc](https://github.com/trumank/retoc), which does the actual reading and writing of the game's containers. **You don't have to go and get it**. Blamforge offers to download it the first time you run it, tells you exactly what file it's fetching and from where, puts it in its own folder, and checks it runs before carrying on.

Blamforge itself is the offsets (which took a while to find) and a web UI to wrangle them with.

### Getting Python

**Windows.** Open PowerShell:

```
winget install --id Python.Python.3 --source winget --accept-package-agreements --accept-source-agreements
```

**Close PowerShell and open it again** afterwards, or it won't be found.

> If `winget` isn't recognized, your App Installer is out of date. Get Python from python.org instead and tick "Add Python to PATH" during the install.

> If typing `python` opens the Microsoft Store instead of running anything, that's Windows' app execution aliases getting in the way. Settings -> Apps -> Advanced app settings -> App execution aliases -> turn off the `python.exe` and `python3.exe` entries.

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

1. It looks for the game. If it can't find it, paste either the game folder or the `Paks` folder inside it. Steam and Game Pass keep things in different places and name the container differently, and it handles both. The top corner says which one it found.
2. First time only, it unpacks the game container to get at the tags. A minute or two. It keeps about a dozen files and bins the rest. Your install isn't modified, this only reads from it.
3. Pick something and drag the sliders. Each one shows what the value was before you touched it.
4. Install. That builds the mod and puts it in its own folder under `Content/Paks`.

Remove removes the associated mod it created and resets the interface to the default value for that selection.

Launch the game and enjoy. Blamforge doesn't need to be running.

## What's in it

|                    | Damage | Ammo | Battery | Heat | Fire rate | Spread |                                           |
| ------------------ | :----: | :--: | :-----: | :--: | :-------: | :----: | ----------------------------------------- |
| Assault rifle      |   ✓    |  ✓   |         |      |     ✓     |   ✓    |                                           |
| Battle rifle       |   ✓    |  ✓   |         |      |     ✓     |        |                                           |
| Magnum             |   ✓    |  ✓   |         |      |     ✓     |        |                                           |
| Rocket launcher    |   ✓    |  ✓   |         |      |           |        | damage is center and edge of the blast    |
| Shotgun            |   ✓    |  ✓   |         |      |           |        | damage falls off with distance            |
| SMG                |   ✓    |  ✓   |         |      |     ✓     |        |                                           |
| Sniper rifle       |   ✓    |  ✓   |         |      |           |        | damage falls off with distance            |
| Beam rifle         |   ✓    |      |    ✓    |  ✓   |           |        |                                           |
| Brute plasma rifle |   ✓    |      |    ✓    |  ✓   |     ✓     |        | fire rate ramps up, damage falls off      |
| Fuel rod cannon    |        |  ✓   |         |      |           |        | never found its damage                    |
| Needle rifle       |   ✓    |  ✓   |         |      |     ✓     |        |                                           |
| Needler            |   ✓    |  ✓   |         |      |     ✓     |        | fire rate ramps up                        |
| Plasma pistol      |   ✓    |      |    ✓    |  ✓   |           |        | charged shot has its own battery and heat |
| Plasma rifle       |   ✓    |      |    ✓    |  ✓   |     ✓     |        | fire rate ramps up, damage falls off      |
| Spiker             |   ✓    |  ✓   |         |      |     ✓     |        |                                           |
| Sentinel beam      |   ✓    |      |    ✓    |  ✓   |           |        |                                           |
| Grenades           |        |  ✓   |         |      |           |        | how many of each type you can carry       |

Plus the Chief's shield and health recovery timing and rate.

**Ammo** is magazine size, the reserve you can carry, and how much comes with a weapon placed in the level. 
**Battery** is what each shot drains, on the weapons that have one instead of a magazine. 
**Heat** is how fast it overheats.


## About rate of fire

The AR's rate of fire reads 12 in the tag. The devs say (in [their blurb](https://store.steampowered.com/news/app/2806050/view/669499588924673054) where they talk about how they fixed it in the latest update) the intended rate is 10 rounds a second. Higher is faster, I checked by setting both 1 and 48. What the number measures, not a clue at this time.
It will probably take someone smarter than me to figure it out.

## Health and shield amounts

You can't change them. Three fields in the tag look like they should do it and none of them work, because the engine rebuilds the damage data when the tag loads. The recharge sliders are fine.

## Damage

Some weapons do less damage the further away you are, so those get two sliders, one for point blank and one for range. The rest do the same damage at any distance and get one.

For a sense of scale, a magnum round is 23, an assault rifle round is 8.5, and a rocket is 240 at the center of the blast.

## Co-op

Not a stinkin' clue. Nobody has tried any of this in co-op and I don't know whether it's host file driven or not. If you try it, please reach out to me.

## Cleansing

Each mod is its own folder under `Content/Paks`, named `bf_` and then whatever you changed, with a `blamforge.txt` (don't delete this file, cleanse.py requires it) in it saying what was changed and when. The Remove button deletes the folder, and so does deleting it yourself.

If you've binned Blamforge and still have mods installed:

Windows: `python cleanse.py`

Linux: `python3 cleanse.py`

That lists what's there. Add a name to remove one, or `--all` for everything. It clears the matching saved slider values too. It only touches folders with that text file in them, so nobody else's mods get caught up in it.

Close the game first. Windows won't let you delete files something else has open.

## Platforms

Written and tested on Linux. Steam and Game Pass are both handled, and it looks on every drive letter you've got rather than guessing.

Game Pass took a while to get right. It keeps the Paks folder a level deeper than Steam does and calls the container `pakchunk0-WinGDK.utoc` instead of `pakchunk0-Windows.utoc`, so it would find the folder and then not see the game in it. [NagatoZeta](https://next.nexusmods.com/profile/NagatoZeta) worked that out, sent the fix, and confirmed a mod installs and runs on it, none of which I could have done from here.

If something breaks somewhere else, say so.

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

[retoc](https://github.com/trumank/retoc) and [repak](https://github.com/trumank/repak) are [trumank's](https://github.com/trumank), and this doesn't work without them.

[blam-tags](https://github.com/camden-smallwood/blam-tags) by [Camden Smallwood](https://github.com/camden-smallwood). It reads the tag schema instead of making you hunt for offsets, and has definitions for this game. I used it to validate the shield and vitality offsets I couldn't figure out, which is how I worked out why they weren't doing anything.

The Chief recharge values were difficult to find, thankfully [Chance_25](https://www.nexusmods.com/profile/Chance255) set them in [Chief Shield and Health Recharge Overhaul](https://www.nexusmods.com/halocampaignevolved/mods/226)

[NagatoZeta](https://next.nexusmods.com/profile/NagatoZeta) for the Game Pass support, and [SkrappyIE](https://next.nexusmods.com/profile/SkrappyIE) and [SebSpy7IISaidWithThe7II](https://next.nexusmods.com/profile/SebSpy7IISaidWithThe7II) for reporting it in the first place.

## License

MIT
