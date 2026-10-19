"""Offline Phase 14 searches for Mustard, White and Green.

All searches consume a verified :class:`FrozenCorpus`. They write metrics
and hashes, never a production logbook. Numerical gates can reject a
candidate, but cannot approve personality: that remains an explicit human
review before code defaults or staged method documents are promoted.
"""
from __future__ import annotations

import itertools
import json
from pathlib import Path
from typing import Optional

from clude_agents.bandit import BanditAgent
from clude_agents.character import probabilities_confidence
from clude_agents.decision_tree import DecisionTreeAgent
from clude_agents.markov import MarkovAgent
from clude_training import memory as method_memory
from clude_training.arena import DEFAULT_MAX_TURNS, DEFAULT_ROSTER, run_arena
from clude_training.benchmark import _Accumulator, _Calibration
from clude_training.recalibration import FrozenCorpus, document_hash, experiment_context
from clude_training.replay import snapshots_from_record
from clude_training.self_play import DEFAULT_CHECKPOINTS, DEFAULT_PLAYER_COUNTS
from clude_training.sweep import SweepResult

MUSTARD_BASE_GAMES = (25, 50, 100)
MUSTARD_DEPTHS = (4, 6, 8)
MUSTARD_MIN_LEAVES = (10, 20, 40)
MUSTARD_SMOOTHING = (1.0, 3.0, 6.0)
WHITE_PRIOR_MASSES = (1.0, 2.0, 4.0, 8.0, 16.0)
GREEN_STEP_SIZES = (1.0, 2.0, 4.0)
GREEN_DECAY_RATES = (1.02, 1.05, 1.10)


def _atomic_json(path: Optional[Path], value: dict) -> None:
    if path is None:
        return
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def _calibration_dict(calibration: _Calibration) -> dict:
    total = sum(calibration.counts)
    weighted_error = 0.0
    overconfidence = []
    for count, p_sum, correct in zip(
        calibration.counts, calibration.p_sums, calibration.correct
    ):
        if not count:
            continue
        mean_p = p_sum / count
        accuracy = correct / count
        weighted_error += count * abs(mean_p - accuracy)
        if count >= 10:
            overconfidence.append(mean_p - accuracy)
    return {
        **calibration.to_dict(),
        "expected_calibration_error": weighted_error / total if total else float("nan"),
        "max_overconfidence_n10": max(overconfidence, default=0.0),
    }


def evaluate_frozen_agent(
    corpus: FrozenCorpus,
    agent,
    *,
    split: str = "validation",
    checkpoints: tuple = DEFAULT_CHECKPOINTS,
    seed: int = 14014,
    initial_state: Optional[dict] = None,
) -> dict:
    """Score one fixed agent on copied records from a corpus split.

    Reset once, optionally load frozen state, and evaluate masked snapshots
    without outcome feedback. The source store is not modified. Reusing the
    validation split for candidate selection makes it selection evidence,
    rather than an independent final confirmation set.
    """
    agent.reset(seed)
    if initial_state is not None:
        loader = getattr(agent, "load_state", None)
        if loader is None:
            raise ValueError("initial_state supplied for an agent without load_state")
        loader(initial_state)
    cells = {checkpoint: _Accumulator() for checkpoint in checkpoints}
    calibrations = {checkpoint: _Calibration() for checkpoint in checkpoints}
    games = snapshot_count = 0
    for _row, record in corpus.records(split):
        games += 1
        labels = [seat.label for seat in sorted(record.seats, key=lambda seat: seat.seat)]
        if hasattr(agent, "set_table"):
            agent.set_table(labels)
        for snapshot in snapshots_from_record(record, checkpoints):
            belief = agent.select_action(snapshot.obs)
            cells[snapshot.checkpoint].update(belief.probabilities, snapshot.envelope)
            confidence = probabilities_confidence(belief)
            calibrations[snapshot.checkpoint].update(confidence, snapshot.envelope)
            snapshot_count += 1
    return {
        "split": split,
        "games": games,
        "snapshots": snapshot_count,
        "checkpoints": {
            str(checkpoint): {
                **cells[checkpoint].to_dict(),
                "calibration": _calibration_dict(calibrations[checkpoint]),
            }
            for checkpoint in checkpoints
        },
    }


