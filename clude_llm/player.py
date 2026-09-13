"""`LLMCharacter`: an LLM piloting a `Character` (Phase 6b).

For each of the four engine decisions the wrapper builds the character's
leashed menu (`menu.py`), and if more than one option is allowed asks the
backend for a choice and a line of table talk, under a per-game budget.
A reply that names an allowed option is played and the line is buffered
for the engine (`take_remarks`), gated by `chattiness`. Anything else --
a single-option menu, the budget, a backend error or timeout, a refusal,
malformed JSON, an unknown or disallowed letter -- falls back to the
wrapped character's own method, which then draws from the character's
RNG exactly as it would have headless. A backend that never answers
(`NullBackend`) therefore reproduces the headless game byte for byte;
the tests pin that. Every decision is recorded as a `Decision`, the
audit trail the arena's columns and Phase 7's logbooks read.

`LLMCharacter` implements `PlayerProtocol` and `SpeakingPlayer`, and the
duck-typed surface the arena and trace rely on (`name`, `profile`,
`select_action`, `reset`, `observe`, `n_calls`, `seconds`).
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from random import Random
from typing import Any, Optional

from clude_agents.character import Character
from clude_core.events import RemarkEvent
from clude_core.state import ClueObservation

from .backend import DEFAULT_MODEL, LLMBackend, LLMRequest, LLMResult
from .menu import EPS, accusation_menu, movement_menu, show_menu, suggestion_menu
from .persona import Persona, load_persona, load_rules
from .prompt import system_prompt, user_prompt
from .schema import parse_response, schema_for

TRANSCRIPT_LIMIT = 200


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

    def new_game(self) -> None:
        """Clear the transcript, the audit and the per-game budget; the
        arena calls this between games (the totals keep accumulating)."""
        self.transcript = []
        self._pending = []
        self.decisions = []
        self.game_calls = 0
        self.game_tokens = 0

    def observe(self, transition: Any) -> None:
        self.character.observe(transition)

    def system_prompt(self) -> str:
        return self._system

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
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cached_tokens": self.cached_tokens,
            "llm_seconds": round(self.llm_seconds, 3),
        }
