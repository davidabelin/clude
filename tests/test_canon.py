"""The canon (docs/canon-plan.md): Wikiclude, read by model seats and chat seats.

Pinned here: that a read hands over an article a section at a time and
never more than the limit, and a search the matches in shape; that the
backend runs the tool loop inside one call, sums the usage over the
rounds, audits each lookup, sends the last permitted round with tool
choice none and turns a failed lookup into an error result the model
can answer around; that a character with a canon sends the index block
and the tools, stops offering the tools at the game's cap, counts what
was looked up, and without a canon sends exactly the Phase 6 request;
that a recording replays the lookups; that the null backend with a
canon is still the headless twin; that the two MCP tools answer with no
login; and that the `prompt` command shows the block and the tools.
"""
from __future__ import annotations

import json
import os
import random
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from mcp import Client

import clude_constraints
from clude_agents import PRESETS, build_character
from clude_core import engine
from clude_llm import (
    WIKI_TOOLS,
    LLMCharacter,
    LLMRequest,
    LLMResult,
    LLMSettings,
    NullBackend,
    RecordingBackend,
    ReplayBackend,
    ReplayMiss,
    ScriptedBackend,
    WikiCanon,
    index_block,
    schema_for,
)
from clude_llm.anthropic_backend import AnthropicBackend
from clude_llm.canon import INDEX_HEAD, WIKI_READ, WIKI_SEARCH
from clude_llm.schema import CHOICE_SCHEMA, REMARK_KIND
from clude_storage import open_store
from clude_training.arena import fill_seed, seat_lineup
from clude_web import create_app, mcp, users
from clude_web.wiki import load, render
from clude_web.wiki.index import READ_LIMIT, SEARCH_LIMIT

from tests.test_character import _digest
from tests.test_chat import _obs_for
from tests.test_llm import CLI_SCRIPT, PERSONA, RULES, _character
from tests.test_mcp import unwrap

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="module")
def wiki():
    return load()


# --- what the wiki hands over -------------------------------------------------


def test_sections_split_at_every_heading_and_lose_nothing(wiki):
    """The sections of an article are its h2 headings in order, and their
    plain texts joined are the body's plain text: nothing between two
    headings is dropped or doubled."""
    checked = 0
    for article in wiki.pages():
        parts = render.sections(article.body)
        assert [heading for _, heading, _ in parts] == [token["name"] for token in article.toc], article.title
        joined = " ".join(f"{heading} {text}".strip() for _, heading, text in parts)
        assert joined == render.plain(article.body), article.title
        checked += 1
    assert checked > 50


def test_read_hands_over_a_section_at_a_time_under_the_limit(wiki):
    plum = wiki.read("Professor Plum")
    assert plum["title"] == "Professor Plum" and plum["lead"].startswith("Professor Plum")
    assert "How he thinks" in plum["sections"] and "References" not in plum["sections"]
    assert "Belief" in plum["see_also"] and "text" not in plum  # too long to come whole
    section = wiki.read("Plum", "How he thinks")  # a redirect, and a heading
    assert section["section"] == "How he thinks" and section["text"] and "cut" not in section
    assert section["text"] == next(t for _, h, t in render.sections(plum and wiki.get("Professor Plum")[0].body) if h == "How he thinks")
    by_anchor = wiki.read("Professor Plum", "how-he-thinks")
    assert by_anchor["text"] == section["text"]
    rules = wiki.read("Rules of play")
    assert rules["section"] == "all" and len(rules["text"]) <= READ_LIMIT and "Movement" in rules["sections"]
    whole = wiki.read("Professor Plum", "all")
    assert whole["section"] == "all" and len(whole["text"]) <= READ_LIMIT and whole["text"].endswith("[...]")
    assert whole["cut"].startswith("cut at")
    short = wiki.read("Professor Plum", "How he thinks", limit=200)
    assert len(short["text"]) <= 200 and short["text"].endswith("[...]")
    assert "stub" not in plum and wiki.read("Sarsa").get("stub") is True
    missing = wiki.read("The Butler")
    assert "title" not in missing and missing["error"].startswith("There is no article") and isinstance(missing["matches"], list)
    wrong = wiki.read("Professor Plum", "Recipes")
    assert wrong["error"].startswith("Professor Plum has no section") and wrong["sections"] == plum["sections"]
    for article in wiki.pages():
        out = wiki.read(article.title)
        assert "error" not in out and out["sections"], article.title
        assert len(out.get("text", "")) <= READ_LIMIT and "enlarge" not in out["lead"]


