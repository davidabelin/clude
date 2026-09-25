# The web app

`clude_web` is the Flask app in front of the headless game (Phase 8.1,
`docs/phase8.1-plan.md`). It imports every other package; nothing imports
it, so the engine, the agents and the store stay exactly as testable
headless as they were.

Built: 8.1a, the local app -- the login gate and accounts, the lobby, the
replay scrubber and the Watch screen -- and 8.1b, the same app on Cloud
Run at <https://clude-648214345192.us-central1.run.app> ("Deploying",
below). Since Phase 8.2 (2026-09-18) people play at it too: a table
seats you beside the characters and the game is played from the browser
("A table", below).

## Running it locally

```powershell
& .venv\Scripts\python.exe -m flask --app clude_web run --debug
```

It needs two things.

**A session secret** in `FLASK_SECRET_KEY`. The app takes it from the
environment, and falls back to reading the gitignored `.env` at the repo
root for that one variable, so on Orbit there is nothing to export. This
fallback is `clude_web.config.read_env_file` and is used by nothing else:
the rest of clude still never loads `.env` (CLAUDE.md). A deployed service
has the variable in its own environment and never reaches the fallback.
With no secret anywhere the app refuses to start rather than generating
one, because a generated key would sign everybody out on every restart and
hide the mistake.

**At least one account.** There is no sign-up page; accounts are made from
the CLI only:

```powershell
& .venv\Scripts\python.exe scripts\clude_cli.py users add David
```

That is the whole of it: no prompt, and the password is set to `password`.
Pass a different one as a second argument if you like.

By default the app reads `data/llm`, the store holding every grid-era run,
and `users` writes there too. `CLUDE_WEB_STORE` points both somewhere else.

## Accounts

| Command | What it does |
|---|---|
| `users add NAME [PASSWORD]` | Create an account. Without a password it gets `password`. |
| `users list` | Every account and when it was made. No hash is printed. |
| `users passwd NAME [PASSWORD]` | Change a password; asks for one if left off. |
| `users remove NAME` | Delete an account. Records and logbooks are left alone. |

Each is `users <action> [--uri STORE]`.

