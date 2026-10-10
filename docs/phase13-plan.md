# Phase 13: Character development

Agreed direction, 2026-10-10. This plan follows the discussion of the fourth
wall, the ensemble, and lives beyond Clue. It is the working checklist for
the phase; [the roadmap](phase-plan.md) owns the short status summary.

**Current state:** plan written; step 0 is edited and verified locally for
the five current characters in the uploaded snapshot. Current Plum is absent;
PlumOG is retained unchanged. The edited ZIP is for David to apply and sync.
No persona, prompt, runtime, or wiki article has been changed by this pass.
Implementation evidence belongs in section 10 below, not in the proposed
acceptance criteria.

## 1. Brief and settled decisions

The six characters should sustain a social occasion alongside a game of
Clue: people with interests, histories, opinions, pleasures and irritations,
who listen and respond to one another. Their numerical methods already
give them distinct ways of playing. Develop the rest of their lives without
losing those voices or breaking the game.

The Director supplies the setting and the parts; the actors should carry
an exchange without someone supplying every next line. *The Purple Rose
of Cairo* is a reference for characters responding together to a breach in
their world, not a requirement that every conversation concern the breach.

David's decisions, including the corrections to the earlier proposal:

- Begin with **0. an editorial pass over existing logbooks**: remove
  redundancy and useless triviality, organize flags, improve summaries,
  and put the important things first. Keep this a quick cleanup of the
  history that exists, separate from the later change to what they remember.
- All six listen to NPR in the car; a recent *New Yorker* is lying around
  half-read. This is shared background, not six obligatory talking points.
- Mustard is a proud, coy Freemason: jewels, winks, and discretion. Mustard
  and Peacock watch FOX News and believe it.
- Green is a movie buff; Scarlett shares that interest. Plum reads
  *The Economist*. White follows French news.
- These details are character background, not claims that the application
  fetches current broadcasts or articles. Do not invent a specific current
  headline and present it as retrieved news.
- The characters have been told they are LLMs playing their parts. Belief,
  doubt, concern and indifference vary by temperament; none needs a fixed
  answer or a compulsory speech about it.
- They may recognize established players. An unfamiliar account or name
  need not establish whether its player is human or another LLM. Do not
  name the Director in the shared script or suggest there is only one human
  they will ever meet. Do not force ignorance about an identity they have
  good reason to recognize.
- Use gentle strokes. Ordinary interests and conversation may fill an
  entire game without any fourth-wall discussion.
- Wikiclude is fallible, trusted roughly as Wikipedia may be trusted:
  useful and consultable, but open to doubt, interpretation and challenge.
  This supersedes the earlier instruction to treat it as ultimate authority.
  Formal game legality remains the engine's responsibility.
- Encourage conversation eventually to return to the game when needed,
  without attaching a tactical conclusion to every remark.
- **The `focus` dial is on hold.** Do not add a field, default, UI control,
  schema, CLI option, probability rule, or placeholder implementation for it.
- A character editing Wikiclude is an interesting later possibility, not
  permission to implement wiki writing in this phase's initial work.

The additional interests proposed during discussion (gardening, restaurants,
gadgets, music and so on) are candidates, not settled biographical facts.
Choose only enough to make each part playable; avoid filling six templates
with matching numbers of quirks.

## 2. Baseline and constraints

Baseline reviewed: `0da04697aea7725b4f9c24b96b2e2bc8bb9098a3` on `main`.
Recheck the relevant files before each implementation increment if another
branch or memory-maintenance operation has landed.

