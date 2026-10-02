---
title: Deduction floor
short: The logic all six characters share: what is certain, and nothing else
categories: Methods
redirects: Floor, The floor, The deduction floor, Constraint propagation, Floor bot, The floor bot, FloorBot
dyk: ... that every one of clude's six characters stands on the same [[deduction floor]], and that it is the whole of what a person at a table is told?
dyk: ... that the [[deduction floor]] never once ruled out the true holder of a card across hundreds of replayed games, and that a test says so?
---
{{infobox
title: Deduction floor
Shared by | Every character, the floor bot, and every person's notepad
Module | `propagator.py`, `floor_bot.py`
Takes | One seat's hand and the whole history of suggestions
Gives | Where each card could still be, the open facts, the hand sizes
Cost | Recomputed from scratch on every call, in a fraction of a millisecond
= The three rules
Open fact | One card left that the holder could hold: they hold it
Category | Eight of nine rooms placed: the ninth is the envelope's
Hand size | A full hand holds nothing more
}}

The **deduction floor** is the part of every character's reasoning that is not a matter of opinion. From a player's own hand and the history of [[suggestion|suggestions]] it works out, by [[w:Deductive reasoning|deduction]] alone, everything that follows for certain: which cards are placed and where, which holders are still possible for each card that is not, and which facts of the form "this player holds at least one of these cards" remain open. It repeats three rules until nothing changes, and the result is a *mask* that every one of [[clude]]'s six [[Category:Methods|methods]] reasons on top of and is checked against afterwards. A card the floor has ruled out of [[the envelope]] gets a [[belief]] of exactly 0 from every character, whatever their method would have said, and a card it has proved gets exactly 1.

That is the project's first invariant: the six characters "differ in how they reason under uncertainty, never in what is logically certain".[^invariant] It is what makes it safe for [[Miss Scarlett]]'s [[Naive Bayes]] to be sloppy about soft evidence without ever suspecting a card she is holding, and it is why the methods can be compared at all. Each of them starts from the same floor and adds a different judgement about what the floor leaves open; the [[uniform baseline]] the [[belief benchmark]] scores them against is the floor's own belief, with no judgement added.

The floor also plays. The **floor bot** is a seventh, characterless player that acts on the floor alone: it suggests only about cards it has not placed, moves towards rooms it has not placed, and [[accusation|accuses]] exactly when the floor has proved all three cards and never otherwise. It is the standard opponent in every measurement, the player that fills an empty seat, the training partner [[Colonel Mustard]]'s tree was grown against, and the stand-in that plays a person's turn when they run out of time. And it is what fills in a person's [[detective notepad]] at a web table: a human player is told what the floor knows, and nothing a method believes.[^web]

## At the table