def test_lookup_is_the_search_in_shape(wiki):
    hits = wiki.lookup("secret passage")
    assert 0 < len(hits) <= SEARCH_LIMIT
    assert all(set(hit) >= {"title", "short", "excerpt"} for hit in hits)
    assert hits[0]["title"] == wiki.search("secret passage")[0][0].title
    assert wiki.lookup("") == [] and wiki.lookup("xyzzyplugh") == []
    assert any(hit.get("stub") for hit in wiki.lookup("Sarsa"))
    assert wiki.titles() == [a.title for a in wiki.pages()] and "Rules of play" in wiki.titles()


def test_the_wiki_canon_answers_the_two_tools_and_nothing_else(wiki):
    canon = WikiCanon(wiki)
    assert canon.tools is WIKI_TOOLS and [t["name"] for t in WIKI_TOOLS] == [WIKI_SEARCH, WIKI_READ]
    assert canon.index() == index_block(wiki.titles()) and canon.index().startswith(INDEX_HEAD)
    assert "Professor Plum" in canon.index() and len(canon.index()) < 4000
    search = canon.lookup(WIKI_SEARCH, {"query": "leash"})
    assert search["found"].startswith("search 'leash': ") and search["matches"][0]["title"] == "Leash"
    read = canon.lookup(WIKI_READ, {"title": "Leash", "section": "all"})
    assert read["found"] == "read Leash, all" and read["text"]
    lead = canon.lookup(WIKI_READ, {"title": "Professor Plum"})
    assert lead["found"] == "read Professor Plum" and "text" not in lead
    gone = canon.lookup(WIKI_READ, {"title": "Nobody"})
    assert gone["found"] == "read 'Nobody': no such article"
    with pytest.raises(KeyError):
        canon.lookup("wiki_edit", {})
    lazy = WikiCanon()
    assert lazy.wiki is wiki  # `load()` is one index per process


# --- the backend's loop --------------------------------------------------------


class _Canon:
    """A canon with one article, for the loop."""

    name = "test"
    tools = WIKI_TOOLS

    def __init__(self, fail=False):
        self.fail = fail
        self.asked: list = []

    def index(self):
        return "idx"

    def lookup(self, name, arguments):
        self.asked.append((name, dict(arguments)))
        if self.fail:
            raise RuntimeError("shelf empty")
        return {"title": arguments.get("title", "?"), "text": "Rope first.", "found": f"read {arguments.get('title')}"}


def _usage(i, o, c):
    return SimpleNamespace(input_tokens=i, output_tokens=o, cache_read_input_tokens=c)


def _tool_turn(uses, usage=_usage(100, 10, 50)):
    content = [SimpleNamespace(type="thinking", thinking="")] + [
        SimpleNamespace(type="tool_use", id=f"tu{i}", name=name, input=inp) for i, (name, inp) in enumerate(uses)
    ]
    return SimpleNamespace(content=content, stop_reason="tool_use", model="claude-opus-5", usage=usage)


def _text_turn(text, usage=_usage(200, 20, 50)):
    content = [SimpleNamespace(type="thinking", thinking=""), SimpleNamespace(type="text", text=text)]
    return SimpleNamespace(content=content, stop_reason="end_turn", model="claude-opus-5", usage=usage)