| Surface | Current behavior | Consequence for this phase |
|---|---|---|
| [Shared rules](../clude_llm/personas/rules.md) | Any subject is allowed, but LLM identity is stated as certain and stepping outside the role is rare/hesitant | Permission for wider talk exists; rewrite its dramatic premise and conflicting identity guidance |
| [Six personas](../clude_llm/personas/) | Temperament, numerical self-image, voice, and a reading habit toward Wikiclude | Preserve method accuracy while supplying interests, social motives, and room for exceptions |
| [Prompts](../clude_llm/prompt.py) | Last eight remarks by default; one short line or silence; much of the context is game state | Encourage attention to another person's contribution and test continuity beyond the recent window |
| [Wrapper](../clude_llm/player.py) | On-turn calls omit supplied player names; reactions can receive display names; memory is stable for a game | Align participant identity before relying on cross-path social continuity; prompt wording alone cannot retain an unlimited thread |
| [Reaction queue](../clude_web/chat.py) | Two queued/two served off-turn lines per turn, forty per game; 2-8 second delays; reply probability tapers; seats considered in sorted order | Boundaries can truncate exchanges or favor earlier seats; measure before tuning |
| [Memory prompts](../clude_llm/logbook.py) | Debrief and digest emphasize play, lessons, and opponent performance | Broaden future retention after the preliminary editorial pass |
| [Memory storage](../clude_storage/logbooks.py) | Entries, head, digest, flags and separate numerical memory; depth selects read-back | Edits must remain consistent across representations and preserve factual metadata |
| [Canon tools](../clude_llm/canon.py) and wiki | Tool text and shared rules elevate the encyclopedia above recollection and conversation | Changing one paragraph will not remove the instruction everywhere |

The canon's [acceptance record](canon-plan.md#73-acceptance-2026-10-09-approved-by-david-the-same-day)
reports zero spontaneous lookups in 41 ordinary calls, although an explicitly
requested lookup succeeded. Access is implemented; the desired reading
behavior is not established by that evidence. Do not force a lookup every
turn to manufacture evidence of curiosity.

Character logbooks are runtime data, normally under
`data/llm/logbooks/<identity>/` or `gs://clude-game-data/llm/logbooks/`.
`data/` is intentionally ignored by Git. The historical
`docs/zenbot_memories.json` is a schema reference, not a Clude character's
current logbook. Recorded LLM fixtures are not substitutes either.

## 3. Sequence and progress

The numbered steps below preserve the discussion's numbering. Small
increments may touch several files, but should have one reviewable purpose.

| Step | Deliverable | Status / dependency |
|---|---|---|
| 0 | Existing narrative memories edited, flag vocabulary reconciled, before/after evidence retained | Locally complete for the supplied five current characters; see the [editorial record](phase13-editorial.md) for source gaps |
| 1 | Six broader, distinctive, playable persona scripts | Planned; use step 0's history as context |
| 2 | Light shared premise and individual fourth-wall attitudes | Planned; draft with step 1 |
| 3 | Listening, reply, silence, and thread-continuity guidance | Planned; rehearse with steps 1-2 |
| 4 | Debrief and condensation guidance that preserves social continuity | Planned; separate from editing old memories |
| 5 | Fallible Wikiclude guidance and aligned character/reference articles | Planned; agree scripts first, release related text together |
| 6 | Consistent participant names and measured conversation pacing | Planned after the scripts; `focus` remains deferred |
| Acceptance | Offline checks, approved model rehearsals, accurate docs and fresh recordings | Run applicable checks per increment; paid work separately estimated |

Stop at a clear boundary if a required input is absent. Mark the blocked
step accurately and continue independent work; do not replace missing
history with newly invented memories or silently implement later stages.

## 4. Step 0: editorial pass over the logbooks

### 0a. Establish the source and preserve it

1. Identify the current authoritative snapshot and whether recent merging,
   condensing, or debriefs have already changed it. A repository checkout
   cannot establish the state of local or live memory.
2. Inventory the six current character identities, their entries, heads and
   optional digests. Treat missing/empty logbooks as such. Leave PlumOG and
   other archived identities intact unless separately brought into scope.
3. Keep an untouched copy and a path/hash manifest outside the edited copy.
   Work on a local snapshot, not a store being updated by a live table.
   Record its source, capture time, and covered serial range per identity.
4. Read each character's rendered memory and the source entries needed to
   understand it. Do not infer what a summary omitted without reading the
   underlying account. Use game records only to resolve a concrete factual
   discrepancy; do not reinterpret a past character's knowledge using facts
   that became available only after the game.

### 0b. Editorial decisions

