# The LLM wrapper (`clude_llm`)

How a character gets a voice and a little discretion, without losing
its method. Design and David's decisions are in `docs/phase6-plan.md`;
this is the working guide.

## What happens on one decision

The engine asks a seat one of four questions: where to move, what to
suggest, whether to accuse, which card to show. For a headless
`Character` the answer comes from its method's numbers and its five
dials. An `LLMCharacter` wraps that character and, for each question:

1. **Builds a menu** from the character's own scores: every legal option
   the engine offered, lettered `A`, `B`, ... best first, with the
   number behind it ("P(envelope room = Library) 0.31", "already shown
   to this player"). Own-hand cards appear in the suggestion menu as
   labelled bluff options.
2. **Applies the leash.** An option is allowed when its score is at
   least `(1 - leash)` of the best. `leash = 0` leaves only the
   character's best-scored options (ties included, so the model may still
   be asked to break one); `leash = 1` opens every legal option. The
   accusation menu, `[accuse, pass]`, uses the same rope on both sides
   of the character's threshold: the model may jump early once
   `P(correct) >= (1 - leash) * accuse_threshold`, and may hold back
   whenever there is any rope. If one option is left, no call is made
   and the character decides as it would headless.
3. **Asks the model**, with the persona and rules as a cached system
   prompt and the seat's view as the user prompt (below), and a fixed
   JSON schema for the reply: a letter (two for a suggestion) and a
   `say` line.
4. **Plays the letter** if it is an allowed option, and hands the line
   to the engine as a `RemarkEvent`, published with probability
   `chattiness`. Anything else -- the per-game budget, a backend error
   or timeout, a refusal, malformed JSON, a letter that is not on the
   menu or not allowed -- **falls back to the character's own method**.
   The fallback spends the character's RNG exactly as the headless
   character would have, so a backend that never answers plays the
   identical game, event for event; `tests/test_llm.py` checks that
   against the character goldens, and checks that an adversarial
   backend with full rope cannot change a single event either.
5. **Records a `Decision`**: the menu, the letter, the fallback reason
   if any, whether the choice deviated from the character's top option,
   the line, tokens, seconds. Records keep these per seat
   (`GameRecord.llm_log`), and the arena turns them into columns.

## What the model is shown, and what it is not

The user prompt is rendered from the seat's `ClueObservation` only,
never from `GameState`, so the model can be shown nothing its seat
could not know. It contains: who the character is and which token it
plays; who is at the table and who is out; its hand; what the shared
deduction floor has proven (envelope cards) and located (cards held by
named seats); its method's top cards per category and any method
diagnostics (Plum's exact/sampled count, Green's arm, Peacock's
belief/plausibility bounds); its best accusation with `P(correct)` and
its threshold; the suggestion log as that seat saw it, with cards it
was not shown marked hidden; the last few lines of table talk; and the
menu, allowed options only.

`python scripts/clude_cli.py prompt ...` prints exactly this for any
seat, any point in a game, any decision, without making a call. Read it
before editing a persona, and read it when checking that nothing leaks.

The system prompt is `clude_llm/personas/<Suspect>.md` followed by
`clude_llm/personas/rules.md`. It is byte-stable per character, which is
what lets the API cache it (Opus 5 caches prefixes of 512 tokens or
more; the two files together are well past that).

## Personas

One Markdown file per suspect. Each says who the character is, how it
thinks (its method, in plain words, as self-image rather than
instruction) and how it talks. The rule they follow is the one the
personality layer already follows: **do not encode the flaw twice.**
Scarlett's early accusations come from her 0.15 threshold and her naive
Bayes numbers; her file says she is sure of herself, not that she
should accuse early. Tune voices by editing the files; tune behaviour by
editing dials.

## The two Phase 6 dials

| Dial | What it does | Arena footprint |
|---|---|---|
| `leash` | how far below the character's best-scored option the model may pick, and how wide the accusation window opens around the threshold | deviation rate; wrong-accusation rate against the headless twin |
| `chattiness` | the probability a line the model offered is actually said | remarks per game |

Both live on `Profile`, so `--set Plum.leash=0.5`, `sweep --dial leash`
and the presets all work as for the other five. The headless
`Character` ignores them. Presets start at `leash = 0.25`,
`chattiness = 0.5` for everyone until the 6d sweep sets them.

## Memory (Phase 7)