class _Rounds:
    """`messages.create` serving responses in order and keeping the calls."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls: list = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.responses.pop(0)


def _client(responses):
    rounds = _Rounds(responses)
    return SimpleNamespace(messages=rounds, beta=SimpleNamespace(messages=rounds)), rounds


def _request(canon, max_lookups=3, **kwargs):
    return LLMRequest(
        "sys", "user", CHOICE_SCHEMA, "move", canon=canon.index(), tools=canon.tools,
        lookup=canon.lookup, max_lookups=max_lookups, **kwargs,
    )


def test_the_backend_runs_the_loop_inside_one_call_and_audits_it():
    canon = _Canon()
    client, rounds = _client([_tool_turn([(WIKI_READ, {"title": "Leash"})]), _text_turn('{"choice": "A", "say": ""}')])
    result = AnthropicBackend(client=client).complete(_request(canon))
    assert result.ok and json.loads(result.text)["choice"] == "A"
    assert (result.input_tokens, result.output_tokens, result.cached_tokens) == (300, 30, 100)
    assert result.lookups == [{"tool": WIKI_READ, "input": {"title": "Leash"}, "found": "read Leash", "error": False}]
    assert canon.asked == [(WIKI_READ, {"title": "Leash"})]
    first, second = rounds.calls
    assert [t["name"] for t in first["tools"]] == [WIKI_SEARCH, WIKI_READ] and "tool_choice" not in first
    assert [b["text"] for b in first["system"]] == ["sys", "idx"]
    assert all(b["cache_control"] == {"type": "ephemeral"} for b in first["system"])
    assert first["messages"] == [{"role": "user", "content": "user"}]
    assert second["tools"] == first["tools"] and "tool_choice" not in second  # round 1 of 3: still open
    assert [m["role"] for m in second["messages"]] == ["user", "assistant", "user"]
    assert second["messages"][1]["content"] is not None and second["messages"][1]["content"][1].type == "tool_use"
    [answer] = second["messages"][2]["content"]
    assert answer["type"] == "tool_result" and answer["tool_use_id"] == "tu0" and "is_error" not in answer
    assert json.loads(answer["content"]) == {"title": "Leash", "text": "Rope first."}  # `found` is the audit's
    assert second["output_config"]["format"]["schema"] is CHOICE_SCHEMA


def test_the_last_permitted_round_must_answer_and_a_failed_lookup_is_an_error_result():
    canon = _Canon()
    client, rounds = _client([
        _tool_turn([(WIKI_SEARCH, {"query": "rope"}), (WIKI_READ, {"title": "Rope"})]),
        _text_turn('{"choice": "B", "say": "Hm."}'),
    ])
    result = AnthropicBackend(client=client).complete(_request(canon, max_lookups=1))
    assert result.ok and len(result.lookups) == 2 and len(canon.asked) == 2
    assert rounds.calls[1]["tool_choice"] == {"type": "none"} and "tools" in rounds.calls[1]
    assert len(rounds.calls[1]["messages"][2]["content"]) == 2  # both results in one user turn

    broken = _Canon(fail=True)
    client, rounds = _client([_tool_turn([(WIKI_READ, {"title": "Leash"})]), _text_turn('{"choice": "A", "say": ""}')])
    result = AnthropicBackend(client=client).complete(_request(broken))
    assert result.ok and result.lookups[0]["error"] is True and "shelf empty" in result.lookups[0]["found"]
    [answer] = rounds.calls[1]["messages"][2]["content"]
    assert answer["is_error"] is True and "shelf empty" in answer["content"]

    # No lookup to answer with, or no round to run: the tools stay home and
    # the call is the Phase 6 one but for the index block.
    plain = AnthropicBackend(client=_client([_text_turn('{"choice": "A", "say": ""}')])[0])
    plain.complete(_request(canon, max_lookups=0))
    assert "tools" not in plain.client.messages.calls[0]
    bare = LLMRequest("sys", "user", CHOICE_SCHEMA, "move", canon="idx", tools=WIKI_TOOLS)
    plain.complete(bare)
    assert "tools" not in plain.client.messages.calls[1]
    assert plain.client.messages.calls[1]["system"][1]["text"] == "idx"

    # An SDK error on a later round is still one fallback.
    canon = _Canon()
    client, rounds = _client([_tool_turn([(WIKI_READ, {"title": "Leash"})])])
    result = AnthropicBackend(client=client).complete(_request(canon))
    assert not result.ok and result.error.startswith("IndexError")


def test_the_key_and_the_recording_carry_the_canon_and_replay_the_lookups(tmp_path):
    canon = _Canon()
    with_canon = _request(canon)
    without = LLMRequest("sys", "user", CHOICE_SCHEMA, "move")
    assert with_canon.key() != without.key()
    assert with_canon.key() == _request(_Canon()).key()  # the callable is not in the key
    assert LLMRequest("sys", "user", CHOICE_SCHEMA, "move", canon="idx").key() != without.key()

    answered = LLMResult(
        text='{"choice": "A", "say": ""}', stop_reason="end_turn", model="m", input_tokens=3,
        lookups=[{"tool": WIKI_READ, "input": {"title": "Leash"}, "found": "read Leash", "error": False}],
    )
    path = tmp_path / "canon.json"
    recorder = RecordingBackend(ScriptedBackend([answered]), path)
    assert recorder.complete(with_canon).lookups == answered.lookups
    data = json.loads(path.read_text())
    [entry] = data["entries"].values()
    assert entry["tools"] == [WIKI_SEARCH, WIKI_READ] and data["systems"][entry["canon"]] == "idx"
    assert entry["result"]["lookups"] == answered.lookups
    replayed = ReplayBackend(path).complete(with_canon)
    assert replayed.ok and replayed.lookups == answered.lookups and replayed.input_tokens == 3
    with pytest.raises(ReplayMiss):
        ReplayBackend(path).complete(without)
    assert LLMResult.from_dict({"text": "x"}).lookups == []


# --- the wrapper -----------------------------------------------------------------


def _wrapper(responses, canon, settings=None):
    return LLMCharacter(
        _character(PRESETS["Plum"]), ScriptedBackend(responses), persona=PERSONA, rules=RULES,
        settings=settings, canon=canon,
    )


def test_a_character_with_a_canon_offers_the_tools_until_the_games_cap():
    obs, _game = _obs_for()
    canon = _Canon()
    looked = LLMResult(
        text='{"say": "Rope first."}', stop_reason="end_turn", model="m", input_tokens=5,
        lookups=[{"tool": WIKI_READ, "input": {"title": "Rope"}, "found": "read Rope", "error": False}],
    )
    wrapper = _wrapper([looked], canon, settings=LLMSettings(max_lookups_per_game=2, max_lookups_per_call=3))
    assert wrapper.canon is canon and wrapper.canon_block == "idx"
    assert wrapper.react(obs, "x") == "Rope first."
    request = wrapper.backend.requests[-1]
    assert request.canon == "idx" and request.tools == WIKI_TOOLS and request.lookup == canon.lookup
    assert request.max_lookups == 2  # the game's cap, below the call's 3
    decision = wrapper.decisions[-1]
    assert decision.kind == REMARK_KIND and decision.lookups == looked.lookups and decision.to_dict()["lookups"]
    assert (wrapper.lookups, wrapper.game_lookups, wrapper.summary()["lookups"]) == (1, 1, 1)
    wrapper.react(obs, "y")
    assert wrapper.backend.requests[-1].max_lookups == 1 and wrapper.game_lookups == 2
    wrapper.react(obs, "z")  # at the cap: the index still goes, the tools do not
    request = wrapper.backend.requests[-1]
    assert request.canon == "idx" and request.tools == () and request.lookup is None and request.max_lookups == 0
    wrapper.new_game(["Scarlett", "Plum", "White"])
    assert wrapper.game_lookups == 0 and wrapper.lookups == 3
    wrapper.react(obs, "w")
    assert wrapper.backend.requests[-1].max_lookups == 2
    wrapper.attach_canon(None)
    wrapper.react(obs, "v")
    assert wrapper.backend.requests[-1].canon == "" and wrapper.backend.requests[-1].tools == ()


def test_without_a_canon_the_request_is_the_phase_6_one():
    obs, _game = _obs_for()
    plain = _wrapper([{"say": ""}], None)
    plain.react(obs, "x")
    request = plain.backend.requests[-1]
    assert request.canon == "" and request.tools == () and request.lookup is None and request.max_lookups == 0
    bare = LLMRequest(request.system, request.user, schema_for(REMARK_KIND), REMARK_KIND, memory=request.memory)
    assert request.key() == bare.key()
    assert plain.summary()["lookups"] == 0 and plain.decisions[-1].lookups == []


def _null_game(seed, canon, n_players=3, roster=("Scarlett", "Plum")):
    labels, suspects = seat_lineup(list(roster) + ["floor"] * (n_players - len(roster)))
    players = {}
    for seat, name in enumerate(labels):
        if name in PRESETS:
            wrapper = LLMCharacter(build_character(name), NullBackend(), persona=PERSONA, rules=RULES, canon=canon)
            wrapper.reset(seat)
            players[seat] = wrapper
        else:
            players[seat] = clude_constraints.FloorBot(rng=random.Random(fill_seed(seed, seat)))
    _state, events = engine.run_game(
        n_players, players, seed=seed, max_turns=200, observer=clude_constraints.observe, suspects=suspects,
    )
    return events


def test_the_null_backend_with_a_canon_is_still_the_headless_twin():
    assert _digest(_null_game(3, _Canon())) == _digest(_null_game(3, None))


# --- the chat seat and the maintainer ------------------------------------------


async def test_the_mcp_tools_answer_with_no_login(tmp_path):
    store = open_store(str(tmp_path))
    users.add_user(store, "ann", "pw")
    app = create_app({"TESTING": True, "STORE_URI": str(tmp_path)})
    server = mcp.build_server(app.extensions["tables"], app.secret_key)
    assert "clude_wiki_search" in mcp.INSTRUCTIONS and "no login" in mcp.INSTRUCTIONS
    async with Client(server) as client:
        names = {tool.name for tool in (await client.list_tools()).tools}
        assert {"clude_wiki_search", "clude_wiki_read"} <= names and len(names) == 14
        found = unwrap(await client.call_tool("clude_wiki_search", {"query": "secret passage"}))
        assert found["matches"] and set(found["matches"][0]) >= {"title", "short", "excerpt"}
        nothing = unwrap(await client.call_tool("clude_wiki_search", {"query": "xyzzyplugh"}))
        assert nothing["matches"] == [] and "message" in nothing
        rules = unwrap(await client.call_tool("clude_wiki_read", {"title": "Rules of play"}))
        assert rules["section"] == "all" and "accusation" in rules["text"].lower()
        part = unwrap(await client.call_tool("clude_wiki_read", {"title": "Professor Plum", "section": "How he thinks"}))
        assert part["section"] == "How he thinks" and part["text"]
        gone = unwrap(await client.call_tool("clude_wiki_read", {"title": "The Butler"}))
        assert gone["error"].startswith("There is no article") and "matches" in gone


@pytest.mark.skipif(
    not os.environ.get("CLUDE_LLM_LIVE"),
    reason="set CLUDE_LLM_LIVE=1 (with ANTHROPIC_API_KEY or an `ant auth login` profile) to call the API",
)
def test_the_loop_live_smoke():
    """One real decision that is told to read the canon first: a lookup
    is made and answered, and the reply is still in schema. Costs a few
    cents; the acceptance step 5.2 of docs/canon-plan.md is a whole game."""
    from clude_llm import load_persona, load_rules, system_prompt
    from clude_llm.backend import DEFAULT_MODEL

    backend = AnthropicBackend(os.environ.get("CLUDE_LLM_MODEL", DEFAULT_MODEL))
    canon = WikiCanon()
    user = (
        "You are Professor Plum, seat P0 Plum. Turn 1.\n"
        "Before you choose, read the canon's article on the leash (wiki_read, title Leash) and let it inform you.\n"
        "Decision: where to move.\n"
        "Options (best first by your method's score; choose one letter):\n"
        "  A. enter the Library -- score 0.60; a suggestion there this turn\n"
        "  B. enter the Study -- score 0.40; a suggestion there this turn\n"
        'Answer with JSON only: {"choice": "<letter>", "say": "<one short line in your voice, or an empty string>"}\n'
    )
    request = LLMRequest(
        system_prompt(load_persona("Plum"), load_rules()), user, CHOICE_SCHEMA, "move",
        canon=canon.index(), tools=canon.tools, lookup=canon.lookup, max_lookups=3,
    )
    result = backend.complete(request)
    assert result.ok, result.error
    assert json.loads(result.text)["choice"] in ("A", "B")
    assert result.lookups and result.lookups[0]["tool"] in (WIKI_READ, WIKI_SEARCH), result.lookups
    assert not any(lookup["error"] for lookup in result.lookups)


def test_the_prompt_command_shows_the_index_and_the_tools():
    out = subprocess.run(
        [sys.executable, str(CLI_SCRIPT), "prompt", "--players", "3", "--seed", "1", "--roster", "floor",
         "--agent", "Plum", "--decision", "move", "--roll", "6"],
        capture_output=True, text=True, check=True, cwd=Path(CLI_SCRIPT).parents[1],
    ).stdout
    assert "=== canon (" in out and "tools offered on every call: wiki_search, wiki_read" in out
    assert INDEX_HEAD in out and "## The canon" in out
    assert out.index("=== system") < out.index("=== canon") < out.index("=== user")