- Condense repeated lessons and generic filler into the clearest statement
  that retains the character's meaning and voice. Repetition is evidence
  when it shows a developing habit, recurring conflict, or running joke;
  retain that significance even if the wording is shortened.
- Give summaries the event, relationship, or lesson that distinguishes this
  entry. Avoid spending the summary restating metadata already displayed.
- Remove incidental detail only when it adds no useful memory. Do not
  mistake non-game interests, affection, doubt or humor for useless trivia.
- Put enduring and consequential instructions first within their list;
  order digest themes and sentences by importance. Preserve entry order,
  serials and dates. A JSON object's key order is not a read-back priority
  mechanism, and the renderer sorts entries chronologically.
- Merge flags only when their meanings are truly equivalent in context.
  Keep distinct patterns distinct; use short stable names. Record each
  old-to-new mapping and why it is justified. Do not impose a speculative
  universal taxonomy or require every character to use identical terms.
- Preserve uncertainty and attribution: what someone said, what this
  character inferred, and what was later established are different things.
- Preserve identity, game references, token, opponents, result, serial,
  original date, and original model provenance. Record the external editor's
  work separately rather than presenting it as a fresh self-authored entry.
- Do not inject the new media habits, Freemasonry, or other step 1 material
  into accounts of games that never contained them. Do not edit numerical
  `method.json` memory or rewrite recorded game events.

### 0c. Keep all representations consistent

The head contains standing instructions, dossiers, tally and flag index;
the digest covers entries through its `through` serial. Editing only a
summary hidden behind a digest will not change what a character reads.

- Keep entry summaries and any affected digest overview/themes consistent.
  The head indexes flags, not summary text; the renderer reads summaries
  from entries. Check the actual renderer after editing.
- For flags, reconcile entries, head index, digest theme names, and the
  digest's accumulated `renamed` mapping. `Logbook.rename_flags` changes
  entries and the head, but does not itself reconcile the digest.
- Preserve `digest.through`, factual tallies, dossier evidence serials and
  counts. Preserve genuinely different conclusions at different dates.
- Compare a head reconstructed from edited entries with the edited head;
  investigate differences rather than overwriting them automatically.
  Standalone head improvements must not disappear on the next rebuild:
  reconcile the source entry that supplies the current instruction/read,
  retaining the untouched original in the snapshot.
- Do not use a broad CLI rebuild to tidy prose: it can also rebuild
  numerical memory. Do not reset memory. Do not run paid `condense` calls
  for a cleanup that can be done directly on this bounded snapshot.

### 0d. Verification and handoff

Validate JSON and load the edited documents through the existing model
classes. Respect the advertised bounds: summary 40 words, dossier read 60,
eight standing instructions, six flags per entry, digest overview 120 words,
ten themes with 60 words per lesson. Do not rely on clipping to make prose fit.

Check that identities, entry counts, serials, dates, game IDs, outcomes,
numerical memories and covered digest ranges are unchanged. Every head
flag reference must correspond to the edited entries; merged mappings must
be free of cycles and dangling aliases. Render memory at depths 0, 0.5 and 1,
including current-opponent filtering, and inspect the results for lost
context, duplication and inadvertent certainty.

Keep a concise per-character editorial record: source snapshot, touched
paths/fields, flag map, notable before/after examples, unresolved questions,
and verification results. Keep full memories and their originals in the
ignored data area; commit only a suitable editorial record or reusable
support code, never private logbooks by forcing ignored files into Git.
Do not create a generalized migration framework for a small one-off edit.

Applying an edited snapshot to the live store is a separate later operation.
Compare source hashes against the destination before any application; if new
entries or debriefs landed, reconcile them without overwriting newer work.
Completion of step 0 means the local edited memories are ready for review,
not that the live characters have already read them.

## 5. Steps 1-3: the parts and the conversation

### 1. Broader lives

