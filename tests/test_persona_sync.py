"""`clude_llm.persona_sync`: the mirrors of a persona file are found by
their citations, their quotations are judged against the file, the
recordings that a change moves are named, and a model's revisions are
guarded before they are written. The first test is a standing gate: every
quotation of a persona in the wiki and the guides is in the file today.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from clude_llm import DISPLAY_NAMES, NullBackend, ScriptedBackend, load_persona, load_rules, system_prompt
from clude_llm import persona_sync as ps

ROOT = Path(__file__).resolve().parents[1]

KNOWN_UNSOURCED = {
    # A transcript line from the first model-piloted games, cited to Phase 6
    # beside the persona; it is not in any persona file and never was.
    "mustard's stopped fishing for the candlestick and started asking about rooms",
}


# ---------------------------------------------------------------------
# the standing gate


@pytest.mark.parametrize("name", ps.PERSONA_NAMES)
def test_every_quotation_of_a_persona_in_the_corpus_is_in_its_file(name):
    """With old and new both the installed text nothing can be stale, so
    any drift shows as an unsourced quotation; the only ones allowed are
    `KNOWN_UNSOURCED`, and each of those must still be in use."""
    text = ps.current_text(name)
    report = ps.check(name, text, text)
    assert not report.errors and not report.warnings, (report.errors, report.warnings)
    assert not report.changed and not report.stale
    assert len(report.mirrors) >= (12 if name == ps.RULES else 10), [m.mirror.where for m in report.mirrors]
    kinds = {m.mirror.kind for m in report.mirrors}
    if name != ps.RULES:
        assert {"passage", "dyk", "row", "section"} <= kinds, kinds
        own = ps.article_for(name)
        assert any(m.mirror.path == own and m.mirror.kind == "passage" for m in report.mirrors)
    fresh = sum(len(m.fresh) for m in report.mirrors)
    assert fresh >= (2 if name == ps.RULES else 3), fresh
    unsourced = {phrase for m in report.mirrors for phrase in m.unsourced}
    assert unsourced <= KNOWN_UNSOURCED, unsourced - KNOWN_UNSOURCED
    if name == "White":
        assert unsourced == KNOWN_UNSOURCED


def test_a_passage_citing_two_files_is_sourced_to_the_other_one():
    """Peacock's voice paragraph carries [^rules] and [^persona]; for the
    rules its quotations are found in Peacock's file, not reported stale
    or unsourced."""
    report = ps.check(ps.RULES, ps.current_text(ps.RULES), ps.current_text(ps.RULES))
    peacock = [m for m in report.mirrors if m.mirror.path.name == "Mrs._Peacock.md" and m.mirror.kind == "passage"]
    assert peacock and any(m.elsewhere for m in peacock)
    assert not any(m.unsourced for m in peacock)


# ---------------------------------------------------------------------
# the file


def test_validate_source_wants_the_display_name_and_the_shared_sections():
    errors, warnings = ps.validate_source("Mustard", ps.current_text("Mustard"))
    assert errors == [] and warnings == []
    errors, warnings = ps.validate_source("Mustard", "# Colonel Custard\n\n## How you talk\n\nLoud.\n")
    assert errors == ["the first line must be '# Colonel Mustard', not '# Colonel Custard'"]
    assert warnings == ["no '## How you think' section"]
    errors, warnings = ps.validate_source(ps.RULES, "# The house rules, for every character\n\n## Decisions\n\nx\n")
    assert errors == [] and len(warnings) == 2
    with pytest.raises(KeyError):
        ps.persona_path("Nobody")


def test_install_normalises_newlines_and_read_source_refuses_bad_files(tmp_path, monkeypatch):
    monkeypatch.setattr(ps, "PERSONA_DIR", tmp_path)
    assert ps.install("Mustard", "# Colonel Mustard\r\n\r\nLoud.\r\n\r\n\r\n") is True
    assert (tmp_path / "Mustard.md").read_bytes() == b"# Colonel Mustard\n\nLoud.\n"
    assert ps.install("Mustard", "# Colonel Mustard\n\nLoud.") is False
    assert ps.current_text("Mustard") == "# Colonel Mustard\n\nLoud.\n"
    assert ps.repo_path("Mustard").endswith("Mustard.md")
    empty = tmp_path / "empty.md"
    empty.write_text("  \n", encoding="utf-8")
    with pytest.raises(ValueError, match="empty"):
        ps.read_source(empty)
    bad = tmp_path / "bad.md"
    bad.write_bytes(b"# Colonel Mustard\n\n\xff\xfe\n")
    with pytest.raises(ValueError, match="not UTF-8"):
        ps.read_source(bad)
    assert ps.old_text("Mustard", "no-such-revision") is None


# ---------------------------------------------------------------------
# a change


def _changed_mustard() -> tuple:
    old = ps.current_text("Mustard")
    assert "hearty, bluff, decisive" in old
    return old, old.replace("hearty, bluff, decisive", "hearty, blunt, decisive")


def test_a_changed_sentence_names_the_passages_that_quote_it():
    old, new = _changed_mustard()
    report = ps.check("Mustard", new, old)
    assert report.changed and "-You are Colonel Mustard: hearty, bluff" in report.diff()
    stale = {(m.mirror.path.name, phrase) for m in report.stale for phrase in m.stale}
    assert ("Colonel_Mustard.md", "hearty, bluff, decisive, a military man") in stale
    # The other quotations of the file are untouched.
    assert sum(len(m.fresh) for m in report.mirrors) >= 4
    # The dyk hook that paraphrases him is still true.
    dyk = [m for m in report.mirrors if m.mirror.kind == "dyk"]
    assert dyk and not any(m.stale for m in dyk)


def test_quotes_reads_straight_and_curly_marks_links_and_emphasis():
    passage = (
        "She is ‘quick, glamorous, and entirely sure of yourself’ and reads *The Economist*; "
        '"a [[Mr. Green|film]] with nerve" is her phrase, and "no" is not a quotation.'
    )
    assert ps.quotes(passage) == [
        "a film with nerve",
        "quick, glamorous, and entirely sure of yourself",
    ]
    assert ps.quotes('He says "Seen this." often') == []  # two words


# ---------------------------------------------------------------------
# the recordings


def _recorded_games() -> dict:
    """The fixture rows of `tests/test_llm.py`, so `RECORD_COMMANDS` cannot drift from them."""
    text = (ROOT / "tests" / "test_llm.py").read_text(encoding="utf-8")
    rows = re.findall(r'"(llm_seed\d\.json)", "(\d+)", "(\d+)", "([A-Za-z,]+)",', text)
    assert len(rows) == 2
    return {fixture: f"--seed {seed} --players {players} --roster {roster}" for fixture, seed, players, roster in rows}


def test_fixture_status_matches_the_recordings_and_the_test_rows():
    assert {k: v[0] for k, v in ps.RECORD_COMMANDS.items()} == _recorded_games()
    for fixture in sorted(ps.FIXTURE_DIR.glob("llm_*.json")):
        assert ps.stale_in(fixture) == []
    status = {(s.fixture.name, s.name): s.state for s in ps.fixture_status(ps.RULES)}
    assert status[("llm_seed1.json", "Scarlett")] == "fresh"
    assert status[("llm_seed1.json", "Peacock")] == "fresh"
    assert status[("llm_seed2.json", "Mustard")] == "fresh"
    assert status[("llm_seed2.json", "Plum")] == "fresh"
    assert status[("llm_seed2.json", "Green")] == "not recorded"  # seated, never called
    assert status[("llm_seed1.json", "Mustard")] == "not recorded"
    old, new = _changed_mustard()
    moved = {(s.fixture.name, s.state) for s in ps.fixture_status("Mustard", text=new)}
    assert moved == {("llm_seed1.json", "not recorded"), ("llm_seed2.json", "stale")}
    seed2 = [s for s in ps.fixture_status("Mustard", text=new) if s.state == "stale"][0]
    assert seed2.command.startswith("python scripts\\clude_cli.py play --seed 2")
    assert "record:tests/fixtures/llm_seed2.json" in seed2.command and seed2.last_cost.startswith("$")
    # A rules change moves every recorded persona.
    changed_rules = load_rules() + "\nAnd one more thing.\n"
    assert all(s.state != "fresh" for s in ps.fixture_status(ps.RULES, text=changed_rules))


def test_stale_in_reads_a_fixture_by_its_recorded_headings(tmp_path):
    current = system_prompt(load_persona("Mustard"), load_rules())
    fixture = tmp_path / "llm_seed9.json"
    fixture.write_text(json.dumps({"version": 1, "systems": {"a": current + "\n\nolder"}, "entries": {}}), encoding="utf-8")
    assert ps.stale_in(fixture) == ["Mustard"]
    fixture.write_text(json.dumps({"version": 1, "systems": {"a": current, "b": current + " older"}, "entries": {}}), encoding="utf-8")
    assert ps.stale_in(fixture) == []
    assert [s.state for s in ps.fixture_status("Mustard", directory=tmp_path)] == ["fresh"]


# ---------------------------------------------------------------------
# rewriting


def _article_copy(tmp_path: Path) -> tuple:
    """A CRLF copy of Mustard's article and its persona passages as mirrors."""
    source = ps.ARTICLE_DIR / "Colonel_Mustard.md"
    copy = tmp_path / "Colonel_Mustard.md"
    lines = source.read_text(encoding="utf-8").replace("\r\n", "\n").split("\n")
    copy.write_bytes("\r\n".join(lines).encode("utf-8"))
    mirrors = [
        ps.Mirror(copy, "passage", "[^persona]", line, index + 1)
        for index, line in enumerate(lines) if "[^persona]" in line and not line.startswith("[^")
    ]
    assert len(mirrors) >= 3
    return copy, mirrors


