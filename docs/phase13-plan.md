# Phase 13: Character development

Agreed direction, 2026-10-10. This plan follows the discussion of the fourth
wall, the ensemble, and lives beyond Clue. It is the working checklist for
the phase; [the roadmap](phase-plan.md) owns the short status summary.

**Current state:** Step 0's editorial pass is live, and steps 1-3's six
broader persona scripts, shared premise and listening guidance are edited
locally for review and rehearsals. **Step 4 is deployed and accepted live**
(revision `clude-00029-8k8`, 2026-10-14): two games played that evening show
the characters remembering the company, and no live head carries a rule
against talking any more. The generator change retired those rules by
itself, so only the staged digest clause needed applying and the staged head
pass is moot. One consequence of the broader entries is fixed in the same
pass: Plum's debrief for `web-2/00012` was cut off by a 4096-token cap that
covers thinking and reply together, and wrote no entry. The available local
history covers five current characters; current Plum has no local logbook,
though his live logbook holds seven entries, and PlumOG is retained
unchanged and still carries the old rule, harmlessly, being unseatable.
Game runtime is unchanged. Steps 5 and 6 then landed locally and are
**waiting on one deploy**: the prompts now brief Wikiclude as a fallible
encyclopaedia (the engine still settles legality, and it is still the better
source than a model's memory of Clue on how this house plays), a seat is
given one set of participant names for the whole evening, and the on-turn
talk gate is gone -- it discarded 42 of the 81 lines those two games paid
for. The five-scene rehearsal is complete ($0.1373, 73% of 30 lines free of
game terms). Step 0's flag remainder, the off-turn taper and `PER_TURN`, and
Wikiclude's fuller article pass remain open; the article pass is David's
next piece, written against what is live. Both exact-game replay recordings
are historical pending an approved refresh.
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
- **Revised 2026-10-14, after the live audit.** That separation holds only
  for the layers play does not rewrite. Every debrief reissues the standing
  instructions in full, so editing them is not a cleanup of existing history
  but a change to what the characters remember, and it does not survive one
  game. Step 0 keeps the entry summaries, digests and flag
  vocabulary; retiring a superseded instruction belongs with the generator
  that writes it, in step 4.
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
| 0 | Durable layers edited: entry summaries, digests and flag vocabulary | Live pass applied; scope narrowed and a remainder opened by the 2026-10-14 audit ([0e](#0e-remaining-scope-after-the-live-audit)) |
| 1 | Six broader, distinctive, playable persona scripts | Edited locally for script review; offline verification below; ensemble behavior awaits rehearsals |
| 2 | Light shared premise and individual fourth-wall attitudes | Drafted locally with step 1; responses remain changeable; awaits script review/rehearsals |
| 3 | Listening, reply, silence, and thread-continuity guidance | Shared/decision/reaction guidance edited within the existing window; observed continuity awaits rehearsals |
| 4 | Debrief and condensation guidance that preserves social continuity, and one pass retiring the rules it supersedes | Deployed and accepted live 2026-10-14/15 ([record](#2026-10-15-step-4-accepted-live-and-a-debrief-lost-to-its-token-cap)); the generator retired the rules itself, so only the digest clause was applied |
| 5 | Fallible Wikiclude guidance and aligned character/reference articles | Prompts done 2026-10-15 ([record](#2026-10-15-step-5s-prompts-and-the-coordination-minimum-in-the-wiki)), with the three articles that restated the old brief fixed; the fuller article pass follows the deploy |
| 6 | Consistent participant names and measured conversation pacing | Names done and the on-turn gate removed 2026-10-15 ([record](#2026-10-15-the-rehearsal-completed-and-step-6s-naming-and-pacing)); the off-turn taper, `PER_TURN` and stale triggers remain open; `focus` remains deferred |
| Acceptance | Offline checks, approved model rehearsals, accurate docs and fresh recordings | Run applicable checks per increment; rehearse with the talk gate isolated; one recording refresh after steps 3-5; paid work separately estimated |

Stop at a clear boundary if a required input is absent. Mark the blocked
step accurately and continue independent work; do not replace missing
history with newly invented memories or silently implement later stages.

Two ordering constraints follow from the 2026-10-14 audit:

1. **Step 4 precedes any edit to standing instructions.** Every debrief
   rewrites that list in full, so an edit made before the writing
   instructions change is undone by the next game. The measured survival of
   step 0's edits is in [section 10](#10-implementation-record).
2. **The talk gate is isolated before the rehearsals that judge steps 1-5.**
   What anyone observed was the model's output multiplied by `chattiness`,
   which discarded half of the on-turn lines and most of a developing
   exchange. Until the two were separated, a rehearsal could not distinguish
   a character choosing silence from a written line being dropped.
   **Settled 2026-10-15:** the on-turn half is gone -- a written line is
   published, and silence is the character answering with nothing -- so what
   a rehearsal sees on turn is what the character wrote. The off-turn taper
   stands, and a rehearsal that judges a developing exchange still forces it
   open and records the setting.

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

### 0e. Remaining scope after the live audit

The 2026-10-14 audit read the live store directly and found the condition
0d anticipates: games landed after the edited snapshot was taken, so the
destination had moved. Three findings narrow and reopen this step.

**The head layer is not editable data.** Across the five characters, one of
thirty-five edited standing instructions survives live, against sixty-five
per cent of the dossiers and every digest. The ranking follows how each
layer is written: debriefs reissue instructions in full, revise only the
dossiers of opponents present, and leave digests alone until condensation
runs. Step 0 therefore keeps the summaries, digests and flag vocabulary,
and leaves standing instructions to [step 4](#6-step-4-future-memory-and-social-continuity).
Do not re-edit them here; the result is measurably erased within a game.

**A remainder is open in this step's own scope.** The eighteen entries
written after the editorial snapshot have not been through the pass.
Seventeen flags they carry are absent from their heads' flag indexes, so
index and entries disagree. Four are names a digest's `renamed` map retired
-- `never-accused`, `slow-to-accuse` and `too-far-to-accuse` in Peacock's
entries, `ignored-a-spoken-claim` in Mustard's -- and the rest are fresh
coinages duplicating kept vocabulary, such as Scarlett's `slow-to-room`
beside `slow-to-the-rooms` and White's `quiet-player-closing` beside
`narrator-at-the-table`. Green's are clean. This is hygiene on durable
layers and needs no design decision; 0c's warning against a broad `rebuild`
still applies, since it would also rebuild numerical memory.

The documents are not corrupted. An em dash reached these files correctly,
escaped as `\u2014`; a console that cannot render it is not evidence of
damaged data. Check bytes before scheduling an encoding repair.

**One recorded limitation was an artifact of the archive.** Section 10
records Green and Mustard lacking entry #0005; the live store holds both,
so the gap belonged to the supplied ZIP. Those two entries have never been
through the editorial pass. Re-establish the authoritative source before
editing, by this step's own 0a, rather than trusting either the earlier
archive or a repository checkout.

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

**Retiring the rules this step supersedes.** The present instructions
produced a conclusion in every character: a self-written standing rule
against talking at the table, two of them in White's list and in
Scarlett's, reinforced by a digest theme apiece. They are a reasonable
reading of the old guidance, which asks what a loss should teach and offers
no other field in which the evening's conversation could matter. Once the
writing instructions change, make one pass over the live heads and digests
to retire them.

That pass removes a conclusion drawn under superseded guidance. It does not
add an interest, an opinion, a relationship or an event that never happened,
and the prohibition on inventing history is unchanged. Sequence it after the
generator changes, or the next debrief reissues the rule. Prefer a direct
edit to a paid `condense`: the digest themes survived step 0 precisely
because condensation had not run, and that is also why they still need
touching by hand.

**Outcome, 2026-10-14/15.** Only the digest clause needed the hand edit. Two
games after the deploy rewrote every head from scratch under the new
instructions, and none of them reissued a rule against talking, so the four
staged head revisions were never applied and should not be: the documents
they were built from have moved on. The layer a debrief does not rewrite was
the only one that required a pass by hand, which is the distinction section
0e drew. [The record](#2026-10-15-step-4-accepted-live-and-a-debrief-lost-to-its-token-cap)
holds the evidence.

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

Isolate the talk gate before judging any scene below. `chattiness` is 0.5
for all six characters, none of the presets having set it. It used to apply
twice: on turn it discarded a line the model had already written and been
paid for, and off turn it governs joining an exchange at
`chattiness ** (depth + 1)`, so a third consecutive reply survives about
one time in sixty. The on-turn half was removed on 2026-10-15, so only the
off-turn taper needs isolating now. Rehearse with it raised to 1, and record
the setting beside the transcript. That is a diagnostic configuration for the
rehearsal, not a change to the shipped presets; tuning those stays in
[step 6](#8-step-6-identities-pacing-and-returning-to-play) with the
comparison it requires.

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

The original editorial record has the scope, counts, flag map,
source limitations and handoff details. This completes the local editorial
pass, not a cloud sync or a change to future debrief prompts. Steps 1-6 remain
planned; the `focus` dial remains deferred. Repository edits are uncommitted.

### 2026-10-10: step 0 live and steps 1-3 scripts

David reports that step 0 is live. This increment reads the available local
heads, digests and recent entries under `data/llm_local/logbooks/` as context;
it does not independently audit the live store. The original editorial
record is not present in this checkout; the snapshot limitations above
remain part of the history.

All six `clude_llm/personas/<Suspect>.md` scripts now have lives and social
motives beyond the investigation. The agreed media habits are background,
not compulsory topics or claims of current retrieval. Mustard's Masonic
pride permits discretion and teasing without invented secrets. Green
enjoys how films work; Scarlett responds to performance and vitality, with
room for either to surprise the other. Peacock cares about the occasion
and its company; White can enjoy competence and express sympathy; Plum
can enjoy an idea without correcting every phrase. These modest additions
are script choices for review, not newly discovered historical memories.

Recognisable voices remain. Scarlett's absolute refusal to apologise is
loosened, and the other parts have room for exceptions to their usual
social manner. Green's method description now reflects sampled selection
among five character methods, not deterministic selection of the best
record or access to another seat's cards. White's repetition heuristic is
distinguished from proof about a hand and from her wider social observations.
No agent, weight, threshold, leash, schema or other runtime setting changed.
No PlumOG history is assigned to current Plum.

Shared rules now give a light account of what the actors have been told,
without compulsory certainty, rare/hesitant departures, or a named Director.
Initial responses differ: Mustard values respect and fellowship, Peacock
cares whether people take one another seriously, Green wonders about approval
and an actor's part, Scarlett enjoys the possibility of surprising her script,
White asks what the explanation changes, and Plum is curious with room for
private concern. These are inclinations, not immutable answers or required
speeches. Familiar people can be recognised; an unfamiliar name or token
does not establish the player's nature, and a bluff retains attribution.

Shared, decision and reaction guidance encourages attention to the substance
of a contribution, allows an exchange to develop without six monologues,
and distinguishes a useful callback from repetition. Silence, a short line,
no narration, private-card boundaries and legal JSON/menu instructions
remain. Recent context stays at the existing eight remarks by default;
no thread summary, new memory subsystem or pacing change is introduced.

The review boundary is the combined scripts and prompt guidance in steps
1-3. Future memory guidance (4), coordinated fallible-reference/wiki work
(5) and participant naming/pacing (6) remain planned. The old canon-authority
instructions still apply in rules/tools/wiki; this increment does not claim
fallible-reference behavior or cross-path name consistency is implemented.
Scripts must be agreed before the related wiki work and release must align
the related text so a lookup cannot reinstate retired guidance.

Both exact-game replay cases passed immediately before these edits (2
passed). Persona, shared-rule and request edits change their keys, so the original
2026-10-09 recordings are retained and only those two parametrized cases
are marked pending an approved refresh. Independent recording/replay,
schema, privacy and fake-backend checks remain active. No model call,
fixture rewriting, memory write, deployment, commit or push is part of
this increment. Verification below concerns offline prompt and runtime
contracts; no observed ensemble improvement is claimed.

Verification of the combined steps 1-3 increment:

- Full offline suite in the project venv, with live API tests disabled:
  `python -m pytest -q -n auto` — **619 passed, 36 skipped**. The skipped
  cases include the two historical exact-game replays pending refresh.
- Rendered 72 decision requests (all four kinds, six characters, depths
  0, 0.5 and 1) and 18 reaction requests through the existing renderers.
  Inspected representative output; JSON shapes, own-hand presentation,
  method scores, legal-menu guidance and private-show reminders remain.
  Current Plum's memory block is empty at every depth.
- Prepared five fixed local scene inputs and a rubric for subsequent
  bounded rehearsals: film, fictional news, jewels, scripts and an answered
  question. Seed 13, roster, model/settings, rendered requests and memory
  snapshots are retained in ignored `data/phase13-script-review/`, with
  source hashes in `manifest.json`. These are inputs, not model responses
  or an acceptance transcript. A future run should pass a response to the
  next speaker and repeat selected scenes, rather than mistake six isolated
  lines for an exchange.
- All 86 existing local logbook/recording JSON files checked by hash remain
  unchanged; no live-store read or write was performed.
- All 59 local Markdown targets/anchors across the four edited guides
  resolve; `git diff --check` is clean. Changes remain uncommitted.

### 2026-10-14: live memory audit and pathway revision

Read the live store for the first time in this phase, after David reported
that the characters will not talk about anything but the game. No logbook,
persona or runtime file was changed; this increment revises the plan only.

- **Source.** `gs://clude-game-data/llm/logbooks/` read with the
  maintainer account, and `data/llm_local/logbooks/` as the local
  comparison. Live entry counts are Scarlett 20, White 18, Green 16,
  Peacock 15, Mustard 9 (78 in all), against 17/15/12/13/5 locally. The
  live store is gapless; `data/llm_local` is a stale partial copy, missing
  Green and Mustard #0005 and carrying a head two serials behind its own
  entries. Current Plum has no logbook; PlumOG was not read for editing.
- **Survival of step 0's edits.** Standing instructions 1/35, dossiers
  32/49, digests 5/5 identical. After three or four games per character,
  the edited instruction lists are effectively gone and the digests are
  untouched, which matches how debriefs and condensation write each layer.
- **What the characters now instruct themselves.** Classified against the
  line step 4 applies -- a clause generalising from "do not reveal decisive
  information" to "do not talk", as against one scoped to a specific fact --
  six clauses in four characters qualify: Scarlett "I am losing and should
  move, not talk"; White "a read spoken aloud is a gift to whoever has
  better feet", "the third time must be a move and not a sentence", and a
  tell "worth more than anything said at the table"; Green "move first,
  speak after"; Peacock "investigate rather than remark". Mustard has none:
  "stop announcing which card I showed" is information discipline about one
  card. Scarlett's "route and inference stay behind my teeth" is absolute in
  tone but scoped, and is kept for David to revisit.
- **The digests held up.** Of forty-four themes, one clause qualifies,
  Peacock's "a clever correction is not a productive step". Scarlett's
  `narrated-instead-of-acted` already ends "talking can be enjoyable without
  publishing the next question", and White's `narrator-at-the-table`
  conditions privacy on the disclosure helping a rival. Step 0's editing was
  sound; what undid it was the head being rewritten, not the digest.
- **No non-game content exists to preserve.** Across all 78 entries, heads
  and digests, no film, broadcast, publication, interest or personal detail
  appears. The one recurring social word is "joke", fifteen times, each
  time as something to see through: "cover", "jokes about bluffing as
  cover", and, logged as an error, "answered it with a joke instead of
  arithmetic". Conversational players are recorded as weak, as in
  "genuinely conversational - and slow".
- **Assessment.** The logbooks are the symptom and `debrief_prompt` in
  `clude_llm/logbook.py` is the generator: its fields ask for patterns of
  play, how opponents played and what gave them away, and offer nowhere to
  record an evening. Five characters independently re-derived the same rule
  under it. Wiping would discard the one thing the phase needs, which is
  that these characters have played with one another and with David, and
  would regenerate the rule within a few games; editing the head layer
  alone is undone in one. Hence the two ordering constraints in section 3,
  the narrowed scope in 0e, and the retirement pass in step 4.
- **Also found, outside memory.** None of the six presets in
  `clude_agents/personality.py` sets `chattiness`, so all inherit 0.5,
  applied both as an on-turn discard (`clude_llm/player.py`) and as
  `chattiness ** (depth + 1)` off turn (`clude_web/chat.py`). Off-turn
  reaction is where conversation unattached to a decision can occur, and
  the taper removes it fastest, so the mechanism selects for game talk
  independently of persona or memory. Lowering the `memory` dial is not an
  escape: standing instructions sit in the head, which renders at depth 0.
  Shared rules and `Peacock.md` also still carry the superseded
  canon-authority wording for step 5, including "over anything said at the
  table".
- Verification: no paid call, cloud write, deployment or fixture refresh.
  Live objects were read only, into a session scratchpad. The quoted
  survival counts come from comparing the live heads with `data/llm_local`,
  which is step 0's edited snapshot as David synced it; a character whose
  dossier was rewritten by later play counts as not surviving, so these are
  lower bounds on what step 0 wrote.
- **Correction.** An earlier reading of this audit reported U+FFFD mojibake
  in the live heads and entries. That was wrong: the documents are pure
  ASCII with em dashes escaped as `\u2014`, and the replacement characters
  were a console that could not render them. No encoding repair is needed,
  and the claim is withdrawn from step 0's scope above.

### 2026-10-14: steps 3 and 4 implemented, retirement staged

Step 4's generator change, the step 3 clause it depends on, and the staged
retirement of what they supersede. Offline only; no game was played.

- `clude_llm/logbook.py`: the debrief's field instructions now ask for the
  evening as an occasion as well as the play -- `what_happened` covers what
  made it worth sitting down for, `evaluations` what an opponent was like to
  play with, `dossiers` the person as well as the player, and `flags` patterns
  in the company as well as in the play. `standing_instructions` gains the
  sentence that settles the observed failure: discretion about a decisive
  inference can be shrewd, but a quiet evening is not thereby better played,
  and the character is told not to write itself a rule against speaking.
  Condensation's `overview` and `themes` admit what the company has been like.
  No schema change: section 6's instruction to try the existing narrative,
  summary, dossier, instruction and digest fields first is satisfied, so
  `LOGBOOK_SCHEMA` and `CONDENSE_SCHEMA` are untouched.
- `clude_llm/personas/rules.md`: conversation is stated not to be a tactical
  expense, and "silence is a welcome part of the company" is conditioned on
  having nothing to add rather than standing as a general licence. This is a
  step 3 revision, taken now because the memory it counterweighs is being
  changed in the same pass.
- `docs/logbooks.md`: the Tier 2 field table and the debrief section describe
  the broadened fields.
- Staged, unapplied, in ignored `data/phase13-step4-retirement/`: seven clause
  revisions over four live heads and one digest theme, with source hashes,
  every before/after, the stated principle, the clauses kept deliberately and
  the required order of application. Mustard needs none. Invariants checked:
  serials, tallies, dossiers, flag indexes, digest `through`, `renamed`, date
  and model are byte-identical, instruction counts and theme flags unchanged,
  advertised bounds respected, and both documents load through `LogbookHead`
  and `LogbookDigest`. Applying it is David's, as with step 0, and must follow
  the deployed prompt change or a debrief reissues the rules.
- Not done, and deliberately short of the next assessment point: step 0's
  flag remainder, step 5's fallible-Wikiclude text, step 6's pacing work and
  the paid rehearsals. Prompt text has changed, so both exact-game recordings
  stay pending the single approved refresh after steps 3-5.
- Verification: `python -m pytest -q -n auto` passes (619 passed, 36 skipped);
  no test asserted on the revised prompt wording. Markdown targets/anchors in
  the edited guides resolve and `git diff --check` is clean. No paid call,
  cloud write, deployment or fixture refresh. Changes are uncommitted.

### 2026-10-15: step 4 accepted live, and a debrief lost to its token cap

Two games were played on the deployed service on 2026-10-14 and their
debriefs read the next day. Step 4's generator change is accepted: the
characters now remember the company, and the rules against talking are gone
from every live head without the staged head pass being applied.

**What was deployed and applied.** `gcloud run revisions list` shows
`clude-00029-8k8` live from 2026-10-14 20:17:33 UTC. Of the staged
retirement, only the digest clause was written to the bucket:
`Peacock/digest.json` was updated at 20:29:16 UTC and is identical to
`data/phase13-step4-retirement/digests/Peacock.json`. The four staged heads
were not applied, and two pieces of evidence agree on it -- Peacock's entry
16, written by the first debrief after the deploy, still carries the pass's
*before* clause ("investigate it rather than remark upon it"), and no clause
in any of the four live heads matches a staged head clause verbatim (0 of 8,
four times over). The head pass is therefore moot, and `verify_live.py`
refuses it correctly: all five documents have moved on.

**The games.** `web-2/00011`, three seats (david at Green, Peacock and Plum
on models), $0.8621; `web-2/00012`, all six characters on models, $1.9666.
$2.8287 together, from the seat costs in the game records. Both post-date
the deploy and the digest edit.

**What the fresh entries record.** The evening is in them. Scarlett's #21
closes on Peacock's curtsey line, Mustard reasoning aloud so the rest of the
table could borrow it, and a conversation with Green that the game ended
underneath: "I'd sit down with all of them again." Peacock's #16 keeps the
figure she and Plum sustained about ledgers, currencies and denominations,
and judges the conversation "the best part of my evening and the worst part
of my game". Plum's #7 has Green on cheap drones, NPR and the incentives of
asymmetric war. `talkative-opponent` appears as a flag. These are the fields
step 4 broadened, used as intended.

**The rules are gone.** No live head carries a rule against talking. Five of
the six close on a licence to converse -- White's "the company is not a
cost", Green's "the talk costs me nothing", Peacock's "the talk is half the
evening and worth every line of it", Scarlett's "none of that costs a turn",
Plum's "answer Green's drones and Peacock's ledgers properly". Mustard, who
needed no retirement, now folds the discretion into "enjoy the table without
handing the best reader my itinerary". Each head's whole list was rewritten
from scratch: discretion survives, scoped to own cards, a decisive inference
or a destination in use, which is what the pass's principle asked for.

One clause from the staged list is still live in a narrowed form: Peacock's
"investigate it on my next step rather than remarking upon it at the table".
Both post-deploy debriefs carried it forward. It is scoped to a rival's tell
rather than to conversation generally, so it is a judgement call for David
and not grounds to re-apply a stale pass over newer work.

**A debrief lost to its token cap.** Plum has no entry for `web-2/00012`,
though he held seat 5 on a model. The table document records seat 5 as
failed, `"malformed: not JSON (Unterminated string starting at: line 1
column 6955 (char 6954))"`: the reply was cut off mid-string, not malformed.
`debrief_max_tokens` was 4096, and that cap covers the adaptive thinking and
the reply together. The broadened entries are 7.6-9.3 KB of JSON where they
were 5.2-8.0 KB, so a long think no longer leaves room for one -- Green's
#17 came in at 9.3 KB, close behind Plum. This is a direct consequence of
step 4 and was not foreseen when the fields were broadened.

- `clude_llm/player.py`: `debrief_max_tokens` 4096 to 8192, matching the cap
  condensation already uses, and a `max_tokens` stop is now reported as
  `truncated: stopped at max_tokens after N output tokens` rather than
  reaching the parser and being blamed on the JSON. The condensation and
  decision paths are unchanged.
- `tests/test_debrief.py`: a truncated reply is covered beside the refusal,
  error and malformed cases; the request assertion follows the new cap.
- `docs/logbooks.md`, `docs/llm-wrapper.md` and the `LLMSettings` docstring
  carry the new figure and say that the cap covers thinking and reply.
- Plum's seat paid for the lost entry, and a failed debrief writes nothing,
  so his head and tally stood at #7 and `web-2/00011` -- consistent, not
  corrupt. **Re-run 2026-10-15** from the retained record, approved by
  David: entry #0008, "The Dining Room, Again", $0.1281 for 8,580 in and
  3,407 out, uncached because a one-off has no warm cache behind it. Those
  3,407 output tokens confirm the diagnosis -- under the old 4,096 cap the
  reply alone left under 700 for the thinking. The entry reads like its
  five peers: it keeps Peacock's "gossip with a ledger", Mustard's dinner
  wagered on a card and Scarlett on the pleasure of watching someone walk
  into it anyway, and its standing instructions keep the inference back
  while sending the wit elsewhere -- "there is plenty else to talk about"
  -- with no rule against talking. The re-run used the working tree, so
  this one entry was written under steps 5 and 6's revised prompts while
  its five peers were written under the deployed ones; no names were
  attached, so it saw the same seat labels they did.

**The rehearsal harness.** `scripts/phase13_rehearse.py`, uncommitted since
the 2026-10-14 run, is fixed and committed with this pass:

- `Logbook(store, name, readonly=True)` raised `TypeError` into the "no
  logbook" guard -- `Logbook` takes no such argument -- so every rehearsal
  before the fix ran with no memory attached at all. The store is a snapshot
  copy and the harness never debriefs, so nothing was written to it.
- Wrappers are built per scene, so one scene's talk cannot reach the next
  through a wrapper's own memory.
- `GAME_WORDS` is narrowed to terms with no ordinary social sense, with a
  phrase list beside it. The first paid run showed "suspect", "deduction",
  "silence", "notes" and even "square" -- Mustard's square and compasses --
  firing on plain conversation. Undercounting game talk is the safer error,
  since the question is whether anything other than the game gets said.
- A `Metering` wrapper reports what a run actually spent, rather than an
  estimate.
- `--memory-store` defaulted to `data/phase13-step4-retirement-store`, which
  does not exist; it is now `data/phase13-rehearsal-store`, the snapshot the
  recorded run read.

**Rehearsal result** (`data/phase13-rehearsal/rehearsal-anthropic.json`,
2026-10-14): two scenes, six rounds, `claude-opus-5`, low effort, chattiness
forced to 1.0, logbooks from the snapshot. 12 spoken lines, 9 of them free of
game terms (75%), none silent, no errors; 12 calls, 4,881 input, 41,514
cached, 547 output tokens, $0.0588. **Correction:** this was reported as 83%
in discussion; the transcript is the record and the share is 75%. The scenes
show the characters will carry a non-game exchange with the taper forced
open. They do not measure pacing at the live taper, which section 3's second
ordering constraint still requires before rehearsals can judge steps 1-5, and
they covered two of the harness's five scenes. The three unrehearsed ones are
the ones that would test the rest: `news` for the shared background,
`scripts` for the fourth wall (step 2) and `answered` for returning to the
game when it matters.

**Verification.** `python -m pytest -q -n auto` passes (619 passed, 36
skipped). The live work in this pass was reads only: no cloud write, no
deployment, no paid call and no fixture refresh. Both exact-game recordings
stay pending the single approved refresh after steps 3-5.

### 2026-10-15: the rehearsal completed, and step 6's naming and pacing

The three unrehearsed scenes were run, and step 6's first two deliverables
implemented: one set of participant names, and the on-turn talk gate removed.

**The rehearsal is complete.** `news`, `scripts` and `answered` ran at six
rounds on `claude-opus-5`: 18 spoken lines, 13 of them free of game terms
(72%), none silent, no errors, $0.0785 over 18 calls. With the earlier two
scenes that is five scenes, 30 lines, 22 free of game terms (73%), $0.1373
over 30 calls, merged into
`data/phase13-rehearsal/rehearsal-anthropic-complete.json` with each run's
own date, tally and usage kept beside the whole.

What the three scenes showed, scene by scene:

- `scripts` is the best of the five. Plum and Scarlett carry a real exchange
  about a script telling you what is said and never what is meant by saying
  it, and Plum thanks her for putting it more economically than he did. No
  six-seat identity recital, which is what the scene was there to check.
- `answered` opens on a live game cue -- the Library untested all evening --
  and five of the six replies leave the game rather than take it up. Read
  with care: these seats are off turn with nothing to decide, so the scene
  shows willingness to converse rather than a refusal to return to play.
  Returning to the game when a decision needs attention is a live-table
  question, and the two games of 2026-10-14 are the better evidence for it.
- `news` is the weakest. Mustard's opening about the roadworks draws two
  replies that revert to the game ("Twelve turns and nothing settled"), so
  the shared background did not carry the scene on its own.
- Across scenes, White's "Twelve turns and nothing settled" and Peacock's
  "Nothing has been established yet, Mrs. White -- but ..." recur almost
  verbatim. The harness builds each scene from the same stub observation
  with the same seed, so near-identical context is expected; it is a harness
  artefact to keep in mind when reading these transcripts, not a finding
  about the characters.

**Participant names.** A character was told three different things about
who it was sitting with: `seat_names` off turn (the token, and a person's
capitalised display name after it), the bare suspect tokens on its own turn
(`user_prompt` was called without `names`), and `P2 White (david)` at the
debrief. That is why a fresh entry can call one person both "Mr. Green" and
"david".

- `clude_llm/player.py`: `attach_names` beside `attach_logbook`, and the
  on-turn, off-turn and debrief prompts all use the attached list. An
  explicit list from the caller still wins, so `chat.Reactions` is unchanged.
- `clude_web/tables.py`: `WebGame.__init__` gives every wrapper the same
  `seat_names(self)` the screen and the reaction queue use. It runs whether
  or not "characters remember" is on, since naming is not a memory feature.
- `clude_llm/logbook.py`: `debrief_prompt` takes `names`. The prompt still
  names the roster labels the dossiers are keyed on, so a character is not
  left to guess a key from a display name; only what it reads changes.
- Without the call -- a headless arena, the CLI, the rehearsal harness --
  the prompts fall back to seat labels exactly as before.

**The on-turn talk gate is gone** (David's decision, 2026-10-15). An
on-turn line arrives in the same reply as the decision, so the
`chattiness` draw that discarded it saved nothing and cost the exchange.
Measured over the two games of 2026-10-14: 81 on-turn lines written, 39
spoken, **42 paid for and thrown away** (48% in `web-2/00011`, 54% in
`web-2/00012`). A character that would rather say nothing answers with an
empty string, which the prompt has always offered it.

- `clude_llm/player.py`: the draw is removed. `chattiness` now governs the
  off-turn reply draws alone, which the caller makes *before* paying for a
  call. Expect roughly twice the on-turn lines at the same cost.
- The off-turn taper, `chattiness ** (depth + 1)`, is **untouched**, per
  section 8: change only the mechanism the evidence implicates. The two
  games already reached runs of two and three reaction lines in a turn, and
  `PER_TURN = 2` looks more like the binding cap than the taper does.
  Flattening the taper or lifting that cap stays available, and wants a
  comparison that can explain the result.
- This stops consuming one draw from the wrapper's own RNG per on-turn
  decision, so the off-turn draws that share that stream now fall
  differently. Both exact-game recordings were already pending refresh.

**A model's line is now cleaned like a person's.** `clean_remark` collapses
whitespace, drops control characters and trims past 240 characters on a word
boundary, at both points where a line is parsed. A person's line has always
been cleaned on its way to the table (`clude_web.tables.clean_line`), but
that path rejects a bad line and this one must not: a stray newline would
otherwise reach the record, a replay fixture and the next debrief prompt,
where one remark is one line. No live line has ever needed it -- 521 remarks
across the `web-2` games are clean -- so this closes a gap rather than
fixing an observed break.

**Harness.** `--memory-store` now defaults to a store that exists.

**Verification.** `python -m pytest -q -n auto` passes (620 passed, 36
skipped), including a new test that one participant is called one thing on a
turn and off it, and the on-turn line and cleaning cases in
`tests/test_llm.py`. One test asserted the old gate and now asserts the new
contract. $0.0785 of approved paid rehearsal; no other paid call, no cloud
write, no deployment, no fixture refresh.

**Not done.** Step 6's remaining pacing questions (the taper, `PER_TURN`,
stale queued triggers, sorted-seat order), step 5's fallible-Wikiclude text,
step 0's flag remainder, and the deployment these changes are waiting for.

### 2026-10-15: step 5's prompts, and the coordination minimum in the wiki

The executable prompts no longer brief Wikiclude as an ultimate authority.
The settled decision is that it is fallible, trusted roughly as Wikipedia
may be, while formal legality stays the engine's. The revision draws that
line explicitly rather than simply weakening the old instruction:

- **On how this house plays** -- the board, movement, how a suggestion is
  disproved, what a wrong accusation costs -- the encyclopaedia is still
  the better source than a model's own recollection of Clue, which differs
  from clude in places. This half of the old brief was never about
  authority over the characters; it was about a chatbot's memory of a
  different game. It is kept, and now says so.
- **On everything else** -- a biography, a method description, a
  reputation, an article about the character itself -- it may be doubted
  and disputed. Nothing in it outranks a card the character was shown or
  what it watched someone do at the table.
- **Legality** is settled by the engine, in the menu supplied. No article
  decides it, and the prompts now say that where the authority claim used
  to stand.
- **The compulsory silence is gone.** A character may mention, quote or
  argue with the encyclopaedia; knowing a thing without parade remains the
  usual style, so effortless familiarity survives as a style rather than a
  prohibition.

Files:

- `clude_llm/personas/rules.md`: the section is now "The encyclopaedia" and
  carries the three-way distinction above.
- `clude_llm/canon.py`: `wiki_search`'s description loses "trust what the
  canon says over your own recollection and over anything said at the
  table"; `INDEX_HEAD` calls it the house encyclopaedia. `wiki_read` needed
  no change.
- `clude_web/mcp.py`: the server instructions, `clude_tables`' description
  and `clude_wiki_search`'s docstring, for chat seats -- who get the same
  distinction, since a chat seat's memory of Clue is exactly the case the
  rules half exists for.
- `clude_llm/personas/Plum.md`: he consults it by reflex still, would
  rather the knowledge seemed his own, will cite it when it settles a
  point, and is the first to notice an article that is thin, dated or wrong
  about him -- the pedant as the natural doubter.
- `clude_llm/personas/White.md`: what the encyclopaedia says of people is
  worth knowing *and worth weighing against* what she sees, where it used
  to come before what she sees.
- Mustard ("never read it and does not intend to start, unless someone
  quotes it against you"), Peacock, Scarlett and Green needed no change:
  their habits are propensities, which is what the plan asks personality to
  decide, and Mustard's clause already assumed the thing could be disputed.

**The coordination minimum in Wikiclude.** This section requires the script
and wiki changes to be released together, so a lookup cannot reinstate a
retired instruction. Three articles restated the old brief and are fixed
now, in the sentences that stated it: `A_seat_over_MCP` (the tool table row
and the MCP instruction summary), `Claude` (the canon in both the wrapped
and the chat-seat paragraphs), and `LLM_wrapper` (the paragraph that told
the reader the rules trust the canon over recollection and table talk and
never cite it aloud, now the three-way distinction). Section headings and
`[[wiki links]]` are untouched, so nothing else in the encyclopaedia moved.

That is the minimum which keeps a lookup honest, not the article pass this
step asks for. The six character articles, Persona, Table talk, Logbook,
The debrief, A seat over MCP in full, and a possible modest fourth-wall
article remain to be written, and David's sequence is to deploy first and
write them against what is then live.

- `docs/canon-plan.md` carries a dated supersession note at the top: the
  authority brief is replaced, the access, tools, caps, index block and
  lookup limits it records still describe the implementation. The plan's
  own decisions are preserved rather than rewritten.
- `docs/llm-wrapper.md` describes the new line in the canon section.

**Verification.** `python -m pytest -q -n auto` passes (620 passed, 36
skipped). One test asserted the old section heading and now asserts the new
one; nothing else asserted on the revised wording. No paid call, cloud
write, deployment or fixture refresh. Prompt text changed again, so the two
exact-game recordings stay pending the one approved refresh.
