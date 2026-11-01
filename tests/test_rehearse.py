"""The rehearsal harness (scripts/phase13_rehearse.py, harness 2) lets the
characters hear one another: every request after the first carries the
scene's opening and the replies so far, a scripted person's line arrives
under the display name a table screen would show, the canon is offered,
and nothing is written anywhere."""
from __future__ import annotations

import importlib.util
from pathlib import Path
from random import Random

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "phase13_rehearse.py"


@pytest.fixture(scope="module")
def rehearse():
    spec = importlib.util.spec_from_file_location("phase13_rehearse", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _wrappers(rehearse, scene, backend):
    settings = rehearse.LLMSettings(model="stub", effort="low", remark_max_tokens=200, speak=True)
    canon = rehearse.WikiCanon()
    person = scene.get("person")
    wrappers = {}
    for name in rehearse.ROSTER:
        if person and name == person[0]:
            continue
        wrappers[name] = rehearse.build(name, backend, settings, None, canon)
        wrappers[name].rng = Random(13)
    return wrappers


def test_every_speaker_hears_the_opening_and_the_replies(rehearse):
    backend = rehearse.stub_backend()
    scene = rehearse.SCENES["film"]
    out = rehearse.run_scene("film", scene, _wrappers(rehearse, scene, backend), 3, False)
    assert [line["speaker"] for line in out["lines"]] == scene["order"][:3]
    first, second, third = backend.requests[:3]
    for request in (first, second, third):
        assert scene["opening"][0][1] in request.user and scene["opening"][1][1] in request.user
        assert "Table talk" in request.user
    assert "(stub line 1)" in second.user and "(stub line 2)" in third.user
    assert "(stub line 2)" not in second.user, "a speaker is shown what came before its turn"
    assert 'said: "(stub line 1)"' in second.user, "the trigger names the last speaker's line"
    assert all(line["turn"] == scene["turn"] for line in out["lines"])


def test_a_scripted_person_speaks_under_the_screen_name_and_is_not_a_speaker(rehearse):
    backend = rehearse.stub_backend()
    scene = rehearse.SCENES["bluff"]
    wrappers = _wrappers(rehearse, scene, backend)
    assert "Peacock" not in wrappers, "the guest holds Peacock's seat"
    out = rehearse.run_scene("bluff", scene, wrappers, 2, False)
    assert out["person"] == ("Peacock", "Peacock (Guest)")
    request = backend.requests[0]
    assert "Peacock (Guest)" in request.user and "rematch" in request.user
    assert request.canon, "the canon index is offered"
    assert request.tools, "and its two lookup tools"
    assert out["lines"][0]["lookups"] == []


def test_the_biography_scene_quotes_plums_current_article(rehearse):
    article = (ROOT / "clude_web" / "wiki" / "articles" / "Professor_Plum.md").read_text(encoding="utf-8")
    assert "Wall Street Journal" in article
    line = rehearse.SCENES["biography"]["opening"][0][1]
    assert "Wall Street Journal" in line and "Economist" in line


def test_classify_and_scenes_are_well_formed(rehearse):
    assert rehearse.classify("The Ballroom has not been tested.") == "game"
    assert rehearse.classify("I rather liked the film.") == "other"
    for key, scene in rehearse.SCENES.items():
        assert scene["opening"] and scene["trigger"] and len(scene["order"]) == 4, key
        assert isinstance(scene["turn"], int)
        person = scene.get("person")
        for who in scene["order"]:
            assert who in rehearse.ROSTER and (not person or who != person[0]), key
    assert rehearse.HARNESS == 2
