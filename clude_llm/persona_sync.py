"""Keep every copy of a persona's prose in step with its file.

A persona file (`personas/<Suspect>.md`, or the shared `rules.md`) is the
only source: the wiki articles and guides that quote or paraphrase it are
hand-written mirrors, and the replay fixtures hold the exact prompt it was
part of. This module finds the mirrors by their citations, says which of
their quotations a new text leaves stale, says which recordings it moves,
and can ask a model to bring the mirrors into line. The CLI's `persona`
commands print what it reports; `docs/cli.md` describes them.
"""
from __future__ import annotations

import difflib
import hashlib
import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .backend import LLMBackend, LLMRequest, LLMResult
from .persona import DISPLAY_NAMES, PERSONA_DIR, RULES_FILE, Persona, load_persona, load_rules
from .prompt import system_prompt
from .schema import REWRITE_KIND, parse_response, schema_for

ROOT = PERSONA_DIR.parents[1]
ARTICLE_DIR = ROOT / "clude_web" / "wiki" / "articles"
FIXTURE_DIR = ROOT / "tests" / "fixtures"

RULES = "rules"
"""The name the shared rules go by in these commands."""

RULES_TITLE = "The house rules, for every character"
PERSONA_NAMES: tuple = (*DISPLAY_NAMES, RULES)

REQUIRED_SECTIONS: dict = {
    RULES: ("The company and the parts", "The encyclopaedia", "Decisions"),
}
"""Level-two headings a file is expected to keep: the suspects share two,
the rules three that articles cite as locators."""
SUSPECT_SECTIONS: tuple = ("How you think", "How you talk")

EXTRA_MIRRORS: tuple = (
    ("clude_web/wiki/articles/Wikiclude.md", "row", "What the characters make of it", "suspects"),
    ("docs/llm-wrapper.md", "section", "Personas", "all"),
)
"""Mirrors that no footnote finds: ``(path, kind, heading, applies)``. A
``row`` is a table row under the heading that links the character; a
``section`` is a line under the heading that names it."""

REPORT_ONLY: dict = {
    RULES: (
        "clude_llm/canon.py: the two tool descriptions in WIKI_TOOLS paraphrase 'The encyclopaedia'",
        "clude_web/mcp.py: the MCP instructions draw the same line for chat seats",
    ),
}
"""Code that paraphrases a file and is part of replay keys: named, never rewritten."""

RECORD_COMMANDS: dict = {
    "llm_seed1.json": ("--seed 1 --players 3 --roster Scarlett,Peacock", "$0.0322 on 2026-10-26"),
    "llm_seed2.json": ("--seed 2 --players 4 --roster Plum,Mustard,Green,White", "$0.0360 on 2026-10-26"),
}
"""Each fixture's `play` settings and the cost of its last refresh
(`tests/test_llm.py` keeps the history)."""

REWRITE_MAX_TOKENS = 8192

REWRITE_BRIEF = (
    "You are the copy editor of Wikiclude, the house encyclopaedia of clude, a private game of "
    "Clue played by people and six characters piloted by language models. A character's persona "
    "file has been edited. You are given the persona before and after the edit, the difference, "
    "and numbered passages from articles and guides that quote or paraphrase it. Return each "
    "passage revised so that it agrees with the persona as it now reads.\n\n"
    "Rules. Change only what the edit requires; a passage that needs nothing returns unchanged. "
    "Keep every piece of markup exactly as it is: {{...}} templates, [[...]] links, [^...] "
    "footnote marks, table pipes, a leading 'dyk:' and its '... that' form. Keep each passage on "
    "one line and within about a fifth of its present length. Quote short phrases and "
    "paraphrase the rest, in the article's descriptive voice: an article describes, the persona "
    "file instructs, so never copy instructions wholesale. Do not add facts the persona does not "
    "state. Answer with JSON only."
)


# ---------------------------------------------------------------------
# the files
# ---------------------------------------------------------------------


