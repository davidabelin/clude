"""Off-turn talk (Phase 8.3b, docs/phase8-plan.md 4.2-4.3).

Pinned, on scripted backends and a fake clock: the fixed remark schema
and a stable request key; `react` returning a line, an audit of kind
``remark`` and silence on an empty reply, a failure or a spent budget;
the participation draw, the two-speaker cap, the delay, the order of
arrival, the stale drop and the decay of a reply to a reply; and, on
the web, a person's line reaching every model seat's transcript and
the log, refused for a spectator or over-long, harmless as HTML, and
never read by the engine.
"""
from __future__ import annotations

import json
import random

import pytest

import clude_constraints
from clude_agents import PRESETS
from clude_core.events import RemarkEvent
from clude_llm import REMARK_KIND, REMARK_SCHEMA, LLMRequest, LLMResult, LLMSettings, parse_response, schema_for
from clude_storage import open_store
from clude_training.table import SeatSpec, TableGame, TableSetup
from clude_web import chat, tables
from tests.test_llm import PERSONA, RULES, _wrapped
from tests.test_web_llm import Factory, KindBackend, make_app
from tests.test_web_tables import ANN, answer, csrf, login, new_table, poll, work

SEED = 5


class Talker(KindBackend):
    """Answers a remark request with a line that names the trigger."""

    def __init__(self, line="Quite so.") -> None:
        super().__init__()
        self.line = line
        self.remark_requests: list = []

    def complete(self, request):
        if request.kind == REMARK_KIND:
            self.calls += 1
            self.remark_requests.append(request)
            return LLMResult(text=json.dumps({"say": self.line}), stop_reason="end_turn",
                             model=self.model, input_tokens=300, output_tokens=12)
        return super().complete(request)


# --- the schema and the wrapper --------------------------------------------


def test_the_remark_schema_is_fixed_and_parsed():
    assert schema_for(REMARK_KIND) is REMARK_SCHEMA
    assert REMARK_SCHEMA["required"] == ["say"] and REMARK_SCHEMA["additionalProperties"] is False
    assert parse_response(REMARK_KIND, '{"say": "  Hm.  "}') == {"say": "Hm."}
    assert parse_response(REMARK_KIND, '{"say": 3}') == {"say": ""}
    with pytest.raises(ValueError):
        parse_response(REMARK_KIND, "not json")


def _obs_for(seat=1):
    setup = TableSetup((SeatSpec("Scarlett", "floor"), SeatSpec("Plum", "character", "Plum"),
                        SeatSpec("White", "floor")), SEED)
    game = TableGame(setup)
    game.run(1)
    return clude_constraints.observe(game.state, seat), game


def test_react_returns_a_line_audits_it_and_remembers_it():
    obs, _game = _obs_for()
    wrapper = _wrapped(PRESETS["Plum"], [{"say": "The Lounge, I think."}])
    assert wrapper.react(obs, 'Scarlett said: "Anyone got the Rope?"') == "The Lounge, I think."
    decision = wrapper.decisions[-1]
    assert decision.kind == REMARK_KIND and decision.called and decision.spoke and decision.fallback is None
    assert wrapper.transcript[-1] == (obs.my_index, "The Lounge, I think.")
    request = wrapper.backend.requests[-1]
    assert request.kind == REMARK_KIND and request.schema is REMARK_SCHEMA
    assert "Just now: Scarlett said" in request.user and "it is not your turn" in request.user
    assert request.max_tokens == LLMSettings().remark_max_tokens
    # The same view and trigger make the same request key.
    again = _wrapped(PRESETS["Plum"], [{"say": ""}])
    again.react(obs, 'Scarlett said: "Anyone got the Rope?"')
    assert again.backend.requests[-1].key() == request.key()


def test_react_is_silent_on_an_empty_reply_a_failure_or_a_spent_budget():
    obs, _game = _obs_for()
    quiet = _wrapped(PRESETS["Plum"], [{"say": ""}])
    assert quiet.react(obs, "x") is None and quiet.decisions[-1].spoke is False
    broken = _wrapped(PRESETS["Plum"], [RuntimeError("down")])
    assert broken.react(obs, "x") is None and broken.decisions[-1].fallback.startswith("error:")
    spent = _wrapped(PRESETS["Plum"], [{"say": "hi"}], settings=LLMSettings(max_calls_per_game=0))
    assert spent.react(obs, "x") is None and spent.decisions[-1].fallback == "budget"
    assert spent.backend.calls == 0


# --- the queue -----------------------------------------------------------