With a logbook attached (`LLMCharacter.attach_logbook`; `--logbook` on
the CLI) the wrapper reads the character's logbook back before each
game at the depth of a third dial, `memory` (default 0: the head only;
0.5 every entry's summary and flags; 1 every entry in full), and sends
it with every decision as a **second cached system block** after the
persona and rules (`LLMRequest.memory`). The block is stable for a
game, so it is written to the cache once and read cheaply after, and
the persona block stays the prefix every game shares. With no logbook,
or an empty one, the request and its replay key are exactly the ones
above, so every recorded fixture still replays.

After the game the wrapper asks the model for the game's logbook entry
(`debrief`): the same persona and rules, a prompt with the outcome, the
deal face up, the seat's own view of the game, its decisions, its
final belief against the truth and its logbook so far, and a third
fixed schema, `LOGBOOK_SCHEMA`, at effort `medium` with 4096 tokens
and 180 s (`LLMSettings.debrief_effort`, `debrief_max_tokens`,
`debrief_timeout`; `debrief=False`
skips it). A failed or malformed debrief writes nothing and leaves the
reason in `last_debrief`. `docs/logbooks.md` has the rest.

## Backends

`--llm-backend` on `play`, `arena` and `sweep`:

| Backend | What it does | When |
|---|---|---|
| `anthropic` | the real API (`clude_llm.anthropic_backend`, SDK imported lazily) | play, measurement |
| `null` | never answers; every decision falls back | the control: the headless twin |
| `record:PATH` | the real API, every exchange saved to a JSON file | building a replay |
| `replay:PATH` | serves a recording back, keyed by a digest of the request | re-analysis and tests, no spend |

A replay raises `ReplayMiss` on a request it has not seen, so a prompt
change shows up as a miss rather than a silent divergence.

Credentials: `ANTHROPIC_API_KEY`, or an `ant auth login` profile,
resolved by the SDK; nothing is stored in the repo. With no credentials
the backend returns an authentication error on every call and the game
falls back throughout, which the `play --llm` trailer makes visible.

The key has to be **workspace-scoped**. An organisation-level key fails
every call with a 400 -- "not scoped to a workspace, so this request
must include the anthropic-workspace-id header" -- and since the backend
sends no such header, every seat falls back and the run is worthless.
Create the key inside a workspace. A `.env` at the repo root is
gitignored but nothing loads it: export the variable into the
environment before running, or the SDK will not see it.

Call settings (`LLMSettings`): model `claude-opus-5`, `effort` low,
`max_tokens` 2048, timeout 30 s, one SDK retry, server-side refusal
fallbacks on, budget 200 calls or 500K tokens per game, eight lines of
recent table talk in the prompt; the debrief (Phase 7) at effort
`medium` with 4096 tokens and its own 180 s timeout (at medium effort
it runs 40-90 s; the smoke run's first six debriefs all timed out at
30 s before it had one).

## Cost

Most menus have one allowed option at the default leash (refutations
especially), so a game asks the model far less often than it decides:
at seed 1 Scarlett made 7 calls across 17 decisions, Peacock 11 across
18. `play --llm` prints an estimate at list prices per game.

Measured on Opus 5 (2026-09-13), at list prices:

| Game | Seats | Turns | Cost | Cached |
|---|---|---|---|---|
| seed 1, 3 players, 2 LLM seats | 2 | 16 | $0.14 | 52% |
| seed 2, 4 players, 4 LLM seats | 4 | 39 | $0.43 | 46% |

That is roughly **$0.07-0.11 per LLM seat-game**, which is the number to
budget an arena with: a 24-game, 4-seat run is order $10. Plum's games
run long and ask the model often, so his seat-game is about $0.25. A
logbook (Phase 7) adds a debrief per seat-game, measured on six Plum
games (2026-09-14) at $0.06-0.11, mean $0.09: 2.5-7K fresh input
tokens, 2K cached, 1.8-3.1K output including thinking, 33-48 s at
medium effort; over the 24-game run of 7d, 24 debriefs cost $2.24,
$0.093 and 42 s each. At the default `memory` of 0 the read-back is a
few hundred cached tokens per call.

Read the usage fields carefully: `input_tokens` counts only the *fresh*
tokens and `cache_read_input_tokens` the cached ones, disjointly -- so
the cache share is `cached / (input + cached)`, not `cached / input`,
and `estimate_cost` bills them separately at $5 and $0.50 per MTok. On
seed 2 that is 57.6K cached against 68.9K fresh: 46%, and about $0.26
saved on a $0.43 game. Expect the share to fall as a game lengthens,
since the cached system block is fixed while the per-turn state grows.

## Measuring it

The comparison is always against the headless twin on the same seeds:

```
python scripts/clude_cli.py arena --games 12 --players 4 --roster Scarlett,Plum,Peacock,floor --seed 7007
python scripts/clude_cli.py arena --games 12 --players 4 --roster Scarlett,Plum,Peacock,floor --seed 7007 --llm
```

Same deals, same dice; the difference in win rate and wrong-accusation
rate is what the rope cost or bought each character. The `--llm` run
adds an LLM table: decisions, calls, fallback rate, deviation rate
(played options that scored below the character's best), remarks per
game, tokens per game, and milliseconds per call. `sweep --dial leash
--llm` is the keep-a-dial test for the leash. Results go in
`docs/strategy-glossary.md` as they are run.