def persona_path(name: str) -> Path:
    """The file for `name`: a suspect's persona or `rules.md`."""
    if name == RULES:
        return PERSONA_DIR / RULES_FILE
    if name not in DISPLAY_NAMES:
        raise KeyError(name)
    return PERSONA_DIR / f"{name}.md"


def repo_path(name: str) -> str:
    """The file as citations and git name it, e.g. ``clude_llm/personas/Mustard.md``."""
    return f"clude_llm/personas/{persona_path(name).name}"


def relative(path: Path) -> str:
    """`path` from the repository root, or as given when outside it."""
    try:
        return Path(path).relative_to(ROOT).as_posix()
    except ValueError:
        return Path(path).as_posix()


def title_of(name: str) -> str:
    """The H1 the file must open with."""
    return RULES_TITLE if name == RULES else DISPLAY_NAMES[name]


def article_for(name: str) -> Optional[Path]:
    """The suspect's own wiki article; None for the rules."""
    if name == RULES:
        return None
    return ARTICLE_DIR / (DISPLAY_NAMES[name].replace(" ", "_") + ".md")


def normalise(text: str) -> str:
    """One newline style, no trailing blank lines, one final newline: the
    bytes `install` writes. Whitespace at the ends never reaches a replay
    key (`system_prompt` strips it), so this changes no recording."""
    return text.replace("\r\n", "\n").replace("\r", "\n").strip() + "\n"


def read_source(path: Path) -> str:
    """A candidate file's text, normalised.

    Raises
    ------
    ValueError
        If the file is not UTF-8 or is empty.
    """
    raw = Path(path).read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{path} is not UTF-8: {exc}") from None
    if not text.strip():
        raise ValueError(f"{path} is empty")
    return normalise(text)


def current_text(name: str) -> str:
    """The installed file's text, normalised."""
    return normalise(persona_path(name).read_text(encoding="utf-8"))


def old_text(name: str, rev: str = "HEAD") -> Optional[str]:
    """The file as git has it at `rev`, normalised; None when git or the
    revision is unavailable (the caller falls back to the installed file)."""
    try:
        done = subprocess.run(
            ["git", "show", f"{rev}:{repo_path(name)}"],
            cwd=ROOT, capture_output=True, check=False,
        )
    except OSError:
        return None
    if done.returncode != 0:
        return None
    try:
        return normalise(done.stdout.decode("utf-8"))
    except UnicodeDecodeError:
        return None


def install(name: str, text: str) -> bool:
    """Write `text` as the file for `name`, LF newlines and one trailing
    newline, as the persona files are kept. Returns whether bytes changed."""
    path = persona_path(name)
    data = normalise(text).encode("utf-8")
    if path.exists() and path.read_bytes() == data:
        return False
    path.write_bytes(data)
    return True


def validate_source(name: str, text: str) -> tuple:
    """``(errors, warnings)`` for a candidate text: the H1 must be the
    character's display name (the `prompt` command and its test rely on
    it); the shared section headings should still be there."""
    errors: list = []
    warnings: list = []
    lines = [line for line in normalise(text).split("\n") if line.strip()]
    first = lines[0].strip() if lines else ""
    if first != f"# {title_of(name)}":
        errors.append(f"the first line must be '# {title_of(name)}', not {first!r}")
    headings = {line[3:].strip() for line in lines if line.startswith("## ")}
    for heading in REQUIRED_SECTIONS.get(name, SUSPECT_SECTIONS):
        if heading not in headings:
            warnings.append(f"no '## {heading}' section")
    return errors, warnings


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------
# the mirrors
# ---------------------------------------------------------------------


@dataclass(frozen=True)
class Mirror:
    """One line of a file that quotes or paraphrases the persona.

    `kind` is ``passage`` (carries a footnote citing the file), ``dyk``
    (a front-matter hook of the character's own article), ``row`` (a
    table row linking the character) or ``section`` (a line of a guide's
    section that names it); `anchor` says which; `text` is the line as
    it stands, `line` its 1-based number.
    """

    path: Path
    kind: str
    anchor: str
    text: str
    line: int

    @property
    def where(self) -> str:
        """``path:line`` as a report names it."""
        return f"{relative(self.path)}:{self.line}"


