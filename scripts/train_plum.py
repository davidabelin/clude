"""Train Plum: regularised Nash dynamics over the floor (Phase 12, N4;
`docs/deepnash-plan.md` 3.2).

    python scripts/train_plum.py --games 200000 --batch 256 --workers 8 \\
        --out data/plum-training/run1 --eval-every 20
    python scripts/train_plum.py --resume data/plum-training/run1/ckpt-0100.npz \\
        --games 50000 --out data/plum-training/run2 --export clude_agents/weights/plum.npz

Each update rolls out `--batch` games through `clude_training.rollout`
(the real engine, the mixed population, a worker pool playing with the
current numpy weights), then takes `--epochs` Adam steps on the batch:

- a NeuRD-style policy gradient on the regularised reward: each
  decision's reward is its seat's outcome less `--eta` times the log
  ratio of the policy to a reference policy, the R-NaD transform that
  pulls the dynamics toward an equilibrium rather than around one;
  the advantage is that reward less the value head's estimate;
- the value head toward the seat's outcome;
- the belief head by cross-entropy against the true envelope, over the
  cards the floor still allows (`--lambda-belief`);
- an entropy bonus (`--entropy`).

The reference policy is a frozen copy refreshed every `--refresh`
updates (R-NaD's outer loop). V-trace is left out: every batch is
on-policy, so no importance weights are needed.

`TorchNet` is `clude_agents.deep_nash.WEIGHT_SHAPES` as parameters,
nothing more: it is built from the numpy dict and exported to it, so
the forward pass Plum plays with is the one trained. A run writes
`curve.jsonl` (a line per update), `ckpt-NNNN.npz` and an `eval.jsonl`
line every `--eval-every` updates (`rollout.evaluate` on the two
standard tables, and the belief benchmark's log-loss), and, with
`--export`, the final weights where Plum reads them. torch is a
developer dependency only (`requirements.txt`); nothing in the game
imports this script.
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
import time
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from clude_agents import deep_nash  # noqa: E402
from clude_core.domain import ALL_CARDS, ROOMS, SUSPECTS, WEAPONS  # noqa: E402
from clude_training import rollout  # noqa: E402

try:
    import torch
    import torch.nn.functional as F
    from torch import nn
except ImportError as exc:  # pragma: no cover - the suite skips without torch
    raise SystemExit("train_plum.py needs torch: pip install torch (docs/deepnash-plan.md 3.2)") from exc

DEFAULT_OUT = REPO / "data" / "plum-training"
CATEGORY_SLICES = (
    slice(0, len(SUSPECTS)),
    slice(len(SUSPECTS), len(SUSPECTS) + len(WEAPONS)),
    slice(len(SUSPECTS) + len(WEAPONS), len(ALL_CARDS)),
)
assert CATEGORY_SLICES[2].stop == len(SUSPECTS) + len(WEAPONS) + len(ROOMS)
NEG = -1e9


# -- the network in torch -----------------------------------------------------------


class TorchNet(nn.Module):
    """`deep_nash.WEIGHT_SHAPES` as parameters, with the same forward
    arithmetic as `deep_nash.forward` and `deep_nash.move_scores`."""

    def __init__(self) -> None:
        super().__init__()
        for name, shape in deep_nash.WEIGHT_SHAPES.items():
            setattr(self, name, nn.Parameter(torch.zeros(shape, dtype=torch.float32)))

    @classmethod
    def from_numpy(cls, weights: dict) -> "TorchNet":
        net = cls()
        with torch.no_grad():
            for name in deep_nash.WEIGHT_SHAPES:
                getattr(net, name).copy_(torch.as_tensor(np.asarray(weights[name], dtype=np.float32)))
        return net

    def to_numpy(self) -> dict:
        return {name: getattr(self, name).detach().cpu().numpy().astype(np.float64) for name in deep_nash.WEIGHT_SHAPES}

    def trunk(self, x: torch.Tensor) -> torch.Tensor:
        h = F.relu(x @ self.trunk1_w + self.trunk1_b)
        return F.relu(h @ self.trunk2_w + self.trunk2_b)

    def heads(self, h: torch.Tensor) -> dict:
        return {
            "belief": h @ self.belief_w + self.belief_b,
            "suspect": h @ self.suspect_w + self.suspect_b,
            "weapon": h @ self.weapon_w + self.weapon_b,
            "value": torch.tanh(h @ self.value_w + self.value_b)[:, 0],
        }

    def move_logits(self, hidden_rows: torch.Tensor, choice_rows: torch.Tensor) -> torch.Tensor:
        joined = torch.cat([hidden_rows, choice_rows], dim=1)
        z = F.relu(joined @ self.move1_w + self.move1_b)
        return (z @ self.move2_w + self.move2_b)[:, 0]


# -- a batch of traces as tensors --------------------------------------------------------


def stack_traces(traces: list) -> dict:
    """Every trace's `to_arrays` end to end, the ragged offsets rebased,
    plus ``row_decision`` (the decision each option row belongs to) and
    ``row_action`` (True on the row of the action taken). Empty traces
    (no network decision) are skipped."""
    parts = [t.to_arrays() for t in traces if t.decisions]
    if not parts:
        raise ValueError("no network decisions in this batch")
    out: dict = {}
    for key in ("states", "possible", "envelope", "head", "action", "reward", "seat", "game", "choices", "candidates"):
        out[key] = np.concatenate([p[key] for p in parts])
    n = len(out["head"])
    row_decision: list = []
    row_action = np.zeros(0, dtype=bool)
    decision = 0
    rows = []
    for p in parts:
        for i in range(len(p["head"])):
            if p["head"][i] == 0:
                k = p["choice_offsets"][i + 1] - p["choice_offsets"][i]
            else:
                k = p["candidate_offsets"][i + 1] - p["candidate_offsets"][i]
            row_decision.extend([decision] * int(k))
            taken = np.zeros(int(k), dtype=bool)
            taken[int(p["action"][i])] = True
            rows.append(taken)
            decision += 1
    out["row_decision"] = np.array(row_decision, dtype=np.int64)
    out["row_action"] = np.concatenate(rows) if rows else row_action
    out["n_decisions"] = n
    return out


def _segment_logsumexp(logits: torch.Tensor, segment: torch.Tensor, n: int) -> torch.Tensor:
    """log-sum-exp of `logits` within each segment id, a vector of `n`."""
    top = torch.full((n,), NEG, dtype=logits.dtype, device=logits.device)
    top = top.scatter_reduce(0, segment, logits, reduce="amax", include_self=True)
    shifted = torch.exp(logits - top[segment])
    total = torch.zeros(n, dtype=logits.dtype, device=logits.device).scatter_add(0, segment, shifted)
    return top + torch.log(total)


def option_logits(net: TorchNet, batch: dict, device) -> tuple:
    """One logit per option row of the batch, from the right head, and
    the decisions' hidden vectors and heads."""
    states = torch.as_tensor(batch["states"], dtype=torch.float32, device=device)
    hidden = net.trunk(states)
    heads = net.heads(hidden)
    head = torch.as_tensor(batch["head"], device=device)
    row_decision = torch.as_tensor(batch["row_decision"], device=device)
    logits = torch.zeros(len(row_decision), dtype=torch.float32, device=device)
    is_move_row = head[row_decision] == 0
    if is_move_row.any():
        choices = torch.as_tensor(batch["choices"], dtype=torch.float32, device=device)
        move_rows = torch.nonzero(is_move_row)[:, 0]
        logits = logits.index_put((move_rows,), net.move_logits(hidden[row_decision[move_rows]], choices))
    if (~is_move_row).any():
        sugg_rows = torch.nonzero(~is_move_row)[:, 0]
        candidates = torch.as_tensor(batch["candidates"], device=device)
        which = row_decision[sugg_rows]
        suspect = heads["suspect"][which].gather(1, candidates[:, None])[:, 0]
        weapon = heads["weapon"][which].gather(1, candidates[:, None])[:, 0]
        logits = logits.index_put((sugg_rows,), torch.where(head[which] == 1, suspect, weapon))
    return logits, hidden, heads


