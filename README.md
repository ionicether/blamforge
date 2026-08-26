# halo-ce-2026-tags

Notes and a script for editing gameplay values in Halo: Campaign Evolved.

Spent today working out where the numbers live. Got the assault rifle magazine
changed and it works in game, so the approach is sound. Writing it down before
I forget how any of it fits together.

## what's going on

The game is UE5 but the gameplay data is still Blam tags. Actual `blam` magic
bytes at 0x3C, `weap`/`char`/`hlmt` group fourccs at 0x30 (stored backwards, so
they show up as `paew` etc in a hex dump). Those tags are sitting inside
Unreal's IoStore containers.

Values are just ints and floats at fixed offsets once you've got the tag out.
The whole problem is finding the offsets.

## what i've got so far

Working and tested in game:

- assault rifle: magazine, reserve, starting ammo, RPM, spread
- SMG: magazine, reserve, starting ammo
- master chief: shields, health, recharge delays and times

Offsets look right but haven't played it:

- sentinel beam: battery drain, heat per shot

All in `offsets.json`. `python3 patch.py --list` prints them.

## getting a tag out

```
retoc unpack-raw pakchunk0-Windows.utoc out/
```

Two things about this. Don't extract into /tmp. Mine's a tmpfs and it filled
up silently, gave me a partial extraction, and I spent an hour convinced half
the game's tags didn't exist. Second, it's ~106,000 files, so put it somewhere
with a few GB spare.

Files come out named by chunk id with no extension. To find one, grep by
content:

```
cd out/chunks
grep -l spartans *
```

or just take the id out of `offsets.json`, they're listed there.

## editing

```
python3 patch.py out/chunks/422244d93c8d5f7300000002 --show
python3 patch.py out/chunks/422244d93c8d5f7300000002 ar.tag --set magazine=90 --set total_max=900
```

It checks every known field against the stock value before writing anything.
If they don't match it bails, which catches you patching an already-patched
file, or the game having updated.

Some fields are derived and it works them out for you. The ammo block has a
reserve count that has to equal ceiling minus magazine or the game desyncs;
found that out by setting them independently and getting a weapon that ate its
own ammo.

## putting it back

```
mkdir -p mod/chunks
cp ar.tag mod/chunks/422244d93c8d5f7300000002
cp out/manifest.json mod/
retoc pack-raw mod dist/zzz_ar_P.utoc
```

That gives you a .utoc and .ucas. The engine also wants a .pak next to them.
retoc doesn't make one, but every mod ships an identical 339 byte stub, so copy
one from an existing mod folder and rename it to match.

Then all three go in their own folder under `Content/Paks/`. The `_P` suffix is
what marks it as a patch container. Delete the folder to undo.

## how i found the offsets

Diffing. The tags carry their own field names as strings:

```
strings -a -t d chunk | grep -i magazine
```

which tells you what's in there but not where. For that, get two versions of
the same tag (a stock one and a modded one) and diff:

```
cmp -l stock.tag modded.tag
```

The differing bytes are the values. Read four bytes at each offset as a float
and see if the number means anything.

The AR came from an existing community mod. Took maybe an hour. The Chief
shield values came from a shield mod someone had already made, and that was
about ten minutes, way faster than trying to find them cold.

## todo

- rest of the weapons. there's a structural fingerprint for the magazine block
  (five u16s where inventory == total - magazine) so a scanner should find them
- plasma weapons don't have magazines, they're battery like the sentinel beam.
  different fields
- some kind of UI. the CLI is fine for me but nobody else is going to use this
- work out if the offsets survive a game patch

## things that didn't work

Spent a while trying to get at damage resistance and the difficulty skulls.
They're not in the tags at all. That stuff lives in UE5-side code and you'd
need UE4SS to touch it. Also chased Flood weapon spawns through style tags,
character tags and squad templates and never found where they're actually
assigned.

Also: cargo needs `--locked` when building retoc, otherwise it resolves a
dependency to a version that doesn't build.

## note

Offsets only, no game files in here. Bring your own.