The login name is matched case-insensitively but displayed as typed,
because it is the player's identity and not just a credential: Phase 8.2
writes it into `SeatRecord.label`, so a human's logbook follows the name
across whichever suspect they play (`docs/architecture.md`, "Seats and
player identity").

### Convenience over secrecy

This is a family game, and David judged that friction costs more than
secrecy buys (2026-09-17; CLAUDE.md, "Settled decisions"). So a new
account's password is `password`, any non-empty password is accepted --
a single character included -- and the CLI prints passwords rather than
hiding them.

A player is offered a change **once**, right after their first login:
the app holds them on `/password` until they either type a new one or
click "Keep the one I have". Either answer settles it for good, and the
page afterwards only says who to ask. From then on the password changes
only through `users passwd`, which is David asking on their behalf. An
account made before this existed has no record of being asked, so it
reads as never offered and gets the question on its next login.

What is not traded away: a password is still only ever stored as a
Werkzeug hash (scrypt by default in Werkzeug 3), and the plaintext never
reaches the store, a record or the event log. The login still gates every
route, CSRF and the rate limit still stand, and 8.1b still runs the
service as a narrow identity, so the damage ceiling is the game store.
The open question this leaves, raised and knowingly accepted: the Cloud
Run service is reachable by anyone, and `password` is guessable.

## The gate

The Cloud Run service is reachable by anyone, deliberately: choosing
an app login means the login page is public and nothing else is
(`docs/phase8.1-plan.md` 3.6). So the gate is the whole security boundary,
and it is enforced in one place -- `auth.require_session`, registered as an
app-wide `before_request` in `create_app`. A route added later is private
unless someone marks it `@auth.public` on purpose, which is the safer way
round; `tests/test_web.py` walks the app's entire url map and asserts every
route but the login redirects, so a route added in step 3 is covered the
day it appears.

Alongside it:

- **CSRF.** Every form carries a token from the session, checked on every
  POST before anything else happens, including the login POST. The token
  is regenerated on login, so a token fixed before signing in is useless
  after.
- **Rate limiting.** A handful of attempts a minute per name, in memory.
  In memory is correct because the service runs `--max-instances 1`; were
  that raised, each instance would count separately. It is keyed on the
  name so that one account under attack cannot lock everyone else out, and
  cleared by a successful login.
- **The same answer for a wrong name and a wrong password**, in the same
  time -- `users.authenticate` hashes against a dummy when there is no such
  account -- so the login page is not a way to find out who has one.
- **The session cookie** is `HttpOnly` and `SameSite=Lax` always, and
  `Secure` when `CLUDE_WEB_HTTPS=1`. That variable is off locally, since a
  `Secure` cookie would never come back over plain http, and **the Cloud
  Run deploy must set it** (`docs/phase8.1-plan.md` 3.6).

## Layout

| File | What it holds |
|---|---|
| `clude_web/__init__.py` | `create_app`, the factory: config, store, blueprints, the gate. |
| `clude_web/config.py` | Secret, store URI and cookie policy. Imports no Flask. |
| `clude_web/auth.py` | The login blueprint, `require_session`, CSRF, `RateLimit`. |
| `clude_web/users.py` | Accounts as `users/<name>.json` documents. |
| `clude_web/board_svg.py` | The Classic grid as SVG, generated from `clude_core.board`. |
| `clude_web/replay_data.py` | Per-event lines and board frames, and the cached per-game belief trace. |
| `clude_web/tables.py` | Tables people play at (Phase 8.2): the registry that stores, drives and rebuilds every game, the form, and the view of a game from one seat. |
| `clude_web/chat.py` | Off-turn talk (Phase 8.3b): the reaction queue, the participation draw, the pacing and the caps. |
| `clude_web/watch.py` | Watch as a table with nobody human at it: the all-bot form and the names the Watch screen speaks. |
| `clude_web/views.py` | The lobby, a run's games, the replay, Watch, and the table routes (page, poll, work, answer, sit, deal, autopilot). |
| `clude_web/templates/` | Jinja templates; `base.html` is the shell, `table.html` the table. |
| `clude_web/static/style.css` | One stylesheet, every colour a variable. |
| `clude_web/static/table.js` | The table screen: polls, fires bot work, draws the decision and posts the answer; writes only text into the page. |

The stylesheet is plain on purpose. Typography, ornament, the decorated
board and its logo, and motion are Phase 10; what is there now is the colour
system those screens will inherit, declared once for light and once for
dark, so Phase 10 restyles the app by editing that block rather than hunting
through templates.

## The board and the replay data

`board_svg.board_svg(tokens)` returns the whole board as one `<svg>`
string, generated from `clude_core.board` and nothing else -- the rooms,
corridor, cellar, 17 doors and six start squares all come from the same
map the engine plays, so the drawing cannot drift from the rules. It sets
no colour at all: every shape carries a class and the stylesheet decides
how it looks, which is what lets Phase 10 replace the look without touching
the generator. A test fails on any class with no rule.

`replay_data` is split by cost:

- **`event_frames(record)`** folds the event log once and gives the board
  after every event with the line that describes it. Cheap, so it runs per
  request.
- **`cached_trace(store, record)`** gives every seat's belief after every
  suggestion, plus what each seat's floor has *proven*. This is slow --
  Plum alone is about 0.7 s a call, so a six-seat table is about a minute
  -- so it is computed once and written to `traces/<run_id>/<index>.json`
  beside the record. A document from an older version is rebuilt rather
  than trusted.

Two details worth knowing when drawing a seat's bars. A proven holder is a
seat index **or** the string `"envelope"`: a card proven to be the
envelope's is the strongest thing a seat can know, and a different claim
from "nobody has shown it". And a trace never calls `observe`, so White's
and Green's bars are a stateless reading of the evidence rather than what
they believed live -- the document carries that caveat as `limitation`, to
be shown on the screen rather than hidden.

## The lobby

`/` is the lobby, in four parts:

- **Play a game** (Phase 8.2, labels and defaults updated 2026-09-21).
  Six rows, one per token, with options in this order: **empty**, **open**,
  **floorbot**, **me (signed-in name)**, **X (LLM)**, **X (headless)**.
  X is that token's named character. Empty leaves the token out; open
  reserves it for another player; floorbot is the plain deduction bot.
  An LLM character combines its numerical method with Claude's persona,
  leashed decisions and chat; a headless character uses only its numerical
  method and never chats. LLM options remain visible but disabled without
  a service key. Three to six occupied/reserved seats, an optional seed,
  and "the characters remember", **checked by default**. Each remembering
  LLM seat has a memory-depth dial from 0 to 1, saved with the table.
  `static/lobby.js` shows the method only for character seats and the
  memory dial only for an LLM seat with remembering checked; the form
  still works without JavaScript. Stored seat kinds remain `character`
  (headless), `llm`, `floor`, `human` and `open`. Checkbox forms submit an
  explicit `remember=0` when unchecked; missing fields default to on.
  "Deal" starts the game at once, or, with an open
  seat, puts the table under **Tables** until people have sat and someone
  seated deals it. An open seat is reserved for someone: the table is
  not dealt until every one is taken (the button is disabled and the
  deal refused until then; David, 2026-09-21).
- **Tables.** Every unfinished table, newest first: who sits where,
  whether it waits for people, whose turn it is, and whether you are at
  it. A table survives closing the tab, a restart and a fresh Cloud Run
  instance. **End table** (anyone seated, or whoever started it) ends
  one for good, after a confirm: it leaves the lobby, its game is
  dropped and nothing is recorded; the same button is on a waiting
  table's page, and `clude_cli.py tables abandon ID --uri STORE` does
  it from outside the app (`docs/cli.md`).
- **Watch a game.** Characters only: tick who sits, pick a table size
  and optionally a seed, and step through it a turn at a time on the
  Watch screen. Nothing here can call a model, so nothing here costs
  money.
- **Stored games.** Every run in the store, the web app's own run (`web`)
  first. It is read from each run's summary, which already carries every
  game's seats, winner and length, so the lobby opens no game record at
  all: 51 runs list in about 0.3 s on Orbit. `/runs/<run_id>` lists that
  run's games, each a link to its replay.

## A table

`/tables/<id>` is a game with people at it (Phase 8.2,
`docs/phase8-plan.md` 3.2-3.5). It is Watch's layout -- the board on the
left, a column on the right, stacked on a phone -- plus the person's own
panel: a status line ("Your move.", "Waiting for Mustard to suggest.",
"Mustard named cards you hold. Show one."), the decision, the Accuse
panel, their hand, Table Talk, the log of the game as their seat saw it,
who else is at the table, and their notes.

**The decision** is one form at a time, from the request the game is
stopped on. A move shows the legal destinations both as highlighted
squares and rooms on the board, at coordinates the server works out from
`clude_core.board` (so the geometry stays in one place, as the replay's
does), and as a list of buttons -- "Enter the Lounge", "Corridor, row 9,
column 7", "Stay where you are", "Secret passage to the Study". A
suggestion is two selects, the room fixed, and "Suggest" or "No
suggestion"; an accusation shows "Pass" and points at the Accuse panel;
a card to show, when another seat's suggestion names cards you hold, one
button per card, on someone else's turn. What you see is the engine's own
list of legal options, the same list a character scores. Each move also
carries `distances` -- every room and how many steps away it would leave
you, from `board.room_distances` -- as the button's and the board
target's tooltip.

The panel is rebuilt only when the decision itself changes, keyed on its
kind and `seq`. That matters because `seq` counts answers rather than
entries (Phase 9d): table talk, bot work and other people's moves do not
move it, so a poll landing while you are choosing leaves your dropdowns
alone. Before that fix a queued chat line put the table on a 1.5-second
poll and reset the Suggest selects under the player.

**Accuse** is its own panel, always there, shut, one red word. Opening it
shows the three selects, the Accuse button and Close. The selects are
built once when the page loads and nothing ever rebuilds them, so an
accusation you set up early is still set up later. Under the rules you
may only accuse at the accusation question, so the button is disabled
until that decision is yours -- the panel takes a red border then -- and
accusing still goes behind a confirm (David, 2026-09-22).

**Table Talk** is the panel above the log, with the say box: every
remark, whether a person's line, a character's aside on its turn or a
model seat's off-turn reaction. "The game so far" keeps the moves,
suggestions and accusations. A person's line is upright, a character's
italic. Both panels fold away -- click the heading -- and both start
open; the state is not remembered between page loads.

**Spectators.** Anyone signed in who opens a table they hold no seat at
is watching it: they see the board, the log and Table Talk in real time,
and the answer, say and autopilot routes all refuse them with a 403.
Asking for a view of a table you do not sit at is what puts you in its
gallery, for `WATCHING_FOR` (45 seconds, which outlasts a hidden tab's
slower poll), so closing the tab drops you within a poll or two. The
people *playing* see a line naming who is there, and no line at all when
nobody is; a spectator is not shown the gallery. Presence is kept in the
registry's memory rather than on the table document -- a poll arrives
every few seconds from every open page, and writing the store that often
would churn it for something true only for the next few seconds. A
restarted process forgets who was watching and learns it again on their
next poll. Watching needs an account (David, 2026-09-22): the table id
is not a capability URL, and the MCP endpoint remains the only route
outside the login gate.

**The notes** are the deduction floor from your seat: for every card,
who is proven to hold it and which holders are still possible. Every
cludebot gets the same sheet, so the person does too (David, 2026-09-18).

**The other seats**, to someone *playing*, are a plain roster: the
token, who holds it (a name, `(LLM)`, `(headless)`, `floorbot`), and
whether it is out or on autopilot. No deduction bars. At a real table
nobody can see how close another player is to solving it, so a seated
viewer gets `readings: null` (David, 2026-09-22, after game
`7075f3ae29`); it also spares a fresh belief per poll, most of a second
for Plum. Someone *watching* -- a spectator at a table, or the Watch
screen -- still sees Watch's compact bar for each seat: cards placed and
how sure its method is per category (David, 2026-09-18), with a human
seat showing what its floor has placed and no confidence.

**What the bars give away, and to whom.** `readings()` counts, from a
seat's own view, how many of the 21 cards it has proven a holder for.
At the deal the only thing a seat has proven is its own hand, so early
on the three numbers *are* that seat's hand composition by category.
Measured on seed 7 with six seats: for turns 0 to 9 all six seats' bars
read exactly as their hands, 5 of 6 by turn 12, 3 by turn 18, none by
turn 21. That is why a seated player no longer gets them. A spectator
and the Watch screen still do, knowingly (David, 2026-09-22): a
spectator telling a player what is in the bars is a social problem, not
a software one. The real game gives away nothing of the sort -- the
card backs are identical, the three stacks being separated only to
build the envelope before the remaining 18 are shuffled together and
dealt.

**What each viewer sees.** The card shown at a refutation is named only
to the suggester and the refuter, which is `ClueObservation.for_player`'s
rule; everyone else reads "Mustard disproved it". A spectator -- anyone
signed in who holds no seat -- sees the board, the log, Table Talk and
the bars and nothing else: no hand, no notes, no decision, no say box. A person whose token a
suggestion dragged into a room is told so, since the drag has no event of
its own, and may stay and suggest there on their turn, as the rules
allow.

**How it moves.** Nothing runs between requests: the service is billed
per request and has CPU only while one is in flight. So the page polls
(`GET /tables/<id>/poll?since=N`, a few seconds apart, slower while it
waits on a person, not at all while the tab is hidden) and fires one
unit of bot work (`POST /tables/<id>/work`) whenever the poll says work
is due: one bot turn, no sooner than a second and a half after the last,
so a run of bot turns reads at a human pace. The first caller takes the
game lock without waiting and does the work; everyone else comes
straight back; the poll never takes the lock at all, reading a snapshot
the driver publishes after every advance, so six browsers polling never
queue behind a slow turn. An answer (`POST /tables/<id>/answer`) quotes
the entry count it answers, so a stale or doubled submission is refused
rather than applied twice, and a bad answer -- a square not offered, a
card you do not hold -- is a 400 with the reason and the game is exactly
as it was. Every write is a form POST with the CSRF token, which the page
reads from a `<meta>` tag; a JSON body would fail the check on purpose.

**Autopilot.** "Let the floor bot play for me" hands your seat to the
stand-in -- the plain characterless player, so a seat on autopilot never
impersonates a character -- and "Take my seat back" takes it back. Anyone
seated may hand a seat to the stand-in once it has kept the table
waiting three minutes, and since 2026-09-21 nobody has to: the next unit
of `work` after those three minutes (`AUTOPILOT_AFTER`, 180 s; ten until 2026-09-21) hands the seat
over itself, flag and all, so a person who left never stalls a table;
they take it back with the button when they return. A person put out
by a wrong accusation is answered by the stand-in from then on -- all
they can do is show cards -- without the flag, so the table never
waits on someone with nothing left to decide. The clock is the
instance's: a cold rebuild starts it again.

**Surviving a restart.** A table's document (`tables/<id>.json`) holds
its setup and its *entries*: every answer sent in, with the length of
the event log when it was applied. A game is deterministic per seed and
every pause is deterministic given the entries before it, so a game
missing from memory is rebuilt by replaying its entries into a fresh
generator, which lands on the same pause, its pending decision included.
The rebuild replays every bot decision too, so a long six-seat game with
Plum and Green at the table can take most of a minute on a cold
instance; it happens only after the instance has idled to zero or a
redeploy, never while anyone is polling. The rebuild is single-flight,
so two polls arriving together do not both replay it.

**Characters remember.** On by default for new Play and Watch tables
since 2026-09-21; uncheck to opt out. With it on, the deal loads each
character's method memory from the store's `logbooks/` as `play
--logbook` does (Mustard's rows, White's per-opponent counts, Green's
posteriors), a model seat's logbook is attached for read-back and a
debrief (below), and the finish folds the game back in -- White's counts
under the person's account key, so a human's suggestion habits follow
them across whichever token they play. The document snapshots what was
loaded (Green's arms; the game ids Mustard's and White's documents held)
so a rebuild loads the same memory and not a document that has moved on
since, which would change the bots' moves. Green's arms are reloaded
from the latest document before the game's outcome is folded in, so two
tables finishing in either order lose nothing. The cost is Mustard's
tree retraining at the deal, about 30 s with his 116k-row memory; the
form says so.

**An LLM character** (Phase 8.3a, `docs/phase8-plan.md` 4.1 and
12). The seat form offers "Plum (LLM)" beside "Plum (headless)":
the same numerical character, its moves chosen by
Claude within its leash, its table talk in its voice. A model seat is
answered from outside the engine like a person's, one decision per
`work` call (two to three seconds each, the status line reading "Plum is
thinking"), and every answer is stored with the model's audit and the
lines it said, so a rebuilt table replays them without a call and the
record carries `llm_log` and `kind="llm"`. The form's **budget** is what
the table may spend (default `CLUDE_WEB_LLM_BUDGET`, $2); the service
has a daily cap besides (`CLUDE_WEB_LLM_DAILY_CAP`, $10); the spend is
metered per call into `spend/<date>.json` and shown under the status
line, and past either cap the character plays on by itself and the
line says so. Without a key the LLM option is disabled, submitted LLM seats are
refused, and nothing reachable from the URL can spend.

**Table talk** (8.3b). A seated person types a line under the log
(`POST /tables/<id>/say`, at most 240 characters, control characters
stripped); everyone reads it, every model seat hears it, and the engine
never does: "I don't have it" changes nothing about a forced show.
Model seats answer off-turn: a line, a suggestion resolving, an
accusation or another seat's remark opens the floor, each model seat
joins with probability `chattiness` (squared for a reply to a reply, so
a thread tails off), at most two are queued, each a few seconds out,
and `work` serves one at a time -- holding the next bot move until the
chatter has landed, so the table reads at a human pace. Two off-turn
lines a turn, forty a game, and the dollar budget bound the rest.

**The end.** The game is saved as an ordinary record in the `web` run,
human seats recorded with `kind="human"` under the account key, and the
page offers the replay, where everything is laid face up. With
"characters remember" on and a model seat at the table (8.3c), the
table first **wraps up**: each such seat writes its logbook entry
(`docs/logbooks.md`; 42 s and about $0.09 with Claude, one per `work`
call, the status line naming who is writing), with its dossier on every
opponent present, people by account key; the lobby lists the table as
wrapping up until then, and whoever has it open drives it. Before the
deal such a seat read its logbook back at its `memory` dial's depth, so
a character that has met you before comes to the table with its read on
you.

The same driver plays from the terminal: `clude_cli.py play --human
Scarlett` (`docs/cli.md`).

## The Watch screen

`/watch/<id>` plays a headless game a turn at a time, in Direction D's
order: the board first, the latest suggestion spoken under it, then a
compact bar per seat. **Next turn** plays one turn; **Play to the end**
plays the rest, which takes about 20 s with Plum or Green at the table
(well under a second without them). When the game ends it is saved as an
ordinary record in the `web` run and the screen becomes its replay.

Since Phase 8.2 a watched game is a table with nobody human at it: the
same driver (`clude_training.table.TableGame`), registry and
`tables/<id>.json` document as a game people play, advanced by the two
buttons rather than by polling. Watch remembers method memory by
default, with its own checkbox to opt out. With remembering off it plays
exactly the game `clude_cli.py play` would for the same roster, table size
and seed; with remembering on its stored memory snapshot also matters:
`clude_training.arena.headless_table` now builds its table through the
same `TableSetup.from_roster`, and the tests pin both the table and the
turn-by-turn game to the CLI's own code.

**What a spectator sees, and why so little.** The hands and the envelope
stay hidden until the end. That rules out the replay's per-card bars, and
not only for the obvious reason: every seat's own hand is proven to that
seat from the first turn, and all the hands together are exactly the
eighteen cards that are *not* the answer -- so showing each seat's cards
would put the envelope on screen before anyone moved. Instead each seat
shows:

| Part | Means |
|---|---|
| `9/21` | Cards it has placed: its own hand, plus whatever its floor has proven. |
| Filled cells, per category | How many of that category's cards it has placed. Red once it has proven the answer there. |
| Pale bar and % | How sure its own method is of its best guess in that category. |

No card is named. A refutation reads "Scarlett disproved it", never what
she showed -- which is all anyone but the two seats involved learns at a
real table. A wrong accusation is announced, as it is in the game.

**Surviving a restart.** Only the setup and the number of turns played
matter for a watched game (its entry log is empty); a game missing from
memory is rebuilt by dealing the same setup and replaying that many
turns, which the engine's determinism makes exact. Belief readings come
from fresh agents reset with the game seed, never from the agents
actually playing, so a reading cannot disturb the game and a rebuilt
game reads exactly as the live one did.

## The replay screen

`/replay/<run_id>/<index>` is Direction A, the scrubber: the board with
the tokens where they stood, a block per seat, the line for the current
step, and a slider with step buttons and the arrow keys (also Home and
End).

The whole game goes to the page once, as JSON in a `<script>` block, and
`static/replay.js` redraws from it -- so stepping never touches the
server. A real 4-seat game is about 148 KB. Token positions are sent as
SVG coordinates worked out server-side, so the board's geometry stays in
one place.

Each seat's three strips read in three states:

| Row | Means |
|---|---|
| Solid, full width | That seat has **proven** the card is in the envelope. |
| Greyed, struck through | It has proven someone **holds** it: settled and out. |
| Pale bar | Still open; the width is that seat's own belief it is the answer. |

A red mark is the truth. A replay is a post-game, omniscient view, so it
names the card shown at every refutation -- live, only the two seats
involved saw it.

The first open of a game computes its trace and takes about ten seconds;
every open after that reads the cache and is immediate.

## Looking at it

The screens can be seen without opening a browser by hand:

```powershell
& .venv\Scripts\python.exe scripts\clude_shots.py --dark --phone
```

It boots the app on a spare port against a throwaway store seeded from
real records, signs in, and writes a PNG per screen -- login, lobby,
lobby with an LLM memory dial, run listing, Watch and Play states, a
waiting table, and replay at its start, middle and end -- in light and
dark and at wide and phone widths. `--out DIR` chooses where they land; `--run` and
`--game` choose which game.

`tests/test_browser.py` drives the same browser and checks what markup
tests cannot: that every token lands where the payload says, that tokens
sharing a room never stack, that the arrow keys step the game, that a
proven envelope row is drawn solid and full, and that the board is
painted at all. It also checks the six seat labels, remembering defaults,
LLM memory-dial visibility and the lobby's fit at 390 px. It is skipped
unless `CLUDE_WEB_BROWSER=1`, like the
tests that need credentials, so the default suite stays fast.

Both need Playwright, which is optional:

```powershell
& .venv\Scripts\python.exe -m pip install playwright
& .venv\Scripts\python.exe -m playwright install chromium
```

An SVG rasteriser will not do instead. `board_svg` sets no colour at all,
so rendering the SVG alone gives an unstyled blank; only a browser applies
the stylesheet and runs `replay.js`.

## Deploying

The app runs on Cloud Run as the service `clude` in `clude-game`,
us-central1, at <https://clude-648214345192.us-central1.run.app>
(Phase 8.1b, `docs/phase8.1-plan.md` 3.6 and section 8).

As measured on 2026-09-18: a build and deploy takes about a minute; the
first request after the service has scaled to zero takes 8-10 s (a cold
start, the price of free idle time); after that the lobby is 0.6 s, a
replay 0.4 s once its trace is cached, and a watched three-seat game
plays to the end in about a second. A replay opened for the first time
computes its trace, which took 16 s for a three-seat game there against
about 10 s on Orbit.

As measured on 2026-09-19 with the live check below (Phase 8.2d and
8.3): a four-seat table with two people plays 63 turns in about 190 s
of wall time; the poll median is 93 ms, an answer 850 ms and a unit of
bot work 820 ms (n = 94, 92 and 77). The cold rebuild, a table three
answers in with no memory to load, polled after a redeploy in 0.1 s: a
rebuild replays the entry log, so a long table costs more, and a
remembering table pays Mustard's logbook load (about 30 s) on top. The
one live LLM table so far (David with White (LLM) and Peacock (LLM),
"remember" on, 58 turns, 28 off-turn lines) cost $0.34 against its $2
budget, with no fallbacks.

As measured on 2026-09-21, the first deploy of the combined app (Phase
9c, revision 6): the MCP endpoint answers `initialize` in 180 ms, and a
four-seat game resumed after Cloud Run replaced the instance mid-game
(the cold rebuild 0.1 s) polled at a median 112 ms, answered in
1,113 ms and did a unit of bot work in 1,074 ms (n = 67, 65, 53): about
a quarter slower than the threaded worker's numbers above, on one
sample. The worker boots in 8 s, as before. `live_check.bat play` can
trip if Cloud Run replaces the instance between two polls, which it did
that day; `resume` on the table it printed is then the check.

**Name the project on every command.** Orbit keeps a gcloud
configuration per project, and a command that relies on the active one
acts on whichever project was used last: forgetting to switch back from
zenbot would deploy clude into zenbot's project. Every command below
names its account and project, and anything added here should too:

```powershell
$A = '--account=clude-sa@clude-game.iam.gserviceaccount.com'
$P = '--project=clude-game'
```

### What is out there

| Piece | What it is |
|---|---|
| Service `clude` | The `Dockerfile`'s image: gunicorn with its uvicorn worker serving the combined ASGI app (Flask and, with `CLUDE_MCP_SECRET`, the MCP endpoint; Phase 9), one worker, 300 s timeout; 1 vCPU, 1 GiB; 0 to 1 instances, so idle time is free and the in-memory tables and login rate limit are simply correct. Before Phase 9 it was gunicorn's threaded worker on the Flask app alone. |
| `clude-run@clude-game` | The identity the service runs as. It holds **Storage Object Admin on `gs://clude-game-data`** and **Secret Accessor on `clude-flask-secret`**, and nothing else, so the most the internet-facing login page can ever expose is the game store. `clude-sa`, which is project owner, stays on Orbit. |
| `clude-flask-secret` | The session secret, in Secret Manager, generated for the service and never the same as the local `.env` one. Handed to the app as `FLASK_SECRET_KEY`. |
| `clude-mcp-secret` | The MCP endpoint's path segment (Phase 9), handed to the app as `CLUDE_MCP_SECRET`; `clude-run` holds Secret Accessor on it. Its value is the connector URL's last segment and nothing else guards the endpoint. |
| `clude-anthropic-key` | The workspace-scoped Anthropic key, in Secret Manager since Phase 8.3a, handed to the app as `ANTHROPIC_API_KEY`; `clude-run` holds Secret Accessor on it. With it the lobby enables "X (LLM)" seats; the spend is capped per table (`CLUDE_WEB_LLM_BUDGET`, $2 by default, the form may change it) and per UTC day (`CLUDE_WEB_LLM_DAILY_CAP`, $10), and the ledger is `spend/<date>.json` in the store. |
| `gs://clude-game-data/llm` | The service's store: a mirror of `data/llm`'s grid-era runs, cached traces and logbooks, plus the service's own accounts (`users/`), every table played or watched there (`tables/`), the games they became (`runs/web`) and the traces it computes. |
| `cloud-run-source-deploy` | The Artifact Registry repository the builds go to, with a cleanup policy that keeps the 3 newest images. |

What the URL can spend is bounded by the two caps: a table with model
seats stops calling the model at its budget and the whole service at
its daily cap, and past either the characters play on by themselves
(`docs/phase8-plan.md` 4.1, "The model on the web"). The service is
reachable without Cloud Run authentication on purpose: the app login is
the gate, and anyone can load the login page and nothing else.

### Deploying a new version

```powershell
gcloud run deploy clude --source . --region us-central1 `
    --service-account clude-run@clude-game.iam.gserviceaccount.com `
    --allow-unauthenticated --min-instances 0 --max-instances 1 --concurrency 8 `
    --cpu 1 --memory 1Gi --timeout 300 `
    --set-env-vars "CLUDE_WEB_HTTPS=1,CLUDE_WEB_STORE=gs://clude-game-data/llm,CLUDE_WEB_LLM_BUDGET=2.00,CLUDE_WEB_LLM_DAILY_CAP=10.00" `
    --set-secrets "FLASK_SECRET_KEY=clude-flask-secret:latest,ANTHROPIC_API_KEY=clude-anthropic-key:latest,CLUDE_MCP_SECRET=clude-mcp-secret:latest" `
    --quiet $A $P
```

`scripts\deploy.bat` is this command, runnable from any directory. The
key secret was made once, on 2026-09-19, from the key in `.env` written
to a temporary file so no newline rides along (a key with a trailing
newline fails every call):

```powershell
$k = (Get-Content .env | Where-Object { $_ -match '^ANTHROPIC_API_KEY=' }) -replace '^ANTHROPIC_API_KEY=', ''
[IO.File]::WriteAllText("$env:TEMP\clude-key.txt", $k)
gcloud secrets create clude-anthropic-key --replication-policy=automatic --data-file="$env:TEMP\clude-key.txt" $A $P
Remove-Item "$env:TEMP\clude-key.txt"
gcloud secrets add-iam-policy-binding clude-anthropic-key --member=serviceAccount:clude-run@clude-game.iam.gserviceaccount.com --role=roles/secretmanager.secretAccessor $A $P
```

`--source .` uploads the repo minus `.gcloudignore` and Cloud Build
builds the `Dockerfile` (Orbit has no Docker). The two ignore files keep
the key file, `.env` and `data/` out of both the upload and the image,
which `tests/test_deploy.py` checks; `gcloud meta list-files-for-upload`
shows exactly what would go. The image installs `requirements-web.txt`
only. `CLUDE_WEB_HTTPS=1` matters twice: it marks the session cookie
`Secure` and makes the app trust Cloud Run's forwarded scheme and host
(`ProxyFix`); without it the login would work but the cookie would not be
marked `Secure`.

### Checking a deploy with a game

`scripts/clude_live_check.py` plays a table on the service through the
same JSON routes the table screen uses, under two throwaway accounts,
and times every request kind (Phase 8.2d). `scripts/live_check.bat`
wraps it with the URL, the store and the accounts filled in, and
`scripts/deploy.bat` is the deploy command above; both run from any
directory on Orbit with the venv's interpreter. The sequence:

```powershell
scripts\live_check.bat play      # makes t8a and t8b if missing; a four-seat game to the end, then the replay
scripts\live_check.bat start     # a second table left three answers in; prints its TABLE id
scripts\deploy.bat               # the redeploy that empties the instance
scripts\live_check.bat resume TABLE_ID
scripts\live_check.bat cleanup   # removes t8a and t8b
```

`play` sits, deals, plays a four-seat game with two people to the end
and opens the replay; `start` leaves a second table three answers in;
`resume`, after a redeploy, is the cold rebuild: the first poll must
come back at the same pending decision, and its time is the rebuild
cost recorded under "Deploying" above. The two games stay in `runs/web`.

### Accounts and records in the cloud

Accounts are per store, so a cloud account is made against the bucket:

```powershell
& .venv\Scripts\python.exe scripts\clude_cli.py users add NAME --uri gs://clude-game-data/llm
```

New runs from Orbit reach the cloud with `store copy`, which overwrites
and so can be run again at any time (`docs/cli.md`):

```powershell
& .venv\Scripts\python.exe scripts\clude_cli.py store copy --uri data/llm --to gs://clude-game-data/llm
```

### Taking it down

`gcloud run services delete clude --region us-central1 $A $P` removes the
URL. The bucket's `llm/` prefix, the identity and the secret stay until
removed by hand.

## A seat over MCP (Phase 9)

A Claude in a chat window at claude.ai can play one seat of a table
itself, through an MCP server mounted beside the Flask app on the same
`TableRegistry` (`docs/phase9-plan.md`; built 2026-09-21). The chat
seat is an ordinary account in an ordinary human seat: it sits in an
open seat, the person deals from the browser, and it answers the
engine's decisions through seven tools -- `clude_tables`, `clude_sit`,
`clude_turn` (which holds for up to 60 s while the bots play, driving
the same `work` the browser does), `clude_answer` (which answers, folds
in the accusation that follows if told to, then holds the same way for
the next decision), `clude_say`, `clude_note` (a free-text note of its
own, kept on the table document and never an entry) and
`clude_autopilot` (the seat handed to the floor bot when a chat must
end). Every view is cut at a `since` cursor and kept compact -- one
line per seat, per event and per card -- because a chat pays for every
token it reads: the first live game (2026-09-21) ran out of room at
turn 30 on views of about 9,000 tokens (`docs/phase9-plan.md` 8). Its
answers are entered ``by="mcp"``, and the record shows it as a person
under its account key, so its dossier accrues like anyone's. It gets
the floor's numbers (the notepad) and nothing else: a chat player is
its own head (David, 2026-09-21; the first deploy's optional `head`, a
character's numbers beside the seat, is gone). The tool docstrings in
`clude_web/mcp.py` are the only instructions the player gets. A chat
seat that keeps the table waiting three minutes is handed to the floor
bot like any human seat, and an ended table tells it so.

**What the second live game changed** (game `7075f3ae29`, 2026-09-22;
`docs/phase9-plan.md` 8, "Eight fixes"). Four things the chat seat
reported, all fixed:

- *Table talk no longer stales a pending decision.* `seq` counted entries
  and a remark is an entry, so anyone speaking -- including the seat
  itself -- invalidated the answer it was composing. It counts answers
  now.
- *`accuse` folded into a suggestion lands.* It used to be tested against
  whatever was pending the instant the answer arrived, which after a
  suggestion is usually somebody else's card to show; `clude_answer`
  now waits for the seat's own next decision and answers the accusation
  there.
- *The board goes out once.* `clude_sit` and any `since=0` view carry
  `board`: the 25 x 24 picture and a legend for reading it, about 1,200
  characters, never repeated on a turn. `me.at` says where the seat's
  own token stands.
- *Every movement option carried `distances`*, each room and how many
  steps away it would leave you, so the seat need not walk the board in
  its head. (Replaced by one line per room after the third game, below;
  the browser keeps them in its tooltips.)
- *A spent budget is announced.* The view gains a `models` line when the
  table's model budget is gone. The characters play on with their own
  headless methods -- not the floor bot, which is only ever the autopilot
  stand-in -- but they also stop talking, which from the seat looked
  like the table had gone mechanical for no reason.

**What the third live game changed** (game `b089937cb8`, 2026-09-24;
`docs/phase9-plan.md` 8, "Phase 9f"). The chat seat found the notepad
the best part and named two costs:

- *A move is one line per room.* It had been every legal move, each with
  nine distances: 1,800 characters on average and 4,700 at 26 moves. A
  movement now carries `toward`, each room with what the best move
  toward it does ("enter it now", "3 steps short, ending at row 13, col
  19"), and the seat answers `{"toward": "Library"}`. That is about 500
  characters whatever the roll. The log records an ordinary move, and a
  move named outright still works.
- *Waiting is cheaper.* A call holds up to 60 s rather than 25 s, one
  deadline covering both of `clude_answer`'s waits. A reply with nothing
  new leaves out the notepad and the seats (467 characters rather than
  1,527) and says when the floor bot takes a person's seat. The seat asked
  for this after four or five empty replies in a row while David thought.

The third thing it asked for, a warning in `clude_say` against naming
its own hand, David declined (2026-09-25): players learn what
over-sharing costs.

**The account.** Make it once, per store, as any account:

```powershell
& .venv\Scripts\python.exe scripts\clude_cli.py users add claude --uri gs://clude-game-data/llm
```

`CLUDE_MCP_ACCOUNT` names another account if wanted.

**The guard.** The mount sits outside the login gate, and a claude.ai
custom connector sends either an OAuth flow or nothing, never a static
header, so the endpoint is a capability URL: `/mcp/<CLUDE_MCP_SECRET>`,
with anything else under `/mcp` a 404 and the secret 16 to 128 URL-safe
characters. That is the same trade "Convenience over secrecy" made for
the login: the damage ceiling is the game store, and what a stranger
with the URL could do is play Clue as `claude`. Without the variable the
endpoint is simply not mounted and the app serves as before.

**Serving.** `clude_web.mcp.combined_app()` is one ASGI app: Flask under
`/` (asgiref's bridge, with its one-request-at-a-time lane turned off so
Flask's requests still run in a thread pool) and the MCP endpoint under
`/mcp/<secret>`, stateless with JSON responses. The `Dockerfile` runs it
under gunicorn's uvicorn worker, one worker as before. Locally:

```powershell
$env:CLUDE_MCP_SECRET = 'a-local-secret-0123456789'
& .venv\Scripts\python.exe -m uvicorn "clude_web.mcp:combined_app" --factory --port 5000
```

The lobby is then at <http://127.0.0.1:5000/> and the endpoint at
`http://127.0.0.1:5000/mcp/a-local-secret-0123456789`; the plain
`flask run` command above still serves everything but the endpoint.
claude.ai reaches only a public URL, so the local endpoint is for the
SDK's own client (`tests/test_mcp.py` shows the shape) and the deployed
one is what a chat plays on.

**Deploying with the endpoint (9c, 2026-09-21).** The secret lives in
Secret Manager beside the Flask secret and the key, made once (the
value was generated by `secrets.token_urlsafe(24)`, 32 characters):

```powershell
$s = -join ((48..57 + 97..122) | Get-Random -Count 32 | ForEach-Object { [char]$_ })
[IO.File]::WriteAllText("$env:TEMP\clude-mcp.txt", $s)
gcloud secrets create clude-mcp-secret --replication-policy=automatic --data-file="$env:TEMP\clude-mcp.txt" $A $P
Remove-Item "$env:TEMP\clude-mcp.txt"
gcloud secrets add-iam-policy-binding clude-mcp-secret --member=serviceAccount:clude-run@clude-game.iam.gserviceaccount.com --role=roles/secretmanager.secretAccessor $A $P
```

`CLUDE_MCP_SECRET=clude-mcp-secret:latest` is in the `--set-secrets`
list of the deploy command and of `scripts\deploy.bat`, and the
connector is added at claude.ai (Settings, Connectors, add a
custom connector) with the URL
`https://clude-648214345192.us-central1.run.app/mcp/<the secret>` and no
authentication. A game then goes: make a table in the browser with one
open seat (and LLM seats if wanted; remembering starts on); in the chat, ask
Claude to sit; deal; Claude plays, `clude_say`ing as it goes; the
finished game shows in the lobby and replays like any other, the chat
seat labelled `claude`.

## Tests

`tests/test_web.py` runs Flask's test client against a `LocalStore` in a
temp dir, with no network and no real store. `tests/test_web_watch.py` pins the Watch screen and
`tests/test_web_tables.py` the table: two accounts play a game to the end
through the JSON routes, each reading only what its seat may; a bad
answer leaves the game alive; a cold registry rebuilds a table at its
pending decision; open seats, dealing, autopilot, reserved names and the
memory toggle. `tests/test_mcp.py` plays a whole game through the MCP tools on the
SDK's in-memory client, and checks the combined app's mount and guard
("A seat over MCP"). `tests/test_browser.py` adds the table page in Chromium:
the legal squares drawn where the server says, a click that plays the
move, and the reveal rule holding in the log. `TESTING` makes the app sign
its cookies with an ephemeral key, so a test never depends on the
developer's `FLASK_SECRET_KEY` and never signs anything with the real one.