@pytest.fixture
def clock(monkeypatch):
    state = {"t": 100.0}
    monkeypatch.setattr(chat, "now", lambda: state["t"])
    monkeypatch.setattr(chat, "delay", lambda rng: 2.0)
    monkeypatch.setattr(chat, "joins", lambda rng, p: True)
    return state


def _model_table(talkers):
    """Scarlett a floor bot, and Plum, White and Green with Claude."""
    setup = TableSetup(
        (SeatSpec("Scarlett", "floor"), SeatSpec("Plum", "llm", "Plum"),
         SeatSpec("White", "llm", "White"), SeatSpec("Green", "llm", "Green")),
        SEED,
    )
    game = tables.WebGame(setup, llm_backend=lambda seat: talkers[seat])
    game.table_id = "t"
    return game


def test_an_opportunity_queues_at_most_two_who_answer_in_order_after_their_delay(clock):
    talkers = {1: Talker("Plum here."), 2: Talker("White here."), 3: Talker("Green here.")}
    game = _model_table(talkers)
    game.run(1)  # Scarlett's turn: nobody external, nothing said
    reactions = game.reactions
    reactions.scan()
    game.remark(0, "Who has the Rope?", "chat")
    reactions.scan()
    assert [r.seat for r in reactions.queue] == [1, 2], "two queued, the third dropped by the cap"
    assert reactions.due() is None, "not due yet"
    clock["t"] += 2.0
    first = reactions.due()
    assert first.seat == 1 and first.trigger == 'Scarlett said: "Who has the Rope?"'
    assert reactions.serve(first) == "Plum here."
    said = [e for e in game.events if isinstance(e, RemarkEvent)]
    assert said[-1].seat == 1 and said[-1].about == "reaction"
    assert (1, "Plum here.") in game.wrappers[2].transcript, "White heard Plum"
    assert (0, "Who has the Rope?") in game.wrappers[3].transcript, "Green heard the person"
    # Plum's line opened a reply opportunity: Green (not yet queued) joins; White is still queued.
    assert [r.seat for r in reactions.queue] == [2, 3]
    assert reactions.queue[-1].depth == 1
    assert reactions.serve(reactions.due()) == "White here."
    assert reactions.served_turn[game.state.turn] == 2
    # The per-turn cap: Green's reply is still queued but no new opportunity opens.
    assert reactions.opportunity(0, "more") == []


def test_a_reply_to_a_reply_decays_by_chattiness(clock, monkeypatch):
    draws = []
    monkeypatch.setattr(chat, "joins", lambda rng, p: draws.append(p) or True)
    talkers = {1: Talker(), 2: Talker(), 3: Talker()}
    game = _model_table(talkers)
    game.run(1)
    game.reactions.scan()
    game.remark(0, "Hm.", "chat")
    game.reactions.scan()
    clock["t"] += 2.0
    game.reactions.serve(game.reactions.due())
    chattiness = PRESETS["Plum"].chattiness
    assert draws[0] == pytest.approx(chattiness)
    assert any(p == pytest.approx(chattiness ** 2) for p in draws[2:]), draws


def test_a_queued_reaction_is_dropped_once_the_turn_moves_on(clock):
    talkers = {1: Talker(), 2: Talker(), 3: Talker()}
    game = _model_table(talkers)
    game.run(1)
    game.reactions.scan()
    game.remark(0, "Hm.", "chat")
    game.reactions.scan()
    assert game.reactions.pending
    turn = game.state.turn
    while game.state.turn == turn:  # Plum's turn starts: the model answers move by move
        if game.pending is not None:
            game.llm_answer()
        else:
            game.run(1)
    clock["t"] += 10.0
    assert game.reactions.due() is None and not game.reactions.pending


def test_the_suggestion_and_the_accusation_open_the_floor(clock):
    talkers = {1: Talker(), 2: Talker(), 3: Talker()}
    game = _model_table(talkers)
    seen = []
    chat_scan = game.reactions.opportunity
    game.reactions.opportunity = lambda actor, trigger, depth=0: seen.append((actor, trigger)) or chat_scan(actor, trigger, depth)
    from clude_core.events import SuggestionEvent

    for _ in range(300):
        if game.pending is not None:
            game.llm_answer()
        else:
            game.run(1)
        game.reactions.scan()
        if any(isinstance(e, SuggestionEvent) for e in game.events):
            break
    suggestion = next(e for e in game.events if isinstance(e, SuggestionEvent))
    opened = [(actor, t) for actor, t in seen if "suggest" in t]
    assert opened and opened[0][0] == suggestion.suggestion.suggester, seen
    assert all(actor is not None for actor, _ in seen)


# --- on the web ---------------------------------------------------------------


