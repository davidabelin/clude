# clude

A web app for playing Clue with a mix of human and LLM players. The name is a nod to Claude.
Owner: David (David Abelin, github.com/davidabelin). Solo project.

## Status (September 2026)

The design was worked out in claude.ai conversations. No engine code exists yet.
`legacy/` holds code from an earlier chat, which is material to port from rather than a foundation to build on.
Read `legacy/README.md` before touching it, because several pieces are unfinished.

## Settled decisions (David's)

- **Six LLM characters, one per suspect.** Each uses a genuinely distinct probability method: six real algorithms, not one engine with six parameter sets. Part of the point is revisiting old-school ML methods David studied but never got to play with enough.

  | Suspect | Method | Intended flavor |
  |---|---|---|
  | Scarlett | Naive Bayes | Overconfident, accuses early |
  | Plum | Exact posterior enumeration over consistent deals | Correct but slow |
  | Peacock | Dempster–Shafer belief/plausibility | Cautious, won't commit until plausibility collapses |
  | Mustard | Decision tree trained on game logs | Pattern-matches, confidently wrong on unusual deals |
  | Green | Bandit ensemble over the other five methods | Ports almost directly from rps `multi_armed_bandit.py` |
  | White | Markov model over opponents' suggestion sequences | Reads people rather than cards |

- **Each character's turn** works in two steps. It calls its own strategy model for numbers, then combines those numbers with its personality settings to choose an action.
- **In-game chat.** Characters initiate and respond even off-turn, gated by numeric settings such as a chattiness dial.
- **Persistent logbooks.** Each character writes to its logbook after every game.
- **Sequencing.** First the models work and players receive numbers from them. Personalities and memories come after that.
- **Documentation.** Each player's model and strategy gets documented in detail.
- **Parallel design track.** Aesthetics, gameplay design, and UX are developed alongside the model work.
- **IP.** clude stays a private project shared with a few family and friends, so it copies the Classic board game as closely as possible. That means the real rules, suspects, weapons, and rooms under their real names: Miss Scarlett, Colonel Mustard, Mrs. White, Mr. Green, Mrs. Peacock, Professor Plum, with card lists as in `legacy/domain.py`. If it is ever published (e.g. to an app store), scrub it for infringement first. Visual assets are drawn fresh rather than copied from the board or card art.
- **Structure mirrors David's `rps` repo** (and `c4`, which already copies it):
  - a shared `AgentProtocol` with `reset` / `select_action` / `observe`
  - an `AgentSpec` name-keyed registry
  - one module per method
  - sibling packages in the style of `rps_agents`, `rps_core`, `rps_training`, `rps_storage`, `rps_web`, plus `scripts/`, `tests/`, `docs/`

## Architecture direction (agreed in principle, details still to plan)

- **Shared deduction floor.** A constraint-propagation layer masks logically impossible worlds before any agent's output is used, and each agent's probabilities are renormalized over what survives. Agents differ in how they reason under uncertainty, never in what is logically certain. `legacy/constraints.py` is the starting point, but it needs finishing first.
- **Observation contract.** One `ClueObservation` / event contract that every agent consumes. Design it first, and make the event log rich enough to support post-game replay of all six belief traces.
- **Mustard needs data.** His tree trains on game logs, so a headless engine plus self-play has to exist before he can.
- **Logbooks as data.** Logbooks may later become training input for Mustard and extra history for White.

## Proposed but not yet confirmed by David

Treat these as suggestions to raise, not decisions to implement.

- **Setting (shelved).** Not used while the game uses the Classic names. It is kept here as a ready-made reskin if clude is ever published: the stormbound ocean liner *SS Meridian*, chosen to avoid Hasbro's trade dress.
  - Rooms: Wheelhouse, Wireless Room, Grand Saloon, Purser's Office, Boiler Room, Galley, Promenade, Stateroom, Cargo Hold.
  - Cast: Ms. Vermilion (Scarlett), Cpt. Ochre (Mustard), Dr. Indigo (Plum), Mme. Verdigris (Peacock), Mr. Sable (Green), Sister Celadon (White).
  - Weapons are not chosen yet.
- **Visual direction.** Mid-century modernist structure, with case-file styling reserved for the logbook and post-game replay.
  - The signature element is a two-tone belief/plausibility bar for every player: solid means logically forced, pale means still plausible.
  - Each character's method appears under its name, as a toggle.
- **Post-game replay** of all six belief traces as the payoff feature and debugging tool.
- **Chat pacing.** Stagger arrivals and cap concurrent speakers at two. The chattiness dial gates participation, not just verbosity.
- **Phasing.**
  1. Headless rules engine, dumb bots, and event log.
  2. Deduction engine, with tests that it converges.
  3. Personality parameters, with self-play checks that they actually move win rate.
  4. LLM wrapper.
  5. Flask front end, then chat, then human seats.
- **Deployment.** Cloud Run rather than App Engine, since live chat wants websockets. David's other apps run on App Engine.
- **Logbook reset.** A "reset logbooks" control for fairness.
- **Seats and player identity.** Each suspect is a Seat, occupied by a
  human or a fixed, seat-locked cludebot. Human identity is a chosen
  display name, independent of seat, so tells persist across games
  regardless of which suspect they play next. Logbooks split into an
  immutable per-game entry and a mutable per-opponent dossier that
  actually carries tells forward. Details and rationale in
  `docs/architecture.md`.

## Open questions (ask, don't assume)

None outstanding as of 2026-09-11. Resolved:

- **Talk/bluffing about own cards:** allowed. Characters may hint, bluff,
  and make side-bets about their own hand at their own discretion, and are
  meant to learn the cost of over-sharing rather than have it designed
  away. House rule: refusing a reveal you are actually required to make
  (the formal suggestion-refutation step) is system-enforced expulsion,
  not just a bad move -- see `docs/architecture.md` for why the engine
  already makes this hard to violate by accident.
- **Human tells across games:** yes, logbooks must remember them,
  independent of which suspect/seat the human plays next -- see the Seat
  model discussion in project notes.
- **Python/conda:** Python 3.14 venv, no conda -- see `docs/architecture.md`.
- **Deployment target:** Cloud Run, budget permitting -- see
  `docs/architecture.md` for the cost caveat.

## Working with David

- Confirm shared understanding of a plan before writing code.
- Break large efforts into ordered phases. Change working systems one incremental step at a time.
- Prefer simple, pragmatic, modular code with docstrings, error handling, and unit tests.
- Build headless/CLI first and stay general before investing in UI.
- Give honest, independent evaluation. Say so when something is a bad idea.
- Get something working first. Brief theory tangents are welcome after that.

## Environment

- Windows 11 laptop ("Orbit"): i7-11800H, 32 GB RAM, RTX 3080 Laptop GPU.
- Editor: VS Code.
- For CUDA to engage, Python may need to be added to Windows' high-performance GPU app list.

## First session

Read this file and `legacy/README.md`, and look at github.com/davidabelin/rps for conventions. Then produce the phase plan and architecture (package layout, `AgentProtocol` for Clue, `ClueObservation`, and the deduction floor) and present it for review before writing code.
