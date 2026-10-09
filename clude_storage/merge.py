"""Merge a downloaded copy of a store into a local store, in place.

`store merge` folds a bucket download (``data/llm_bucket``) into the local
store (``data/llm``). The download is never changed, and where both hold a
document the download's keeps its name:

- Equal documents (JSON-equal, so line endings do not count) stay as they are.
- A run clashes when a game record in both differs: the local run
  (summary, records, traces) becomes ``<run>_local`` and every local
  reference to it (``run_id`` fields, ``<run>/<index>`` game ids) is
  rewritten. Otherwise the download's summary stands and local records it
  lacks fill the gaps.
- A logbook keeps the download's entries, head and digest. Local entries it
  lacks are appended after its last serial and absorbed into its head; an
  entry older than the download's newest leaves the newer standing
  instructions and opponent reads in place. Mustard's and White's per-game
  method memory becomes the union of both; Green's local lessons are
  replayed on the download's posteriors (`_Planner.merge_posteriors`).
- A day's spend document combines both days' tables.
- Accounts, tables, watch state and per-table spend keep the download's
  document and drop the local one, which would otherwise be listed as live;
  so do cached traces of runs that do not clash, which rebuild on demand.
- Any other differing document keeps the download's under its name; the
  local one moves to ``<name>_local.json``.

Running it again with the same download changes nothing. See docs/cli.md.
"""
from __future__ import annotations

import json
import math
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from .logbooks import LOGBOOKS_PREFIX, Dossier, LogbookEntry, LogbookHead

LOCAL_SUFFIX = "_local"
RUN_FOLDERS = ("games", "traces")
DROP_LOCAL = ("users/", "tables/", "watch/", "spend/tables/", "traces/")
"""Folders whose documents are listed as live (a renamed local copy would
be read as another account, table or watch) or are caches; where both
differ, the download's alone is kept."""
_SPEND_DAY = re.compile(r"^spend/[^/]+\.json$")
_MEMORY_UNION = ("rows", "counts")


@dataclass
class MergePlan:
    """What `plan_merge` will do to the local store.

    Attributes
    ----------
    copy : dict
        Local key -> the download's file to copy there, byte for byte.
    write : dict
        Local key -> new content: a JSON document or raw bytes.
    delete : set
        Local keys to remove (after the copies and writes).
    added, equal, kept : int
        Documents only in the download, equal in both, only local.
    renamed_runs : dict
        Clashing run id -> the local run's new id.
    rewritten : int
        Local documents whose references to a renamed run were rewritten.
    logbooks, memory, spend : list of str
        One line per merged logbook, method memory and spend day.
    dropped : list of str
        Keys where the local document was dropped for the download's.
    moved : dict
        Key -> where the local document went (``*_local.json``).
    """

    copy: dict = field(default_factory=dict)
    write: dict = field(default_factory=dict)
    delete: set = field(default_factory=set)
    added: int = 0
    equal: int = 0
    kept: int = 0
    renamed_runs: dict = field(default_factory=dict)
    rewritten: int = 0
    logbooks: list = field(default_factory=list)
    memory: list = field(default_factory=list)
    spend: list = field(default_factory=list)
    dropped: list = field(default_factory=list)
    moved: dict = field(default_factory=dict)

    def changes(self) -> int:
        return len(self.copy) + len(self.write) + len(self.delete - set(self.copy) - set(self.write))


# ---------------------------------------------------------------------
# Files and documents
# ---------------------------------------------------------------------


def _files(root: Path) -> dict:
    return {p.relative_to(root).as_posix(): p for p in root.rglob("*") if p.is_file()}


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _same(a: Path, b: Path) -> bool:
    x, y = a.read_bytes(), b.read_bytes()
    if x == y or x.replace(b"\r\n", b"\n") == y.replace(b"\r\n", b"\n"):
        return True
    if a.suffix != ".json":
        return False
    try:
        return json.loads(x) == json.loads(y)
    except ValueError:
        return False


def _dumps(document: dict) -> str:
    return json.dumps(document, indent=2, sort_keys=False)


def _local_name(key: str, taken) -> str:
    stem, dot, suffix = key.rpartition(".")
    if not dot:
        stem, suffix = key, ""
    n = 1
    while True:
        candidate = f"{stem}{LOCAL_SUFFIX}{n if n > 1 else ''}{dot}{suffix}"
        if candidate not in taken:
            return candidate
        n += 1


# ---------------------------------------------------------------------
# Runs
# ---------------------------------------------------------------------


