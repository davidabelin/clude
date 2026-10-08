"""LLMCharacter: legal model choices and voice around a numerical Character.

Build a leashed menu; ask only when choices exist and budget permits.
Allowed replies play, remarks pass chattiness, and failures fall back using
the numerical character's RNG path. Decisions audit choices/fallbacks and
usage. NullBackend reproduces numerical play.

Attached logbooks render a stable memory block at new_game and can receive
a post-game debrief. Off-turn react calls produce talk, not engine actions.
condense_logbook asks a character's model, outside any game, to fold its
logbook into a digest. See docs/llm-wrapper.md and docs/logbooks.md for
lifecycle/contracts.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from random import Random
from typing import Any, Optional

from clude_agents.character import Character
from clude_core.events import RemarkEvent
from clude_core.state import ClueObservation
from clude_storage.logbooks import LogbookDigest, LogbookEntry, clean_flag_map

from .backend import DEFAULT_MODEL, LLMBackend, LLMRequest, LLMResult
from .logbook import condense_prompt, debrief_prompt, opponents_of, resolve_opponents
from .menu import EPS, accusation_menu, movement_menu, show_menu, suggestion_menu
from .persona import Persona, load_persona, load_rules
from .prompt import remark_prompt, system_prompt, user_prompt
from .schema import CONDENSE_KIND, LOGBOOK_KIND, REMARK_KIND, parse_response, schema_for

TRANSCRIPT_LIMIT = 200

CONDENSE_MAX_TOKENS = 8192
"""Room for the condensing reply: up to ten themes and an overview, after
the model's thinking on a long prompt."""


@dataclass(frozen=True)
class LLMSettings:
    """Everything about the wrapper that is not a personality dial.

    Parameters
    ----------
    model, effort, max_tokens, timeout
        Passed to the Anthropic backend (6c).
    max_calls_per_game, max_tokens_per_game
        Budget; past either, every decision falls back for the rest of
        the game (`new_game` resets the counters).
    recent_remarks : int
        How many lines of table talk the prompt shows.
    speak : bool
        False silences the character entirely (choices still count).
    server_fallbacks : bool
        Enable the API's server-side refusal fallbacks (6c).
    debrief : bool
        Write a logbook entry after each game when a logbook is attached
       ; False skips the call.
    debrief_effort, debrief_max_tokens, debrief_timeout
        The debrief's own effort, room and patience: a reflective task,
        unlike a move, gets ``medium``, 4096 tokens and 180 s by default
        (at medium effort it runs 40-90 s, past a move's 30 s).
    remark_max_tokens
        Room for an off-turn line: one short sentence.
    """

    model: str = DEFAULT_MODEL
    effort: str = "low"
    max_tokens: int = 2048
    timeout: float = 30.0
    max_calls_per_game: int = 200
    max_tokens_per_game: int = 500_000
    recent_remarks: int = 8
    speak: bool = True
    server_fallbacks: bool = True
    debrief: bool = True
    debrief_effort: str = "medium"
    debrief_max_tokens: int = 4096
    debrief_timeout: float = 180.0
    remark_max_tokens: int = 200

    def to_dict(self) -> dict:
        return dict(vars(self))


@dataclass
class Decision:
    """The audit record of one decision.

    `called` says whether the backend was asked (a single-option menu is
    not a call). `fallback` is None when the LLM's choice was played,
    else why not: ``budget``, ``refusal``, ``error: ...``, ``malformed:
    ...``, ``unknown_label`` or ``not_allowed``. `deviated` means the
    played choice scored below the character's top option (for the
    accusation, differed from its threshold answer). `said` is the line
    the model offered; `spoke` whether `chattiness` let it through.
    """

    turn: int
    kind: str
    called: bool
    chosen: Optional[str]
    action: str
    fallback: Optional[str]
    deviated: bool
    said: str
    spoke: bool
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    seconds: float = 0.0
    menu: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return dict(vars(self))


