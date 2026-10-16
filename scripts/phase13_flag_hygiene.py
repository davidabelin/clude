"""Phase 13 step 0's remainder: reconcile the durable layers with the entries.

The editorial pass applied a head computed from a snapshot that several
already-stored entries post-dated, so those entries were never folded in.
Three things in each head are wrong as a result: the flag index, the tally,
and the dossiers' games_together counters.

This is deliberately NOT `rebuild_head()`, which 0c warns off: a full
rebuild also replaces each dossier's `read` with whatever the last entry
mentioning that opponent happened to say, discarding step 0's edited reads
for david, floor and guest. So the reads, their dates and serials are kept
exactly as stored, and only the counters move.

Flag vocabulary is normalised first, in the entries themselves, using each
character's own digest `renamed` map plus the duplicate coinages 0e names.
`never-accused` is left alone on purpose -- see NOT_RENAMED.

    python scripts\phase13_flag_hygiene.py --dry     report, write nothing
    python scripts\phase13_flag_hygiene.py --apply   write to the live bucket

Idempotent: a second --apply reports every character clean.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from clude_storage import open_store  # noqa: E402
from clude_storage.logbooks import (  # noqa: E402
    Logbook,
    LogbookEntry,
    LogbookHead,
    entry_key,
)

URI = "gs://clude-game-data/llm"
WHO = ["Scarlett", "Mustard", "White", "Green", "Peacock", "Plum"]

# Each entry: the retired coinage -> the kept name, and why it is safe.
RENAME = {
    "Mustard": {
        # The character's own digest retires this spelling.
        "ignored-a-spoken-claim": "ignored-spoken-claim",
    },
    "Peacock": {
        "slow-to-accuse": "late-certainty",
        "too-far-to-accuse": "late-position",
        # Duplicates the indexed own-cards-as-bluff.
        "bluff-naming-own-cards": "own-cards-as-bluff",
    },
    "Scarlett": {
        # 0e: beside the kept slow-to-the-rooms.
        "slow-to-room": "slow-to-the-rooms",
    },
    "White": {
        # 0e: beside narrator-at-the-table, which the map already retires
        # quiet-player-closes to.
        "quiet-player-closing": "narrator-at-the-table",
        # The map retires repeat-the-other-seat-s-question to this.
        "repeat-ask-tell": "borrowed-question",
    },
}

# Left as live vocabulary, with the reason, so the choice is on the record.
NOT_RENAMED = {
    "Peacock/never-accused":
        "the digest retires it, but the character used it in its two most "
        "recent entries, after that digest, and the tally already carries the "
        "fact in its own field; retiring a name in active use is a design "
        "decision, which this step is not",
    "Scarlett/chased-low-value-rooms, chatterbox-opponent, lost-the-race, "
    "missed-unrefuted-room, tell-reading-noise":
        "fresh vocabulary with no kept equivalent",
    "White/room-fixation": "shared with Peacock's index; genuine vocabulary",
    "Peacock/opponent-tempo": "fresh vocabulary with no kept equivalent",
}


def reconcile(lb, entries):
    """The head as it should stand: the stored one, with the flag index
    rebuilt from the entries, the tally recounted, and each dossier's
    games_together recounted -- reads, dates and serials untouched."""
    stored = lb.head()
    fresh = LogbookHead.empty(lb.identity)
    for entry in entries:
        fresh.absorb(entry)

    out = stored.to_dict()
    fresh_d = fresh.to_dict()
    out["flags"] = fresh_d["flags"]
    out["tally"] = fresh_d["tally"]
    for label, d in out["dossiers"].items():
        if label in fresh_d["dossiers"]:
            d["games_together"] = fresh_d["dossiers"][label]["games_together"]
    return LogbookHead.from_dict(out), stored.to_dict(), out


def main(apply: bool) -> int:
    store = open_store(URI)
    print(f"{'APPLYING to' if apply else 'DRY RUN against'} {URI}\n")
    for who in WHO:
        lb = Logbook(store, who)
        renames = RENAME.get(who, {})
        touched = []

        entries = list(lb.entries())
        for entry in entries:
            data = entry.to_dict()
            old = list(data.get("flags") or [])
            new, changed = [], False
            for f in old:
                target = renames.get(f, f)
                if target != f:
                    changed = True
                if target not in new:
                    new.append(target)
            if changed:
                data["flags"] = new
                touched.append((data["serial"], old, new))
                if apply:
                    store.put_doc(entry_key(who, data["serial"]), data)
        if touched:
            entries = list(lb.entries()) if apply else entries
            if not apply:  # reflect the renames in memory for the head diff
                fixed = []
                for entry in entries:
                    d = entry.to_dict()
                    for serial, _o, n in touched:
                        if d["serial"] == serial:
                            d["flags"] = n
                    fixed.append(LogbookEntry.from_dict(d))
                entries = fixed

        head, before, after = reconcile(lb, entries)
        moved = {k: (before.get(k), after.get(k)) for k in ("tally", "flags")
                 if before.get(k) != after.get(k)}
        counters = [k for k, v in after["dossiers"].items()
                    if v["games_together"] != before["dossiers"][k]["games_together"]]

        print("=" * 68)
        print(who)
        for serial, old, new in touched:
            print(f"  entry #{serial:04d} flags {old} -> {new}")
        if "tally" in moved:
            b, a = moved["tally"]
            print(f"  tally games {b['games']} -> {a['games']}, won {b['won']} -> {a['won']}, "
                  f"never_accused {b['never_accused']} -> {a['never_accused']}")
        if "flags" in moved:
            b, a = moved["flags"]
            added = sorted(set(a) - set(b))
            dropped = sorted(set(b) - set(a))
            reserialed = sorted(k for k in set(a) & set(b) if sorted(a[k]) != sorted(b[k]))
            print(f"  flag index: +{len(added)} {added}")
            if dropped:
                print(f"              -{len(dropped)} {dropped}")
            if reserialed:
                print(f"              serials corrected for {len(reserialed)}: {reserialed}")
        if counters:
            print(f"  dossier games_together corrected: {sorted(counters)} "
                  "(reads, dates and serials untouched)")
        if not (touched or moved or counters):
            print("  clean, nothing to do")
            continue
        if apply:
            lb.save_head(head)
            print("  head written")
    print("\nleft as live vocabulary, on purpose:")
    for k, v in NOT_RENAMED.items():
        print(f"  {k}\n      {v}")
    return 0


if __name__ == "__main__":
    if "--apply" not in sys.argv and "--dry" not in sys.argv:
        sys.exit("pass --dry or --apply")
    raise SystemExit(main("--apply" in sys.argv))