def _run_of(key: str):
    parts = key.split("/")
    if parts[0] == "runs" and len(parts) == 2 and key.endswith(".json"):
        return parts[1][: -len(".json")]
    if parts[0] in RUN_FOLDERS and len(parts) >= 3:
        return parts[1]
    return None


def _renamed_key(key: str, new_run: str) -> str:
    parts = key.split("/")
    parts[1] = f"{new_run}.json" if parts[0] == "runs" else new_run
    return "/".join(parts)


def _clashing_runs(src: dict, dst: dict) -> dict:
    """Run id -> ``<run>_local`` for every run where a game record in both
    stores differs. A local record the download lacks fills its gap."""
    clashes: dict = {}
    for key in sorted(src.keys() & dst.keys()):
        run = _run_of(key)
        if key.startswith("games/") and run not in clashes and not _same(src[key], dst[key]):
            clashes[run] = f"{run}{LOCAL_SUFFIX}"
    for run, new in clashes.items():
        taken = [k for k in (*src, *dst) if _run_of(k) == new]
        if taken:
            raise ValueError(
                f"run {run} clashes, but {new} already exists ({taken[0]}); rename it first"
            )
    return clashes


def _rewriter(renames: dict):
    """A function rewriting a document's references to renamed runs; it
    returns None when nothing changed."""
    if not renames:
        return lambda document: None
    pattern = re.compile(r"^(" + "|".join(re.escape(r) for r in renames) + r")/(\d{5})$")

    def fix(text: str) -> str:
        match = pattern.match(text)
        return f"{renames[match[1]]}/{match[2]}" if match else text

    def walk(value):
        if isinstance(value, dict):
            return {
                fix(k): (renames.get(v, v) if k == "run_id" and isinstance(v, str) else walk(v))
                for k, v in value.items()
            }
        if isinstance(value, list):
            return [walk(v) for v in value]
        return fix(value) if isinstance(value, str) else value

    needles = [f'"{run}'.encode() for run in renames]

    def rewrite(document: dict):
        new = walk(document)
        return None if new == document else new

    rewrite.needles = needles
    return rewrite


# ---------------------------------------------------------------------
# Planning
# ---------------------------------------------------------------------


