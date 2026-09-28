"""Build the Phase 10a artboards: docs/ux/table/ and docs/ux/logo/.

    .venv\\Scripts\\python.exe docs\\ux\\build_sketches.py

Writes one ``.dc.html`` per artboard, a ``canvas.json`` per canvas in
the shape of docs/ux/replay/, and an ``index.html`` contact sheet per
canvas that lays the artboards out with their notes in any browser.
The artboards link docs/ux/table/engraved-sketch.css, the draft of
Phase 10b's stylesheet, and take the four faces from Google Fonts.

Everything factual comes from `sketch_parts`: seed 7007 with David at
Scarlett, stopped after fourteen turns and again at its end. The table
talk is the one thing made up, since no model plays here; it is marked
as such in the canvas notes.
"""
from __future__ import annotations

import json
import sys
from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sketch_parts as parts  # noqa: E402

TABLE = HERE / "table"
LOGO = HERE / "logo"
SEED = 7007
FONTS = (
    "https://fonts.googleapis.com/css2?family=Bodoni+Moda:ital,opsz,wght@0,6..96,400..900;1,6..96,400..900"
    "&family=Playfair+Display:ital,wght@0,400..900;1,400..900&family=Inter:wght@400..700"
    "&family=IBM+Plex+Mono:wght@400;500&display=swap"
)
METHODS = {
    "Scarlett": "Naive Bayes over suggestion evidence",
    "Mustard": "Decision tree trained on self-play game logs",
    "White": "Markov model over opponents' suggestion patterns",
    "Green": "Bandit ensemble over the other five methods",
    "Peacock": "Dempster-Shafer belief and plausibility",
    "Plum": "Exact enumeration over consistent deals",
}
# The story the artboards tell about who sits where: David at Scarlett,
# Peacock and Plum with Claude, the rest their silent methods. The game
# itself was played by the methods alone.
STORY_KINDS = {"Scarlett": "you", "Mustard": "headless", "White": "headless", "Green": "headless", "Peacock": "LLM", "Plum": "LLM"}
COST_SHARE = {"Peacock": 0.31, "Plum": 0.69}
SUSPECT_COLOUR = {s: f"var(--suspect-{s.lower()})" for s in parts.INITIALS}


def card(name: str) -> str:
    return name.replace("_", " ")


# --- page scaffolding -----------------------------------------------------


def page(body: str, css: str, theme: str, title: str) -> str:
    bg = "#E9E2D3" if theme == "light" else "#121013"
    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>{escape(title)}</title>
  <script src="./support.js"></script>
</head>
<body>
<x-dc>
<helmet>
  <link href="{FONTS}" rel="stylesheet">
  <link href="{css}" rel="stylesheet">
  <style>body {{ margin: 0; background: {bg}; }}</style>