def heldout_gate(candidate: dict, baseline: dict, tolerance: float = 0.02) -> dict:
    """The shared loss/calibration portion of the Phase 14 promotion gate."""
    checks = []
    for checkpoint, metrics in candidate["checkpoints"].items():
        current = baseline["checkpoints"][checkpoint]
        logloss_ok = metrics["log_loss"] <= current["log_loss"] + tolerance
        ece_ok = (
            metrics["calibration"]["expected_calibration_error"]
            <= current["calibration"]["expected_calibration_error"] + tolerance
        )
        new_failure = (
            metrics["calibration"]["max_overconfidence_n10"] > 0.15
            and metrics["calibration"]["max_overconfidence_n10"]
            > current["calibration"]["max_overconfidence_n10"] + 0.05
        )
        checks.append({
            "checkpoint": checkpoint,
            "candidate_log_loss": metrics["log_loss"],
            "baseline_log_loss": current["log_loss"],
            "within_0.02": logloss_ok,
            "calibration_ece_ok": ece_ok,
            "new_systematic_overconfidence": new_failure,
            "passes": logloss_ok and ece_ok and not new_failure,
        })
    return {"passes": all(check["passes"] for check in checks), "checkpoints": checks}


def _score(metrics: dict) -> tuple:
    checkpoints = metrics["checkpoints"]
    ordered = [checkpoints[key] for key in sorted(checkpoints, key=float)]
    return (
        sum(row["log_loss"] for row in ordered) / len(ordered),
        sum(row["brier"] for row in ordered) / len(ordered),
        sum(row["calibration"]["expected_calibration_error"] for row in ordered) / len(ordered),
    )


def _select_green_candidate(candidates: list[dict]) -> dict:
    """Prefer Green candidates that clear both held-out and arena gates."""
    fully_eligible = [
        candidate for candidate in candidates
        if candidate["heldout_gate"]["passes"] and candidate["arena_gate"]["passes"]
    ]
    heldout_eligible = [
        candidate for candidate in candidates if candidate["heldout_gate"]["passes"]
    ]
    return min(
        fully_eligible or heldout_eligible or candidates,
        key=lambda candidate: tuple(candidate["score"]),
    )


def _method_document(corpus: FrozenCorpus, kind: str) -> dict:
    document = method_memory.empty_memory(kind)
    for row, record in corpus.records("train"):
        label_map = {"Plum": "PlumOG"} if row["plum_generation"] == "plum_og" else None
        method_memory.absorb(document, record, white_label_map=label_map)
    return document


def _arena_gate(
    identity: str,
    baseline_agent,
    candidate_agent,
    *,
    games: int,
    seed: int,
    baseline_state: Optional[dict] = None,
    candidate_state: Optional[dict] = None,
) -> dict:
    common = dict(
        n_games=games, seed=seed, roster=DEFAULT_ROSTER,
        player_counts=DEFAULT_PLAYER_COUNTS, max_turns=DEFAULT_MAX_TURNS,
    )
    baseline = run_arena(
        **common, agent_overrides={identity: baseline_agent},
        agent_states=({identity: baseline_state} if baseline_state is not None else None),
        run_id=f"phase14-{identity.lower()}-baseline-{seed}",
    )
    candidate = run_arena(
        **common, agent_overrides={identity: candidate_agent},
        agent_states=({identity: candidate_state} if candidate_state is not None else None),
        run_id=f"phase14-{identity.lower()}-candidate-{seed}",
    )
    before = baseline.per_player[identity]
    after = candidate.per_player[identity]
    paired = SweepResult(
        dial="accuse_threshold", values=(0.0, 1.0), characters=(identity,), roster=DEFAULT_ROSTER,
        results=[baseline, candidate],
    ).paired_deltas()[1]
    win_delta = after.win_rate - before.win_rate
    wrong_delta = after.wrong_accusation_rate - before.wrong_accusation_rate
    return {
        "games": games,
        "seed": seed,
        "baseline": before.to_dict(),
        "candidate": after.to_dict(),
        "win_rate_delta": win_delta,
        "wrong_accusation_rate_delta": wrong_delta,
        "paired": paired,
        "passes": win_delta >= -0.05 and wrong_delta <= 0.05,
    }