class LLMCharacter:
    """A `Character` with an LLM choosing within its leash.

    Parameters
    ----------
    character : Character
        The headless character: its method, dials and confidence.
    backend : LLMBackend
    persona : Persona or None
        Default `load_persona(character.name)`.
    settings : LLMSettings or None
    rules : str or None
        The standing rules text; default `load_rules()`.

    Notes
    -----
    Table talk the model offers is published with probability
    `profile.chattiness`, drawn from the wrapper's own RNG (seeded from
    `reset`'s seed, a stream separate from the character's), so the
    character's RNG is consumed only where the headless character would
    consume it.
    """

    def __init__(
        self,
        character: Character,
        backend: LLMBackend,
        persona: Optional[Persona] = None,
        settings: Optional[LLMSettings] = None,
        rules: Optional[str] = None,
    ) -> None:
        self.character = character
        self.backend = backend
        self.persona = persona if persona is not None else load_persona(character.name)
        self.rules = rules if rules is not None else load_rules()
        self.settings = settings if settings is not None else LLMSettings()
        self.name = character.name
        self.rng = Random()
        self._system = system_prompt(self.persona, self.rules)
        self._pending: list = []
        self.transcript: list = []
        self.decisions: list = []
        self.table: list = []
        self.logbook = None
        self.memory_block = ""
        self.entries_written = 0
        self.last_debrief: dict = {}
        self.llm_calls = 0
        self.llm_seconds = 0.0
        self.input_tokens = 0
        self.output_tokens = 0
        self.cached_tokens = 0
        self.singles = 0
        self.played = 0
        self.fallbacks = 0
        self.deviations = 0
        self.remarks_made = 0
        self.game_calls = 0
        self.game_tokens = 0

    # -- the character's surface, delegated -------------------------------

    @property
    def profile(self):
        return self.character.profile

    @property
    def agent(self):
        return self.character.agent

    @property
    def confidence_fn(self):
        return self.character.confidence_fn

    @property
    def n_calls(self) -> int:
        return self.character.n_calls

    @property
    def seconds(self) -> float:
        return self.character.seconds

    @property
    def last_triple(self):
        return self.character.last_triple

    @property
    def last_confidence(self) -> float:
        return self.character.last_confidence

    def select_action(self, obs: ClueObservation):
        """The character's belief (cached per observation, as always)."""
        return self.character.select_action(obs)

    def reset(self, seed: "int | None") -> None:
        """Reset the character, seed the wrapper's own RNG, start a game."""
        self.character.reset(seed)
        self.rng.seed(None if seed is None else f"clude_llm:{seed}")
        self.new_game()

    def new_game(self, table=None) -> None:
        """Clear the transcript, the audit and the per-game budget, and
        pass `table` (roster labels by seat, Phase 7) to the character;
        the arena calls this before every game (the totals keep
        accumulating)."""
        self.transcript = []
        self._pending = []
        self.decisions = []
        self.table = list(table) if table is not None else []
        self.game_calls = 0
        self.game_tokens = 0
        self.character.new_game(table)
        self.memory_block = self.read_back()

    def observe(self, transition: Any) -> None:
        self.character.observe(transition)

    def system_prompt(self) -> str:
        return self._system

    # -- the logbook (Phase 7c) ---------------------------------------------

    def attach_logbook(self, logbook) -> None:
        """Give the character its `Logbook`: read back at each `new_game`
        at the `memory` dial's depth, written by `debrief`."""
        self.logbook = logbook
        self.memory_block = self.read_back()

    def read_back(self) -> str:
        """The memory block for the current table: the logbook rendered
        at `profile.memory`, with the dossiers of the opponents present
        (every dossier when no table is known); empty with no logbook."""
        if self.logbook is None:
            return ""
        return self.logbook.memory(self.profile.memory, opponents_of(self.table, self.name))

    def debrief(self, record, seat: int) -> Optional[LogbookEntry]:
        """After a game, ask the model for this game's logbook entry and
        store it. Returns the entry, or None when no logbook is attached,
        `settings.debrief` is off, or the call failed (the reason is in
        `last_debrief`, as a decision's fallback would be). Tokens count
        toward the game just played; call before `new_game`. Draws no
        random numbers.

        Parameters
        ----------
        record : GameRecord
            The finished game, omniscient.
        seat : int
            The seat this character occupied.
        """
        if self.logbook is None:
            self.last_debrief = {"called": False, "fallback": "no logbook"}
            return None
        if not self.settings.debrief:
            self.last_debrief = {"called": False, "fallback": "debrief off"}
            return None
        head = self.logbook.head()
        digest = self.logbook.digest()
        entries = self.logbook.entries(after=digest.through if digest is not None else 0)
        request = LLMRequest(
            system=self._system,
            user=debrief_prompt(record, seat, self.character, self.decisions, head, entries, digest),
            schema=schema_for(LOGBOOK_KIND),
            kind=LOGBOOK_KIND,
            effort=self.settings.debrief_effort,
            max_tokens=self.settings.debrief_max_tokens,
            timeout=self.settings.debrief_timeout,
        )
        started = time.perf_counter()
        try:
            result = self.backend.complete(request)
        except Exception as exc:  # any backend failure means no entry, never a crash
            result = LLMResult(error=f"{type(exc).__name__}: {exc}")
        if not result.seconds:
            result.seconds = time.perf_counter() - started
        self._account(result)
        cost = {
            "input_tokens": result.input_tokens, "output_tokens": result.output_tokens,
            "cached_tokens": result.cached_tokens, "seconds": result.seconds,
        }
        if not result.ok:
            reason = "refusal" if result.stop_reason == "refusal" else (
                f"error: {result.error or result.stop_reason or 'empty reply'}"
            )
            self.last_debrief = {"called": True, "fallback": reason, **cost}
            return None
        try:
            written = parse_response(LOGBOOK_KIND, result.text)
        except ValueError as exc:
            self.last_debrief = {"called": True, "fallback": f"malformed: {exc}", **cost}
            return None
        entry = LogbookEntry.build(
            self.logbook.identity, self.logbook.next_serial(), record, seat,
            resolve_opponents(written, record, seat), model=result.model or self.settings.model,
        )
        self.logbook.add_entry(entry)
        self.entries_written += 1
        self.last_debrief = {"called": True, "fallback": None, "serial": entry.serial, **cost}
        return entry

    # -- off-turn talk (Phase 8.3b) -------------------------------------------

    def react(self, obs: ClueObservation, trigger: str, names=None) -> Optional[str]:
        """One off-turn line, or None for silence: the model is shown the
        seat's view and what just happened (`remark_prompt`) and asked for
        a line or an empty string. Audited as a `Decision` of kind
        ``remark``; counts toward the game's call and token budget; falls
        silent, never crashes, on any failure. Whether to ask at all -- the
        chattiness draw -- is the caller's, so the wrapper's own RNG is
        consumed exactly where the caller says.

        Parameters
        ----------
        obs : ClueObservation
            This seat's masked view now.
        trigger : str
            What opened the floor, in words.
        names : Sequence[str] or None
            A label per seat, as `user_prompt` takes.
        """
        base = {"turn": obs.turn, "kind": REMARK_KIND, "menu": {}}
        if (self.game_calls >= self.settings.max_calls_per_game
                or self.game_tokens >= self.settings.max_tokens_per_game):
            self.fallbacks += 1
            self._record(Decision(called=False, chosen=None, action="", fallback="budget",
                                  deviated=False, said="", spoke=False, **base))
            return None
        request = LLMRequest(
            system=self._system,
            user=remark_prompt(
                obs, self.character.select_action(obs), self.character, self.transcript, trigger,
                names=names, recent_remarks=self.settings.recent_remarks,
            ),
            schema=schema_for(REMARK_KIND),
            kind=REMARK_KIND,
            memory=self.memory_block,
            max_tokens=self.settings.remark_max_tokens,
        )
        started = time.perf_counter()
        try:
            result = self.backend.complete(request)
        except Exception as exc:  # any backend failure is silence, never a crash
            result = LLMResult(error=f"{type(exc).__name__}: {exc}")
        if not result.seconds:
            result.seconds = time.perf_counter() - started
        self._account(result)
        cost = {
            "input_tokens": result.input_tokens, "output_tokens": result.output_tokens,
            "cached_tokens": result.cached_tokens, "seconds": result.seconds,
        }
        if not result.ok:
            reason = "refusal" if result.stop_reason == "refusal" else (
                f"error: {result.error or result.stop_reason or 'empty reply'}"
            )
            self.fallbacks += 1
            self._record(Decision(called=True, chosen=None, action="", fallback=reason,
                                  deviated=False, said="", spoke=False, **cost, **base))
            return None
        try:
            say = parse_response(REMARK_KIND, result.text)["say"]
        except ValueError as exc:
            self.fallbacks += 1
            self._record(Decision(called=True, chosen=None, action="", fallback=f"malformed: {exc}",
                                  deviated=False, said="", spoke=False, **cost, **base))
            return None
        if say and self.settings.speak:
            self._remember(obs.my_index, say)
            self.remarks_made += 1
        self._record(Decision(called=True, chosen=None, action="", fallback=None, deviated=False,
                              said=say, spoke=bool(say and self.settings.speak), **cost, **base))
        return say if say and self.settings.speak else None

    # -- SpeakingPlayer ------------------------------------------------------

    def take_remarks(self) -> list:
        out, self._pending = self._pending, []
        return out

    def hear(self, remark: RemarkEvent) -> None:
        self._remember(remark.seat, remark.text)

    def _remember(self, seat: int, text: str) -> None:
        self.transcript.append((seat, text))
        if len(self.transcript) > TRANSCRIPT_LIMIT:
            del self.transcript[: len(self.transcript) - TRANSCRIPT_LIMIT]

    # -- PlayerProtocol ------------------------------------------------------

    def choose_movement(self, obs: ClueObservation, choices: list, rng: Random):
        option = self._decide(obs, movement_menu(self.character, obs, choices), "move")
        if option is None:
            return self.character.choose_movement(obs, choices, rng)
        return option.action

    def choose_suggestion(self, obs: ClueObservation, room: str, rng: Random) -> Optional[tuple]:
        picks = self._decide(obs, suggestion_menu(self.character, obs), "suggest")
        if picks is None:
            return self.character.choose_suggestion(obs, room, rng)
        return picks[0].action, picks[1].action

    def choose_accusation(self, obs: ClueObservation, rng: Random) -> Optional[tuple]:
        menu = accusation_menu(self.character, obs)
        option = self._decide(obs, menu, "accuse")
        if option is None:
            return self.character.choose_accusation(obs, rng)
        accuse = menu.options[0]
        self.character.last_triple, self.character.last_confidence = accuse.action, accuse.score
        return option.action

    def choose_card_to_show(
        self, obs: ClueObservation, candidates: list, shown_to: int, rng: Random
    ) -> str:
        option = self._decide(obs, show_menu(self.character, obs, candidates, shown_to), "show")
        if option is None:
            return self.character.choose_card_to_show(obs, candidates, shown_to, rng)
        return option.action

    # -- the one decision procedure -----------------------------------------

    def _decide(self, obs: ClueObservation, menu, kind: str):
        """Ask the backend if the menu leaves a choice; return the chosen
        `Option` (a pair for a suggestion), or None to fall back."""
        base = {"turn": obs.turn, "kind": kind, "menu": menu.to_dict()}
        single = menu.single()
        if single is not None:
            if kind == "suggest":
                chosen = f"{single[0].label}/{single[1].label}"
                action = f"{single[0].text}, {single[1].text}"
            else:
                chosen, action = single.label, single.text
            self.singles += 1
            self._record(Decision(called=False, chosen=chosen, action=action, fallback=None,
                                  deviated=False, said="", spoke=False, **base))
            return None
        if (self.game_calls >= self.settings.max_calls_per_game
                or self.game_tokens >= self.settings.max_tokens_per_game):
            self.fallbacks += 1
            self._record(Decision(called=False, chosen=None, action="", fallback="budget",
                                  deviated=False, said="", spoke=False, **base))
            return None

        request = LLMRequest(
            system=self._system,
            user=user_prompt(
                obs, self.character.select_action(obs), self.character, menu,
                self.transcript, recent_remarks=self.settings.recent_remarks,
            ),
            schema=schema_for(kind),
            kind=kind,
            memory=self.memory_block,
        )
        started = time.perf_counter()
        try:
            result = self.backend.complete(request)
        except Exception as exc:  # any backend failure is a fallback, never a crash
            result = LLMResult(error=f"{type(exc).__name__}: {exc}")
        if not result.seconds:
            result.seconds = time.perf_counter() - started
        self._account(result)
        cost = {
            "input_tokens": result.input_tokens, "output_tokens": result.output_tokens,
            "cached_tokens": result.cached_tokens, "seconds": result.seconds,
        }

        def fail(reason: str):
            self.fallbacks += 1
            self._record(Decision(called=True, chosen=None, action="", fallback=reason,
                                  deviated=False, said="", spoke=False, **cost, **base))
            return None

        if not result.ok:
            if result.stop_reason == "refusal":
                return fail("refusal")
            return fail(f"error: {result.error or result.stop_reason or 'empty reply'}")
        try:
            data = parse_response(kind, result.text)
        except ValueError as exc:
            return fail(f"malformed: {exc}")

        if kind == "suggest":
            picks = (menu.suspect.option(data["suspect"]), menu.weapon.option(data["weapon"]))
            if any(p is None for p in picks):
                return fail("unknown_label")
            if not all(p.allowed for p in picks):
                return fail("not_allowed")
            deviated = (picks[0].score < menu.suspect.top.score - EPS
                        or picks[1].score < menu.weapon.top.score - EPS)
            chosen = f"{picks[0].label}/{picks[1].label}"
            action = f"{picks[0].text}, {picks[1].text}"
            value: Any = picks
        else:
            option = menu.option(data["choice"])
            if option is None:
                return fail("unknown_label")
            if not option.allowed:
                return fail("not_allowed")
            if kind == "accuse":
                deviated = option is not menu.top
            else:
                deviated = option.score < menu.top.score - EPS
            chosen, action, value = option.label, option.text, option

        say = data["say"]
        spoke = False
        if say and self.settings.speak and self.rng.random() < self.profile.chattiness:
            self._pending.append(say)
            self._remember(obs.my_index, say)
            self.remarks_made += 1
            spoke = True
        if deviated:
            self.deviations += 1
        self.played += 1
        self._record(Decision(called=True, chosen=chosen, action=action, fallback=None,
                              deviated=deviated, said=say, spoke=spoke, **cost, **base))
        return value

    def _account(self, result: LLMResult) -> None:
        self.llm_calls += 1
        self.game_calls += 1
        self.llm_seconds += result.seconds
        self.input_tokens += result.input_tokens
        self.output_tokens += result.output_tokens
        self.cached_tokens += result.cached_tokens
        self.game_tokens += result.input_tokens + result.output_tokens

    def _record(self, decision: Decision) -> None:
        self.decisions.append(decision)

    def summary(self) -> dict:
        """Run totals, for the CLI trailer and the arena."""
        return {
            "backend": self.backend.name,
            "model": self.settings.model,
            "decisions": len(self.decisions),
            "singles": self.singles,
            "llm_calls": self.llm_calls,
            "played": self.played,
            "fallbacks": self.fallbacks,
            "deviations": self.deviations,
            "remarks": self.remarks_made,
            "entries": self.entries_written,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cached_tokens": self.cached_tokens,
            "llm_seconds": round(self.llm_seconds, 3),
        }


