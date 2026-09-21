# Contributing

Offsets. That's what's useful here.

18 targets so far. The energy sword isn't in here, grenades only have a carry count, and vehicles haven't been touched at all.

## Start with the manifest

When retoc unpacks a container it writes a `manifest.json` next to the chunks. Open it.

It maps every chunk id to a path. 114,281 entries, 24,000 of them blam tags:

```
6d78b216566666fe00000002 -> .../Tags/objects/weapons/Pistol/magnum/projectiles/magnum_bullet-damage_effect.ubulk
```

So "which chunk is the magnum's damage" is a dictionary lookup, not a search:

```python
import json
cp = json.load(open('manifest.json'))['chunk_paths']
for cid, p in cp.items():
    if '/Tags/' in p and 'magnum' in p:
        print(cid, p.split('/Tags/')[1])
```

## Then blam-tags

[blam-tags](https://github.com/camden-smallwood/blam-tags) reads the tag schema and prints fields by name, and it has definitions for this game specifically.

```
blam-tag-shell --game haloce_evolved inspect --full <chunk> --filter damage
```

Between those two you can get from "I want to change weapon damage" to a named field without guessing once. It's how I found out the health fields I'd been shipping were in a block the game ignores.

## Finding where the value actually sits

Here's the annoying part. blam-tags tells you the field exists and what it reads. It won't tell you the byte offset, and Blamforge needs the offset.

Two ways. Set the field with blam-tags and diff:

```
cp chunk /tmp/x
blam-tag-shell --game haloce_evolved set /tmp/x 'damage lower bound' 400
cmp -l chunk /tmp/x
```

`cmp -l` prints in octal, which caught me out. Byte positions are 1-indexed too.

Or scan for the value you already know:

```python
import struct
b = open(chunk,'rb').read()
for off in range(len(b)-4):
    if abs(struct.unpack_from('<f', b, off)[0] - 8.5) < 1e-4:
        print(hex(off))
```

The second is better when several fields share a value, because you see all the candidates at once instead of one.

Some fields are the same offset in every tag of a kind. Weapon damage is at 0x1121 in every damage effect tag in the game. Worth checking before you go hunting per weapon.

## Adding a target

**Make sure the thing is in the game.** This game is Reach underneath, so the whole Reach sandbox is sitting in the files whether the campaign uses it or not. I had a DMR and a spartan laser in here for a while, data looked perfect. Halo Studios publish the weapon list. Check against it.

**Sanity check the value.** A magazine reads 60, not 1536. A delay reads 6.0, not 6e-38. A float that converts to a round number of degrees is probably a spread.

Read the byte.

**Add it as `"status": "derived"`.**

**Then go play it.** Install, load a level, check the thing changed. If it did, flip to `"confirmed"` and say so in the PR.

Don't mark something confirmed you haven't played. That flag is the only thing telling anyone whether an entry has ever been off the page, and it's worth nothing the moment someone guesses.

## Field notes

`derived` fields aren't editable, they're worked out from other ones. Ammo blocks have a reserve count that has to be ceiling minus magazine or the game desyncs.

`locked` is for fields where changing it might break something. Shotgun reloads one shell at a time and I don't know what happens if it doesn't.

`warn_over` turns the row red past a set number, `warn_above` past another field's value. Neither stops you. AR and BR use `warn_over` at 99 because the counter on the gun is two digits, so 123 rounds shows as 23.

`mirror` writes the same value to a second offset. Bounds pairs mostly.

`chunk` on a field points it at a different tag. Damage needs this, since it isn't stored in the weapon's own file.

The schema name is a hint, not a description. "Total initial" is how much ammo a weapon comes with when it's set dressing, not what you start a level with. Took someone noticing the needler behaved differently from the AR to work that out.

Units too. The AR's rate of fire reads 12 and the devs say the intended rate is 10 rounds a second. Higher is faster (set it to 1, watched it crawl). What the number measures, no idea. Write down what you tested and leave the rest alone.

Slider ranges around 10x stock. They all used to share one range, which put the sniper rifle (4 rounds) on a track running to 600. Every useful value was in the first half centimetre.

## Don't commit game files

No chunks, no containers, no `.tag` files. `.gitignore` catches the obvious ones but look at your diff before you push. Offsets are fine to ship. Bungie's data is not.

## Submitting

Fork it and open a pull request.

Commit messages use [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/).

Python goes through `ruff check` and `ruff format`, config's in `ruff.toml`. HTML and JSON through [Prettier](https://prettier.io) on defaults. There are a few `# noqa: BLE001` on blind excepts that are deliberate, they stop a failed install taking the server down with it.

There's no test suite yet, so the bar is: it runs, ruff passes, and if you added an offset you've played it in game and marked it confirmed.

## Something broken?

Game build, which target, and what the verification error said. Blamforge names the field that disagreed and shows both values, so pasting that is usually enough.