def belief_loss(belief_logits: torch.Tensor, possible: torch.Tensor, envelope: torch.Tensor) -> torch.Tensor:
    """Cross-entropy per category over the cards the floor allows,
    averaged over decisions and the three categories."""
    masked = belief_logits.masked_fill(possible == 0, NEG)
    total = torch.zeros((), device=belief_logits.device)
    for part in CATEGORY_SLICES:
        log_p = F.log_softmax(masked[:, part], dim=1)
        total = total - (log_p * envelope[:, part]).sum(dim=1).mean()
    return total / len(CATEGORY_SLICES)


def losses(net: TorchNet, ref: TorchNet, batch: dict, args, device) -> dict:
    """Every term of one step on `batch`, and the total."""
    n = batch["n_decisions"]
    row_decision = torch.as_tensor(batch["row_decision"], device=device)
    row_action = torch.as_tensor(batch["row_action"], device=device)
    logits, _hidden, heads = option_logits(net, batch, device)
    lse = _segment_logsumexp(logits, row_decision, n)
    log_pi_rows = logits - lse[row_decision]
    log_pi = log_pi_rows[row_action]  # one per decision, in decision order
    with torch.no_grad():
        ref_logits, _h, _heads = option_logits(ref, batch, device)
        ref_lse = _segment_logsumexp(ref_logits, row_decision, n)
        log_ref = (ref_logits - ref_lse[row_decision])[row_action]
    reward = torch.as_tensor(batch["reward"], dtype=torch.float32, device=device)
    regularised = reward - args.eta * (log_pi.detach() - log_ref)
    value = heads["value"]
    advantage = regularised - value.detach()
    policy = -(advantage * log_pi).mean()
    value_loss = F.mse_loss(value, regularised)
    probs = torch.exp(log_pi_rows)
    entropy = -torch.zeros(n, device=device).scatter_add(0, row_decision, probs * log_pi_rows).mean()
    possible = torch.as_tensor(batch["possible"], dtype=torch.float32, device=device)
    envelope = torch.as_tensor(batch["envelope"], dtype=torch.float32, device=device)
    belief = belief_loss(heads["belief"], possible, envelope)
    total = policy + args.value * value_loss + args.lambda_belief * belief - args.entropy * entropy
    return {
        "total": total, "policy": policy, "value": value_loss, "belief": belief, "entropy": entropy,
        "kl_ref": (log_pi.detach() - log_ref).mean(),
    }


