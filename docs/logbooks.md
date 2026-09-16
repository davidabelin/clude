# Logbooks: playerbot memory (`clude_storage.logbooks`, `clude_training.memory`, `clude_llm.logbook`)

How a character remembers across games, what it reads back before one,
and how to look at what it wrote. The design and David's decisions are
in `docs/phase7-plan.md`; this is the working guide.

## Three tiers

```
Tier 0  the record      GameRecord in the store (Phase 5d)          omniscient, immutable
Tier 1  method memory   numeric, per method, headless, no LLM       logbooks/<id>/method.json
Tier 2  narrative       an entry per game plus a rolling head,      logbooks/<id>/entries/NNNN.json
        memory          written and read by the character's model   logbooks/<id>/head.json
```

A logbook belongs to an *identity*: the roster label of a seat, so a
character's logbook is its own whichever token it plays, and a human's
display name (Phase 8) will get one the same way. Logbooks live in the
same store as the game records, local directory or `gs://` bucket,
under `logbooks/<identity>/`.

"Each character writes to its logbook after every game" means two
things. Every game played with a logbook store updates the method
memory of Mustard, White and Green (Tier 1, headless or not). An
LLM-piloted seat also writes an entry (Tier 2), because that needs a
model. Scarlett, Plum and Peacock have memoryless methods, so their
memory is Tier 2 only.

## Tier 1: method memory

| Character | What is remembered | How it is used |
|---|---|---|
| Mustard | `rows_from_view` training rows from every seat's view of every stored game, at his training checkpoints | appended to his 25-game self-play base before the tree is trained (`DecisionTreeAgent.set_extra_rows`) |
| White | each opponent label's repeat/new transition counts, summed over stored games | replaces the chain's Laplace prior for that opponent at the same total mass (`prior_cells`), so only the starting shape of the chain is informed |
| Green | his Beta posteriors over the five arms | restored after `reset`, saved after every game |

Mustard and White learn from every stored game, including ones they
did not sit in. Documents are keyed by game id, so updating twice with
one game changes nothing and `logbook rebuild` from a whole store agrees
with the incremental updates. Green's posteriors depend on what his
arms predicted live, which no record holds, so his memory is only ever
accumulated, never rebuilt.

Determinism becomes "per seed and logbook state": with no logbook, or
an empty one, a character plays exactly the game it played before, and
every golden fingerprint holds.

## Tier 2: the entry and the head

An entry is the zenbot memory shape (`docs/zenbot_memories.json`)
without the koans. Code computes the facts (identity, serial, date, game
id, token, the table, the outcome, the model); the character's model
writes the rest at the debrief:

| field | what |
|---|---|
| `title` | a short title |
| `summary` | one or two sentences, at most 40 words |
| `flags` | two to six short lowercase keywords shared across entries |
| `what_happened` | the game as the character experienced it |
| `evaluations` | per opponent present: an evaluation and notes on tells |
| `key_insights`, `lessons_learned` | short lists |
| `final_outcome` | the result in its words |
| `standing_instructions` | the whole list rewritten, at most eight |
| `dossiers` | a revised read on any opponent present, at most 60 words each |

Flags are normalised (`"Over Confident!"` becomes `over-confident`),
lists are capped, and evaluations and dossiers are kept only for
opponents who were at the table (`LogbookEntry.build`).

The head is what the character reads back: a computed tally (games
with an entry, won, wrong accusations, never accused), the standing
instructions from the last entry, a dossier per opponent it has met
(`read`, `games_together`, when it was last revised), and a flag index.
Only the opponents present at a game have their dossiers touched by its
entry; an entry with no standing instructions leaves the previous list
standing.

## The `memory` dial: what a character reads back

`memory` is a `Profile` dial in [0, 1], default 0. Before each game the
wrapper renders one block from the head and entries (`render_memory`):

| `memory` | the character reads |
|---|---|
| 0 | the head: tally, standing instructions, the dossiers of the opponents present |
| 0 < m <= 0.5 | the head plus a one-line index of the most recent `ceil(n * m / 0.5)` entries (serial, date, table, outcome, summary, flags), headed by the flags recurring across them; at 0.5 the whole index |
| 0.5 < m <= 1 | the head, the whole index, and the most recent `ceil(n * (m - 0.5) / 0.5)` entries in full; at 0.75 the most recent half, at 1 every entry |

The block travels as a **second cached system block** after the persona
and rules (`LLMRequest.memory`). It is stable for a whole game, so it is
written to the cache once and read at a tenth of the price on every
call after; the persona block stays the prefix every game shares. An
empty logbook sends no block, and the request, its replay key and the
API call are then exactly the Phase 6 ones, which is why every recorded
fixture still replays. `logbook show --identity X --memory 0.75` prints
exactly the block a character at that depth would read.