</helmet>
{body}
</x-dc>
</body>
</html>
"""


def screen(inner: str, theme: str = "dark", focus: str = "", wide: bool = False, style: str = "") -> str:
    cls = "screen wide" if wide else "screen"
    attrs = f' data-theme="{theme}"' + (f' data-focus="{focus}"' if focus else "") + (f' style="{style}"' if style else "")
    return f'<div class="{cls}"{attrs}>\n{inner}\n</div>'


def bar(logo: str = "A", user: str = "David") -> str:
    mark = parts.logo_svg(logo, 120, 168, 22, mark_only=True)
    return (
        '<header class="bar">'
        f'<a class="mark" href="#" style="display:flex;align-items:center;gap:6px">{mark}<span>clude</span></a>'
        '<div class="bar-right">'
        '<span class="select">Engraved</span>'
        f'<span class="who">{user}</span>'
        '<span class="quiet">Sign out</span>'
        "</div></header>"
    )


def status(text: str, cls: str = "", clock: str = "") -> str:
    clock_html = f'<span class="clock">{clock}</span>' if clock else ""
    return f'<p class="status {cls}" aria-live="polite">{text}{clock_html}</p>'


def stage(svg: str, cls: str = "", over: str = "") -> str:
    return f'<section class="stage {cls}">{svg}{over}</section>'


def plate(inner: str, cls: str = "") -> str:
    rivets = "".join(f'<span class="rivet {c}"></span>' for c in ("tl", "tr", "bl", "br"))
    return f'<div class="plate {cls}">{rivets}{inner}</div>'


def beat(text: str, kicker: str, speaker: str = "", cls: str = "") -> str:
    style = f' style="--speaker: {SUSPECT_COLOUR[speaker]}"' if speaker else ""
    return f'<p class="beat {cls}"{style}><span class="turn">{kicker}</span>{text}</p>'


def choice(text: str, small: str = "", cls: str = "") -> str:
    tail = f"<small>{small}</small>" if small else ""
    return f'<span class="choice {cls}">{text}{tail}</span>'


def tag(name: str, certainty: float, extra: str = "") -> str:
    return f'<span class="tag" style="--certainty: {certainty:.3f}" title="certainty {round(certainty * 100)}%">{name}{extra}</span>'


def seats_strip(moment: dict, acting: str = "", acting_word: str = "thinking", me: str = "Scarlett") -> str:
    out = ['<div class="seats">']
    for seat, suspect in enumerate(moment["suspects"]):
        classes = ["seat", "compact"]
        if suspect == me:
            classes.append("me")
        if suspect == acting:
            classes.append("acting")
        if not moment["active"][seat]:
            classes.append("out")
        kind = STORY_KINDS[suspect]
        if not moment["active"][seat]:
            word = "out"
        elif suspect == acting:
            word = acting_word
        elif suspect == me:
            word = "you"
        elif kind == "LLM":
            word = "LLM"
        else:
            word = "headless"
        cost = ""
        if suspect in COST_SHARE:
            cost = f'<span class="cost" title="${COST_SHARE[suspect] * 0.41:.2f} of $0.41 spent with Claude"><i style="width:{COST_SHARE[suspect] * 100:.0f}%"></i></span>'
        out.append(
            f'<article class="{" ".join(classes)}" data-seat="{seat}">'
            f'<span class="pip suspect-{suspect.lower()}">{parts.INITIALS[suspect]}</span>'
            f"{tag(suspect, moment['certainties'][seat])}"
            f'<span class="state">{word}</span>{cost}</article>'
        )
    out.append("</div>")
    return "".join(out)


def tabs(active: str, talk: int = 0, record: bool = False, hand: int = 3) -> str:
    def one(name, extra=""):
        cls = "tab active" if name == active else "tab"
        return f'<span class="{cls}">{name}{extra}</span>'

    return (
        '<nav class="tabs">'
        + one("Talk", f'<span class="badge">{talk}</span>' if talk else "")
        + one("Record", '<span class="dot"></span>' if record else "")
        + one("Hand", f'<span class="badge">{hand}</span>')
        + one("Notes")
        + "</nav>"
    )


def rail(active: str, panel: str = "", minimized: bool = False, foot: str = "", **badges) -> str:
    cls = "rail min" if minimized else "rail"
    body = "" if minimized else f'<div class="rail-panel">{panel}</div>'
    foot_html = f'<p class="rail-foot">{foot}</p>' if foot else ""
    return f'<div class="{cls}">{tabs(active, **badges)}{body}{foot_html}</div>'


def record_list(lines: list, last: int = 6, newest: bool = True, pips: tuple = ()) -> str:
    shown = [line for line in lines if line["kind"] != "remark"][-last:]
    out = ['<ol class="record">']
    for index, line in enumerate(shown):
        cls = line["kind"] + (" newest" if newest and index == len(shown) - 1 else "")
        pip = ' <span class="pip-talk" title="table talk on this turn">&#9679;</span>' if line["turn"] in pips else ""
        out.append(f'<li class="{cls}"><span class="turn">{line["turn"]}</span><span class="line">{escape(line["text"])}{pip}</span></li>')
    out.append("</ol>")
    return "".join(out)


TALK = [
    ("Plum", 7, "reaction", "A candlestick in the Dining. How very traditional."),
    ("Peacock", 11, "reaction", "Green, was it? Somebody at this table is very fond of the Conservatory."),
    ("Scarlett", 11, "mine", "Just passing through. Ask me about the Rope, though."),
]
"""Invented: no model plays in the sketch. Marked as such in the notes."""


def talk_list(items: list, names: dict) -> str:
    out = ['<ol class="talk">']
    for speaker, turn, kind, text in items:
        if kind == "mine":
            out.append(f'<li class="balloon mine"><span class="speaker">You<span class="gauge-text">turn {turn}</span></span>{escape(text)}</li>')
        else:
            out.append(
                f'<li class="balloon {kind}" style="--speaker: {SUSPECT_COLOUR[speaker]}">'
                f'<span class="speaker">{names.get(speaker, speaker)}<span class="gauge-text">turn {turn}</span></span>{escape(text)}</li>'
            )
    out.append("</ol>")
    return "".join(out)


def say_box(text: str = "", count: int = 0) -> str:
    inner = f'<span class="text">{escape(text)}</span>' if text else '<span class="placeholder">Say something at the table</span>'
    counter = f'<span class="count{" over" if count > 200 else ""}">{count} / 240</span>' if count > 200 else ""
    return f'<div class="say"><div class="box">{inner}{counter}</div>{choice("Say", cls="quiet")}</div>'


def hand_list(hand: list, shown: set = frozenset()) -> str:
    return '<ul class="hand">' + "".join(
        f'<li class="card-chip{" shown" if c in shown else ""}">{card(c)}</li>' for c in hand
    ) + "</ul>"


def notepad_table(rows: list, suspects: list) -> str:
    out = ['<table class="notepad"><tr><th>card</th>']
    out += [f"<th>{s[:3]}</th>" for s in suspects] + ["<th>env</th></tr>"]
    last = None
    for row in rows:
        if row["category"] != last:
            out.append(f'<tr class="category"><th colspan="{len(suspects) + 2}">{row["category"]}</th></tr>')
            last = row["category"]
        cls = "open" if row["holder"] is None else ("solved" if row["holder"] == "envelope" else "placed")
        out.append(f'<tr class="{cls}"><td class="card">{card(row["card"])}</td>')
        for seat in range(len(suspects)):
            if row["holder"] == seat:
                out.append('<td><span class="holder"></span></td>')
            elif row["holder"] is None and seat in row["possible"]:
                out.append('<td><span class="maybe"></span></td>')
            else:
                out.append("<td></td>")
        if row["holder"] == "envelope":
            out.append('<td><span class="holder envelope"></span></td>')
        elif row["holder"] is None and row["envelope"]:
            out.append('<td><span class="maybe"></span></td>')
        else:
            out.append("<td></td>")
        out.append("</tr>")
    out.append("</table>")
    return "".join(out)


def main_block(*sections: str, wide: bool = False) -> str:
    return '<main class="table">' + "".join(sections) + "</main>"


def wrap(name: str, title: str, body: str, theme: str = "dark", out_dir: Path = TABLE, css: str = "./engraved-sketch.css") -> None:
    (out_dir / name).write_text(page(body, css, theme, title), encoding="utf-8")


# --- the table canvas -----------------------------------------------------


def option_text(option: dict) -> str:
    if option["move"] == "stay":
        return "Stay where you are"
    if option["move"] == "secret_passage":
        return f"Secret passage to the {option['to']}"
    if isinstance(option["to"], str):
        return f"Enter the {option['to']}"
    return f"{option['to']['row']} · {option['to']['col']}"


def build_table(mid: dict, end: dict) -> list:
    names = {s: (f"{s} (David)" if s == "Scarlett" else s) for s in mid["suspects"]}
    by_kind: dict = {}
    for request in mid["requests"]:
        by_kind.setdefault(request["request"]["kind"], []).append(request)
    move_req = by_kind["movement"][-1]
    suggest_req = by_kind["suggestion"][-1]
    show_req = by_kind["card_to_show"][-1]
    boards = []

    # 7 board: waiting on Mustard, the record open.
    svg = parts.board(mid["positions"], logo="A", thinking="Mustard")
    for theme, name, panel_tab, panel in (
        ("dark", "Board.dc.html", "Record", '<h2>The record</h2>' + record_list(mid["lines"], 6, pips=(7, 11))),
        ("light", "BoardLight.dc.html", "Notes", '<h2>Your notes</h2>' + notepad_table(mid["notepad"], mid["suspects"])),
    ):
        body = screen(
            bar()
            + main_block(
                status("Waiting for Mustard to move.", clock="47 s left"),
                stage(svg),
                seats_strip(mid, acting="Mustard", acting_word="moving"),
                rail(panel_tab, panel, talk=2, record=False, foot="Watching: Ann"),
            ),
            theme=theme,
            focus="board",
            style="min-height: 1040px" if theme == "light" else "",
        )
        wrap(name, f"Table · {panel_tab}", body, theme)
        boards.append((name, 390, 1040 if theme == "light" else 844, f"7 · board ({theme})"))

    # 3 move: Scarlett's move at turn 12, every option lit.
    options = move_req["request"]["options"]
    rooms = [o for o in options if isinstance(o["to"], str) or o["move"] in ("stay", "secret_passage")]
    squares = [o for o in options if not isinstance(o["to"], str) and o["move"] not in ("stay", "secret_passage")]
    room_choices = "".join(choice(option_text(o), o.get("distances", ""), "passage" if o["move"] == "secret_passage" else "") for o in rooms)
    square_choices = "".join(choice(option_text(o), cls="quiet") for o in squares)
    dock = (
        '<div class="dock"><h2>Your move</h2>'
        f'<div class="choices stack">{room_choices}</div>'
        f'<p class="note">Or a corridor square, row · column:</p><div class="choices" style="grid-template-columns: repeat(4, 1fr)">{square_choices}</div></div>'
    )
    body = screen(
        bar()
        + main_block(
            status("Your move.", "yours", clock="82 s left"),
            stage(parts.board(move_req["positions"], logo="A", lit=options)),
            dock,
            rail("Record", minimized=True, talk=2, record=True),
        ),
        focus="move",
    )
    wrap("Move.dc.html", "Table · your move", body)
    boards.append(("Move.dc.html", 390, 1010, "3 · move"))

    # 4 decide: the suggestion form in the Lounge.
    room = suggest_req["request"]["room"]
    dock = (
        f'<div class="dock"><h2>Suggest, in the {room}</h2>'
        '<div class="field"><span class="label">Suspect</span><span class="value">Scarlett</span></div>'
        '<div class="field"><span class="label">Weapon</span><span class="value">Candlestick</span></div>'
        f'<div class="choices">{choice("Suggest", cls="primary")}{choice("No suggestion", cls="quiet")}</div>'
        '<div class="accuse">Accuse <small>set up any time; fires at the accusation question</small></div></div>'
    )
    body = screen(
        bar()
        + main_block(
            status(f"You are in the {room}. Make a suggestion?", "yours", clock="76 s left"),
            stage(parts.board(suggest_req["positions"], logo="A"), cls="strip", over="")
            .replace("</section>", f'<div><p class="title">In the {room}</p><p class="note">Nobody else is here. A suggestion calls its suspect in.</p></div></section>'),
            seats_strip(mid, acting="Scarlett", acting_word="you"),
            dock,
            rail("Record", minimized=True, talk=2, record=True),
        ),
        focus="decide",
    )
    wrap("Decide.dc.html", "Table · suggest", body)
    boards.append(("Decide.dc.html", 390, 844, "4 · decide"))

    # 1 show: Peacock's suggestion at turn 11, the cards you could show.
    suggestion_line = next(l for l in mid["lines"] if l["kind"] == "suggestion" and l["turn"] == show_req["turn"] + 1)
    asker = mid["suspects"][show_req["request"]["shown_to"]]
    caption = escape(suggestion_line["text"].split(". ")[0] + ".")
    candidates = "".join(choice(card(c), "one of your cards", "primary") for c in show_req["request"]["candidates"])
    dock = (
        f'<div class="dock"><h2>Show a card to {asker}</h2>'
        f'<div class="choices stack">{candidates}</div>'
        '<p class="note">Only the cards that disprove it are offered; with two matching, two buttons.</p></div>'
    )
    body = screen(
        bar()
        + main_block(
            status(f"{asker} named cards you hold. Show one.", "yours", clock="88 s left"),
            stage(parts.board(show_req["positions"], logo="A"), cls="dimmed", over=f'<div class="over">{beat(caption, f"Turn {show_req['turn'] + 1} · suggestion", asker)}</div>'),
            dock,
            rail("Record", minimized=True, talk=2, record=True),
        ),
        focus="show",
    )
    wrap("Show.dc.html", "Table · show a card", body)
    boards.append(("Show.dc.html", 390, 844, "1 · show"))

    # 5 beat: the same suggestion, resolved, 2.2 s later.
    resolved = next(l for l in mid["lines"] if l["kind"] == "suggestion" and l["turn"] == show_req["turn"] + 1)
    body = screen(
        bar()
        + main_block(
            status("Waiting for Plum to move."),
            stage(parts.board(show_req["positions"], logo="A"), cls="dimmed", over=f'<div class="over">{beat(escape(resolved["text"]), f"Turn {resolved['turn']} · refutation", asker)}</div>'),
            seats_strip(mid, acting="Plum"),
            rail("Record", '<h2>The record</h2>' + record_list(mid["lines"][: resolved["i"] + 1], 5, pips=(7, 11)), talk=2),
        ),
        focus="beat",
    )
    wrap("Beat.dc.html", "Table · the beat", body)
    boards.append(("Beat.dc.html", 390, 844, "5 · beat"))

    # 6 talk: two balloons over the board, the Talk panel open.
    balloons = talk_list(TALK[1:], names)
    long_line = "I will say this once: whoever keeps dragging me into the Conservatory owes me a drink, and I have my eye on the Rope, the Study and one of you in particular"
    panel = '<h2>Table talk</h2>' + talk_list(TALK, names) + '<p class="typing">Plum is typing…</p>' + say_box(long_line, 212)
    body = screen(
        bar()
        + main_block(
            status("The table is talking."),
            stage(parts.board(mid["positions"], logo="A"), cls="dimmed", over=f'<div class="over bottom">{balloons}</div>'),
            seats_strip(mid),
            rail("Talk", panel, talk=0, record=True),
        ),
        focus="talk",
    )
    wrap("Talk.dc.html", "Table · talk", body)
    boards.append(("Talk.dc.html", 390, 1030, "6 · talk"))

    # 2 end: the envelope on the plate, the winner, the debriefs.
    s, w, r = end["solution"]
    over_plate = plate(
        '<p class="kicker">The envelope</p>'
        f'<p class="envelope">{s}<small>with the</small>{card(w)}<small>in the</small>{r}</p>'
        f'<p class="winner">{end["winner"]} wins on turn {end["turns"]}.</p>',
        "hero",
    )
    dock = (
        '<div class="dock">'
        f'<div class="choices stack">{choice("Open the replay", "every seat, cards face up", "primary")}{choice("Back to the lobby", cls="quiet")}</div>'
        '</div>'
    )
    body = screen(
        bar()
        + main_block(
            status(f"{end['winner']} wins. Plum is writing up notes on the game.", "warn"),
            stage(parts.board(end["positions"], logo="A"), cls="dimmed", over=f'<div class="over">{over_plate}</div>'),
            seats_strip(end, acting=end["winner"], acting_word="won"),
            dock,
            rail("Record", minimized=True, talk=4, record=True),
        ),
        focus="end",
    )
    wrap("End.dc.html", "Table · game over", body)
    boards.append(("End.dc.html", 390, 844, "2 · end"))

    # Wide: the three columns of section 6.
    col1 = (
        '<div class="col">'
        + stage(svg)
        + '<div class="section" style="box-shadow:none"><h2 style="font-size:1rem">Your hand <span class="who">(Scarlett)</span></h2>'
        + hand_list(mid["hand"], shown={"Green"})
        + '<h2 style="font-size:1rem;margin-top:8px">Your notes</h2>'
        + notepad_table(mid["notepad"], mid["suspects"])
        + "</div></div>"
    )
    col2 = (
        '<div class="col">'
        + status("Waiting for Mustard to move.", clock="47 s left")
        + '<div class="section" style="box-shadow:none"><h2 style="font-size:1rem">The record</h2>'
        + record_list(mid["lines"], 9, pips=(7, 11))
        + "</div>"
        + '<div class="section" style="box-shadow:none"><h2 style="font-size:1rem">Not your decision</h2><p class="note">Wait for your turn.</p>'
        + '<div class="accuse">Accuse <small>set up any time; fires at the accusation question</small></div></div>'
        + "</div>"
    )
    col3 = (
        '<div class="col">'
        + '<div class="section" style="box-shadow:none;flex:1"><h2 style="font-size:1rem">Table talk</h2>'
        + talk_list(TALK, names)
        + '<p class="typing">Plum is typing…</p>'
        + say_box()
        + '<p class="rail-foot">Watching: Ann</p></div>'
        + "</div>"
    )
    body = screen(bar() + main_block(seats_strip(mid, acting="Mustard", acting_word="moving") + col1 + col2 + col3), focus="board", wide=True)
    wrap("Wide.dc.html", "Table · wide", body)
    boards.append(("Wide.dc.html", 1280, 980, "7 · board, wide"))

    # Waiting for players.
    rows = []
    for suspect, occupant, action in (
        ("Scarlett", "David (you)", ""),
        ("Mustard", "open", choice("Sit here", cls="quiet")),
        ("White", "floorbot", ""),
        ("Green", "Green (headless)", ""),
        ("Peacock", "Peacock (LLM)", ""),
        ("Plum", "Plum (LLM)", ""),
    ):
        rows.append(
            f'<li class="seat-row"><span class="pip suspect-{suspect.lower()}">{parts.INITIALS[suspect]}</span>'
            f'<span class="name">{suspect}</span><span class="occupant">{occupant}</span>{action}</li>'
        )
    body = screen(
        bar()
        + '<main class="table">'
        + '<p class="crumbs"><a href="#">Lobby</a> › table</p>'
        + plate('<p class="kicker">Table 5019abeb0a</p><p class="title">Waiting for players</p><p class="note">6 seats, seed 7007, started by David; the characters remember; 90 s a decision.</p>', "")
        + '<ul class="seat-rows">' + "".join(rows) + "</ul>"
        + '<div class="dock"><div class="choices stack">'
        + choice("Deal now", "every open seat must be taken first", "disabled")
        + f'<div class="choices">{choice("Leave the table", cls="quiet")}{choice("End table", cls="warn quiet")}</div>'
        + '</div><p class="note">The table is dealt once every open seat is taken. Send the others this page’s address.</p></div>'
        + "</main>",
    )
    wrap("Waiting.dc.html", "Table · waiting", body)
    boards.append(("Waiting.dc.html", 390, 844, "the open table"))

    # The lobby.
    picks = []
    values = {"Scarlett": "me (David)", "Mustard": "open", "White": "floorbot", "Green": "Green (headless)", "Peacock": "Peacock (LLM)", "Plum": "Plum (LLM)"}
    for suspect in mid["suspects"]:
        picks.append(
            f'<div class="pick"><span class="pip suspect-{suspect.lower()}">{parts.INITIALS[suspect]}</span><span class="name">{suspect}</span>'
            f'<span class="select">{values[suspect]}</span><span class="method">{METHODS[suspect]}</span></div>'
        )
    lobby = (
        '<main class="table" style="gap:16px">'
        + '<div class="section"><h2>Play a game</h2>'
        + '<p class="note">Take a token and pick who sits at the others. <em>Empty</em> leaves the token out; <em>open</em> reserves it; <em>floorbot</em> is the plain deducer. An <em>LLM</em> character uses Claude within its leash and talks; a <em>headless</em> one plays its method and never chats.</p>'
        + '<div class="picks">' + "".join(picks) + "</div>"
        + '<div class="knob"><span class="label note" style="min-width:4rem">Seed</span><span class="box">7007</span></div>'
        + '<div class="knob"><span class="check on"></span>the characters remember <span class="note">(logbooks and method memory)</span></div>'
        + '<div class="knob"><span class="check"></span>speed mode <span class="note">(30 s a decision)</span></div>'
        + '<div class="knob"><span class="label note" style="min-width:4rem">Budget $</span><span class="box">2.00</span><span class="note">about $0.10 a seat-game, Plum $0.25</span></div>'
        + f'<div class="choices stack">{choice("Deal", cls="primary")}</div></div>'
        + '<div class="section"><h2>Tables</h2><ul class="listing">'
        + '<li><a href="#">David as Scarlett, Mustard (open), White (floorbot), Green (headless), Peacock (LLM), Plum (LLM)</a><span class="note">waiting for 1 more · seed 7007 · <strong>you are seated</strong> · remembering</span></li>'
        + '<li><a href="#">Ann as Peacock, Scarlett (LLM), Plum (LLM)</a><span class="note">turn 23 · seed 1181 · started by Ann · <span class="cost">$0.41</span> with Claude</span></li>'
        + "</ul></div>"
        + '<div class="section"><h2>Watch a game</h2><p class="note">Headless characters only, no people or chat: pick who sits and step through it a turn at a time.</p>'
        + f'<div class="choices">{choice("Deal and watch", cls="quiet")}</div></div>'
        + '<div class="section"><h2>Stored games</h2><ul class="listing">'
        + '<li><a class="run-id" href="#">web</a><span class="note">14 games · 3/4/6 seats · <span class="cost">$4.81</span> with Claude</span></li>'
        + '<li><a class="run-id" href="#">grid-twin-llm-24</a><span class="note">96 games · 4 seats · <span class="cost">$9.36</span> with Claude</span></li>'
        + '<li><a class="run-id" href="#">grid-twin-base-24</a><span class="note">96 games · 4 seats</span></li>'
        + "</ul></div></main>"
    )
    wrap("Lobby.dc.html", "Lobby", screen(bar() + lobby, style="min-height: 1560px"))
    boards.append(("Lobby.dc.html", 390, 1560, "the lobby"))

    # The replay: omniscient.
    game = end["game"]
    blocks = []
    for seat, suspect in enumerate(end["suspects"]):
        pad = parts.notepad_for(game, seat)
        open_by = {}
        for row in pad:
            if row["holder"] is None and row["envelope"]:
                open_by.setdefault(row["category"], []).append(row["card"])
        minis = []
        for category in ("suspects", "weapons", "rooms"):
            n = len(open_by.get(category, []))
            minis.append('<i class="proof"></i>' if n <= 1 else f'<i style="--w:{100 / n:.0f}%"></i>')
        who = "(David)" if suspect == "Scarlett" else ""
        method = "a person" if suspect == "Scarlett" else METHODS[suspect]
        head = (
            f'<div class="head"><span class="pip suspect-{suspect.lower()}">{parts.INITIALS[suspect]}</span>'
            f'{tag(suspect, end["certainties"][seat], f" <span class=who>{who}</span>" if who else "")}<span class="mini">{"".join(minis)}</span></div>'
        )
        detail = f'<p class="method">{method}</p><p class="holds">Holds: {", ".join(card(c) for c in end["hands"][suspect])}</p>'
        strips = ""
        if suspect == end["winner"]:
            for category, cards in tables_categories():
                rows = []
                for c in cards:
                    row = next(r for r in pad if r["card"] == c)
                    truth = '<span class="mark-truth on"></span>' if c in end["solution"] else '<span class="mark-truth"></span>'
                    if row["holder"] == "envelope":
                        rows.append(f'<div class="row proven-envelope"><span class="card">{card(c)}</span><span class="track"><span class="fill"></span></span>{truth}</div>')
                    elif row["holder"] is not None:
                        rows.append(f'<div class="row proven-held"><span class="card">{card(c)}</span><span class="track"><span class="fill"></span></span>{truth}</div>')
                    else:
                        n = len(open_by.get(category, [])) or 1
                        rows.append(f'<div class="row open"><span class="card">{card(c)}</span><span class="track"><span class="fill" style="--w:{100 / n:.0f}%"></span></span>{truth}</div>')
                strips += f'<div class="strip" data-group="{category}">{"".join(rows)}</div>'
        blocks.append(f'<article class="seat block" data-seat="{seat}">{head}{detail}{strips}</article>')
    step = end["lines"][57]
    ticks = "".join(f'<span class="tick" style="left:{i * 10}%"></span>' for i in range(11))
    scrubber = (
        '<div class="scrubber">'
        + choice("Play", cls="step")
        + choice("‹", cls="step quiet")
        + f'<div class="track">{ticks}<span class="thumb" style="left: {58 / len(end["lines"]) * 100:.0f}%"></span></div>'
        + choice("›", cls="step quiet")
        + f'<span class="counter">58 / {len(end["lines"])}</span></div>'
        + '<div class="speed" style="margin-top:8px">slower<span class="slide"><i style="left:50%"></i></span>faster</div>'
    )
    replay = (
        '<main class="table">'
        + '<p class="crumbs"><a href="#">Lobby</a> › web › game 3</p>'
        + f'<p class="title">Game 3</p><p class="note">6 seats, {end["turns"]} turns, seed {SEED}. {end["winner"]} won. It was <strong>{s}, {card(w)}, {r}</strong>.</p>'
        + stage(parts.board(end["positions"], logo="A"))
        + beat(escape(step["text"]), f"Step 58 · turn {step['turn']}", step["text"].split(" ")[0] if step["text"].split(" ")[0] in parts.INITIALS else "")
        + scrubber
        + '<div class="replay-seats">' + "".join(blocks) + "</div>"
        + '<p class="key">A solid bar is proven by the deduction floor; a toned bar is that seat’s own belief; a struck row is a card it has proven someone holds. The red mark is the truth. Tap a seat to open its rows; the winner’s are open.</p>'
        + "</main>"
    )
    wrap("Replay.dc.html", "Replay", screen(bar() + replay, style="min-height: 1500px"))
    boards.append(("Replay.dc.html", 390, 1500, "the replay"))
    return boards


def tables_categories():
    from clude_web.tables import CATEGORIES

    return CATEGORIES


TABLE_NOTES = {
    "Board.dc.html": "7 · board. Nothing is happening to you: the board holds the stage, Mustard's token wears the thinking ring, the status line carries the time-out clock (9h). The seat rail is public facts only (3.2) plus the two numbers David allowed everyone: the certainty tag on each name (9h) and the cost bar on the two model seats (9g). No bars, no methods. The rail shows what it holds back: two unread lines on Talk. The Record is case-file: turn numbers in the gauge face, a hairline between turns, a brass pip where talk happened that turn.",
    "BoardLight.dc.html": "7 · board, case-file light. The same moment under a stated light preference, with Notes open: a proven holder is solid ink, a still-possible holder a screentone dot, the envelope column in the red thread. The panel scrolls in the real screen; here the board is drawn taller so the whole sheet shows.",
    "Move.dc.html": "3 · move. Your move at turn 12, a six: every legal destination is lit on the board at server-side coordinates, and the same destinations are the buttons beneath, rooms first with their distance line, corridor squares as a compact grid. The rail collapses to its tab strip; nothing can steal the buttons (3.1). Drawn taller because seventeen options is the honest case.",
    "Decide.dc.html": "4 · decide. The suggestion form: the board shrinks to a strip, two fields, Suggest and No suggestion, and the Accuse panel folded but reachable — set up on any turn, it fires only at the accusation question (8.2's rule, kept).",
    "Show.dc.html": "1 · show. Peacock's suggestion spelled out as a caption in Peacock's colour over the dimmed board, and one button per card you could show. Rank 1: nothing outranks it. In this game the deal gave you one matching card; two would be two buttons.",
    "Beat.dc.html": "5 · beat. Within 2.2 s of the refutation: the narration caption set large over the dimmed board, then it decays to rank 7. The record beneath already carries the line.",
    "Talk.dc.html": "6 · talk. A line arrived in the last 6 s and nothing above applies: the last two balloons over the board, tails in the speakers' colours, yours right-aligned. The Talk panel: the 240-character box with its counter past 200, and 'Plum is typing' (9h). The lines themselves are invented: no model plays in a sketch.",
    "End.dc.html": "2 · end. The envelope on the hero plate over the board, the winner, the debrief progress in the status line, Open the replay as the one primary choice. The impact frame (the 80 ms flash to ink) has already passed.",
    "Wide.dc.html": "7 · board at ≥ 62rem: three columns 6:4:3. Board, hand and notes; status, record and the decision; talk full height. Nothing collapses; focus changes emphasis, not the grid.",
    "Waiting.dc.html": "The open table before the deal: the plate, one row per seat, Sit here on the open one, Deal now disabled with its reason, Leave and End. Methods are not shown here (D3): only the setup form names them.",
    "Lobby.dc.html": "The lobby. Six picks in the settled order (empty, open, floorbot, me, LLM, headless) each naming its method (D3: the setup form may), the knobs, one primary Deal; the Tables list with its Cost column (9g); Watch; Stored games. Scrolls.",
    "Replay.dc.html": "The replay, omniscient. Every seat's method named, its hand, its certainty tag; the winner's block open with a row per card (solid = proven, tone = belief, struck = held elsewhere, red = truth), the others collapsed to three mini gauges. The machined scrubber: brass track with ticks, an engraved plate for a thumb, Play and the speed slider (9h). Scrolls.",
}

LOGO_NOTES = {
    "A-Plate.dc.html": "A · the plate wordmark — the proposed lead (section 9). 'clude' lowercase in Bodoni Moda, letter-spaced, on a hairline brass plate with four rivets; the mark is the keyhole-c, an escutcheon whose keyway is the c. For: the wordmark scales from the cellar to the header bar unchanged. Against: the keyhole is a familiar mystery signifier.",
    "B-Seal.dc.html": "B · the seal. A wax seal in the red thread with the c pressed in and an uneven edge, the wordmark beside it. For: the only candidate in colour, so it reads at 16 px by colour alone; says 'case closed'. Against: the one accent-filled surface in the app, and a red disc is a common favicon.",
    "C-Plan.dc.html": "C · the plan. The nine rooms as a 3 × 3 engraved floor plan with the c in the cellar cell and brass door ticks, the wordmark beneath. For: it is the board itself, so it is nobody's trade dress, and it says what the game is. Against: nine cells at 16 px become a grey square.",
    "D-Cartouche.dc.html": "D · the cartouche. The wordmark in a Victorian oval with a double hairline; the mark a hatched roundel with the c cut out. For: the most 'engraved' of the four; the roundel reads at any size. Against: the oval fights the cellar's 5 × 7 box.",
    "Compare.dc.html": "All four in the cellar of the real board at phone size, both themes: the place the choice will be seen most. The cellar is 5 × 7 cells; at 390 px that is about 75 × 105 px.",
}


# --- the logo canvas ------------------------------------------------------


def build_logo(mid: dict) -> list:
    boards = []
    crop = "216 216 168 216"  # cols 9-16, rows 9-18: the cellar and its neighbours
    for kind in "ABCD":
        halves = []
        for theme in ("dark", "light"):
            cropped = parts.board(mid["positions"], logo=kind, viewbox=crop, crop=True)
            thumb = parts.board(mid["positions"], logo=kind)
            nav = (
                '<div class="bar" style="border:var(--rule-ink)">'
                f'<a class="mark" href="#" style="display:flex;align-items:center;gap:6px">{parts.logo_svg(kind, 120, 168, 22, mark_only=True)}<span>clude</span></a>'
                '<div class="bar-right"><span class="select">Engraved</span><span class="who">David</span></div></div>'
            )
            favicons = (
                '<div style="display:flex;align-items:center;gap:16px">'
                + f'<span style="display:inline-block;padding:6px;background:var(--page);border:var(--rule)">{parts.logo_svg(kind, 120, 168, 32, mark_only=True)}</span>'
                + f'<span style="display:inline-block;padding:6px;background:var(--page);border:var(--rule)">{parts.logo_svg(kind, 120, 168, 16, mark_only=True)}</span>'
                + '<span class="note">32 and 16 px</span></div>'
            )
            halves.append(
                f'<section data-theme="{theme}" style="background:var(--page);color:var(--ink);padding:12px 16px;display:grid;grid-template-columns:200px 1fr;gap:12px;align-items:start">'
                f'<div><p class="note" style="margin-bottom:6px">In the cellar, {theme}</p><div class="stage" style="padding:4px">{cropped}</div></div>'
                f'<div style="display:flex;flex-direction:column;gap:10px;min-width:0">{nav}{favicons}<p class="note">At phone size:</p><div class="stage" style="padding:3px;width:150px">{thumb}</div></div>'
                "</section>"
            )
        title = f'<div style="padding:14px 16px 6px"><p class="title">{kind} · {parts.NAMES[kind]}</p><p class="note">{"The proposed lead" if kind == "A" else "Alternate"}: at the cellar, in the header bar, as the favicon, and on the phone board.</p></div>'
        body = screen(title + "".join(halves))
        wrap(f"{kind}-{parts.NAMES[kind]}.dc.html", f"Logo {kind}", body, out_dir=LOGO, css="../table/engraved-sketch.css")
        boards.append((f"{kind}-{parts.NAMES[kind]}.dc.html", 390, 844, f"{kind} · {parts.NAMES[kind]}"))

    grids = []
    for theme in ("dark", "light"):
        cells = "".join(
            f'<div><p class="note" style="margin-bottom:4px">{k} · {parts.NAMES[k]}</p><div class="stage" style="padding:3px">{parts.board(mid["positions"], logo=k)}</div></div>'
            for k in "ABCD"
        )
        grids.append(f'<section data-theme="{theme}" style="background:var(--page);color:var(--ink);padding:12px 16px;display:grid;grid-template-columns:1fr 1fr;gap:12px">{cells}</section>')
    body = screen('<div style="padding:14px 16px 6px"><p class="title">Compare</p><p class="note">The four in the cellar of the real board at phone size, both themes.</p></div>' + "".join(grids), style="min-height: 900px")
    wrap("Compare.dc.html", "Logo · compare", body, out_dir=LOGO, css="../table/engraved-sketch.css")
    boards.append(("Compare.dc.html", 390, 900, "Compare"))
    return boards


# --- canvas.json and the contact sheet ------------------------------------


def write_canvas(folder: Path, boards: list, notes: dict, brief: str, launch: str) -> None:
    artboards = []
    annotations = [{"id": "brief", "x": 0, "y": -360, "w": 780, "text": brief}]
    x = 0
    for name, w, h, title in boards:
        artboards.append({"file": name, "x": x, "y": 0, "w": w, "h": h, "title": title})
        annotations.append({"id": "note-" + name.split(".")[0].lower(), "x": x, "y": -190, "w": min(w, 390), "text": notes[name]})
        x += w + 80
    canvas = {"artboards": artboards, "annotations": annotations, "launch": {"view": "focused", "file": launch}}
    (folder / "canvas.json").write_text(json.dumps(canvas, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    top = min(a["y"] for a in annotations)
    width = max(a["x"] + a["w"] for a in artboards) + 40
    height = max(a["y"] + a["h"] for a in artboards) - top + 60
    items = []
    for a in annotations:
        items.append(
            f'<div class="ann" style="left:{a["x"] + 20}px;top:{a["y"] - top + 20}px;width:{a["w"]}px">{escape(a["text"])}</div>'
        )
    for a in artboards:
        items.append(
            f'<div class="art" style="left:{a["x"] + 20}px;top:{a["y"] - top + 20}px;width:{a["w"]}px">'
            f'<p class="label">{escape(a["title"])} <a href="{a["file"]}">{a["file"]}</a></p>'
            f'<iframe src="{a["file"]}" width="{a["w"]}" height="{a["h"]}" loading="lazy"></iframe></div>'
        )
    html = f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>{escape(folder.name)} · Phase 10a artboards</title>
<style>
body {{ margin: 0; background: #2b282c; color: #d9d3c7; font: 14px/1.45 Inter, system-ui, sans-serif; }}
.canvas {{ position: relative; width: {width}px; height: {height}px; }}
.ann {{ position: absolute; white-space: pre-wrap; font-size: 13px; color: #d9d3c7; }}
.art {{ position: absolute; }}
.art .label {{ margin: 0 0 6px; font: 600 13px/1.2 "IBM Plex Mono", ui-monospace, monospace; color: #f0c67e; }}
.art .label a {{ color: #a9a090; font-weight: 400; margin-left: 8px; }}
.art iframe {{ display: block; border: 1px solid #6b5d49; background: #000; }}
</style>
</head>
<body>
<div class="canvas">
{chr(10).join(items)}
</div>
</body>
</html>
"""
    (folder / "index.html").write_text(html, encoding="utf-8")