_FOOTNOTE = re.compile(r"^\[\^([^\]]+)\]:\s*\{\{cite:(clude_llm/personas/[^|}]+)(?:\|[^}]*)?\}\}(.*)$")


def _lines(path: Path) -> list:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n").split("\n")


def _footnote_keys(lines: list, name: str) -> set:
    """The footnote keys of an article whose definition cites `name`'s
    file. A definition that cites one suspect's file 'and the other five'
    counts for every suspect."""
    wanted = repo_path(name)
    keys: set = set()
    for line in lines:
        match = _FOOTNOTE.match(line.strip())
        if match is None:
            continue
        key, cited, tail = match.groups()
        if cited == wanted:
            keys.add(key)
        elif name != RULES and cited != repo_path(RULES) and "other five" in tail.lower():
            keys.add(key)
    return keys


def _section_lines(lines: list, heading: str) -> list:
    """``(index, line)`` for every line under ``## heading`` up to the next ``##``."""
    out: list = []
    inside = False
    for index, line in enumerate(lines):
        if line.startswith("## "):
            inside = line[3:].strip() == heading
            continue
        if inside and line.strip():
            out.append((index, line))
    return out


def _mentions(line: str, name: str) -> bool:
    if name == RULES:
        return "rules" in line.lower()
    return name in line or DISPLAY_NAMES[name] in line


def find_mirrors(name: str) -> list:
    """Every `Mirror` of `name` in the wiki articles and guides, in file
    and line order. Articles are hard-wrapped nowhere, so a passage is
    one line."""
    mirrors: list = []
    for path in sorted(ARTICLE_DIR.glob("*.md")):
        lines = _lines(path)
        keys = _footnote_keys(lines, name)
        marks = [f"[^{key}]" for key in sorted(keys)]
        for index, line in enumerate(lines):
            if not marks or _FOOTNOTE.match(line.strip()):
                continue
            hit = [mark for mark in marks if mark in line]
            if hit:
                mirrors.append(Mirror(path, "passage", " ".join(hit), line, index + 1))
    own = article_for(name)
    if own is not None and own.exists():
        for index, line in enumerate(_lines(own)):
            if line.startswith("---") and index > 0:
                break
            if line.startswith("dyk:"):
                mirrors.append(Mirror(own, "dyk", f"dyk {sum(1 for m in mirrors if m.kind == 'dyk') + 1}", line, index + 1))
    for relative, kind, heading, applies in EXTRA_MIRRORS:
        if applies == "suspects" and name == RULES:
            continue
        path = ROOT / relative
        if not path.exists():
            continue
        for index, line in _section_lines(_lines(path), heading):
            if kind == "row" and not (line.startswith("|") and f"[[{DISPLAY_NAMES[name]}]]" in line):
                continue
            if kind == "section" and not _mentions(line, name):
                continue
            mirrors.append(Mirror(path, kind, heading, line, index + 1))
    mirrors.sort(key=lambda m: (m.path.as_posix(), m.line))
    return mirrors


# ---------------------------------------------------------------------
# quotations
# ---------------------------------------------------------------------

_QUOTE_MAP = {"‘": "'", "’": "'", "“": '"', "”": '"'}


def _plain(text: str) -> str:
    """Prose for comparison: straight quotes, links by their label, no
    emphasis, one space, lower case."""
    for curly, straight in _QUOTE_MAP.items():
        text = text.replace(curly, straight)
    text = re.sub(r"\[\[[^\]|]*\|([^\]]*)\]\]", r"\1", text)
    text = re.sub(r"\[\[([^\]]*)\]\]", r"\1", text)
    text = text.replace("*", "").replace("`", "")
    return re.sub(r"\s+", " ", text).strip().lower()


_DOUBLE = re.compile(r'"([^"]+)"')
_SINGLE = re.compile(r"(?<![A-Za-z0-9])'([^']+)'(?![A-Za-z0-9])")


