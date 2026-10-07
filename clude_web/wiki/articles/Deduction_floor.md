---
title: Deduction floor
short: Shared logical deductions from one player's hand and observed disproofs
categories: Methods
redirects: Floor, The floor, The deduction floor, Constraint propagation, Floor bot, The floor bot, FloorBot
dyk: ... that all six characters use the same [[deduction floor]] to fill in their notepads before applying different methods to the unresolved cards?
dyk: ... that the [[deduction floor]] retained every card's true holder in the seeded games used by its soundness test?
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

The **deduction floor** is [[clude]]'s shared system for deriving facts about the cards by [[w:Deductive reasoning|deduction]]. It uses one player's hand and the recorded answers to [[suggestion|suggestions]] to determine where cards are known to be, where they could still be, and which statements such as "Mustard holds at least one of these cards" remain unresolved. Three rules repeat until they make no further changes. Their output is a *mask* that constrains every [[Category:Methods|method]]'s [[belief]]: cards excluded from [[the envelope]] receive probability 0, and cards proven to be inside receive 1.[^module][^base]

The floor keeps methods with very different approaches consistent with the same deductions.[^invariant] [[Miss Scarlett]]'s [[Naive Bayes]] may overestimate an unresolved card, but cannot assign envelope probability to one in her hand. The [[uniform baseline]] adds no further judgement: it distributes probability evenly across the floor's remaining candidates. The floor is sound for valid observations but incomplete; some deductions require a search that its three rules do not perform.

The **floor bot** plays using these deductions alone, without a character-specific method or personality. It asks about unresolved cards and [[accusation|accuses]] only when the floor proves all three envelope cards. It supplies opponents for training and several measurement regimes, fills designated floor-bot seats and takes over timed-out human turns. A person's [[detective notepad]] also uses the floor, while omitting the characters' probability estimates.[^floorbot][^web]

## At the table

