# halo-ce-2026-tags

Scripts for editing gameplay values in Halo: Campaign Evolved. Magazine sizes,
shield strength, recharge timing, that sort of thing.

## what's mapped

Tested in game:

- assault rifle: magazine, reserve, starting ammo, RPM, spread
- SMG: magazine, reserve, starting ammo
- master chief: shields, health, recharge delays and times

Offsets check out but I haven't played them:

- sentinel beam: battery drain, heat per shot
- battle rifle, DMR, spike rifle, shotgun, needler, sniper rifle, rocket
  launcher, grenade launcher, fuel rod cannon, concussion rifle: magazine,
  reserve, starting ammo

`python3 patch.py --list` prints the lot with offsets.

Not done: plasma weapons, energy sword, gravity hammer. Those have no magazine
block because they run off a battery like the sentinel beam. Different fields,
haven't looked yet.

## what's going on

UE5 game, but the gameplay data is still Blam tags. `blam` magic at 0x3C, group
fourcc at 0x30 stored backwards so `weap` shows up as `paew`. Those tags are
packed inside Unreal's IoStore containers.

Once a tag's out, the values are ints and floats at fixed offsets and changing
them is trivial. Working out which offset is the whole job.

## getting the tags out

```
retoc unpack-raw pakchunk0-Windows.utoc out/
```

Don't send that to /tmp. Mine's a tmpfs, it filled up, and I got a partial
extraction with no error. Spent an hour convinced the Chief's model tag wasn't
in the game before I noticed the file count was wrong. It's about 106,000 files
so give it somewhere with a few GB.

Chunks come out named by id with no extension. Ids are in `offsets.json`, or
grep for one:

```
cd out/chunks
grep -l spartans *
```

## changing values

```
python3 patch.py out/chunks/422244d93c8d5f7300000002 --show
python3 patch.py out/chunks/422244d93c8d5f7300000002 ar.tag --set magazine=90 --set total_max=900
```

Every known field gets checked against its stock value before anything is
written. If they don't line up it stops, which catches an already-patched file
or a game update having moved things.

Some fields are worked out for you. The ammo block has a reserve count that has
to equal ceiling minus magazine, and if it drifts the weapon starts eating its
own ammo. Rounds-per-reload follows the magazine too, except on the shotgun,
which loads one shell at a time and breaks if you change it.

## building a mod

```
python3 mkmod.py ar.tag --chunk 422244d93c8d5f7300000002 --install "/path/to/Halo Campaign Evolved"
```

Packs the container, sorts out the .pak, drops all three files into their own
folder under Content/Paks. `rm -rf` that folder to undo.

The .pak thing is annoying. The engine won't mount a container without one
sitting next to the .utoc and .ucas, and retoc doesn't generate them. But every
mod ships one that's byte-identical, 339 bytes, so mkmod just finds one and
copies it. Checked several and they're all the same file.

## finding more

Tags carry their own field names:

```
strings -a -t d chunk | grep -i magazine
```

That tells you the tag has a field called "rounds loaded maximum". It does not
tell you where the number is. Names live in a schema block near the front,
values live somewhere else entirely.

Diffing is how you bridge that. Two versions of the same tag, stock and modded,
and the differing bytes are the values:

```
cmp -l stock.tag modded.tag
```

Read four bytes at each spot as a float and see if it means anything. 60 next
to 600 is a magazine and its reserve. Two floats that come out as exactly 3.50
and 5.00 degrees once converted from radians are a spread.

If someone's already modded the thing you want, diff their file. The Chief
shield values took ten minutes that way. I'd spent hours getting nowhere on the
same problem beforehand.

`findmags.py` does the boring part for the magazine block, which has a
recognisable shape (five u16s where inventory equals total minus magazine):

```
python3 findmags.py out/chunks
```

First version of that told me the sniper rifle held 1024 rounds. Turns out that
arithmetic holds by accident in a few other structs, so there are extra checks
in there now.

## todo

- plasma weapons, they're battery-based like the sentinel beam
- ammo pickups. there are equipment tags for assault rifle ammo, shotgun ammo
  and rockets, and the amount they give you should be in there
- some kind of UI. the CLI is fine for me, nobody else is going to touch it
- find out whether the offsets survive a game patch

## didn't work

Wanted damage resistance and the difficulty skulls. Not in the tags at all,
that's UE5-side and you'd need UE4SS.

Also chased Flood weapon spawns through style tags, character tags and squad
templates. Squad templates do have loadouts with per-weapon spawn chances, and
zeroing them changes nothing, so encounters must get their weapons somewhere
else. Gave up on it.

## note

cargo needs `--locked` when building retoc or a dependency resolves to a
version that doesn't compile.

Offsets only in here, no game files.