The block can only steer the model among the options its leash allows;
it never widens a menu. Plum's escape from a cleared room is on his
menu only at leash 0.34 or more, so at the preset 0.25 his notes cannot
unpark him whatever they say (`docs/strategy-glossary.md`,
"Per-character leash ladders"). At leash 0.5, where the escape is on
the menu, they do: over 24 games his stalls fell by more than half
and to almost nothing by the last quarter, at the price of two
accusations below his threshold (glossary, "Plum's logbook at leash
0.5").

## The debrief

After a game an LLM-piloted seat is asked, under its persona and rules
(the same cached system block), to write the entry. It is told the
outcome and the envelope, its hand, **the whole deal face up** (so a
claim about a hand can now be checked), the suggestions as it saw them
live, the table talk with its own lines marked, the decisions the model
was asked to make (by kind, each with the note the menu showed beside
the chosen option, deviations and fallbacks marked, and a run of the
same decision collapsed into one line so a stall reads as one), its final belief
against the truth, its head, an index of its earlier entries with their
flags, and the field-by-field instructions. The reply is JSON against
`LOGBOOK_SCHEMA` (`clude_llm.schema`), at effort `medium` with 4096
tokens of room and its own 180 s timeout (`LLMSettings.debrief_effort`,
`debrief_max_tokens`, `debrief_timeout`; `debrief=False` skips it). Any error, refusal or malformed reply means
no entry and a reason in `LLMCharacter.last_debrief`; the game is
unaffected. The debrief's tokens count toward the game just played.

Opponents may be named any way the model likes ("Mrs. Peacock", "the
Mustard token", `P2 White (Green)`); `resolve_opponents` maps them to
roster labels before the entry is built.

## Running it

```
python scripts/clude_cli.py play --roster Plum,Mustard,Green --players 3 --store data/llm --logbook
python scripts/clude_cli.py play --roster Plum,Mustard,Green --players 3 --llm --llm-characters Plum --store data/llm --logbook
python scripts/clude_cli.py arena --games 6 --players 3 --roster Plum,Mustard,Green --llm --store data/llm --logbook --run-id logbook-smoke
python scripts/clude_cli.py sweep --dial memory --values 0 0.5 1 --llm --logbook data/llm --roster Plum,Mustard,Green --players 3
python scripts/clude_cli.py logbook list --uri data/llm
python scripts/clude_cli.py logbook show --uri data/llm --identity Plum
python scripts/clude_cli.py logbook show --uri data/llm --identity Plum --entry 3
python scripts/clude_cli.py logbook show --uri data/llm --identity Plum --memory 0.5
python scripts/clude_cli.py logbook rebuild --uri data/llm --identity Mustard
python scripts/clude_cli.py logbook reset --uri data/llm --identity Plum --keep-entries
python scripts/clude_cli.py prompt --roster Plum,Mustard,Green --players 3 --logbook data/llm --memory 0.5
python scripts/clude_cli.py train-mustard --logbook data/llm --eval-games 8
```

- `--logbook [URI]` on `play` and `arena` turns memory on: read before
  each game, written after. With no URI it uses the `--store` location.
  `--logbook-readonly` reads and writes nothing, which is what a fair
  comparison against a fixed memory needs. `sweep --logbook` is always
  read-only, so the `memory` dial can be swept on one logbook state.
  `--logbook-characters Plum` gives only the named characters a
  logbook, so one character's memory can be measured with the rest
  of the table exactly as it plays without memory.
- `play --store` now writes a single game's record (and a one-game run
  summary) so a game played from the CLI can leave memory.
- `logbook reset` is the fairness control: forget the head and method
  memory, and the entries too unless `--keep-entries`. `rebuild`
  recomputes the head from the entries and the method memory from
  every grid-era game record in a store (the bootstrap from the games
  already in `data/llm`). Since 2026-09-16 it skips records older than
  `--min-version` (default 3, the first on the Classic grid), so ring
  games cannot leak back into a reset memory; `--min-version 1` reads
  every era.
- The arena's LLM table gains an `entries` column; the footer says
  which store the logbooks came from and whether they were written.

## Cost

Measured on Opus 5 in Phase 6, an LLM seat-game costs about $0.07-0.11
(Plum about $0.25). The debrief adds one call per seat per game,
measured on six Plum games (2026-09-14): 2.5-7K fresh input tokens,
2K cached, 1.8-3.1K output including thinking, 33-48 s at medium
effort, $0.06-0.11 (mean $0.09). Read-back at `memory` 0
is a few hundred cached tokens per call, near nothing; at depth 1 with
twenty entries roughly $0.15-0.20 per seat-game (one cache write, then
cached reads). Over the 24-game run of 7d the 24 debriefs cost $2.24,
$0.093 and 42 s each, and the on leg's decisions cost less than the
off leg's because the games got shorter. `play --llm` and the arena
footer estimate a run's cost including the debriefs.

## Where things are

- `clude_storage/logbooks.py`: the documents, `Logbook`, `render_memory`.
- `clude_training/replay.py`: a stored record back into a `GameState`
  or any seat's masked view.
- `clude_training/memory.py`: Tier 1, the record-to-memory
  contributions and the load / update / rebuild glue.
- `clude_llm/logbook.py`: the debrief prompt and opponent resolution;
  `clude_llm/player.py`: `attach_logbook`, `read_back`, `debrief`.
- `tests/test_logbooks.py`, `tests/test_replay.py`, `tests/test_memory.py`,
  `tests/test_debrief.py`.
