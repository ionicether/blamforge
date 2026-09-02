# Contributing

Offsets. That's the useful thing.

Fourteen targets is a start, not a finish. Every plasma weapon is missing, along with vehicles, grenades, and whatever else turns out to be sitting in there.

## How the offsets get found

Gameplay values live in Blam tags, packed inside Unreal IoStore containers. Once a tag's out the values are just ints and floats at fixed offsets, so changing them is trivial. Knowing which offset is the entire problem.

Blam tags carry their own field names as plain strings:

```
strings -a -t d <chunk> | grep -iE 'magazine|rounds|recharge|vitality'
```

Now you know the tag has a field called "rounds loaded maximum". You still don't know where the value is. The names live in a schema block, the numbers live somewhere else entirely.

Diffing closes that gap. Two versions of the same tag (stock and modded, or a Grunt and an Elite) and the bytes that differ are the bytes holding values:

```
cmp -l stock.tag modded.tag | head -40
```

Then read four bytes at each spot as a float and see if the number means anything. 60 sitting next to 600 is a magazine and its reserve. Two floats that come out as exactly 3.50 and 5.00 degrees once you convert from radians are a spread. Everything in the registry got found this way.

If someone's already made a mod that does what you want, diff theirs. The Chief shield offsets took about ten minutes that way, against hours of getting nowhere on the same problem from scratch.

## Adding a target

Rough shape of it:

**Find the chunk.** Unpack a container with `retoc unpack-raw`, then grep the output for a string that identifies what you're after. Weapon tags tend to name their own animation graph, so `grep -l plasma_rifle *` gets you close.

**Find the fields.** `strings -a -t d <chunk>` dumps the schema, which tells you what the tag *has*. Finding where the values sit is the other half, and diffing two variants of the same tag type is the way. The bytes that differ between a Grunt and an Elite are the bytes holding numbers.

**Check it's real.** Read your offset in a stock chunk and see if the value makes sense. A magazine reads 60, not 1536. A delay reads 6.0, not 6e-38. If you converted a float and got a round number of degrees, you've probably found a spread.

This is where it's easy to fool yourself. I once added a field because I assumed it matched its neighbour by symmetry, never actually read it, and shipped an offset with a wrong stock value that made the whole tag fail verification. Read the byte.

**Add it to `registry.json`** with `"status": "derived"`.

**Then play it.** Build the mod, install it, load a level, check the thing actually changed. If it did, flip the status to `"confirmed"` and say so in the PR.

Please don't mark something confirmed you haven't played. That status is the only signal anyone has about whether an entry has ever been off the page, and it stops meaning anything the moment it's guessed at.

## Field notes

`derived` fields aren't editable, they're computed from other fields. Ammo blocks have a reserve count that has to equal ceiling minus magazine or the game desyncs.

`locked` fields aren't editable either, but for a different reason: changing them might break something. I have no idea what happens when the shotgun reloads more than one at a time. Even if it worked, it kinda breaks immersion.

`mirror` writes the same value to a second offset. Some fields are stored as min/max pairs the game expects to be identical.

Keep slider ranges sane. Roughly 10x stock is about right. I originally set every magazine slider to the same wide range, which meant the sniper rifle (4 rounds stock) had a track running to 600. Technically it worked. In practice every value you'd actually want sat in the first half centimetre and you couldn't land on any of them.

## Don't commit game files

No chunks, no containers, no `.tag` files. `.gitignore` covers the obvious cases but glance at your diff before pushing. Shipping offsets is fine. Shipping Bungie's data is how repos get taken down.

## Something broken?

Tell me the game build, which target, and what the verification error said. Blamforge prints exactly which field disagreed and by how much, so pasting that is usually enough.