def quotes(text: str) -> list:
    """The quoted phrases of a passage, three words or longer, as `_plain`
    renders them, with no trailing punctuation."""
    plain = _plain(text)
    found: list = []
    for pattern in (_DOUBLE, _SINGLE):
        for match in pattern.finditer(plain):
            phrase = match.group(1).strip().rstrip(".,;:!?").strip()
            if len(phrase.split()) >= 3 and "{{" not in phrase and phrase not in found:
                found.append(phrase)
    return found


def _contains(text: str, phrase: str) -> bool:
    return phrase in _plain(text)


@dataclass
class MirrorCheck:
    """A mirror's quotations sorted against the persona: `fresh` are in
    the new text, `stale` were in the old text and are not in the new,
    `elsewhere` are in another persona file (a passage citing two), and
    `unsourced` are in none (a transcript line, or drift from before the
    old text)."""

    mirror: Mirror
    fresh: list = field(default_factory=list)
    stale: list = field(default_factory=list)
    elsewhere: list = field(default_factory=list)
    unsourced: list = field(default_factory=list)


def check_mirror(mirror: Mirror, old: str, new: str, others: tuple = ()) -> MirrorCheck:
    result = MirrorCheck(mirror)
    for phrase in quotes(mirror.text):
        if _contains(new, phrase):
            result.fresh.append(phrase)
        elif _contains(old, phrase):
            result.stale.append(phrase)
        elif any(_contains(other, phrase) for other in others):
            result.elsewhere.append(phrase)
        else:
            result.unsourced.append(phrase)
    return result


def other_texts(name: str) -> tuple:
    """The installed text of every persona file but `name`'s."""
    return tuple(current_text(other) for other in PERSONA_NAMES if other != name)


# ---------------------------------------------------------------------
# the recordings
# ---------------------------------------------------------------------


@dataclass(frozen=True)
class FixtureStatus:
    """Whether `fixture` still holds the prompt `name`'s current text
    makes: ``fresh``, ``stale`` (it recorded other versions only) or
    ``not recorded`` (no prompt of that persona at all)."""

    fixture: Path
    name: str
    state: str
    recorded: int

    @property
    def command(self) -> str:
        settings, _ = RECORD_COMMANDS.get(self.fixture.name, ("<settings>", ""))
        return (
            f"python scripts\\clude_cli.py play {settings} --llm "
            f"--llm-backend record:tests/fixtures/{self.fixture.name} --verbose"
        )

    @property
    def last_cost(self) -> str:
        return RECORD_COMMANDS.get(self.fixture.name, ("", "unknown"))[1]


def _recorded_systems(fixture: Path) -> dict:
    """Recorded system prompts grouped by their H1 line."""
    data = json.loads(fixture.read_text(encoding="utf-8"))
    groups: dict = {}
    for text in data.get("systems", {}).values():
        head = text.strip().split("\n", 1)[0].strip()
        groups.setdefault(head, []).append(text)
    return groups


def fixture_status(name: str, text: Optional[str] = None, rules: Optional[str] = None, directory: Optional[Path] = None) -> list:
    """`FixtureStatus` per fixture, for `name` or, for the rules, for every
    suspect, judged against `text` (a candidate; default the installed
    file) and `rules` (default the installed rules)."""
    folder = FIXTURE_DIR if directory is None else Path(directory)
    rules_text = rules if rules is not None else (text if name == RULES else None)
    if rules_text is None:
        rules_text = load_rules()
    names = list(DISPLAY_NAMES) if name == RULES else [name]
    statuses: list = []
    for fixture in sorted(folder.glob("llm_*.json")):
        groups = _recorded_systems(fixture)
        for suspect in names:
            persona_text = text if (text is not None and name == suspect) else load_persona(suspect).text
            current = system_prompt(Persona(suspect, persona_text), rules_text)
            recorded = groups.get(f"# {DISPLAY_NAMES[suspect]}", [])
            if not recorded:
                state = "not recorded"
            elif any(entry == current for entry in recorded):
                state = "fresh"
            else:
                state = "stale"
            statuses.append(FixtureStatus(fixture, suspect, state, len(recorded)))
    return statuses