!!! example "Worked example: the Rope question, as the floor sees it"
    {{figure:floor-notepad|What the floor knows in the Rope question, from the viewer's chair. Seventeen cards are placed, including the Study in the envelope; four remain unresolved.}}

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

The rules interact. Resolving an open fact can fill a hand; excluding other cards from that full hand can leave a category with one envelope candidate; resolving that category can then simplify another open fact. The loop stops at a [[w:Fixed point (mathematics)|fixed point]], where another pass changes nothing. Each change removes a possibility, so the process terminates.

### Contradictions

The floor raises an error if its constraints contradict one another: a card has no possible holder, an open fact has no possible member, or a hand contains more placed cards than its capacity. Valid game observations should not produce these contradictions; the project treats one as a bug in the construction or processing of the observation.[^module]

!!! algorithm "The deduction floor"
        Input: one seat's view: own hand, every suggestion and its answers, hand sizes
        for every card: holders(c) ← every seat, and the envelope
        own hand:                      holders(c) ← {me}
        a player passed over:          remove that player from the three named cards
        a card shown to me:            holders(c) ← {the player who showed it}
        a card shown, unseen by me:    record "that player holds one of the three"
        repeat until a pass changes nothing:
            for each open fact: drop the cards its player can no longer hold;
                if one card remains, it is that player's;  if none, contradiction
            in each category: once one card is the envelope's, no other can be;
                if only one card can be the envelope's, it is
            for each player: once their hand is full, nothing else is theirs
        return holders, the open facts still unresolved, and the hand sizes

## Formally

What the floor does is [[w:Constraint satisfaction problem|constraint propagation]]. Each card is a variable whose domain is the set of holders it could still have; each fact is a constraint; and the three rules are propagators that shrink domains until no rule can shrink one further. The result is a fixed point of the rules, reached in finitely many steps because every step removes something and nothing is ever put back.[^aima]

Soundness and completeness describe different properties of this process.

**[[w:Soundness|Soundness]].** Given valid observations, each rule excludes only holders incompatible with the evidence. The actual deal therefore remains possible. The soundness test runs seeded games and checks each player's completed-game observation against the true holders. A separate convergence test checks that at least one player can prove the envelope after sufficiently informative play.[^tests]

**[[w:Completeness (logic)|Incompleteness]].** The rules do not derive every conclusion implied by the evidence. They process individual constraints, somewhat like [[w:Unit propagation|unit propagation]], without exploring alternative assignments. A conclusion requiring cases such as "if Mustard holds Peacock, then ...; otherwise he must hold the Rope, so ..." may remain unresolved. A completed [[exact posterior enumeration|search over consistent deals]] can find such conclusions: if every surviving deal puts a card in the envelope, its probability under the counting model is 1. The floor trades this completeness for inexpensive propagation.

The floor's output has three parts, and the shape was chosen for the methods that read it. Each card's set of possible holders is exposed as a set rather than collapsed to known-or-unknown, because [[Mrs. Peacock]]'s [[Dempster-Shafer theory]] wants exactly that structure to put weight on. The open facts are exposed separately, because per-card sets lose the joint "one of these three" that [[Professor Plum]]'s search needs to enumerate consistent deals and that Peacock holds as a mass on a set.[^architecture]

## In clude

{{figure:floor-then-method|wide|The floor comes before every method and after it: one gate in front of the six, and one behind.}}

The module is `clude_constraints/propagator.py`, with the floor bot beside it. It was built by finishing a constraint propagator from the project's earlier code, whose own list of known issues had five items: eliminations were not actually tracked, the category rule was missing, hand sizes were stored and never read, contradictions were dropped silently, and two parts of the code disagreed about what to call the envelope. All five were fixed, and the floor recomputes its result from scratch on every call, so that no character can ever act on a stale mask.[^architecture]

Every method ends with the same step, in `clude_agents/base.py`: whatever raw scores a method has produced, a card the floor has ruled out of the envelope is set to 0, a card it has proved is set to 1, and the scores of the cards still in question are scaled to sum to 1 within each category. A method with no opinion at all gets an even spread over what the floor permits, which is the uniform baseline.[^base]

One bug of the floor's own was found by Peacock. Until Phase 5, an open fact that a placed card already satisfied was kept and reported as open; Plum's search filtered such facts for itself, but Peacock read the fact's other, unplaced members as live evidence against those cards. The floor now drops them.[^phase5]

### The floor bot

The floor bot implements the engine's player contract without a probability method or personality dials. It chooses uniformly among unresolved suspects and weapons that it does not hold. Once a category is resolved, it names the proven envelope card so the answer can test the other categories. For movement, it prefers unresolved rooms, then moves towards them. When every room is resolved, it favours a room whose card opponents cannot show. It accuses only on proof.[^floorbot]

An earlier uniform movement policy produced uninformative games: bots repeatedly entered rooms whose cards were held and received the same disproofs. Tracing the stalled games also exposed a board bug that prevented ordinary exits from rooms. The exits were repaired and movement was changed to favour unresolved rooms.[^phase5]

The floor bot fills spare seats in small [[arena]] tables, plays the games used by the [[belief benchmark]] and trains [[Colonel Mustard]]'s tree. It also answers for eliminated players. At a web table it takes a human player's turn after a timeout; three consecutive timeouts hand the seat over to it.[^web]

### People

A person's notepad records the floor's deductions as suggestions are answered. Their public certainty tag uses an even distribution over the remaining envelope candidates. During play, they see no character's probability bars, which could reveal private cards. A [[Claude]] playing through the chat interface receives the floor's notepad rather than a character method's estimates. The person or chat agent supplies its own reasoning beyond those deductions.[^web][^mcp]

## Measured

The floor itself produces constraints rather than probabilities. The uniform baseline supplies a probability score for those constraints, while self-play measures the floor bot's information gathering.

In the recorded self-play comparison, floor-bot games took about {{fact:floor.suggestions}} suggestions, and {{fact:floor.solved}} of the viewers had proved the envelope by the end. The earlier random-bot games took {{fact:random.suggestions}} suggestions; their deductions plateaued, and no viewer proved the envelope at a full table.[^selfplay] Floor-bot play was therefore adopted for Mustard's training data and benchmark positions.

{{table:bench.grid|The six methods on the Classic board: log-loss at four checkpoints, {{fact:bench.grid.games}} games, 15 September 2026. The uniform row is the floor's own belief.}}

The uniform row gives the baseline score for this run: {{fact:bench.grid.uniform.50}} at halfway and {{fact:bench.grid.uniform.100}} at the end, with final top-choice accuracy {{fact:bench.grid.uniform.top1}}. Four methods had lower final log-loss; [[Naive Bayes]] and [[Dempster-Shafer theory]] had higher loss at every checkpoint.[^grid]

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