class _Planner:
    def __init__(self, source: Path, dest: Path, bandit_decay: float = 0.0) -> None:
        self.bandit_decay = bandit_decay
        self.src = _files(source)
        self.dst = _files(dest)
        self.plan = MergePlan()
        self.plan.renamed_runs = _clashing_runs(self.src, self.dst)
        self.rewrite = _rewriter(self.plan.renamed_runs)
        self.taken = set(self.src) | set(self.dst)

    def local_doc(self, key: str) -> dict:
        """A local JSON document with its run references rewritten."""
        document = _load(self.dst[key])
        return self.rewrite(document) or document

    def put(self, key: str, content) -> bool:
        """Plan writing `content` (a document or bytes) at `key`, unless
        the local file already holds it; True if it will be written."""
        path = self.dst.get(key)
        if path is not None:
            existing = path.read_bytes()
            if existing == content if isinstance(content, bytes) else _load(path) == content:
                return False
        self.plan.write[key] = content
        return True

    def keep_local(self, key: str, new_key: str = None) -> None:
        """Keep the local `key` at `new_key` (default: where it is),
        rewriting its run references."""
        new_key = new_key or key
        path = self.dst[key]
        data = path.read_bytes()
        document = None
        if path.suffix == ".json" and any(n in data for n in getattr(self.rewrite, "needles", [])):
            document = self.rewrite(json.loads(data))
        if document is not None:
            self.put(new_key, document)
            self.plan.rewritten += 1
        elif new_key != key:
            self.put(new_key, data)
        if new_key != key:
            self.plan.delete.add(key)
        self.taken.add(new_key)

    def take_source(self, key: str) -> None:
        if key not in self.dst or not _same(self.src[key], self.dst[key]):
            self.plan.copy[key] = self.src[key]

    def merge_file(self, key: str) -> None:
        """The per-document rule for everything not merged by content."""
        s, d = self.src.get(key), self.dst.get(key)
        run = _run_of(key)
        if d is not None and run in self.plan.renamed_runs:
            self.keep_local(key, _renamed_key(key, self.plan.renamed_runs[run]))
            if s is not None:
                self.plan.copy[key] = s
        elif s is None:
            self.plan.kept += 1
            self.keep_local(key)
        elif d is None:
            self.plan.added += 1
            self.plan.copy[key] = s
        elif _same(s, d):
            self.plan.equal += 1
        elif key.startswith(DROP_LOCAL) or run is not None:
            self.plan.dropped.append(key)
            self.plan.copy[key] = s
        else:
            new_key = _local_name(key, self.taken)
            self.plan.moved[key] = new_key
            self.plan.copy[key] = s
            self.keep_local(key, new_key)

    # -- spend ----------------------------------------------------------

    def merge_spend_day(self, key: str) -> None:
        s, d = _load(self.src[key]), _load(self.dst[key])
        tables = dict(s.get("tables", {}))
        total = float(s.get("total", 0.0))
        added = 0
        for table, dollars in d.get("tables", {}).items():
            extra = float(dollars) - float(tables.get(table, 0.0))
            if extra > 0:
                added += table not in tables
                tables[table] = dollars
                total += extra
        merged = {**s, "total": round(total, 6), "tables": tables}
        if self.put(key, merged):
            self.plan.spend.append(f"{key}: {added} local tables added, total ${merged['total']:.2f}")

    # -- logbooks -------------------------------------------------------

    def merge_logbook(self, identity: str, keys: set) -> None:
        prefix = f"{LOGBOOKS_PREFIX}/{identity}/"
        entries = f"{prefix}entries/"
        head_key, method_key = f"{prefix}head.json", f"{prefix}method.json"

        def body(entry: dict) -> str:
            return json.dumps({k: v for k, v in entry.items() if k != "serial"}, sort_keys=True)

        src_entries = {k: _load(self.src[k]) for k in self.src if k.startswith(entries)}
        known = {body(e) for e in src_entries.values()}
        fresh, stale = [], []
        for key in sorted(k for k in self.dst if k.startswith(entries)):
            entry = self.local_doc(key)
            if body(entry) not in known:
                fresh.append(entry)
            stale.append(key)
        for key in src_entries:
            self.take_source(key)

        head = None
        if head_key in self.src:
            head = LogbookHead.from_dict(_load(self.src[head_key]))
        serial = max([e["serial"] for e in src_entries.values()] + [head.serial if head else 0])
        latest = max((e.get("date", "") for e in src_entries.values()), default="")
        if head is None and fresh:
            head = LogbookHead.empty(identity)

        written, changed = [], 0
        for entry in sorted(fresh, key=lambda e: (e.get("date", ""), e["serial"])):
            serial += 1
            entry["serial"] = serial
            key = f"{entries}{serial:04d}.json"
            changed += self.put(key, entry)
            written.append(key)
            _absorb(head, LogbookEntry.from_dict(entry), latest)
            latest = max(latest, entry.get("date", ""))
        for key in stale:
            if key not in src_entries and key not in written:
                self.plan.delete.add(key)

        if written:
            changed += self.put(head_key, head.to_dict())
            if changed:
                self.plan.logbooks.append(
                    f"{identity}: {len(written)} local entries appended as "
                    f"#{serial - len(written) + 1:04d}-#{serial:04d}; head absorbed them"
                )
        elif head_key in self.src:
            self.take_source(head_key)
        elif head_key in self.dst:
            self.keep_local(head_key)

        handled = {head_key, *src_entries, *(k for k in self.dst if k.startswith(entries))}
        if method_key in self.src and method_key in self.dst:
            handled.add(method_key)
            self.merge_method(identity, method_key)
        for key in sorted(keys - handled):
            self.merge_file(key)

    def merge_method(self, identity: str, key: str) -> None:
        if _same(self.src[key], self.dst[key]):
            self.plan.equal += 1
            return
        s, d = _load(self.src[key]), self.local_doc(key)
        kind = s.get("kind")
        if kind == "state" and d.get("kind") == kind and self.bandit_decay:
            self.merge_posteriors(identity, key, s, d)
            return
        if kind not in _MEMORY_UNION or d.get("kind") != kind:
            self.merge_file(key)
            return
        new = {g: v for g, v in d.get("games", {}).items() if g not in s.get("games", {})}
        if not new:
            self.plan.copy[key] = self.src[key]
            return
        merged = {**s, "games": {**s.get("games", {}), **new}}
        if self.put(key, merged):
            self.plan.memory.append(
                f"{identity}: {len(new)} local games added to the download's {len(s['games'])}"
            )

    def merge_posteriors(self, identity: str, key: str, s: dict, d: dict) -> None:
        """Green's arms: each lesson shrinks the excess over Beta(1, 1) by
        the decay and adds itself, so the local lessons replay exactly on
        top of the download's arms, as if played after them.
        ``merged_from`` keeps the arms they were replayed on, so a second
        merge recovers the local lessons instead of adding them twice."""
        base = d.get("merged_from") or {"games": 0, "arms": {}}
        n_local = int(d.get("games", 0)) - int(base.get("games", 0))
        if n_local <= 0:
            self.plan.copy[key] = self.src[key]
            return
        shrink = self.bandit_decay ** n_local

        def excess(arms, name):
            alpha, beta = arms.get(name, (1.0, 1.0))
            return float(alpha) - 1.0, float(beta) - 1.0

        arms = {}
        for name in dict.fromkeys([*s.get("arms", {}), *d.get("arms", {})]):
            sa, sb = excess(s.get("arms", {}), name)
            da, db = excess(d.get("arms", {}), name)
            ba, bb = excess(base.get("arms", {}), name)
            arms[name] = [sa / shrink + da - ba / shrink + 1.0, sb / shrink + db - bb / shrink + 1.0]
        merged = {
            **s,
            "games": int(s.get("games", 0)) + n_local,
            "arms": arms,
            "merged_from": {"games": int(s.get("games", 0)), "arms": s.get("arms", {})},
        }
        if _close(merged, d):
            return
        self.plan.write[key] = merged
        self.plan.memory.append(
            f"{identity}: {n_local} local games replayed on the download's {s.get('games', 0)}"
        )

    def run(self) -> MergePlan:
        handled: set = set()
        logbooks: dict = {}
        for key in self.src.keys() | self.dst.keys():
            parts = key.split("/")
            if parts[0] == LOGBOOKS_PREFIX and len(parts) >= 3:
                logbooks.setdefault(parts[1], set()).add(key)
        for identity, keys in sorted(logbooks.items()):
            if any(k in self.src for k in keys) and any(k in self.dst for k in keys):
                self.merge_logbook(identity, keys)
                handled |= keys
        for key in sorted(self.src.keys() & self.dst.keys()):
            if _SPEND_DAY.match(key) and not _same(self.src[key], self.dst[key]):
                self.merge_spend_day(key)
                handled.add(key)
        for key in sorted((self.src.keys() | self.dst.keys()) - handled):
            self.merge_file(key)
        return self.plan


