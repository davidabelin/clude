"""
Reproduces the verified legacy bugs listed in legacy/README.md.

Run from the repo root:  python -m legacy.known_issues_check
Each line prints what the code does now and what it should do. When a line's
two values match, that issue is fixed (in whatever code replaces legacy/).
Only needs numpy and scipy.
"""
from legacy.domain import GameState, Suggestion, SUSPECTS
from legacy.belief_tracker import BayesianBeliefTracker
from legacy.constraints import ConstraintPropagator

MY_CARDS = frozenset(["Scarlett", "Knife", "Kitchen", "Ballroom", "Rope", "Plum"])


def main():
    gs = GameState(n_players=3, my_index=0, my_cards=MY_CARDS)

    cp = ConstraintPropagator(gs, cards_per_player=6)
    cp.add_no_refutation([1, 2], ("Mustard",))
    print(f"C1 elimination:   Mustard ruled out for p1 and p2 -> {cp.known['Mustard']!r}  (should be 'envelope')")

    t = BayesianBeliefTracker(gs)
    t.update_from_suggestion(Suggestion(1, "Green", "Wrench", "Study", refuter=0, shown_to=1))
    p = t.belief[t.card_idx["Green"], 3]  # holder 3 = player 2, who passed
    print(f"B1 skipped player: P(p2 holds Green) after p2 passed -> {p:.3f}  (should be 0.000)")

    t = BayesianBeliefTracker(gs)
    t.update_from_suggestion(Suggestion(1, "Green", "Wrench", "Study", refuter=None, shown_to=1))
    env = t.envelope_probabilities()
    total = sum(env[s] for s in SUSPECTS)
    print(f"B2 envelope sum:  sum of suspect envelope probs -> {total:.3f}  (should be 1.000)")

    for card, holder in [("Mustard", 1), ("White", 2), ("Peacock", 2)]:
        t.mark_card_seen(card, holder)
    print(f"B3 last suspect:  P(Green in envelope), all others located -> "
          f"{t.envelope_probabilities()['Green']:.3f}  (should be 1.000)")


if __name__ == "__main__":
    main()