def test_rewrite_request_carries_both_texts_the_diff_and_numbered_passages(tmp_path):
    _, mirrors = _article_copy(tmp_path)
    old, new = _changed_mustard()
    request = ps.rewrite_request("Mustard", old, new, mirrors)
    assert request.kind == "rewrite" and request.system == ps.REWRITE_BRIEF
    assert request.schema["properties"]["passages"]["items"]["required"] == ["id", "text"]
    assert "## The persona before" in request.user and "-You are Colonel Mustard: hearty, bluff" in request.user
    assert f"[{len(mirrors)}] (" in request.user and mirrors[0].text in request.user
    assert request.max_tokens == ps.REWRITE_MAX_TOKENS and request.effort == "medium"


def test_rewrite_file_writes_guarded_passages_and_keeps_the_newline_style(tmp_path):
    copy, mirrors = _article_copy(tmp_path)
    old, new = _changed_mustard()
    first = mirrors[0].text.replace("hearty, bluff, decisive", "hearty, blunt, decisive")
    assert first != mirrors[0].text
    reply = {"passages": [
        {"id": "1", "text": first + "\n"},
        {"id": "2", "text": mirrors[1].text.replace("[^persona]", "")},  # drops the mark
        {"id": "3", "text": mirrors[2].text},  # unchanged
    ]}
    report = ps.rewrite_file("Mustard", old, new, mirrors, ScriptedBackend([reply]))
    assert report["fallback"] is None and report["changed"] == 1 and report["unchanged"] == 1
    assert ("2", "drops [^persona]") in report["refused"]
    assert all(number != "1" for number, _ in report["refused"])
    raw = copy.read_bytes()
    assert b"\r\n" in raw and b"hearty, blunt, decisive" in raw
    assert raw.decode("utf-8").count("\n") == raw.decode("utf-8").count("\r\n")
    lines = raw.decode("utf-8").split("\r\n")
    assert lines[mirrors[0].line - 1] == first.strip() and lines[mirrors[1].line - 1] == mirrors[1].text
    assert [m.text for m in mirrors if m.line == mirrors[1].line] == [mirrors[1].text]


