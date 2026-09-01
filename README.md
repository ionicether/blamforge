# Blamforge

Sliders for Halo: Campaign Evolved. Magazine sizes, shield strength, how fast
shields come back, sentinel beam battery.

```
python3 blamforge.py
```

Browser opens. Pick something, drag a slider, hit Install.

This replaces the command line scripts that were in here before. Those worked
but meant shuffling files between a terminal, a downloads folder and the game
directory, which was tedious enough that I stopped using my own tool.

## what's in it

Tested in game:

- master chief: shields, health, recharge delays and times
- assault rifle: magazine, reserve, starting ammo, RPM, spread
- SMG: magazine, reserve, starting ammo

Offsets check out, haven't played them:

- sentinel beam: battery drain, heat
- battle rifle, DMR, spike rifle, shotgun, needler, sniper rifle, rocket
  launcher, grenade launcher, fuel rod cannon, concussion rifle: magazine,
  reserve, starting ammo

No plasma weapons. They run on a battery rather than a magazine, same as the
sentinel beam, and I haven't gone after those fields yet.

## what you need

Python 3.8 or newer and [retoc](https://github.com/trumank/retoc) on your PATH.
retoc does the actual container reading and writing, this is a front end on it.

Prebuilt binaries are on retoc's releases page. Building works too but use
`--locked`:

```
git clone https://github.com/trumank/retoc && cd retoc
git checkout v0.1.5
cargo build --release --locked
```

Without that flag cargo pulls a newer version of a dependency and the build
fails.

Run `blamforge.py` and it should find your Steam install. If not it asks.

First launch unpacks the game container to get the tags out. Minute or two,
only happens once. It reads from your install and writes only into new folders
under Content/Paks.

## how it works

Gameplay values live in Blam tags packed inside Unreal IoStore containers.
`blam` magic at 0x3C, group fourcc at 0x30 stored backwards. Once you've got a
tag out the values are ints and floats at fixed offsets, so changing them is
easy. Finding the offset is the work.

`registry.json` holds every offset along with the value it has in a clean
install. Before writing anything Blamforge checks that value matches. If it
doesn't, either there's a mod installed already, or the file's been patched, or
the game updated and everything shifted. Either way it stops.

Every mod gets its own folder under Content/Paks. Remove deletes the folder.

## adding things

Tags carry their field names as plain strings:

```
strings -a -t d chunk | grep -i magazine
```

That tells you what's in the tag, not where. For that, diff two versions of the
same tag and look at the bytes that differ:

```
cmp -l stock.tag modded.tag
```

Read four bytes at each offset as a float and see if the number means anything.
60 next to 600 is a magazine and reserve. Diffing an existing mod is much
faster than working blind, the Chief shield values came out of a community mod
in about ten minutes.

Add an entry to `registry.json` and it turns up in the sidebar.

## known rough edges

The slider ranges are the same for every weapon, which is wrong. A sniper rifle
holds four rounds and its slider goes to 600. Works, but you can't land on
anything useful.

Rounds per reload is editable and unlinked, so if you set a big magazine you
have to remember to raise it too or the gun reloads a quarter of a clip.

## limits

Offsets are for build 2026.08.11.1121610. A game update will move them and it'll
refuse to patch rather than break anything.

Damage resistance, difficulty skulls and anything else in player traits are
UE5-side, not in the tags at all. That needs
[UE4SS](https://github.com/UE4SS-RE/RE-UE4SS).

Extracting containers yourself: don't do it into /tmp. Mine's a tmpfs, it
filled up and truncated silently, and I spent an evening sure a tag wasn't in
the game.

## note

Offsets in here, no game data. Bring your own copy.

Server binds to localhost and makes no outbound requests.

retoc is [trumank's](https://github.com/trumank). MIT licensed.
