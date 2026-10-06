# Architecture

Read [README](../README.md) for setup. This guide describes the current checkout; completed phase plans record how it got here. Measurements belong in [the strategy glossary](strategy-glossary.md), commands in [CLI](cli.md), and deployment in [Web](web.md).

## Package layout

| Package | Responsibility | Boundary |
|---|---|---|
| `clude_core` | Cards, board, state, events and rules engine | No inference, storage, LLM or web imports |
| `clude_constraints` | Per-seat deduction and FloorBot | Consumes core observations |
| `clude_agents` | Six methods, registry, profiles and Character | Consumes masked observations; NumPy for Plum |
| `clude_llm` | Menus, prompts, backends, metering and debriefs | Wraps Character; replies cannot bypass validation |
| `clude_training` | Self-play, benchmark, arena, sweeps, replay, memory and TableGame | Reusable drivers; no Flask |
| `clude_storage` | Game/logbook documents and local/GCS stores | Same JSON keys for both backends |
| `clude_web` | Pages, accounts, table registry, MCP and Wikiclude | Transport and application policy |

`clude_training.__init__` avoids eager imports: Mustard imports `self_play`, so importing the arena from that initializer would create a cycle. `legacy/` is reference only.

## Environment

Python 3.14 and a plain venv. Use `.venv/Scripts/python.exe` explicitly on Windows. Developer dependencies are in `requirements.txt`; the container installs only `requirements-web.txt`. Plum uses NumPy; its trainer additionally uses PyTorch. GCS and Anthropic clients are imported when needed. No live service is needed by the default suite. Opt-in checks are in [Web](web.md#tests).

## The deduction floor (`clude_constraints`)

`observe(state, viewer)` builds a redacted `ClueObservation`, then attaches `propagate(obs)` as `obs.mask`. Propagation recomputes from visible history rather than carrying incremental hidden state.

`ConstraintResult.possible_holders` maps each card to possible seat indices and/or `"envelope"`. `hand_sizes` fixes capacity. `or_constraints` holds unresolved claims that a seat has at least one card from a set. Own hands, disproof order, private reveals, hand sizes and one envelope card per category are propagated to a fixpoint. Contradictions raise rather than silently discarding evidence.

`holder_of(card)` returns a proven holder or `None`; `solution()` returns the triple only when all categories are proven. Satisfied OR constraints are removed so methods do not reuse them as unresolved evidence. `tests/test_constraints.py` checks soundness against dealt games.

## `ClueObservation`

The agent's input, distinct from omniscient `GameState`: seat index, own hand, active seats, hand sizes, suggestion/accusation logs, turn, suspect tokens and optional mask. `suspects` supplies seat-order tokens, with a fallback for older hand-built observations.

`for_player(state, viewer)` retains `card_shown` only for suggester and refuter. It leaves `mask=None`; use `clude_constraints.observe` for agents and FloorBot. The mask type is imported under `TYPE_CHECKING` to avoid a core/constraints cycle. Movement positions are conveyed by legal choices rather than added to this contract.

## The engine seam (Phase 5a)

`PlayerProtocol` asks four questions with the deciding seat's observation:

| Method | Answer |
|---|---|
| `choose_movement(obs, choices, rng)` | One offered `MoveChoice` |
| `choose_suggestion(obs, room, rng)` | `(suspect, weapon)` or `None` |
| `choose_accusation(obs, rng)` | `(suspect, weapon, room)` or `None` |
| `choose_card_to_show(obs, candidates, shown_to, rng)` | One offered card |

`run_game` accepts an injected observer; the default is `for_player`. Numerical characters need `observer=clude_constraints.observe`. A fresh view after refutation lets the accusation see new evidence. `SpeakingPlayer` appends remarks to the log without changing rules; chat is never formal evidence.

### Resumable: `game_steps` (Phase 8.1)

The turn loop is written once as `game_steps`. It yields a `LiveGame` handle, `DecisionRequest` for an external seat, and `TurnComplete`. Drivers send answers with `steps.send(answer)`. `run_game` drains it without external seats; `TableGame` pauses it for human and externally driven LLM seats.

`TableGame.answer` checks the sequence and calls `engine.check_answer` **before** sending into the generator. An exception inside a generator closes it, so invalid user answers must be rejected outside it.

Cold tables restore their setup, memory snapshot and ordered entries into a fresh driver. Model answers, audits and remarks are persisted; rebuilding never calls the model. Live games are caches, not the persistence authority. See [table lifecycle](web.md#a-table).

## `AgentProtocol`

`select_action(obs)` returns `ClueBelief`, despite its historical name: it does not select a game action. `probabilities` covers all 21 cards and sums to one **within each category**. `extra` carries diagnostics. `mask_and_normalize` forces eliminated candidates to zero and proven ones to one; zero raw mass falls back to uniform over allowed cards.

`reset(seed)` initializes state/RNG, `choose_destination` owns room choice, and `observe(transition)` accepts feedback. Green learns from `RevealedOutcome`; other methods currently have no outcome update. `AGENT_SPECS` maps suspect names to factories, presets and confidence functions. Use `build_agent` for belief and `build_character` for a player.

Optional pure hooks `movement_scores(obs, choices, features, profile)` and `suggestion_scores(obs, candidates, category)` return `[0, 1]` scores in candidate order. Character and LLM menus share those hooks. They must not draw randomness or mutate state, so fallback preserves the ordinary character's RNG path.

## Method-to-suspect mapping

[README](../README.md#the-six-methods) lists live methods. `ExactEnumAgent` is now **PlumOG**, absent from the registry and Green's arms; it remains for historical analysis and tests.

Plum uses `deep_nash.py` and committed `weights/plum.npz`, still seeded initial weights. Smoke checkpoints under ignored `data/plum-training/` are not the active agent. [Phase 12](deepnash-plan.md) owns training, limitations and acceptance steps.

## Per-turn data flow

```text
GameState -> observing seat's ClueObservation -> deduction mask
          -> agent belief + optional policy scores
          -> Character decisions (Profile)
          -> optional LLM choice from a leashed legal menu
          -> engine validation/application -> events
```

Web/MCP adapters expose each viewer's permitted payload despite holding omniscient state. Replay is deliberately face up.

## Room/suggestion target selection is not the same problem as belief

Belief estimates the envelope; movement chooses how to gather information. The shared policy blends room information/proximity through `curiosity`, then samples with `temperature`. A room placed in another seat's hand is a place to travel through rather than a landing target. Own-hand/envelope rooms remain useful for testing suspect and weapon. This landing rule fixed passage loops.

Plum's network owns movement and honest suggestion scores, so `curiosity` is inert for him. Bluffing, accusation and card disclosure remain Character decisions.

## Personality layer (Phase 5c)

`Character` caches belief per observation and implements PlayerProtocol. Profile has eight dials:

| Dial | Effect |
|---|---|
| `accuse_threshold` | Accuse when the product of category maxima reaches the threshold |
| `bluff_rate` | Chance of naming an own-hand card rather than an honest candidate |
| `curiosity` | Shared movement blend; inert for Plum |
| `secrecy` | Prefer re-showing a card to the same recipient |
| `temperature` | Softmax sampling; zero is greedy |
| `leash` | Permitted distance below the best score for LLM choices |
| `chattiness` | Gate proposed remarks |
| `memory` | Narrative read-back depth with a logbook |

Peacock accuses on the Dempster-Shafer lower belief bound; others use envelope probabilities. Presets live in `personality.PRESETS`. The glossary records dated tuning, including PlumOG results.

## The LLM wrapper (Phase 6)

`LLMCharacter` wraps Character and implements SpeakingPlayer. It builds RNG-free menus, asks a backend when a choice exists, validates the reply and otherwise falls back to Character. NullBackend is the deterministic control. Persona/rules files are executable prompts; changes require new recordings after spend approval. See [LLM wrapper](llm-wrapper.md).

## Memory: the logbooks (Phase 7)

Records are omniscient source data; method memory is numerical; entries and the rolling head are narrative. Mustard, White and Green have method memory; LLM characters can additionally have narrative memory. New web tables remember by default, legacy documents without the field retain `False`, and CLI runs opt in. [Logbooks](logbooks.md) owns schema, depths and reset/rebuild.

## Self-play regimes: `RandomBot` and `FloorBot` (Phase 5b)

FloorBot is the default snapshot/training opponent: it names unlocated cards, seeks useful rooms and accuses only on proof. RandomBot is the rules-exercising baseline.

Historical Phase 5 measurements: FloorBot games end in about 12-23 suggestions with a third of viewers holding a proven envelope at the end; the old regime ran 80-180 suggestions with a floor that plateaued early. These are ring-era results, not estimates for the current board/network.

Plum trains from whole-game Episode rollouts, not benchmark snapshots. `RecordingPlum` samples policies at a mixed population of tables; `scripts/train_plum.py` fits policy/value/belief heads. [Phase 12](deepnash-plan.md) records smoke-run limitations.

## Arena, sweeps and game records (Phase 5d)

The benchmark measures beliefs on shared snapshots; the arena measures full games. Green receives outcome feedback per snapshot in the benchmark, per game in the arena. Sweeps use paired seed sequences and fixed memory when requested. Deals/dice match; action paths and game lengths can differ.

GameRecord includes seats, profiles, deal, omniscient events, outcome and optional model audit/costs. `RECORD_VERSION=3` is the Classic grid; versions 1/2 remain readable with ring HallwayCell positions. Traces use fresh agents/current weights without live method memory or Green's feedback. They are reconstructed estimates, not recorded live beliefs.

## Cloud Storage

RecordStore supports local/GCS backends through the same keys:

```text
runs/<run_id>.json                 settings and summary
games/<run_id>/<index>.json        omniscient record
traces/<run_id>/<index>.json       reconstructed trace
logbooks/<identity>/               entries, head, method memory
users/<account>.json              account
tables/<id>.json                  setup, entries, lifecycle
spend/<date>.json                 UTC-day usage
spend/tables/<id>.json             usage across midnight
```

Credentials resolve from explicit path, `CLUDE_GCS_CREDENTIALS`, ignored `clude-game-sa.json`, then application default credentials. Cloud Run uses its runtime identity. Never commit/print credential files. [Web](web.md#deploying) owns deployment configuration.

## Claude API credentials (Phase 6c)

The CLI backend uses SDK credential resolution; export `ANTHROPIC_API_KEY` for direct scripts. Web configuration additionally reads selected `.env` values; Flask's CLI can load it through python-dotenv. Direct Python commands do not do that automatically. The default model is a repository setting, not a claim about provider availability/pricing. See [Backends](llm-wrapper.md#backends).

## Deferred legacy code

`legacy/` is never imported. Its DQN/GNN/all-purpose agent does not implement the six-method design. See [legacy README](../legacy/README.md).

## Reveal integrity and the lying/expulsion house rule

Talk/bluffing about one's hand is allowed. Formal refutation uses actual hands to find the first matching seat and offers only held cards. A spoken refusal cannot replace this check. Invalid external answers are refused without changing the game; timeout/autopilot uses FloorBot. Expulsion for refusing a mandatory reveal is a product backstop, not a separately implemented engine state.

## Deployment cost

Configuration has one worker and at most one instance, scaling to zero. Tables advance during requests; there are no persistent game workers or websockets. Timings/cost observations in [Web](web.md#deploying) are dated evidence, not billing guarantees.

## Seats and player identity (both halves built)

A token is a suspect; a seat is its position in turn order; a label is persistent occupant identity. Characters use their own tokens; human/MCP labels use normalized account keys independent of token. Display capitalization changes no record/dossier key.

SeatSpec stores token, kind, label and LLM narrative depth. Stored kinds are `character`, `llm`, `floor`, `random`, `human`, `open`; `empty` omits a token in the form. Open seats must fill before dealing. The registry applies memory/transport policy around the Flask-free driver. MCP uses a human seat with `by="mcp"` answers, its own reasoning and no character agent/persona.

## Open questions

[The roadmap](phase-plan.md) and [Phase 12](deepnash-plan.md) track unfinished work. The parking question was resolved by Phase 8.0.4's landing rule.
