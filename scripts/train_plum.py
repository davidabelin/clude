"""Train Plum's policy/value/belief heads from engine self-play rollouts.

PyTorch is developer-only; deployment uses NumPy inference. Each iteration
collects ordered seeded Episodes, fits a regularised NeuRD policy gradient
(or --policy-grad softmax), regresses value to return, and fits belief with
masked cross-entropy from a multi-iteration replay buffer. Advantages are
standardized unless --no-adv-norm; --refresh updates the reference policy.
Outcome reward is +1 win/-1 eliminated/0 otherwise, with optional deduction
shaping defaulting to zero.

--help owns complete flags. Evaluations write config/curve/checkpoints,
best.npz and latest.npz under ignored data/plum-training. --export copies
final weights, not the best checkpoint, to committed plum.npz; validate and
update goldens deliberately. Determinism is bounded to fixed seeds, machine
and library versions. See docs/deepnash-plan.md for smoke failures, policy
limitations and outstanding acceptance, plus weights/README.md for export.
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import multiprocessing as mp
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import torch  # noqa: E402
import torch.nn.functional as F  # noqa: E402
from torch import nn  # noqa: E402

from clude_agents import deep_nash as dn  # noqa: E402
from clude_training import rollout as R  # noqa: E402
from clude_training.arena import DEFAULT_ROSTER, run_arena  # noqa: E402
from clude_training.benchmark import run_benchmark  # noqa: E402

PLUM_TABLE: tuple = ("Plum", "Mustard", "Green")
EVAL_SEED = 7007
BENCH_SEED = 4004
CARD_ENVELOPE_BIT = dn.MAX_SEATS
"""Index within a card's `CARD_FEATURES` of "the floor allows the
envelope to hold it" (`encode_state`)."""
NEURD_THRESHOLD = 2.0
"""A centred logit past this stops being pushed further out (DeepNash's
logit threshold), so the policy heads cannot run away."""
NEURD_RHO_MAX = 10.0
"""The cap on the sampled NeuRD estimator's ``1 / pi(a)`` weight."""


# -- the network in torch -------------------------------------------------------