# ---------------------------------------------------------------------
# Condensing a logbook (outside any game)
# ---------------------------------------------------------------------


def condense_request(logbook, settings: Optional[LLMSettings] = None) -> Optional[tuple]:
    """The condensing call for `logbook`, without making it:
    ``(request, entries, previous)``, with the entries after the stored
    digest `previous` (None if there is none), or None when no entry is
    new. The system prompt is the character's own persona and rules, so
    the digest is written in its voice; effort and timeout are the
    debrief's."""
    settings = settings if settings is not None else LLMSettings()
    previous = logbook.digest()
    entries = logbook.entries(after=previous.through if previous is not None else 0)
    if not entries:
        return None
    request = LLMRequest(
        system=system_prompt(load_persona(logbook.identity), load_rules()),
        user=condense_prompt(logbook.identity, logbook.head(), previous, entries),
        schema=schema_for(CONDENSE_KIND),
        kind=CONDENSE_KIND,
        effort=settings.debrief_effort,
        max_tokens=CONDENSE_MAX_TOKENS,
        timeout=settings.debrief_timeout,
    )
    return request, entries, previous


def condense_logbook(logbook, backend: LLMBackend, settings: Optional[LLMSettings] = None) -> dict:
    """Ask the identity's model to condense its logbook, and store what it
    wrote: the flag merges through every entry and the index
    (`Logbook.rename_flags`), then the new digest. The digest is written
    last, so a run cut short leaves a consistent logbook that a rerun
    completes. A backend error, refusal, or malformed or empty reply
    writes nothing. Draws no random numbers.

    Returns
    -------
    dict
        ``called`` and ``fallback`` (None on success, else why nothing was
        written), as a debrief reports; when a call was made, its token
        counts, ``seconds`` and ``model``; on success also ``through``,
        ``themes``, ``merged`` (flags retired) and ``entries_renamed``.
    """
    settings = settings if settings is not None else LLMSettings()
    prepared = condense_request(logbook, settings)
    if prepared is None:
        return {"called": False, "fallback": "nothing new"}
    request, entries, previous = prepared
    started = time.perf_counter()
    try:
        result = backend.complete(request)
    except Exception as exc:  # any backend failure means no digest, never a crash
        result = LLMResult(error=f"{type(exc).__name__}: {exc}")
    report = {
        "called": True,
        "fallback": None,
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
        "cached_tokens": result.cached_tokens,
        "seconds": result.seconds or time.perf_counter() - started,
        "model": result.model or settings.model,
    }
    if not result.ok:
        report["fallback"] = "refusal" if result.stop_reason == "refusal" else (
            f"error: {result.error or result.stop_reason or 'empty reply'}"
        )
        return report
    try:
        written = parse_response(CONDENSE_KIND, result.text)
        known = set(logbook.head().flags) | {flag for entry in entries for flag in entry.flags}
        mapping = clean_flag_map(written.get("flag_map"), known)
        digest = LogbookDigest.build(
            logbook.identity, entries[-1].serial, written, mapping, previous, model=report["model"],
        )
    except ValueError as exc:
        report["fallback"] = f"malformed: {exc}"
        return report
    renamed = logbook.rename_flags(mapping)
    logbook.save_digest(digest)
    report.update(
        through=digest.through, themes=len(digest.themes),
        merged=renamed["flags"], entries_renamed=renamed["entries"],
    )
    return report