def search_mustard(
    corpus: FrozenCorpus,
    *,
    output: Optional[Path] = None,
    arena_games: int = 192,
    arena_seed: int = 141400,
) -> dict:
    """Evaluate all 81 required Mustard configurations and arena-check the best."""
    train_document = _method_document(corpus, "rows")
    extra_rows = method_memory.extra_rows(train_document)
    baseline_document = corpus.baseline_method("Mustard") or method_memory.empty_memory("rows")
    baseline_agent = DecisionTreeAgent(extra_rows=method_memory.extra_rows(baseline_document))
    baseline = evaluate_frozen_agent(corpus, baseline_agent)
    report = {
        "method": "Mustard",
        "corpus_sha256": corpus.sha256,
        "context": experiment_context(),
        "training_document_sha256": document_hash(train_document),
        "training_games": method_memory.n_games(train_document),
        "training_rows": len(extra_rows),
        "baseline": baseline,
        "candidates": [],
        "complete": False,
    }
    for base_games, depth, min_leaf, smoothing in itertools.product(
        MUSTARD_BASE_GAMES, MUSTARD_DEPTHS, MUSTARD_MIN_LEAVES, MUSTARD_SMOOTHING
    ):
        config = {
            "n_training_games": base_games,
            "max_depth": depth,
            "min_samples_leaf": min_leaf,
            "smoothing_m": smoothing,
        }
        agent = DecisionTreeAgent(**config, extra_rows=extra_rows)
        metrics = evaluate_frozen_agent(corpus, agent)
        report["candidates"].append({
            "config": config, "metrics": metrics, "score": list(_score(metrics)),
            "heldout_gate": heldout_gate(metrics, baseline),
        })
        _atomic_json(output, report)
    eligible = [candidate for candidate in report["candidates"] if candidate["heldout_gate"]["passes"]]
    ranked = sorted(eligible or report["candidates"], key=lambda candidate: tuple(candidate["score"]))
    best = ranked[0]
    config = best["config"]
    arena = _arena_gate(
        "Mustard",
        DecisionTreeAgent(extra_rows=method_memory.extra_rows(baseline_document)),
        DecisionTreeAgent(**config, extra_rows=extra_rows),
        games=arena_games,
        seed=arena_seed,
    )
    report.update({
        "complete": True,
        "shortlist": config,
        "shortlist_score": best["score"],
        "arena": arena,
        "numerical_gate": best["heldout_gate"]["passes"] and arena["passes"],
        "personality_gate": "pending human review",
        "ready_for_promotion": False,
    })
    _atomic_json(output, report)
    return report


def search_white(
    corpus: FrozenCorpus,
    *,
    output: Optional[Path] = None,
    arena_games: int = 192,
    arena_seed: int = 141500,
) -> dict:
    """Evaluate White's five prior masses and arena-check the best."""
    train_document = _method_document(corpus, "counts")
    priors = method_memory.priors(train_document)
    baseline_document = corpus.baseline_method("White") or method_memory.empty_memory("counts")
    baseline_priors = method_memory.priors(baseline_document)
    baseline = evaluate_frozen_agent(corpus, MarkovAgent(priors=baseline_priors))
    report = {
        "method": "White",
        "corpus_sha256": corpus.sha256,
        "context": experiment_context(),
        "training_document_sha256": document_hash(train_document),
        "training_games": method_memory.n_games(train_document),
        "private_identity_count": len(priors),
        "baseline": baseline,
        "candidates": [],
        "complete": False,
    }
    for mass in WHITE_PRIOR_MASSES:
        metrics = evaluate_frozen_agent(corpus, MarkovAgent(priors=priors, prior_mass=mass))
        report["candidates"].append({
            "config": {"prior_mass": mass}, "metrics": metrics,
            "score": list(_score(metrics)), "heldout_gate": heldout_gate(metrics, baseline),
        })
        _atomic_json(output, report)
    eligible = [candidate for candidate in report["candidates"] if candidate["heldout_gate"]["passes"]]
    best = min(eligible or report["candidates"], key=lambda candidate: tuple(candidate["score"]))
    mass = best["config"]["prior_mass"]
    arena = _arena_gate(
        "White", MarkovAgent(priors=baseline_priors), MarkovAgent(priors=priors, prior_mass=mass),
        games=arena_games, seed=arena_seed,
    )
    report.update({
        "complete": True,
        "shortlist": best["config"],
        "shortlist_score": best["score"],
        "arena": arena,
        "numerical_gate": best["heldout_gate"]["passes"] and arena["passes"],
        "personality_gate": "pending human review",
        "ready_for_promotion": False,
    })
    _atomic_json(output, report)
    return report