# -- the run ---------------------------------------------------------------------------


def parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    p.add_argument("--games", type=int, default=20000, help="Games to play in all.")
    p.add_argument("--batch", type=int, default=256, help="Games per update.")
    p.add_argument("--epochs", type=int, default=2, help="Adam steps per batch.")
    p.add_argument("--workers", type=int, default=1, help="Rollout processes (1: this process).")
    p.add_argument("--seed", type=int, default=2026, help="Seed of the weights and the first game.")
    p.add_argument("--lr", type=float, default=3e-4)
    p.add_argument("--weight-decay", dest="weight_decay", type=float, default=0.0, help="AdamW decay.")
    p.add_argument("--eta", type=float, default=0.2, help="Regularisation toward the reference policy.")
    p.add_argument("--refresh", type=int, default=50, help="Updates between reference refreshes.")
    p.add_argument("--lambda-belief", dest="lambda_belief", type=float, default=1.0)
    p.add_argument("--entropy", type=float, default=0.01)
    p.add_argument("--value", type=float, default=0.5)
    p.add_argument("--population", choices=rollout.POPULATIONS, default="mixed")
    p.add_argument("--max-turns", type=int, default=rollout.DEFAULT_MAX_TURNS)
    p.add_argument("--eval-every", type=int, default=20, help="Updates between checkpoints and evaluations (0: none).")
    p.add_argument("--eval-games", type=int, default=24, help="Games per standard table at an evaluation.")
    p.add_argument("--bench-games", type=int, default=10, help="Belief-benchmark games at an evaluation (0: skip).")
    p.add_argument("--out", type=Path, default=None, help=f"Run folder (default {DEFAULT_OUT}/<timestamp>).")
    p.add_argument("--resume", type=Path, default=None, help="Start from this weights file instead of a fresh draw.")
    p.add_argument("--export", type=Path, default=None, help="Write the final weights here (clude_agents/weights/plum.npz).")
    p.add_argument("--device", default="cpu")
    p.add_argument("--quiet", action="store_true")
    return p.parse_args(argv)


def table_size(seed: int) -> int:
    """Three to six seats, cycling with the seed."""
    return 3 + seed % 4


def evaluate_checkpoint(weights: dict, args) -> dict:
    report = {"tables": rollout.evaluate(weights, n_games=args.eval_games)}
    if args.bench_games > 0:
        from clude_training.benchmark import run_benchmark

        result = run_benchmark(
            n_games=args.bench_games, seed=4004, agents={"Plum": deep_nash.DeepNashAgent(weights)},
        )
        report["benchmark"] = {
            str(cp): {"log_loss": cell.log_loss, "brier": cell.brier}
            for cp, cell in result.per_agent["Plum"].items()
        }
        report["uniform"] = {
            str(cp): {"log_loss": cell.log_loss} for cp, cell in result.per_agent["uniform"].items()
        }
    return report