class PlumNet(nn.Module):
    """`clude_agents.deep_nash`'s network with one parameter per entry
    of `WEIGHT_SHAPES`, under the same names and orientations, so the
    two forward passes agree to float32 rounding."""

    def __init__(self) -> None:
        super().__init__()
        for name, shape in dn.WEIGHT_SHAPES.items():
            setattr(self, name, nn.Parameter(torch.zeros(shape)))

    @classmethod
    def from_numpy(cls, weights: dict) -> "PlumNet":
        net = cls()
        with torch.no_grad():
            for name in dn.WEIGHT_SHAPES:
                getattr(net, name).copy_(torch.as_tensor(np.asarray(weights[name]), dtype=torch.float32))
        return net

    def to_numpy(self) -> dict:
        return {name: getattr(self, name).detach().cpu().numpy().astype(np.float64) for name in dn.WEIGHT_SHAPES}

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

    def move_logits(self, h: torch.Tensor, choices: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
        """``(B, N)`` logits for padded choices ``(B, N, CHOICE_SIZE)``,
        ``-inf`` where `mask` is False."""
        joined = torch.cat([h[:, None, :].expand(-1, choices.shape[1], -1), choices], dim=-1)
        z = F.relu(joined @ self.move1_w + self.move1_b)
        logits = (z @ self.move2_w + self.move2_b)[..., 0]
        return logits.masked_fill(~mask, float("-inf"))


# -- a batch of episodes as tensors ------------------------------------------


@dataclass
class Batch:
    """Every step of a rollout as flat tensors, episodes contiguous.

    `kinds`, `actions`, `gains` and `episode` are per step; `targets`
    the envelope's three indices per step; `possible` the 21 bits per
    step; `terminal` the outcome at a seat's last step and 0 before.
    Move steps have rows in `choices`/`choice_mask` (`move_row` maps a
    step to its row, -1 otherwise); suggestion steps a 6-bit
    `cand_mask` and a `cand_target` into the category (`sugg_row`).
    """

    states: torch.Tensor
    kinds: torch.Tensor
    actions: torch.Tensor
    gains: torch.Tensor
    terminal: torch.Tensor
    episode: torch.Tensor
    bounds: list
    targets: torch.Tensor
    possible: torch.Tensor
    move_row: torch.Tensor
    choices: torch.Tensor
    choice_mask: torch.Tensor
    sugg_row: torch.Tensor
    cand_mask: torch.Tensor
    cand_target: torch.Tensor

    def __len__(self) -> int:
        return len(self.kinds)


class Replay:
    """The belief head's training set: a fraction of each of the last
    `keep` iterations' steps (state, the floor's envelope bits, the
    envelope), so one update sees thousands of games' envelopes rather
    than one iteration's."""

    def __init__(self, keep: int, fraction: float) -> None:
        self.keep = keep
        self.fraction = fraction
        self.chunks: list = []

    def add(self, batch: Batch, generator: torch.Generator) -> None:
        n = max(1, int(len(batch) * self.fraction))
        idx = torch.randperm(len(batch), generator=generator, device=batch.states.device)[:n]
        self.chunks.append((batch.states[idx], batch.possible[idx], batch.targets[idx]))
        del self.chunks[: -self.keep]

    def __len__(self) -> int:
        return sum(len(c[0]) for c in self.chunks)

    def sample(self, n: int, generator: torch.Generator) -> tuple:
        states = torch.cat([c[0] for c in self.chunks])
        possible = torch.cat([c[1] for c in self.chunks])
        targets = torch.cat([c[2] for c in self.chunks])
        idx = torch.randint(0, len(states), (min(n, len(states)),), generator=generator, device=states.device)
        return states[idx], possible[idx], targets[idx]


def assemble(episodes: list, device: torch.device) -> Batch:
    episodes = [ep for ep in episodes if len(ep)]
    states = np.concatenate([ep.states for ep in episodes])
    kinds = np.concatenate([ep.kinds for ep in episodes]).astype(np.int64)
    actions = np.concatenate([ep.actions for ep in episodes]).astype(np.int64)
    gains = np.concatenate([ep.gains for ep in episodes]).astype(np.float32)
    n = len(kinds)
    terminal = np.zeros(n, dtype=np.float32)
    episode = np.zeros(n, dtype=np.int64)
    targets = np.zeros((n, 3), dtype=np.int64)
    bounds = []
    start = 0
    for e, ep in enumerate(episodes):
        stop = start + len(ep)
        terminal[stop - 1] = ep.reward
        episode[start:stop] = e
        targets[start:stop] = ep.envelope
        bounds.append((start, stop))
        start = stop
    possible = states[:, [c * dn.CARD_FEATURES + CARD_ENVELOPE_BIT for c in range(len(dn.ALL_CARDS))]] > 0.5

    options = [o for ep in episodes for o in ep.options]
    move_steps = np.flatnonzero(kinds == R.KIND_MOVE)
    n_max = max((options[i].shape[0] for i in move_steps), default=1)
    choices = np.zeros((len(move_steps), n_max, dn.CHOICE_SIZE), dtype=np.float32)
    choice_mask = np.zeros((len(move_steps), n_max), dtype=bool)
    move_row = np.full(n, -1, dtype=np.int64)
    for row, i in enumerate(move_steps):
        rows = options[i]
        choices[row, : len(rows)] = rows
        choice_mask[row, : len(rows)] = True
        move_row[i] = row

    sugg_steps = np.flatnonzero((kinds == R.KIND_SUSPECT) | (kinds == R.KIND_WEAPON))
    cand_mask = np.zeros((len(sugg_steps), len(dn.SUSPECTS)), dtype=bool)
    cand_target = np.zeros(len(sugg_steps), dtype=np.int64)
    sugg_row = np.full(n, -1, dtype=np.int64)
    for row, i in enumerate(sugg_steps):
        idx = options[i]
        cand_mask[row, idx] = True
        cand_target[row] = idx[actions[i]]
        sugg_row[i] = row

    t = lambda a, dtype=None: torch.as_tensor(a, dtype=dtype, device=device)  # noqa: E731
    return Batch(
        states=t(states, torch.float32), kinds=t(kinds), actions=t(actions), gains=t(gains),
        terminal=t(terminal), episode=t(episode), bounds=bounds, targets=t(targets),
        possible=t(possible), move_row=t(move_row), choices=t(choices), choice_mask=t(choice_mask),
        sugg_row=t(sugg_row), cand_mask=t(cand_mask), cand_target=t(cand_target),
    )


# -- the losses ---------------------------------------------------------------


def policy_logits(net: PlumNet, batch: Batch, idx: torch.Tensor, h: torch.Tensor) -> tuple:
    """For the steps `idx` (with trunk output `h`): the move steps'
    masked logits and taken actions, and the suggestion steps' masked
    logits and taken category indices, each with the positions within
    `idx` they belong to."""
    kinds = batch.kinds[idx]
    is_move = kinds == R.KIND_MOVE
    is_sugg = (kinds == R.KIND_SUSPECT) | (kinds == R.KIND_WEAPON)
    rows = batch.move_row[idx[is_move]]
    move = net.move_logits(h[is_move], batch.choices[rows], batch.choice_mask[rows])
    heads = net.heads(h[is_sugg])
    srows = batch.sugg_row[idx[is_sugg]]
    sugg = torch.where(
        (kinds[is_sugg] == R.KIND_SUSPECT)[:, None], heads["suspect"], heads["weapon"]
    ).masked_fill(~batch.cand_mask[srows], float("-inf"))
    return (move, batch.actions[idx[is_move]], is_move), (sugg, batch.cand_target[srows], is_sugg)


def log_prob_taken(logits: torch.Tensor, taken: torch.Tensor) -> torch.Tensor:
    return F.log_softmax(logits, dim=-1).gather(1, taken[:, None])[:, 0]


@torch.no_grad()
def step_log_probs(net: PlumNet, batch: Batch, chunk: int = 4096) -> torch.Tensor:
    """``log pi(a_t | s_t)`` under `net` for every step, 0 at belief
    steps."""
    out = torch.zeros(len(batch), device=batch.states.device)
    for start in range(0, len(batch), chunk):
        idx = torch.arange(start, min(start + chunk, len(batch)), device=out.device)
        h = net.trunk(batch.states[idx])
        (move, taken_m, is_move), (sugg, taken_s, is_sugg) = policy_logits(net, batch, idx, h)
        out[idx[is_move]] = log_prob_taken(move, taken_m)
        out[idx[is_sugg]] = log_prob_taken(sugg, taken_s)
    return out


def returns(batch: Batch, step_rewards: torch.Tensor, gamma: float) -> torch.Tensor:
    """Per-step discounted sums of `step_rewards` to the episode's end."""
    out = torch.empty_like(step_rewards)
    for start, stop in batch.bounds:
        acc = 0.0
        for i in range(stop - 1, start - 1, -1):
            acc = float(step_rewards[i]) + gamma * acc
            out[i] = acc
    return out


def neurd_term(logits: torch.Tensor, taken: torch.Tensor, advantage: torch.Tensor) -> torch.Tensor:
    """The sampled NeuRD loss: minus the advantage, weighted by the
    capped ``1 / pi(a)``, times the taken action's centred logit, with
    DeepNash's threshold on the logit (`NEURD_THRESHOLD`)."""
    legal = torch.isfinite(logits)
    centred = logits - (logits.masked_fill(~legal, 0.0).sum(1) / legal.sum(1))[:, None]
    y = centred.gather(1, taken[:, None])[:, 0]
    pi = F.softmax(logits, dim=-1).gather(1, taken[:, None])[:, 0].detach()
    weight = (advantage * torch.clamp(1.0 / pi, max=NEURD_RHO_MAX)).detach()
    blocked = ((weight > 0) & (y.detach() > NEURD_THRESHOLD)) | ((weight < 0) & (y.detach() < -NEURD_THRESHOLD))
    return -(weight * y).masked_fill(blocked, 0.0)


def entropy(logits: torch.Tensor) -> torch.Tensor:
    logp = F.log_softmax(logits, dim=-1)
    return -(logp.exp() * logp.masked_fill(~torch.isfinite(logp), 0.0)).sum(1)


def belief_loss(belief_logits: torch.Tensor, possible: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    """Cross-entropy per category over the cards the floor allows,
    summed over the three categories, mean over steps."""
    total = torch.zeros((), device=belief_logits.device)
    start = 0
    for k, category in enumerate(dn.CATEGORIES):
        stop = start + len(category)
        logits = belief_logits[:, start:stop].masked_fill(~possible[:, start:stop], float("-inf"))
        total = total + F.cross_entropy(logits, targets[:, k])
        start = stop
    return total


def minibatch_loss(
    net: PlumNet, batch: Batch, idx: torch.Tensor, G: torch.Tensor, adv_all: torch.Tensor, belief_batch: tuple, args
) -> tuple:
    """One minibatch's loss: the policy and value terms on the steps
    `idx` of the iteration's `batch` (`adv_all` their advantages, already
    standardised when asked), the belief term on `belief_batch` from the
    replay buffer."""
    h = net.trunk(batch.states[idx])
    heads = net.heads(h)
    value = heads["value"]
    v_loss = 0.5 * ((value - G[idx]) ** 2).mean()
    b_states, b_possible, b_targets = belief_batch
    b_loss = belief_loss(net.heads(net.trunk(b_states))["belief"], b_possible, b_targets)
    (move, taken_m, is_move), (sugg, taken_s, is_sugg) = policy_logits(net, batch, idx, h)
    adv = adv_all[idx]
    terms = []
    ents = []
    for logits, taken, sel in ((move, taken_m, is_move), (sugg, taken_s, is_sugg)):
        if len(taken) == 0:
            continue
        if args.policy_grad == "neurd":
            terms.append(neurd_term(logits, taken, adv[sel]))
        else:
            terms.append(-(adv[sel].detach() * log_prob_taken(logits, taken)))
        ents.append(entropy(logits))
    p_loss = torch.cat(terms).mean() if terms else torch.zeros((), device=h.device)
    ent = torch.cat(ents).mean() if ents else torch.zeros((), device=h.device)
    loss = p_loss + args.value_weight * v_loss + args.lambda_belief * b_loss - args.entropy * ent
    return loss, {"policy": p_loss.item(), "value": v_loss.item(), "belief": b_loss.item(), "entropy": ent.item()}


# -- evaluation ---------------------------------------------------------------


def evaluate(weights: dict, bench_games: int, arena_games: int) -> dict:
    """The free ladder of `docs/deepnash-plan.md` 6 on `weights`."""
    with dn.playing_with(weights):
        bench = run_benchmark(n_games=bench_games, seed=BENCH_SEED, agents={"Plum": dn.DeepNashAgent(weights)})
        plum_table = run_arena(n_games=arena_games, seed=EVAL_SEED, roster=PLUM_TABLE, player_counts=(3,))
        six = run_arena(n_games=arena_games, seed=EVAL_SEED, roster=DEFAULT_ROSTER)

    def table(result) -> dict:
        p = result.per_player["Plum"]
        return {
            "games": p.games,
            "win_rate": p.wins / p.games if p.games else None,
            "wrong_rate": p.games_with_wrong_accusation / p.games if p.games else None,
            "accused_rate": p.games_with_accusation / p.games if p.games else None,
            "mean_turns": result.mean_turns if hasattr(result, "mean_turns") else None,
        }

    return {
        "log_loss": {str(cp): bench.per_agent["Plum"][cp].log_loss for cp in bench.checkpoints},
        "uniform_log_loss": {str(cp): bench.per_agent["uniform"][cp].log_loss for cp in bench.checkpoints},
        "plum_table": table(plum_table),
        "six_table": table(six),
    }


# -- the run ------------------------------------------------------------------


def parse_args(argv: Optional[list] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    p.add_argument("--iterations", type=int, default=50, help="rollout-and-update rounds")
    p.add_argument("--games", type=int, default=256, help="games per iteration")
    p.add_argument("--workers", type=int, default=max(1, (mp.cpu_count() or 2) - 1))
    p.add_argument("--chunk", type=int, default=8, help="games per pool task")
    p.add_argument("--seed", type=int, default=2026)
    p.add_argument("--self-play", type=float, default=0.5, help="P(every seat is the network)")
    p.add_argument("--policy-temperature", type=float, default=1.0, help="the rollout seats' sampler")
    p.add_argument("--max-turns", type=int, default=R.DEFAULT_MAX_TURNS)
    p.add_argument("--eta", type=float, default=0.1, help="the reward regulariser toward pi_ref")
    p.add_argument("--refresh", type=int, default=10, help="iterations between pi_ref refreshes")
    p.add_argument("--gamma", type=float, default=1.0)
    p.add_argument("--shaping", type=float, default=0.0, help="weight of the floor's bits gained per turn in the reward")
    p.add_argument("--lambda-belief", type=float, default=1.0)
    p.add_argument("--replay", type=int, default=10, help="iterations of states the belief head trains on")
    p.add_argument("--replay-fraction", type=float, default=0.25, help="of each iteration's steps kept for it")
    p.add_argument("--value-weight", type=float, default=0.5)
    p.add_argument("--entropy", type=float, default=0.01)
    p.add_argument("--policy-grad", choices=("neurd", "softmax"), default="neurd")
    p.add_argument("--no-adv-norm", dest="adv_norm", action="store_false", help="raw advantages, not standardised")
    p.add_argument("--lr", type=float, default=3e-4)
    p.add_argument("--epochs", type=int, default=1, help="passes over an iteration's steps")
    p.add_argument("--minibatch", type=int, default=2048)
    p.add_argument("--grad-clip", type=float, default=5.0)
    p.add_argument("--eval-every", type=int, default=5)
    p.add_argument("--eval-games", type=int, default=24, help="arena games per table at an evaluation")
    p.add_argument("--bench-games", type=int, default=20, help="benchmark games at an evaluation")
    p.add_argument("--resume", type=Path, default=None, help="start from this weights file instead of a fresh draw")
    p.add_argument("--out", type=Path, default=None, help="run directory (default data/plum-training/<timestamp>)")
    p.add_argument("--export", action="store_true", help="copy the final weights to clude_agents/weights/plum.npz")
    p.add_argument("--device", default="cpu")
    p.add_argument("--quiet", action="store_true")
    return p.parse_args(argv)


def rollout(pool, weights: dict, seeds: list, config: R.RolloutConfig, chunk: int) -> list:
    tasks = R.rollout_tasks(weights, seeds, chunk, config)
    if pool is None:
        results = [R._play_task(task) for task in tasks]
    else:
        results = pool.map(R._play_task, tasks)
    return [ep for episodes in results for ep in episodes]


def train(args: argparse.Namespace) -> dict:
    """The whole run; returns the last curve line."""
    torch.manual_seed(args.seed)
    device = torch.device(args.device)
    out = args.out or ROOT / "data" / "plum-training" / time.strftime("%Y%m%d-%H%M%S")
    out.mkdir(parents=True, exist_ok=True)
    weights = dn.load_weights(args.resume) if args.resume else dn.init_weights(args.seed)
    net = PlumNet.from_numpy(weights).to(device)
    ref = copy.deepcopy(net)
    optimizer = torch.optim.Adam(net.parameters(), lr=args.lr)
    replay = Replay(args.replay, args.replay_fraction)
    generator = torch.Generator(device=device)
    generator.manual_seed(args.seed)
    config = R.RolloutConfig(
        self_play=args.self_play, policy_temperature=args.policy_temperature, max_turns=args.max_turns,
    )
    (out / "config.json").write_text(
        json.dumps({k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()}, indent=2), encoding="utf-8"
    )
    say = (lambda *a: None) if args.quiet else (lambda *a: print(*a, flush=True))
    say(f"run {out}: {args.iterations} iterations of {args.games} games, {args.workers} workers, device {device}")
    pool = None
    if args.workers > 1:
        pool = mp.get_context("spawn").Pool(args.workers)
    best_win: float = -1.0
    last: dict = {}
    curve = (out / "curve.jsonl").open("a", encoding="utf-8")
    try:
        for it in range(1, args.iterations + 1):
            started = time.perf_counter()
            seeds = [args.seed * 10**7 + (it - 1) * args.games + g for g in range(args.games)]
            episodes = rollout(pool, net.to_numpy(), seeds, config, args.chunk)
            rolled = time.perf_counter()
            stats = R.RolloutStats.of(episodes).to_dict()
            batch = assemble(episodes, device)
            logp = step_log_probs(net, batch)
            logp_ref = step_log_probs(ref, batch)
            step_rewards = batch.terminal + args.shaping * batch.gains + args.eta * (logp_ref - logp)
            G = returns(batch, step_rewards, args.gamma)
            with torch.no_grad():
                values = torch.cat([
                    net.heads(net.trunk(batch.states[i:i + 4096]))["value"] for i in range(0, len(batch), 4096)
                ])
            adv_all = G - values
            if args.adv_norm:
                adv_all = (adv_all - adv_all.mean()) / (adv_all.std() + 1e-6)
            replay.add(batch, generator)
            n = len(batch)
            sums: dict = {}
            steps = 0
            for _epoch in range(args.epochs):
                perm = torch.randperm(n, generator=generator, device=device)
                for start in range(0, n, args.minibatch):
                    idx = perm[start:start + args.minibatch]
                    loss, parts = minibatch_loss(
                        net, batch, idx, G, adv_all, replay.sample(args.minibatch, generator), args
                    )
                    optimizer.zero_grad()
                    loss.backward()
                    nn.utils.clip_grad_norm_(net.parameters(), args.grad_clip)
                    optimizer.step()
                    for k, v in parts.items():
                        sums[k] = sums.get(k, 0.0) + v
                    steps += 1
            if it % args.refresh == 0:
                ref = copy.deepcopy(net)
            line = {
                "iteration": it,
                "games_played": it * args.games,
                "rollout_seconds": round(rolled - started, 2),
                "learn_seconds": round(time.perf_counter() - rolled, 2),
                "steps": n,
                "replay_steps": len(replay),
                "mean_return": round(float(G.mean()), 4),
                "return_std": round(float(G.std()), 4),
                "mean_regulariser": round(float((args.eta * (logp_ref - logp)).sum() / max(1, len(batch.bounds))), 4),
                "loss": {k: round(v / max(1, steps), 4) for k, v in sums.items()},
                "rollout": stats,
            }
            if it % args.eval_every == 0 or it == args.iterations:
                weights = net.to_numpy()
                line["eval"] = evaluate(weights, args.bench_games, args.eval_games)
                dn.save_weights(weights, out / f"checkpoint-{it:06d}.npz")
                win = line["eval"]["plum_table"]["win_rate"] or 0.0
                if win > best_win:
                    best_win = win
                    dn.save_weights(weights, out / "best.npz")
                line["eval_seconds"] = round(time.perf_counter() - started - line["rollout_seconds"] - line["learn_seconds"], 2)
            curve.write(json.dumps(line) + "\n")
            curve.flush()
            last = line
            say(format_line(line))
    finally:
        curve.close()
        if pool is not None:
            pool.close()
            pool.join()
    weights = net.to_numpy()
    dn.save_weights(weights, out / "latest.npz")
    if args.export:
        dn.save_weights(weights, dn.WEIGHTS_PATH)
        say(f"exported to {dn.WEIGHTS_PATH}; re-capture the goldens (tests/test_character.py)")
    say(f"done: {out} (best Plum-table win rate {best_win:.3f} in best.npz)")
    return last


def format_line(line: dict) -> str:
    r = line["rollout"]
    text = (
        f"it {line['iteration']:>4} games {line['games_played']:>7} steps {line['steps']:>7} "
        f"roll {line['rollout_seconds']:>6.1f}s learn {line['learn_seconds']:>5.1f}s "
        f"turns {r['mean_turns']:>5.1f} net win {r['net_win_rate']:.3f} out {r['net_out_rate']:.3f} "
        f"loss p {line['loss'].get('policy', 0):+.3f} v {line['loss'].get('value', 0):.3f} "
        f"b {line['loss'].get('belief', 0):.3f} H {line['loss'].get('entropy', 0):.2f}"
    )
    if "eval" in line:
        e = line["eval"]
        ll = " ".join(f"{float(k):.2f}:{v:.2f}" for k, v in e["log_loss"].items())
        text += (
            f"\n     eval: log-loss {ll} | Plum table win {e['plum_table']['win_rate']:.3f} "
            f"wrong {e['plum_table']['wrong_rate']:.3f} | six win {e['six_table']['win_rate']:.3f} "
            f"wrong {e['six_table']['wrong_rate']:.3f} ({line['eval_seconds']:.1f}s)"
        )
    return text


def main(argv: Optional[list] = None) -> None:
    train(parse_args(argv))


if __name__ == "__main__":
    main()
