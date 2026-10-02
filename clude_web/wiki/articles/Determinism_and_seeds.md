---
title: Determinism and seeds
short: What reproduces a deal, a numerical game or a recorded model run
categories: Measurement
redirects: Determinism, Seeds, Seed, Reproducibility
---
**Determinism and seeds** concern the reproducibility of [[clude]] games and measurements. A seed fixes a pseudorandom stream under a particular implementation. Reproducing a whole game also requires the same setup, decision policies and state; live model replies are not guaranteed by the numerical seed.[^engine]

The arena separates engine randomness from character choices so changed settings can share the same deals and dice. Saved answers and model recordings provide stronger replay controls. Remembered state must be included whenever it affects later decisions.

## Three reproduction questions

| Question | Required context |
|---|---|
| Same deal? | Seed, player count and setup procedure |
| Same headless game? | Deal and dice streams, roster, profiles, agent state and implementation |
| Same model-piloted game? | Those controls plus accepted replies or recorded requests and responses |

Changing a character's [[curiosity]] may preserve its deal and dice yet change the game. A new destination permits a different suggestion, which changes card evidence and later decisions. Pairing controls chance in the setup; it does not hold consequences fixed.

## Engine and character streams

The engine's seeded stream chooses the envelope, shuffles the dealt cards and supplies die rolls. A numerical character draws its sampled actions from a private stream. Arena floor fillers also receive private streams, preserving the engine's roll schedule when profiles change.[^arena]

`RandomBot` consumes the engine stream for movement, suggestions, accusations and card shows. The self-play floor regime also uses that stream unless given a private one. A run remains reproducible with its own unchanged setup, but replacing or retuning such a policy can shift the later dice. This is the exception to the usual arena pairing claim.

## Ordering and implementation

Seeded choice requires a stable ordering of candidates as well as a fixed random stream. Sets and process-dependent string hashes can otherwise change which item receives a drawn index. The engine sorts reachable destinations, and the exact method uses stable holder ordering.[^ordering]

An early ring-era sweep preceded the holder-order fix. Its values were paired within one process, but rerunning it on the fixed code changes some absolute outcomes. Historical records identify that limitation instead of claiming current exact reproduction.[^sweeps]

Changes to movement scoring or sample budgets can also change golden game fingerprints legitimately. The [[landing rule]] is an example of an adopted behaviour change with newly recorded references. A golden verifies a particular implementation's outcome, not an eternal rules transcript.

## Memory state

[[Method memory]] can alter a tree, an opponent prior or Green's arm draws. Narrative [[logbook]] context can alter model replies. Thus a remembered run is deterministic, where applicable, per seed **and starting memory state**, not per seed alone.[^memory]

Fixed-state comparisons load the same memory read-only. A writing arena instead measures an evolving sequence, where game order matters. Green's ordinary feedback also persists within an arena run, so constructing a fresh arm ensemble for every individual game is a different experiment.

## Model recordings and table replay

The wrapper's recorded backend stores model exchanges and keys them by a digest of the request. Replay serves the recorded reply only for a known request; a changed prompt can produce a replay miss. This tests exact prompt-and-response reproduction without another live call.[^backends]

The web table instead saves submitted decision answers and audits. Rebuilding its engine generator feeds those saved answers back, allowing a cold process to resume without asking the model to choose again. The replay uses actual stored decisions rather than assuming a fresh live response would match.[^table]

## Limits

A seed is an experimental control, not a complete portable description of a game. Stored records preserve the deal, decisions and settings needed to understand what actually happened. Latency, costs and external model replies can still vary across environments.

Reproduction evidence should name its scope: matching deals and dice, identical headless events, or replayed recorded replies. A [[twin comparison]] usually claims the first, while fallback and replay tests can establish the stronger forms under their stated inputs.


## See also

[[The deal]] · [[Arena]] · [[Twin comparison]] · [[Method memory]] · [[LLM wrapper]]

## References

{{references}}

[^engine]: {{cite:clude_core/engine.py|`setup` and `game_steps`}}
[^arena]: {{cite:clude_training/arena.py|private character and filler streams}}
[^ordering]: {{cite:clude_core/engine.py|`legal_moves`}} and {{cite:clude_agents/exact_enum.py|holder ordering}}
[^sweeps]: {{cite:docs/strategy-glossary.md|Dial sweeps}}
[^memory]: {{cite:docs/logbooks.md|Tier 1: method memory}}
[^backends]: {{cite:docs/llm-wrapper.md|Backends}}
[^table]: {{cite:clude_training/table.py|`TableGame` reconstruction}}

{{navbox:clude}}
