# The web app

`clude_web` is the Flask app in front of the headless game (Phase 8.1,
`docs/phase8.1-plan.md`). It imports every other package; nothing imports
it, so the engine, the agents and the store stay exactly as testable
headless as they were.

Built: 8.1a, the local app -- the login gate and accounts, the lobby, the
replay scrubber and the Watch screen. The Cloud Run deploy is 8.1b.

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

The Cloud Run service will be reachable by anyone, deliberately: choosing
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
| `clude_web/watch.py` | A game watched a turn at a time, its compact readings, and the registry that stores and rebuilds it. |
| `clude_web/views.py` | The lobby, a run's games, the replay, and Watch. |
| `clude_web/templates/` | Jinja templates; `base.html` is the shell. |
| `clude_web/static/style.css` | One stylesheet, every colour a variable. |

The stylesheet is plain on purpose. Typography, ornament, the decorated
board and its logo, and motion are Phase 9; what is there now is the colour
system those screens will inherit, declared once for light and once for
dark, so Phase 9 restyles the app by editing that block rather than hunting
through templates.

## The board and the replay data

`board_svg.board_svg(tokens)` returns the whole board as one `<svg>`
string, generated from `clude_core.board` and nothing else -- the rooms,
corridor, cellar, 17 doors and six start squares all come from the same
map the engine plays, so the drawing cannot drift from the rules. It sets
no colour at all: every shape carries a class and the stylesheet decides
how it looks, which is what lets Phase 9 replace the look without touching
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

`/` is the lobby, in three parts:

- **Watch a game.** Tick the characters to seat, pick a table size (3-6)
  and optionally a seed; empty seats go to `floor` bots, and each
  character plays its own token, as it always does. "Deal" starts the game
  and opens it on the Watch screen. Nothing here can call a model, so
  nothing here costs money.
- **In progress.** Every watched game not yet finished, newest first,
  whoever dealt it -- so a game survives closing the tab.
- **Stored games.** Every run in the store, the web app's own run (`web`)
  first. It is read from each run's summary, which already carries every
  game's seats, winner and length, so the lobby opens no game record at
  all: 51 runs list in about 0.3 s on Orbit. `/runs/<run_id>` lists that
  run's games, each a link to its replay.

## The Watch screen

`/watch/<id>` plays a headless game a turn at a time, in Direction D's
order: the board first, the latest suggestion spoken under it, then a
compact bar per seat. **Next turn** plays one turn; **Play to the end**
plays the rest, which takes about 20 s with Plum or Green at the table
(well under a second without them). When the game ends it is saved as an
ordinary record in the `web` run and the screen becomes its replay.

It plays exactly the game `clude_cli.py play` would for the same roster,
table size and seed: the table comes from
`clude_training.arena.headless_table`, lifted out of the CLI for the
purpose, and the tests pin both the table and the turn-by-turn game to
the CLI's own code.

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

**Surviving a restart.** Only the setup and the number of turns played are
stored (`watch/<id>.json`); the game itself lives in memory. A game
missing from memory -- a restarted process, a fresh Cloud Run instance --
is rebuilt by dealing the same setup and replaying that many turns, which
the engine's determinism makes exact. Belief readings come from fresh
agents reset with the game seed, never from the agents actually playing,
so a reading cannot disturb the game and a rebuilt game reads exactly as
the live one did.

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
real records, signs in, and writes a PNG per screen -- login, the index,
and the replay at its start, middle and end -- in light and dark and at
wide and phone widths. `--out DIR` chooses where they land; `--run` and
`--game` choose which game.

`tests/test_browser.py` drives the same browser and checks what markup
tests cannot: that every token lands where the payload says, that tokens
sharing a room never stack, that the arrow keys step the game, that a
proven envelope row is drawn solid and full, and that the board is
painted at all. It is skipped unless `CLUDE_WEB_BROWSER=1`, like the
tests that need credentials, so the default suite stays fast.

Both need Playwright, which is optional:

```powershell
& .venv\Scripts\python.exe -m pip install playwright
& .venv\Scripts\python.exe -m playwright install chromium
```

An SVG rasteriser will not do instead. `board_svg` sets no colour at all,
so rendering the SVG alone gives an unstyled blank; only a browser applies
the stylesheet and runs `replay.js`.

## Tests

`tests/test_web.py` runs Flask's test client against a `LocalStore` in a
temp dir, with no network and no real store. `TESTING` makes the app sign
its cookies with an ephemeral key, so a test never depends on the
developer's `FLASK_SECRET_KEY` and never signs anything with the real one.