def stale_in(fixture: Path) -> list:
    """The personas whose recorded prompts in `fixture` no longer match
    the installed files (the rules included), for the replay test."""
    groups = _recorded_systems(Path(fixture))
    rules_text = load_rules()
    stale: list = []
    for suspect, display in DISPLAY_NAMES.items():
        recorded = groups.get(f"# {display}", [])
        if recorded and system_prompt(load_persona(suspect), rules_text) not in recorded:
            stale.append(suspect)
    return stale


# ---------------------------------------------------------------------
# the whole check
# ---------------------------------------------------------------------


@dataclass
class Check:
    """What `persona check` reports for one file and one candidate text."""

    name: str
    old: str
    new: str
    errors: list
    warnings: list
    mirrors: list
    fixtures: list

    @property
    def changed(self) -> bool:
        return self.old.strip() != self.new.strip()

    @property
    def stale(self) -> list:
        return [item for item in self.mirrors if item.stale]

    @property
    def stale_fixtures(self) -> list:
        return [item for item in self.fixtures if item.state == "stale"]

    def diff(self) -> str:
        return "\n".join(difflib.unified_diff(
            self.old.split("\n"), self.new.split("\n"), "before", "after", lineterm="",
        ))


def check(name: str, new: Optional[str] = None, old: Optional[str] = None) -> Check:
    """Validate `new` (default the installed file) against `old` (default
    git's HEAD, else the installed file), sort every mirror's quotations,
    and judge the fixtures."""
    if name not in PERSONA_NAMES:
        raise KeyError(name)
    new_text = normalise(new) if new is not None else current_text(name)
    old_text_ = old if old is not None else old_text(name)
    if old_text_ is None:
        old_text_ = current_text(name)
    errors, warnings = validate_source(name, new_text)
    others = other_texts(name)
    mirrors = [check_mirror(mirror, old_text_, new_text, others) for mirror in find_mirrors(name)]
    fixtures = fixture_status(name, text=new_text)
    return Check(name, old_text_, new_text, errors, warnings, mirrors, fixtures)


# ---------------------------------------------------------------------
# rewriting the mirrors
# ---------------------------------------------------------------------

_MARKUP = re.compile(r"\[\^[^\]]+\]|\{\{[^}]*\}\}")


def rewrite_request(name: str, old: str, new: str, mirrors: list, effort: str = "medium", timeout: float = 180.0) -> LLMRequest:
    """One call that revises `mirrors` (all from one file) for the change
    from `old` to `new`. The system text is the editor's brief, not the
    persona; nothing here is cached or keyed with a game's prompts."""
    diff = "\n".join(difflib.unified_diff(old.split("\n"), new.split("\n"), "before", "after", lineterm="")) or "(no change)"
    numbered = "\n\n".join(f"[{i}] ({mirror.where}, {mirror.kind})\n{mirror.text}" for i, mirror in enumerate(mirrors, 1))
    user = (
        f"The file is {repo_path(name)} ({title_of(name)}).\n\n"
        f"## The persona before\n\n{old.strip()}\n\n"
        f"## The persona now\n\n{new.strip()}\n\n"
        f"## What changed\n\n{diff}\n\n"
        f"## Passages to revise\n\n{numbered}\n\n"
        "Return every passage by its number, revised or unchanged, as "
        '{"passages": [{"id": "1", "text": "..."}, ...]}.'
    )
    return LLMRequest(
        system=REWRITE_BRIEF, user=user, schema=schema_for(REWRITE_KIND), kind=REWRITE_KIND,
        effort=effort, max_tokens=REWRITE_MAX_TOKENS, timeout=timeout,
    )


def guard(mirror: Mirror, text: str) -> Optional[str]:
    """Why a revised passage may not replace `mirror`, or None if it may:
    it must be one non-empty line that keeps every footnote mark and
    template the original had, a dyk its prefix, a row its pipes."""
    revised = " ".join(text.split("\n")).strip()
    if not revised:
        return "empty"
    missing = [token for token in _MARKUP.findall(mirror.text) if token not in revised]
    if missing:
        return f"drops {', '.join(missing)}"
    if mirror.kind == "dyk" and not revised.startswith("dyk:"):
        return "a dyk line must start with 'dyk:'"
    if mirror.kind == "row" and not revised.startswith("|"):
        return "a table row must start with '|'"
    if len(revised) > 1.5 * len(mirror.text) + 80:
        return "far longer than the original"
    return None