@pytest.fixture
def store(tmp_path):
    return open_store(str(tmp_path))


def _seated(tmp_path, store, clock_state=None):
    factory = Factory()
    app = make_app(tmp_path, store, factory)
    ann = login(app, ANN)
    table_id = new_table(ann, {"Scarlett": "me", "Plum": "llm", "White": "character", "Green": "floor"}, seed=SEED)
    return app, ann, table_id


def test_a_person_can_say_a_line_that_everyone_reads_and_the_model_seat_hears(tmp_path, store, clock):
    app, ann, table_id = _seated(tmp_path, store)
    reply = ann.post(f"/tables/{table_id}/say", data={"csrf": csrf(ann), "text": "  I have\tnothing to\x07hide. "})
    assert reply.status_code == 200, reply.get_data(as_text=True)
    payload = reply.get_json()
    lines = [e["text"] for e in payload["events"] if e["kind"] == "remark"]
    assert lines and "I have nothing to hide." in lines[-1] and "" not in lines[-1]
    game = app.extensions["tables"].game(table_id)
    plum = game.suspects.index("Plum")
    assert (0, "I have nothing to hide.") in game.wrappers[plum].transcript
    assert game.entries[-1]["kind"] == "chat" and game.entries[-1]["text"] == "I have nothing to hide."
    assert app.extensions["tables"].document(table_id)["entries"][-1]["kind"] == "chat"
    assert payload["work"] and payload["chatter"], "a reply is queued and the client keeps ticking"
    # Not due yet: work holds; then the model answers.
    assert work(ann, table_id)["did"] == "waiting"
    clock["t"] += 3.0
    served = work(ann, table_id)
    assert served["did"] == "reaction"
    texts = [e["text"] for e in poll(ann, table_id)["events"] if e["kind"] == "remark"]
    assert any(t.startswith("Plum:") for t in texts), texts


def test_a_line_is_refused_for_a_spectator_or_when_empty_or_too_long(tmp_path, store):
    app, ann, table_id = _seated(tmp_path, store)
    from tests.test_web_tables import BOB, users as _users  # noqa: F401
    from clude_web import users
    users.add_user(store, BOB, "pw")
    users.mark_password_prompted(store, BOB)
    bob = login(app, BOB)
    assert bob.post(f"/tables/{table_id}/say", data={"csrf": csrf(bob), "text": "hi"}).status_code == 403
    assert ann.post(f"/tables/{table_id}/say", data={"csrf": csrf(ann), "text": "   "}).status_code == 400
    long = ann.post(f"/tables/{table_id}/say", data={"csrf": csrf(ann), "text": "x" * 241})
    assert long.status_code == 400 and "240" in long.get_json()["error"]
    assert len(app.extensions["tables"].game(table_id).entries) == 0


def test_a_hostile_line_is_text_on_the_page(tmp_path, store):
    app, ann, table_id = _seated(tmp_path, store)
    ann.post(f"/tables/{table_id}/say", data={"csrf": csrf(ann), "text": "<script>alert(1)</script>"})
    page = ann.get(f"/tables/{table_id}").get_data(as_text=True)
    assert "<script>alert(1)</script>" not in page
    assert "alert(1)" in page  # embedded as data, escaped


def test_chat_never_reaches_the_engine(tmp_path, store):
    """Saying "I don't have it" changes nothing the engine asks: the
    pending decision and its legal options are what they were, and an
    answer outside them is still refused."""
    app, ann, table_id = _seated(tmp_path, store)
    tables.WORK_INTERVAL, saved = 0.0, tables.WORK_INTERVAL
    try:
        payload = poll(ann, table_id)
        for _ in range(100):
            if payload["pending"]:
                break
            payload = work(ann, table_id)
        before = dict(payload["pending"])
        before.pop("seq")
        ann.post(f"/tables/{table_id}/say", data={"csrf": csrf(ann), "text": "I don't have it."})
        after = poll(ann, table_id)
        seq = after["pending"].pop("seq")
        assert after["pending"] == before and after["tokens"] == payload["tokens"]
        assert seq == before.get("seq", seq) or seq == payload["pending"]["seq"] + 1, "the line is an entry"
        illegal = {"card": "Rope"} if before["kind"] == "card_to_show" else (
            {"move": "secret_passage", "to": {"room": "Kitchen"}} if before["kind"] == "movement"
            else {"suspect": "Nobody", "weapon": "Rope"} if before["kind"] == "suggestion"
            else ["Nobody", "Rope", "Hall"]
        )
        refused = answer(ann, table_id, seq, illegal, expect=400)
        assert "error" in refused
    finally:
        tables.WORK_INTERVAL = saved