def test_rewrite_file_writes_nothing_on_a_failed_or_malformed_reply(tmp_path):
    copy, mirrors = _article_copy(tmp_path)
    old, new = _changed_mustard()
    before = copy.read_bytes()
    report = ps.rewrite_file("Mustard", old, new, mirrors, NullBackend())
    assert report["fallback"].startswith("null backend") and report["changed"] == 0
    report = ps.rewrite_file("Mustard", old, new, mirrors, ScriptedBackend(["not json"]))
    assert report["fallback"].startswith("malformed reply") and report["changed"] == 0
    report = ps.rewrite_file("Mustard", old, new, mirrors, ScriptedBackend([{"passages": [{"id": "9", "text": "x"}]}]))
    assert report["fallback"] is None and report["changed"] == 0 and len(report["refused"]) == len(mirrors)
    assert copy.read_bytes() == before


def test_guard_keeps_dyk_prefixes_table_pipes_and_length():
    dyk = ps.Mirror(Path("x.md"), "dyk", "dyk 1", "dyk: ... that [[Colonel Mustard]] has never read this?", 8)
    assert ps.guard(dyk, "... that he has never read this?") == "a dyk line must start with 'dyk:'"
    assert ps.guard(dyk, "dyk: ... that [[Colonel Mustard]] reads it now?") is None
    row = ps.Mirror(Path("x.md"), "row", "table", "| [[Colonel Mustard]] | Has never read it |", 50)
    assert ps.guard(row, "[[Colonel Mustard]] | Reads it") == "a table row must start with '|'"
    passage = ps.Mirror(Path("x.md"), "passage", "[^p]", "Short.[^p] {{main:Decision tree}}", 3)
    assert ps.guard(passage, "   ") == "empty"
    assert ps.guard(passage, "Short.[^p]") == "drops {{main:Decision tree}}"
    assert ps.guard(passage, "Short.[^p] {{main:Decision tree}} " + "x" * 200) == "far longer than the original"
    assert ps.by_file([passage, row, dyk]) == [(Path("x.md"), [passage, row, dyk])]


# ---------------------------------------------------------------------
# the logbooks


def test_logbook_status_reports_entries_and_digest(tmp_path):
    from clude_storage import LocalStore, Logbook
    from clude_storage.logbooks import LogbookEntry

    store = LocalStore(tmp_path)
    assert ps.logbook_status(store, "Mustard") is None
    assert ps.logbook_status(store, ps.RULES) is None
    from tests.test_logbooks import _record

    logbook = Logbook(store, "Mustard")
    logbook.add_entry(LogbookEntry.build("Mustard", 1, _record(seed=3), 0, {"flags": ["x", "y"]}))
    assert ps.logbook_status(store, "Mustard") == {"entries": 1, "digest": None}
    assert ps.title_of("Mustard") == DISPLAY_NAMES["Mustard"] and ps.title_of(ps.RULES) == ps.RULES_TITLE