def _absorb(head: LogbookHead, entry, latest: str) -> None:
    """`LogbookHead.absorb`, except that an entry older than `latest`
    leaves the head's newer standing instructions, last game and
    opponent reads in place; its tally, games together and flags count."""
    before_rules = list(head.standing_instructions)
    before_last = head.tally.get("last_game_id")
    before_reads = dict(head.dossiers)
    head.absorb(entry)
    if entry.date >= latest:
        return
    head.standing_instructions = before_rules
    head.tally["last_game_id"] = before_last
    for label, old in before_reads.items():
        new = head.dossiers[label]
        if old.updated > entry.date:
            head.dossiers[label] = Dossier(old.read, new.games_together, old.updated, old.serial)


def _close(a, b) -> bool:
    """JSON-equal, except that floats need only agree to 1e-9."""
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(_close(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(_close(x, y) for x, y in zip(a, b))
    if isinstance(a, float) or isinstance(b, float):
        return isinstance(a, (int, float)) and isinstance(b, (int, float)) and math.isclose(a, b, abs_tol=1e-9)
    return a == b


def plan_merge(source, dest, bandit_decay: float = 0.0) -> MergePlan:
    """Plan merging the download at `source` into the local store at
    `dest` (both directories); nothing is written (see the module
    docstring for the rules). `bandit_decay` is Green's
    `BanditAgent.decay_rate`; without it his differing posteriors are
    not merged but kept as ``method_local.json``.

    Raises
    ------
    ValueError
        If a clashing run's ``<run>_local`` name is already taken.
    """
    return _Planner(Path(source), Path(dest), bandit_decay).run()


def apply_merge(plan: MergePlan, dest) -> int:
    """Carry out `plan` in `dest`: copies and writes first, then removals,
    then any folder left empty. Returns the number of documents changed."""
    root = Path(dest)
    for key, path in plan.copy.items():
        target = root / key
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
    for key, content in plan.write.items():
        target = root / key
        target.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            target.write_bytes(content)
        else:
            target.write_text(_dumps(content), encoding="utf-8")
    removed = plan.delete - set(plan.copy) - set(plan.write)
    for key in removed:
        target = root / key
        target.unlink(missing_ok=True)
        folder = target.parent
        while folder != root and folder.is_dir() and not any(folder.iterdir()):
            folder.rmdir()
            folder = folder.parent
    return plan.changes()
