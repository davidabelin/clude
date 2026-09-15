# Fab4 Review at Stage 5

Read the whole thing, David: all three packages, the six agents, the engine, training, tests, and the docs. Good work in there. Two things I found change the plan materially, so here's the Phase 5 design reworked against the actual code.

## What the repo actually dictates

**1. The engine can't feed the agents yet.** `run_game` drives `RandomBotProtocol`: `choose_movement(choices, rng)`, `choose_suggestion(room, own_hand, rng)`, `choose_accusation(rng)`, `choose_card_to_show(candidates, rng)`. None of those receive a `ClueObservation`. The six agents only ever get one from `clude_constraints.observe`, which today runs post-hoc in `self_play.py`, never during a live game. So before any personality exists, the engine needs a seam that hands each decision an observation. That's a small change, but it's step one, not an afterthought.

**2. `docs/architecture.md` already rules out my earlier "one shared policy" idea, for room choice at least.** Your refinement says the decision must stay per-character and trainable, with only feature extraction shared. So the split below is: shared features, shared *scoring machinery*, per-character *weights* — and any character may override the decision outright. The weights are the personality.

## The four decisions Phase 5 has to make

The engine asks exactly four questions per player. Each maps to a dial set:

| Engine call | Numbers it needs | Dials that shape it |
|---|---|---|
| `choose_movement` | room features (see below) | `w_info`, `w_distance`, `w_danger`, `temperature` |
| `choose_suggestion` | belief over unresolved suspects/weapons | `bluff_rate`, `temperature` |
| `choose_accusation` | P(correct) = product of the three category maxima | `accuse_threshold`, `urgency`, `confidence_source` |
| `choose_card_to_show` | what I've already shown to whom (recoverable from `obs.suggestion_log`, since `card_shown` is visible to the refuter) | `secrecy` |

`confidence_source` is the one non-numeric field: `"probabilities"` for five of them, `"belief"` for Peacock, so her caution comes from her own DS lower bound rather than a faked-up threshold. Bluffing is in because you resolved that question as allowed.

## Sub-phases

**5a — engine seam.** Replace `RandomBotProtocol` with a `PlayerProtocol` whose four methods take `obs` first. `run_game` gains an `observer: Callable[[GameState, int], ClueObservation]` parameter, defaulting to `ClueObservation.for_player` (so `clude_core` still never imports `clude_constraints`); the Phase 5 runner passes `clude_constraints.observe`. Accusation's observation is rebuilt *after* this turn's suggestion resolves, so the refutation is visible. `RandomBot` grows an ignored `obs` argument. All 45 existing tests still pass. Nothing else changes.

**5b — profile + character.**
- `clude_agents/personality.py`: `Profile` dataclass (the dials above, plus reserved `chattiness`/`candor`), six presets, `to_dict`/`from_dict` for the future sliders and logbooks.
- `clude_agents/features.py`: shared, deterministic — `room_features(obs, belief, legal_moves)` and `danger(obs)`. Danger is a public proxy only (cards each opponent has been shown, suggestions made, turns active); no one gets to peek. Legacy `info_agent`'s suspect/weapon search is the seed here, with its placeholder gain replaced by belief mass on unresolved cards — real expected-info-gain is a later refinement, not a blocker.
- `clude_agents/character.py`: `Character(agent, profile)` implements `PlayerProtocol`. One `select_action` per turn, then the four decisions off that belief. `SeededAgentMixin.choose_destination` gets a real default (weighted room features through the profile) so the `NotImplementedError` goes away; any agent may still override.
- `AGENT_SPECS` gains a `profile` field so `build_character("Peacock")` is one call.

**5c — arena.** `clude_training/arena.py`: N games among real characters, seat rotation, player count cycling 3–6 like `generate_snapshots`, calling Green's `observe(RevealedOutcome)` at game end (today only the benchmark does that). Metrics per character: win rate, wrong-accusation rate, turn of first accusation, own cards leaked. `scripts/arena.py` and `scripts/sweep_dial.py` (fix everything, slide one dial, plot the metrics).

**5d — tune and document.** Set presets so the arena reproduces the intended flavors, and write the results into `strategy-glossary.md` beside the Phase 4 table. The rule for keeping a dial: it must move at least one metric monotonically in the sweep, or it's cut.

## Three honest flags

- **Speed.** Plum runs a 200k-node search per call, and Green calls all five arms per call, so a six-seat arena game costs roughly two Plum searches per turn. The benchmark hides this because it samples checkpoints. Expect the arena to be slow; per-game budgets and a smaller default `n_games` are the first answer, memoizing Plum on the observation hash is the second.
- **Mustard's distribution shift gets worse.** His tree learned `RandomBot` games. In an arena of characters who actually reason, live play looks even less like his training data than the benchmark did. That's the flaw you chose to keep, so leave him, but the arena will make it loud. Retraining on character self-play is a natural Phase 7 item once logbooks exist.
- **Don't encode the flaw twice.** Mustard and White are already miscalibrated at the belief layer, measured. Their profiles should be neutral on `accuse_threshold` so the wrong accusations come from the method, not the dial, otherwise you can't attribute anything in the sweep.

## To confirm before code

1. 5a's seam: happy with `observer` injected into `run_game` rather than the engine importing the floor?
2. Dial count: the eight above, or trim the three room weights to one `curiosity` dial for a first pass?
3. `confidence_source` as a profile field, or should Peacock override `choose_accusation` outright?