!!! example "Worked example: the Rope question, as the floor sees it"
    {{figure:floor-notepad|What the floor knows in the Rope question, from the viewer's chair. Seventeen cards are placed, one is proven the envelope's, and four are left to the methods.}}

    Late in a three-handed game the viewer holds six cards and has seen enough suggestions answered for the floor to place every other card but four. [[Colonel Mustard]] is known to hold four particular cards; [[Mr. Green]], six. Of the nine rooms, eight are placed in hands, and so the ninth, the Study, is proven the envelope's by the category rule: every category has exactly one card in the envelope, and when eight are elsewhere the last has nowhere else to be.

    Four cards remain: Mrs. White, Mrs. Peacock, the Rope and the Wrench. The floor knows the viewer does not hold them and Green does not hold them, so each could be Mustard's or the envelope's, and it knows Mustard's hand has room for exactly two more. It does not know which two. Then Green suggests *Mrs. Peacock, with the Rope, in the Hall*; the viewer is passed over, and Mustard shows Green a card the viewer does not see. The Hall is Green's own, which the floor knows, so the card Mustard showed was Peacock or the Rope, and the floor records one **open fact**: *Mustard holds at least one of Peacock and the Rope.*

    That is all the floor can say. It cannot place either card, because neither is forced. What it can do is hand the position on to the methods exactly as it stands, with the open fact attached, and that is where the six characters begin to differ: [[Professor Plum]] counts the deals the fact allows and finds Mrs. White in the envelope in two of three; [[Miss Scarlett]] marks the two named cards down; [[Mrs. Peacock]] holds the fact as a weight on the pair. The comparison is at [[Belief#At the table|Belief]].

## How it works

### Seeding

{{figure:floor-propagation|wide|Inside the floor: the four seeding steps run once, then the three rules run in a loop until a pass changes nothing. The rule labels are read from the code.}}

The floor begins with every card possibly anywhere: in any seat's hand or in the envelope. It then reads four kinds of fact, in order.[^module]

- **The viewer's own hand.** Each card in it is placed with the viewer.
- **Players passed over.** For each suggestion, every player who was asked and could not disprove it holds none of its three cards; the three are struck from that hand.
- **A card the viewer saw.** When the viewer made the suggestion or showed the card, the shown card is placed with the player who showed it.
- **A disproof the viewer did not see.** The player who showed a card holds at least one of the three; whichever of the three that player could still hold form an open fact.

### The three rules

With the facts seeded, three rules run over the whole position, and run again whenever one of them has changed something, until a full pass changes nothing.[^module]

**The open-fact rule.**
:   An open fact whose named cards have been whittled down to one that the holder could still hold is no longer open: that card is placed with that holder. A fact that a placed card already satisfies is dropped, since it has nothing more to say.

**The category rule.**
:   Exactly one suspect, one weapon and one room are in the envelope. If a category has a card proven the envelope's, every other card in it is struck from the envelope; if every card but one has been struck from the envelope, the last is placed there.

**The hand-size rule.**
:   A player known to hold as many cards as their hand has room for can hold nothing else; every other card is struck from that hand.

Each rule can feed the others, which is the [[w:Process of elimination|process of elimination]] made mechanical. A card placed by the open-fact rule may fill a hand; a hand filled strikes cards that may leave a category with one candidate; a category resolved may collapse an open fact. The loop runs until the position is still, which is its [[w:Fixed point (mathematics)|fixed point]], and in practice takes a handful of passes.

### Contradictions

If the facts ever contradict one another (no possible holder left for a card, a player who must hold one of a set of cards none of which they can hold, a hand with more cards placed in it than it has room for) the floor raises an error rather than carrying on. Real evidence is never contradictory; a contradiction is a bug in whoever built the observation, and the project treats it as one.[^module]

## Formally

What the floor does is [[w:Constraint satisfaction problem|constraint propagation]]. Each card is a variable whose domain is the set of holders it could still have; each fact is a constraint; and the three rules are propagators that shrink domains until no rule can shrink one further. The result is a fixed point of the rules, reached in finitely many steps because every step removes something and nothing is ever put back.[^aima]

Two properties matter, and they pull in different directions.

**[[w:Soundness|Soundness]].** The floor never strikes a holder that the truth has. Every rule removes only what the facts exclude, so the mask always contains the actual deal, and a test replays many real games through every player's view to check that the true holder of every card survives at every turn and that, given enough play, some viewer reaches full certainty.[^tests]

**[[w:Completeness (logic)|Incompleteness]].** The floor does not find everything that follows. Its rules reason one fact at a time, as [[w:Unit propagation|unit propagation]] does in a logic solver; they never consider cases, and a conclusion that needs "if Mustard holds Peacock then ... but if he holds the Rope then ..." is beyond them. A full search over consistent deals, which is what [[exact posterior enumeration]] performs, finds every card the facts determine; the floor finds only the ones its three rules can reach. This is the usual trade: propagation is cheap and sound, search is complete and expensive. What the floor misses is not lost, because it reaches the methods as uncertainty. A card that is in fact determined but not by the floor's rules will have, in Plum's count, every consistent deal agreeing on it, and a probability of exactly 1.

The floor's output has three parts, and the shape was chosen for the methods that read it. Each card's set of possible holders is exposed as a set rather than collapsed to known-or-unknown, because [[Mrs. Peacock]]'s [[Dempster-Shafer theory]] wants exactly that structure to put weight on. The open facts are exposed separately, because per-card sets lose the joint "one of these three" that [[Professor Plum]]'s search needs to count the true posterior and that Peacock holds as a mass on a set.[^architecture]

## In clude

{{figure:floor-then-method|wide|The floor comes before every method and after it: one gate in front of the six, and one behind.}}

The module is `clude_constraints/propagator.py`, with the floor bot beside it. It was built by finishing a constraint propagator from the project's earlier code, whose own list of known issues had five items: eliminations were not actually tracked, the category rule was missing, hand sizes were stored and never read, contradictions were dropped silently, and two parts of the code disagreed about what to call the envelope. All five were fixed, and the floor recomputes its result from scratch on every call, so that no character can ever act on a stale mask.[^architecture]

Every method ends with the same step, in `clude_agents/base.py`: whatever raw scores a method has produced, a card the floor has ruled out of the envelope is set to 0, a card it has proved is set to 1, and the scores of the cards still in question are scaled to sum to 1 within each category. A method with no opinion at all gets an even spread over what the floor permits, which is the uniform baseline.[^base]

One bug of the floor's own was found by Peacock. Until Phase 5, an open fact that a placed card already satisfied was kept and reported as open; Plum's search filtered such facts for itself, but Peacock read the fact's other, unplaced members as live evidence against those cards. The floor now drops them.[^phase5]

### The floor bot

The floor bot implements the engine's player contract with no belief and no personality: a seventh player, "dumb" in the six-methods sense but never wasteful. For its suggestion it names a suspect and a weapon it neither holds nor has placed, chosen evenly, and once a category has no such card left it names the proven envelope card, which nobody can disprove, so that the suggestion tests the other two cleanly. For its move it prefers a room it has not placed, then the move that comes closest to one, and once every room is placed, a room nobody else can disprove with. It accuses on the floor's proof and never otherwise.[^floorbot]

Its movement was meant to be uniform over the legal moves and was measured not to work: a table of uniform movers piles into one room that some player holds, and every later suggestion there is answered by the same player with the same card. The first floor-bot games plateaued exactly as the random games before them had, and tracing them found why: a bug on the board that kept a token from leaving a room except by [[Classic board|secret passage]]. Both the bug and the movement were fixed together.[^phase5]

The floor bot is used wherever a seat needs a sensible occupant and no character: it fills the empty seats of a small table in the [[arena]], it plays the games the [[belief benchmark]] scores and the games [[Colonel Mustard]]'s tree is grown from, it answers for a seat whose player is out of the game, and at a web table it plays a person's turn when their time runs out, three turns in a row handing the seat over to it altogether.[^web]

### People

A person at a clude table reasons on the floor and nothing else. Their notepad is the floor's grid, filled in as each suggestion is answered; the certainty tag beside their name, shown to everyone, is computed from the floor alone, an even spread over whatever it has not ruled out. They are shown no method's probabilities, since play is blind. A [[Claude]] playing a seat from a chat window gets the same: "MCP players get their numbers from floorbot, that's it. No heads! They're the head!"[^web][^mcp]

## Measured

The floor has no probabilities to score. What has been measured is the game it plays.

Games between floor bots end in about {{fact:floor.suggestions}} suggestions, with {{fact:floor.solved}} of the viewers holding a proven envelope at the end; the random players they replaced ran {{fact:random.suggestions}} suggestions with a floor that plateaued early and no viewer ever proving the envelope at a full table.[^selfplay] That difference is why the floor bot is the training regime: Mustard's rows and the benchmark's positions come from games that carry information throughout and end by deduction.

{{table:bench.grid|The six methods on the Classic board: log-loss at four checkpoints, {{fact:bench.grid.games}} games, 15 September 2026. The uniform row is the floor's own belief.}}

The uniform row is what the floor alone is worth: {{fact:bench.grid.uniform.50}} at the halfway mark and {{fact:bench.grid.uniform.100}} at the end of a game, with its first choice right {{fact:bench.grid.uniform.top1}} of the time. Four of the six methods beat it at the end and two, [[Naive Bayes]] and [[Dempster-Shafer theory]], trail it throughout; the floor is the line every method is measured from.[^grid]

In the arena the floor bot is the "does a character beat a purely logical player" baseline: the sweeps that set the presets seat every character between floor bots, and a win rate there is a character's rate against pure logic.[^sweeps]

## Limitations

- **It is incomplete.** What its three rules cannot reach stays open, however surely the facts determine it; only a full search finds the rest.
- **It says nothing about likelihood.** Every card the floor leaves open is, to the floor, equally open. Every judgement of likelihood is a method's.
- **It reads only the formal record.** Who asked what, and how often, and what anyone said in [[table talk]], are not facts to the floor; the formal answer to a suggestion is.
- **It is one seat's view.** The floor is computed from what one player can see, so each seat has its own, and the floor bot's "proof" is proof from where it sits.

## See also

- [[Belief]], what a method adds on top of the floor, and how the six answers to one question compare
- [[Exact posterior enumeration]], the complete search the floor's propagation stops short of
- [[Dempster-Shafer theory]], which puts weight on the floor's open facts as they stand
- [[Detective notepad]], the floor as a person sees it
- [[Uniform baseline]] and [[Belief benchmark]]
- [[w:Constraint satisfaction problem|Constraint satisfaction problem]] and [[w:Local consistency|local consistency]] on Wikipedia

## References

{{references}}

[^invariant]: {{cite:CLAUDE.md|Architecture in brief}}
[^web]: {{cite:docs/web.md|A table}}
[^module]: {{cite:clude_constraints/propagator.py|`propagate`, `_Working.propagate` and the three rules}}
[^aima]: {{cite:russell-norvig|Chapter 6, "Constraint Satisfaction Problems": constraint propagation, arc consistency, and search}}
[^tests]: {{cite:tests/test_constraints.py|`test_propagator_is_sound_across_real_games` and `test_propagator_can_reach_full_certainty_given_enough_play`}}
[^architecture]: {{cite:docs/architecture.md|The deduction floor (`clude_constraints`)}}
[^base]: {{cite:clude_agents/base.py|`mask_and_normalize`}}
[^phase5]: {{cite:docs/phase5-plan.md|8. As implemented (2026-09-12)}}
[^floorbot]: {{cite:clude_constraints/floor_bot.py|`FloorBot` and its four decisions}}
[^mcp]: {{cite:CLAUDE.md|Settled decisions (David's)}} "No persona advises a chat seat", 2026-09-21.
[^selfplay]: {{cite:docs/architecture.md|Self-play regimes: `RandomBot` and `FloorBot` (Phase 5b)}}
[^grid]: {{cite:docs/strategy-glossary.md|Belief benchmark on the grid (Stage 1a)}}
[^sweeps]: {{cite:docs/strategy-glossary.md|Dial sweeps}}

{{navbox:clude}}