def search_green(
    corpus: FrozenCorpus,
    *,
    output: Optional[Path] = None,
    training_games: int = 200,
    validation_games: int = 200,
    training_seed: int = 141600,
    validation_seed: int = 241600,
) -> dict:
    """Train each Green candidate afresh and evaluate on separate seed blocks.

    Candidates start at Beta(1,1). The comparison agent loads the corpus's
    frozen former method state when present; it is not a fresh-state baseline.
    Rank candidates using both held-out snapshot and validation-arena gates,
    so neither selection input is an independent final confirmation set.
    Write resumable local reports when ``output`` is supplied; do not promote.
    """
    baseline_document = corpus.baseline_method("Green") or {
        "version": 1, "kind": "state", "games": 0, "arms": {},
    }
    baseline_state = {"arms": baseline_document.get("arms", {})}
    baseline_metrics = evaluate_frozen_agent(
        corpus, BanditAgent(), initial_state=baseline_state
    )
    baseline_arena = run_arena(
        n_games=validation_games, seed=validation_seed, roster=DEFAULT_ROSTER,
        player_counts=DEFAULT_PLAYER_COUNTS, max_turns=DEFAULT_MAX_TURNS,
        agent_overrides={"Green": BanditAgent()}, agent_states={"Green": baseline_state},
        run_id=f"phase14-green-baseline-{validation_seed}",
    )
    report = {
        "method": "Green",
        "corpus_sha256": corpus.sha256,
        "context": experiment_context(),
        "training_games": training_games,
        "validation_games": validation_games,
        "baseline": baseline_metrics,
        "candidates": [],
        "complete": False,
    }
    for step_size, decay_rate in itertools.product(GREEN_STEP_SIZES, GREEN_DECAY_RATES):
        config = {"step_size": step_size, "decay_rate": decay_rate}
        training_agent = BanditAgent(**config)
        training_arena = run_arena(
            n_games=training_games, seed=training_seed, roster=DEFAULT_ROSTER,
            player_counts=DEFAULT_PLAYER_COUNTS, max_turns=DEFAULT_MAX_TURNS,
            agent_overrides={"Green": training_agent},
            run_id=f"phase14-green-train-{step_size:g}-{decay_rate:g}",
        )
        state = training_agent.state_dict()
        method_document = {
            "version": 1, "kind": "state", "games": training_games, "arms": state["arms"],
        }
        candidate_metrics = evaluate_frozen_agent(
            corpus, BanditAgent(**config), initial_state=state
        )
        validation_agent = BanditAgent(**config)
        validation_arena = run_arena(
            n_games=validation_games, seed=validation_seed, roster=DEFAULT_ROSTER,
            player_counts=DEFAULT_PLAYER_COUNTS, max_turns=DEFAULT_MAX_TURNS,
            agent_overrides={"Green": validation_agent}, agent_states={"Green": state},
            run_id=f"phase14-green-validation-{step_size:g}-{decay_rate:g}",
        )
        before = baseline_arena.per_player["Green"]
        after = validation_arena.per_player["Green"]
        arena_gate = {
            "win_rate_delta": after.win_rate - before.win_rate,
            "wrong_accusation_rate_delta": after.wrong_accusation_rate - before.wrong_accusation_rate,
        }
        arena_gate["passes"] = (
            arena_gate["win_rate_delta"] >= -0.05
            and arena_gate["wrong_accusation_rate_delta"] <= 0.05
        )
        report["candidates"].append({
            "config": config,
            "state_sha256": document_hash(method_document),
            "state": method_document,
            "training": training_arena.per_player["Green"].to_dict(),
            "metrics": candidate_metrics,
            "score": list(_score(candidate_metrics)),
            "heldout_gate": heldout_gate(candidate_metrics, baseline_metrics),
            "validation": after.to_dict(),
            "arena_gate": arena_gate,
        })
        _atomic_json(output, report)
    best = _select_green_candidate(report["candidates"])
    report.update({
        "complete": True,
        "shortlist": best["config"],
        "shortlist_state_sha256": best["state_sha256"],
        "numerical_gate": best["heldout_gate"]["passes"] and best["arena_gate"]["passes"],
        "personality_gate": "pending human review",
        "ready_for_promotion": False,
    })
    _atomic_json(output, report)
    return report
