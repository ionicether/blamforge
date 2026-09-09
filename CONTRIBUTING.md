# Contributing

Offsets. That's what's useful here.

17 targets so far. The energy sword is in the game and not in here, but it has no magazine and no battery so there might be nothing to change. Vehicles and grenades haven't been touched at all.

## How the offsets get found

The values live in Blam tags, which sit inside Unreal IoStore containers. Get a tag out and the numbers are just ints and floats at fixed spots. Changing them is easy. Finding them is the whole job.

Blam tags carry their own field names as text, which helps:

```
strings -a -t d <chunk> | grep -iE 'magazine|rounds|recharge|vitality'
```

That tells you the tag has a field called "rounds loaded maximum". It does not tell you where the number is. Names are in one block, values are somewhere else entirely.

Diffing is how you bridge it. Two versions of the same tag, stock and modded, or a Grunt and an Elite. Bytes that differ are the values:

```
cmp -l stock.tag modded.tag | head -40
```

Read four bytes at each spot as a float and see if the number means anything. 60 next to 600 is a magazine and its reserve. Two floats that come out to exactly 3.50 and 5.00 degrees once converted from radians are a spread.

Best trick - if someone already made a mod that does what you want, diff theirs. The Chief recharge offsets took ten minutes that way. I'd spent hours on the same problem before that and got nowhere.

## Adding a target

**Find the chunk.** `retoc unpack-raw` a container, then grep the output for something identifying. Weapon tags usually name their own animation graph, so `grep -l plasma_rifle *` gets close.

**Find the fields.** `strings -a -t d <chunk>` gives you the schema. Diffing two variants of the same tag type gives you where the values sit.

**Make sure the weapon is in the game.** There are tags for weapons that aren't in the campaign. I had a DMR and a spartan laser in here for a while. The data is right there and looks fine. Halo Studios publish the weapon list, check against that.

**Sanity check the value.** A magazine reads 60, not 1536. A delay reads 6.0, not 6e-38. If you convert a float and get a round number of degrees, that's probably a spread.

Read the byte. Don't work it out from the byte next to it. I did that once and shipped an offset that made the whole tag fail verification.

**Add it to `registry.json`** as `"status": "derived"`.

**Then go play it.** Install it, load a level, check the thing changed. If it did, flip it to `"confirmed"` and say so in the PR.

Don't mark something confirmed you haven't played. That flag is the only way anyone knows whether an entry has ever been off the page.

## Field notes

`derived` fields aren't editable, they're worked out from other fields. Ammo blocks have a reserve count that has to be ceiling minus magazine or the game desyncs.

`locked` fields aren't editable because changing them might break something. No idea what the shotgun does if it reloads more than one shell at a time. Even if it worked, it kinda breaks immersion.

`warn_over` turns the row red past a set number. `warn_above` turns it red past another field's value. Neither stops you, they just say why it's a bad idea. AR and BR use `warn_over` at 99 because the counter on the gun is two digits and 123 rounds shows as 23.

`mirror` writes the same value to a second offset. Some fields are stored twice and the game wants them matching.

The schema name is a hint, not a description. "Total initial" turned out to be how much ammo a weapon comes with when it's set dressing, not what you start a level with.

Same goes for units. The AR's rate of fire reads 12, the devs say the intended rate is 10 rounds a second, and those don't line up. Higher is faster, I checked by setting it to 1 and watching it crawl. What the number actually measures, no idea. Write down what you tested and leave the rest.

Keep slider ranges around 10x stock. Every magazine slider used to have the same range, which put the sniper rifle (4 rounds) on a track running to 600. Every useful value was in the first half centimetre.

## Don't commit game files

No chunks, no containers, no `.tag` files. `.gitignore` catches the obvious ones but look at your diff before pushing. Offsets are fine to ship. Bungie's data is not.

## Something broken?

Tell me the game build, which target, and what the verification error said. Blamforge names the field that disagreed and shows both values, so pasting that is usually enough.