TABLE_BRIEF = (
    "The table on a phone, in the Engraved look (docs/phase10-plan.md): one moment of a real game, seed 7007, six seats, David at Scarlett, "
    "Peacock and Plum with Claude in the story (the game itself was played by the methods). The seven focus states of 3.1, highest rank first: "
    "show, end, move, decide, beat, talk, board. The stage holds whatever matters most; the rail shows what it holds back. "
    "Play is blind (3.2): no seat's bars or method during play, only the certainty tag (9h) and the cost bar (9g). "
    "Record and Talk are two panels (3.3). Gaslight dark is the default (D6); one board is drawn in case-file light. "
    "Every board links engraved-sketch.css, the draft of 10b's stylesheet; the board is board_svg's own geometry, dressed as 10f will dress it."
)
LOGO_BRIEF = (
    "D5, the logo: the proposed plate wordmark with the keyhole-c (A) beside three alternates (B, C, D), each at its three sizes in both themes: "
    "the cellar of the real board (5 x 7 cells), the header bar's mark at 22 px, and the favicon at 32 and 16 px. "
    "All four are uncoloured, classed SVG that takes the theme like everything else; the winner drops into board_svg in 10f. "
    "No gears, no gradients, no sepia, no blur (section 4)."
)


def main() -> None:
    TABLE.mkdir(exist_ok=True)
    LOGO.mkdir(exist_ok=True)
    mid = parts.play_moment(SEED, 14)
    end = parts.play_moment(SEED, 500)
    boards = build_table(mid, end)
    write_canvas(TABLE, boards, TABLE_NOTES, TABLE_BRIEF, "Board.dc.html")
    logos = build_logo(mid)
    write_canvas(LOGO, logos, LOGO_NOTES, LOGO_BRIEF, "A-Plate.dc.html")
    print(f"table: {len(boards)} artboards; logo: {len(logos)} artboards; seed {SEED}, {mid['turns']} turns mid-game, {end['turns']} at the end, {end['winner']} won")


if __name__ == "__main__":
    main()