def train(args) -> dict:
    """The run; returns the final weights."""
    out = args.out or DEFAULT_OUT / time.strftime("%Y%m%d-%H%M%S")
    out.mkdir(parents=True, exist_ok=True)
    device = torch.device(args.device)
    torch.manual_seed(args.seed)
    weights = deep_nash.load_weights(args.resume) if args.resume else deep_nash.init_weights(args.seed)
    net = TorchNet.from_numpy(weights).to(device)
    ref = copy.deepcopy(net).eval()
    for p in ref.parameters():
        p.requires_grad_(False)
    optimiser = torch.optim.AdamW(net.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    n_updates = max(1, args.games // args.batch)
    (out / "args.json").write_text(json.dumps({k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()}, indent=2))
    curve = (out / "curve.jsonl").open("a")
    evals = (out / "eval.jsonl").open("a")
    started = time.perf_counter()
    for update in range(1, n_updates + 1):
        tick = time.perf_counter()
        seeds = [args.seed * 100_003 + (update - 1) * args.batch + i for i in range(args.batch)]
        numpy_weights = net.to_numpy()
        traces = rollout.rollout_batch(numpy_weights, seeds, table_size, args.population, args.workers, args.max_turns)
        rolled = time.perf_counter() - tick
        batch = stack_traces(traces)
        net.train()
        terms: dict = {}
        for _epoch in range(args.epochs):
            optimiser.zero_grad()
            terms = losses(net, ref, batch, args, device)
            terms["total"].backward()
            nn.utils.clip_grad_norm_(net.parameters(), 1.0)
            optimiser.step()
        if update % args.refresh == 0:
            ref.load_state_dict(net.state_dict())
        net_rewards = [t.rewards[s] for t in traces for s in t.net_seats]
        line = {
            "update": update, "games": update * args.batch, "decisions": int(batch["n_decisions"]),
            **{k: round(float(v.detach()), 5) for k, v in terms.items()},
            "net_reward": round(float(np.mean(net_rewards)), 4) if net_rewards else None,
            "net_wins": round(float(np.mean([r == 1.0 for r in net_rewards])), 4) if net_rewards else None,
            "capped": round(float(np.mean([t.capped for t in traces])), 3),
            "self_play": round(float(np.mean([all(k == rollout.NET for k in t.kinds) for t in traces])), 3),
            "rollout_s": round(rolled, 1), "seconds": round(time.perf_counter() - started, 1),
        }
        curve.write(json.dumps(line) + "\n")
        curve.flush()
        if not args.quiet:
            print(
                f"update {update}/{n_updates}: loss {line['total']:.3f} (policy {line['policy']:.3f}, "
                f"value {line['value']:.3f}, belief {line['belief']:.3f}, entropy {line['entropy']:.3f}) "
                f"reward {line['net_reward']} wins {line['net_wins']} capped {line['capped']} "
                f"[{line['decisions']} decisions, rollouts {rolled:.0f}s]"
            )
        if args.eval_every and update % args.eval_every == 0:
            checkpoint = out / f"ckpt-{update:04d}.npz"
            deep_nash.save_weights(net.to_numpy(), checkpoint)
            report = {"update": update, "games": update * args.batch, **evaluate_checkpoint(net.to_numpy(), args)}
            evals.write(json.dumps(report) + "\n")
            evals.flush()
            if not args.quiet:
                tables = report["tables"]
                bench = report.get("benchmark", {})
                print(
                    f"  eval: tuned win {tables['tuned']['win_rate']:.2f} wrong {tables['tuned']['wrong_rate']:.2f}; "
                    f"plum table win {tables['plum']['win_rate']:.2f} wrong {tables['plum']['wrong_rate']:.2f}; "
                    + (f"log-loss at 0.5: {bench['0.5']['log_loss']:.3f}" if "0.5" in bench else "")
                    + f"; saved {checkpoint.name}"
                )
    curve.close()
    evals.close()
    final = net.to_numpy()
    deep_nash.save_weights(final, out / "final.npz")
    if args.export:
        deep_nash.save_weights(final, args.export)
        print(f"exported to {args.export}: re-capture the goldens (tests/test_character.py) on purpose")
    return final


def main(argv=None) -> int:
    train(parse_args(argv))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