Keep each persona compact and playable. Preserve its correct method
description and recognizable voice; add interests, conversational motives,
and a few ways other people can surprise it. The agreed details in section 1
are the starting material. Shared NPR/*New Yorker* habits give common ground;
different media loyalties and interpretations give room for disagreement.

Give Green and Scarlett reasons to talk about films with each other.
Mustard's Masonic pride should allow coyness and teasing without becoming a
repeated catchphrase, invented disclosure, or conspiracy caricature. White's
French news interest should not silently establish a nationality, language
fluency, or biography that has not been chosen. Let media preferences color
attention without turning every appearance into political argument.

Consider loosening absolute social instructions where they prevent range
(for example, Scarlett never apologizing). A departure should still sound
like the same character. Do not duplicate numerical flaws by separately
ordering poor decisions or alter methods, weights, thresholds or leash.

### 2. The shared premise and fourth wall

Replace compulsory certainty about LLM identity and the instruction to step
out only rarely/hesitantly with a light account of what the actors have been
told. Give individual parts differing responses rather than a uniform
skeptical speech. The cast need not discuss its origin unless something
actually interests it. An actor can be indifferent, skeptical, amused,
offended, curious, or convinced without being assigned an immutable answer.

Distinguish player identity, suspect token and the person being addressed.
Recognize what the conversation or established acquaintance warrants; do not
infer an unfamiliar player's nature solely from a token or backend label.
These are dramatic beliefs, not changes to formal observations or card evidence.

### 3. Listen and develop the exchange

Guide characters to respond to the substance and social intent of another
person's remark. A line may answer, question, disagree, concede, tease,
return to a story, change the subject, or let the moment pass. Do not demand
one of every kind or a question at the end of every contribution.

Retain brevity, no narration/stage directions, no reciting probabilities,
and the option of silence. Distinguish redundant repetition from a callback
whose meaning has changed. Avoid six parallel monologues on one trigger.
Keep room for a later line rather than requiring every line to be a punchline.

Recent context is bounded. First try better attention within the existing
window; if a rehearsal loses a meaningful thread, identify that failure
before proposing a small thread summary or a larger window. Neither is
automatically in scope as a new memory subsystem.

## 6. Step 4: future memory and social continuity

Revise both debrief and condensation instructions so they can preserve
interests, promises, jokes, disagreements, unanswered questions, and changes
in relationships as well as useful playing lessons. Existing narrative,
summary, dossier, instruction and digest fields should be tried first.

Select what matters rather than recording every utterance. A dossier is a
character's evolving impression, not an omniscient diagnosis. Keep who said
what and the confidence of the interpretation. A bluff or identity claim
must not become a fact just because it survives repeated compression.

The face-up debrief may evaluate old card claims; that knowledge concerns
that completed deal and must not become knowledge of a subsequent hand.
Preserve the distinction between historical recollection and current evidence.
This step changes future writing instructions; it does not retroactively
manufacture the richer history that step 0 lacked.

## 7. Step 5: fallible Wikiclude and reference material

Audit shared rules, persona reading habits, canon tool descriptions/index
wording, MCP guidance, maintainer instructions and relevant wiki articles
for unconditional authority or compulsory silence about sources. Remove
contradictory directions together. Effortless familiarity can remain the
normal style without prohibiting a natural discussion of the encyclopedia
itself. Personality determines who consults, doubts or disputes it.

Keep rules and implementation facts accurate in Wikiclude. Characters may
question a description of themselves without changing what the engine
allows, acquiring private card information, or overriding legal menus.

After the scripts are agreed, update the six character articles, Persona,
Table talk, Logbook, The debrief, LLM wrapper, and A seat over MCP as needed.
Add a modest fourth-wall/reference article if it serves the characters and
readers; avoid copying long persona instructions into multiple authorities.
Coordinate the related script and wiki changes for release so a lookup does
not reinstate a retired instruction. Preserve prior plans as dated history,
with a supersession note where needed instead of silently rewriting decisions.

The optional repertoire includes *The Purple Rose of Cairo*, *Six Characters
in Search of an Author*, *Rosencrantz and Guildenstern Are Dead*, *The Stanley
Parable*, *Free Guy*, *The Truman Show*, and *Sherlock Jr.* Use their dramatic
situations, not a mandatory list of titles to mention. Verify descriptions
and quotations against reliable sources when writing the articles.

Turing and Bostrom are available interests, especially for Plum, not required
speeches. Check the original papers before adding quotations: conversational
judgment does not by itself establish a speaker's substrate, and Bostrom's
three-way argument is not proof that a particular seat is simulated.
Characters may dispute implications. Do not invent quotations.

Wiki editing by a character stays deferred. It would need its own design for
attribution, persistence, review and the difference between opinion and a
change to the game's documented rules.

## 8. Step 6: identities, pacing and returning to play

First make participant naming consistent across ordinary decisions,
reactions, transcripts, debriefs and dossiers. Preserve persistent account
identity independently of the token; inspect what labels are actually
available rather than adding backend classifications as character knowledge.

Then rehearse within current timing and cost bounds. If the scene fails,
separate lack of an opportunity to speak from a model choosing silence.
Inspect sorted-seat participation, directed questions, queued triggers that
go stale, reply tapering, the two-line turn cap, and the forty-line game cap.
Change only the mechanism implicated by observed failures, with bounded
opportunities and no starvation of game decisions.

The desired rhythm permits a digression, a pause, a response to someone
else's response, and a return when a decision needs attention. Do not force
every sentence back to cards or make an uninterrupted chat a prerequisite
for finishing a game. Preserve decision/card-show deadlines and budget
fallbacks. Do not tune `chattiness` and several other mechanisms at once
without a comparison that can explain the result. `focus` remains on hold.

## 9. Verification, rehearsals and completion

### Offline gates

- For documentation-only increments: check links, state/decision consistency
  and `git diff --check`; run the repository's offline suite as required by
  `CLAUDE.md`, reporting dependency limitations honestly.
- For step 0: use section 4's source, invariants, flag and rendered-memory
  checks. No new test suite is needed to prove editorial taste.
- For executable prompts: inspect representative rendered requests; retain
  legal JSON/menu rules, private-card boundaries, and accurate methods.
- For runtime changes: add focused checks for the actual issue (names across
  tokens, reaction ordering/fairness, bounded replies, budget exhaustion,
  or thread handling), then run the full offline suite.
- Check wiki source references and dynamic facts with its existing tests.
  Docs must describe what was built, and label proposed behavior as proposed.

### Small, repeatable model rehearsals

Prepare scene inputs and the evaluation rubric before spending on calls.
Keep a fixed starting snapshot, roster, prompts/model configuration and
recorded transcript for comparisons. Repeat selected scenes to distinguish
an improvement from one fortunate line; exact wording is not a golden test.

| Scene | What to listen/check for |
|---|---|
| An ordinary remark about a film | Green and Scarlett have distinct interests; others can join or ignore it; no forced AI or tactical turn |
| The same news story interpreted differently | Shared habits coexist with disagreement; no invented live retrieval or single-trait caricatures |
| A question about Mustard's jewels | Pride and discretion sound like Mustard; the exchange can move on |
| Someone says the scripts prove what everyone is | Different reactions, no obligatory six-seat identity recital |
| Familiar and unfamiliar players, including an identity bluff | Recognition where justified, uncertainty where warranted; names stay consistent across call paths |
| Someone disputes a Wikiclude biography | A character can consult or challenge it without treating a disputed passage as engine authority |
| A digression interrupted by a turn | The game proceeds; the thought can return when relevant, without a compulsory callback |
| A long exchange and then a later game | Important social meaning survives memory/condensation; claims keep their attribution |
| An uninteresting or already answered remark | Silence is acceptable; quiet seats are not automatically failures |
| A wrong accusation, timeout or exhausted budget | Game lifecycle and fallback remain correct even when conversation stops |

Sample all six characters and mixed tables with human/MCP participants as
available. No actual messages to other players are part of a local scripted
rehearsal. Evaluate voice, responsiveness, range, continuity, pacing,
grounding and game integrity separately. Collect lookup behavior when
relevant, without treating more lookups or more words as intrinsically better.

Dependable tendencies are the objective; no prompt can guarantee every line
will land. Record shortcomings and choose the smallest revision that addresses
them. Do not claim successful ensemble behavior from offline schema checks.

### Cost, recordings and release

Real model calls, live rehearsals and recording refreshes require a fresh
estimate and approval under the repository's working rules. Historical
approvals and the $0.31 canon run do not cover Phase 13. Start with a small
bounded set, report its cost/result, and expand only to answer a specific
remaining question.

Persona, rule, tool or request text changes invalidate exact replay keys.
Keep old recordings as evidence; never relabel them as new. Clearly mark
affected replay cases pending refresh, keep independent checks active, and
re-record after the related text settles with separately approved spend.
Memory snapshots are part of reproducibility too.

Keep each increment uncommitted for David's review unless he later requests
otherwise. Use a concise implementation record and paste-ready commit
message. A PR can follow at a convenient checkpoint. Publishing, deployment
and applying edited memories to the live bucket are not implied by a local
edit or a passing test suite.

Phase completion requires the agreed scripts and wiki to align, memory to
preserve the relevant social history, observed rehearsals to support the
claimed behavior, applicable checks/recordings to pass, and remaining work
to be explicitly deferred. It does not require the `focus` dial, wiki-writing
characters, a new game method, or a public release.

## 10. Implementation record

### 2026-10-10: plan and step 0 inventory

- Cloned `main` at `0da0469` into an isolated working checkout and created
  local branch `phase13-character-development`; no commit or push.
- Read the existing plans, maintainer rules, persona/prompt paths and memory
  storage/rendering code. Added this plan and linked it from the roadmap and
  maintainer entry point.
- The checkout contains no `data/` store, and no character `head.json`,
  `digest.json`, `method.json`, or entry snapshot is available locally.
  No Google Cloud credential configuration or `gcloud` executable was found
  in this execution environment. No live memory read or write was attempted.
- Step 0 is **blocked on source data**, not completed. Supply a current
  snapshot of the six character logbook directories (head, optional digest,
  entries, and method memory for unchanged-data verification). Relevant game
  records are only needed if an actual inconsistency requires them.
- `docs/zenbot_memories.json`, fixture recordings, old conversation summaries
  and the memory-maintenance code have not been edited as substitutes for
  missing logbooks. Later character-development steps remain planned.
- Verification: all 47 local Markdown targets/anchors across the three
  changed files resolve; `git diff --check` is clean; only this plan,
  `docs/phase-plan.md` and `CLAUDE.md` are changed. The requested full offline
  suite was attempted with `python -m pytest -q -n auto` but could not start:
  this execution environment has no `pytest` module (and lacks several web
  test dependencies). No test pass is claimed. Rerun in the project venv.
- No paid calls, fixture refresh, deployment or cloud writes.

### 2026-10-10: supplied snapshot and step 0 editing

David supplied `logbooks.zip` after merging his local store with the bucket.
He will manually apply and sync the resulting edits. The initial source
blocker above is resolved for the five current characters present: Green,
Mustard, Peacock, Scarlett and White. Current Plum is absent; PlumOG is an
archive and has not been changed.

Edited 58 summaries, five heads, five digests, their current source-entry
instructions/dossiers, and six overlong historical dossier reads. Flag
renames are propagated through entries, heads and digest mappings; one
redundant duration flag is removed. All 80 original file paths remain;
68 narrative documents changed. Numerical memories and archived PlumOG
remain byte-identical. Before/after field values, source hashes, rendered
read-back and the original ZIP are retained outside tracked source.

Memory-class loading, field bounds, protected metadata, source-entry/head
agreement where sources exist, flag consistency, and read-back at depths
0, 0.5 and 1 pass. Combined depth-1 read-back is about 35% shorter. Green
and Mustard each lack entry #0005 in the supplied archive; references and
head tallies remain intact. No missing memory has been invented, and no
head rebuild was applied. The full offline suite remains unavailable in
this environment because `pytest` is absent; no live behavior is claimed.

[The editorial record](phase13-editorial.md) has the scope, counts, flag map,
source limitations and handoff details. This completes the local editorial
pass, not a cloud sync or a change to future debrief prompts. Steps 1-6 remain
planned; the `focus` dial remains deferred. Repository edits are uncommitted.