def apply_rewrites(path: Path, replacements: list) -> int:
    """Replace each ``(mirror, text)`` line in `path`, keeping the file's
    newline style. Returns how many lines changed."""
    raw = Path(path).read_bytes().decode("utf-8")
    newline = "\r\n" if "\r\n" in raw else "\n"
    lines = raw.replace("\r\n", "\n").split("\n")
    changed = 0
    for mirror, text in replacements:
        revised = " ".join(text.split("\n")).strip()
        index = mirror.line - 1
        if index < len(lines) and lines[index] == mirror.text and revised != mirror.text:
            lines[index] = revised
            changed += 1
    if changed:
        Path(path).write_bytes(newline.join(lines).encode("utf-8"))
    return changed


def rewrite_file(name: str, old: str, new: str, mirrors: list, backend: LLMBackend, effort: str = "medium", timeout: float = 180.0) -> dict:
    """Ask `backend` to revise one file's `mirrors` and write what passes
    `guard`. A failed or malformed reply writes nothing.

    Returns
    -------
    dict
        ``path``, ``fallback`` (None on success, else why nothing was
        written), ``changed`` (lines rewritten), ``refused`` (``(id,
        reason)`` pairs), ``unchanged`` (returned as they were), and the
        call's token counts, ``seconds`` and ``model``.
    """
    request = rewrite_request(name, old, new, mirrors, effort, timeout)
    try:
        result = backend.complete(request)
    except Exception as exc:  # a backend failure writes nothing, never crashes
        result = LLMResult(error=f"{type(exc).__name__}: {exc}")
    report: dict = {
        "path": mirrors[0].path, "fallback": None, "changed": 0, "refused": [], "unchanged": 0,
        "input_tokens": result.input_tokens, "output_tokens": result.output_tokens,
        "cached_tokens": result.cached_tokens, "seconds": result.seconds, "model": result.model,
    }
    if not result.ok:
        report["fallback"] = result.error or f"stop {result.stop_reason}"
        return report
    try:
        data = parse_response(REWRITE_KIND, result.text or "")
        passages = data["passages"]
        replies = {str(item["id"]): str(item["text"]) for item in passages}
    except (ValueError, KeyError, TypeError) as exc:
        report["fallback"] = f"malformed reply ({exc})"
        return report
    replacements: list = []
    for i, mirror in enumerate(mirrors, 1):
        text = replies.get(str(i))
        if text is None:
            report["refused"].append((str(i), "not returned"))
            continue
        if " ".join(text.split("\n")).strip() == mirror.text:
            report["unchanged"] += 1
            continue
        reason = guard(mirror, text)
        if reason is not None:
            report["refused"].append((str(i), reason))
            continue
        replacements.append((mirror, text))
    report["changed"] = apply_rewrites(mirrors[0].path, replacements)
    return report


def by_file(mirrors: list) -> list:
    """Mirrors grouped by file, in file order: ``[(path, [mirror, ...]), ...]``."""
    groups: dict = {}
    for mirror in mirrors:
        groups.setdefault(mirror.path, []).append(mirror)
    return sorted(groups.items(), key=lambda item: item[0].as_posix())


# ---------------------------------------------------------------------
# the logbooks
# ---------------------------------------------------------------------


def logbook_status(store, name: str) -> Optional[dict]:
    """What a store holds in the character's voice: ``entries``, and
    ``digest`` (the serial it runs through, or None); None when there is
    no logbook. The rules have none."""
    if name == RULES:
        return None
    from clude_storage import Logbook  # here, so this module stays light for the wrapper

    logbook = Logbook(store, name)
    if not logbook.exists():
        return None
    digest = logbook.digest()
    return {"entries": len(logbook.serials()), "digest": None if digest is None else digest.through}
