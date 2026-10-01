# Wikiclude (D20, was 10i): the plan

Status: **proposed 2026-10-01, David's four answers recorded the same day (section 7), W1 built that day on the branch `wikiclude` (section 9), awaiting his review.** Written in the shape of the other plan docs: context, what the code dictates, design, sub-phases, files, decisions, out of scope, and "as implemented". Where section 9 differs from the sections above it, section 9 is what was built.

## 1. Context: David's brief (2026-10-01)

- **Wikipedia-style**, by reference to WP:MOS, with exceptions. Not wanted: WP:BLP and its relatives. Attribution looser than WP:FA demands; **writing at WP:FA quality**. It wears clude's skins: what is borrowed is the organisation and the page layout, not Wikipedia's look.
- **Depth and breadth at once.** Readers are family and friends: high-schoolers, twenty-somethings, housewives, senior engineers and scientists, octogenarian parents and grandparents. The computer science and the mathematics are wanted, in digestible hyperlinked articles; so is the basic idea, with very clear examples, and pictures.
- **Hyperlink heavily**, "better too many than too few". Where our own pages run dry, link to Wikipedia, in a colour scheme distinct from the in-app links.
- **Sources.** The docs already written (`docs/strategy-glossary.md` and the rest), the old textbook on Drive, and the papers in the same Drive folder.

This is D20 of `docs/phase10-plan.md`, which replaced D13's two explainers: one article serves both audiences.

## 2. What I found

### 2.1 What the code dictates

- **Articles cannot live under `docs/`.** `.dockerignore` and `.gcloudignore` keep `docs/` out of the Cloud Run image. Articles, figures and the stylesheet go under `clude_web/`; `docs/` stays the source they are written *from*.
- **`/wiki` exists and is gated.** `views.wiki` renders a placeholder; `tests/test_web.py` asserts an anonymous visitor gets a 302 and a signed-in one sees "Wikiclude". The header's wooden question mark and the footer already lead there.
- **`legacy.css` is never edited**, so Wikiclude's rules cannot go into the look sheets symmetrically. They go in one new sheet, `static/styles/wiki.css`, loaded only on wiki pages after the look's sheet and `chrome.css`, under `chrome.css`'s rules: only tokens every sheet defines (`--ink`, `--ink-soft`, `--page`, `--panel`, `--edge`, `--accent`, `--accent-ink`, `--warn`), ASCII only, no literal durations. Any new colour (the Wikipedia-link colour) is a token `wiki.css` defines itself, once per theme.
- **Diagrams have a registry waiting.** `docs/ux/diagrams/build_diagrams.py` has `DIAGRAMS` (five keys today: `floor-then-method`, `floor-propagation`, `scarlett-update`, `scarlett-net`, `mustard-tree`), every fact read from the live modules. `docs/ux/vendor/README.md` already says how Wikiclude is to use it: pre-rendered, classed SVG, Mermaid's inline hex stripped, coloured by the stylesheet, built on a maintainer's machine under Playwright and committed. Nothing ships Mermaid to a browser.
- **The board and the logo already draw as uncoloured SVG** (`board_svg.py`, `logo.py`), so articles can embed the real board, a real room, a real door.
- **The image installs `requirements-web.txt` only.** Any rendering dependency must be added there, and should be pure Python.
- **Play is blind (10c).** Wikiclude explains how every character thinks in general; it never shows a live game's state, so it leaks nothing.

### 2.2 The sources, and two things I could not open

- **The repo's docs**: all read or outlined. The spine is `docs/strategy-glossary.md` (the six methods and every measurement), then `architecture.md`, `llm-wrapper.md`, `logbooks.md`, `board.md`, `web.md`, `cli.md`, the six personas and `rules.md`, and the phase plans for the history.
- **The Drive folder** is the Udacity deep-reinforcement-learning classwork: `RL cheatsheet.pdf` (read), the DQN paper in *Nature*, the dueling-DQN and prioritised-replay papers, DeepNash (Stratego, the one imperfect-information game paper here, and the most relevant to Clue), Heess et al. on locomotion, the DCGAN paper, OSMnx.
- **`RL text.pdf` would not open**: at 89 MB Drive returns no text for it, and it is too large to pull through this session. The classwork README calls the course textbook Sutton and Barto, *Reinforcement Learning: An Introduction* (2nd ed., 2018), which I know well enough to cite by chapter and section. **I am assuming that is the book; say if it is not.** Page numbers I will leave out unless you want to spot-check them.
- **Wikipedia itself is unreachable from this workspace** (the network policy refuses it), so I am working from WP:MOS as I know it, and every Wikipedia link target needs a check I cannot run here. Section 3.6 has the test for that, to be run on Orbit.

## 3. Design

### 3.1 What we take from the Manual of Style, and what we leave

**Kept**

- **Article anatomy** (MOS:LAYOUT): hatnote, infobox, lead, table of contents, body, then See also, Notes, References, Further reading, a navbox, categories. In that order.
- **The lead** (MOS:LEAD): the title in bold in the first sentence, and the whole article in up to four paragraphs that stand alone. Here the lead does double duty: it is the version for the reader who stops there.
- **Sentence-case headings**, no links in headings, no "The" at the head of a title where it can be avoided.
- **Encyclopaedic register**: third person, past tense for what was measured, present for how things work. No "we", no "you".
- **One spelling.** The docs and the placeholder already write "colour" and "encyclopaedia", and the game is British by birth, so British spelling throughout (MOS:ENGVAR asks only for consistency).
- **WP:TECHNICAL**, which is the guideline that matters most for this audience: write one level down, put the accessible part first, explain every symbol where it first appears.
- **The furniture**: a Main Page with a featured article and "Did you know", categories, navboxes, redirects, disambiguation where a word means two things (Green the character, green the token), All pages, Random article, What links here.

**Dropped or reversed**

- WP:BLP, notability, and every process page.
- **No original research is reversed.** Wikiclude is the primary source for clude: the measurements in the glossary are ours and are reported as such.
- **Overlinking is reversed.** Wikipedia links a term once per article; Wikiclude links it at its first appearance in every section.
- **Verifiability is loosened, not dropped**: every number carries a reference to the doc section or run it came from; general statements about a method cite the textbook or a paper where one of ours covers it, and otherwise lean on the Wikipedia link.
- Self-reference is allowed ("in clude", "at a clude table").

### 3.2 One article, every reader

Every method and concept article is layered, in this fixed order, so a reader can stop at any heading and have a complete answer at that depth:

1. **Lead.** What it is and why it matters at the table, in plain words.
2. **At the table.** One worked example from a real seeded game: these cards, this suggestion, this is what changed. A picture.
3. **How it works.** The idea, with small numbers a reader can check by hand.
4. **Formally.** The mathematics, every symbol defined.
5. **In clude.** The module, the constants, the choices made and why.
6. **Measured.** What the benchmark and the arena found, with the tables.
7. **Limitations**, where the method has a flaw that is the character.
8. See also, Notes, References.

Character articles are biographies: infobox (token colour, method, module, the five dials, win rate), Personality, How they think (a summary with a "Main article" hatnote to the method), How they play, Voice, Record, Memory.

### 3.3 Links

Three kinds, told apart by more than colour (a reader who cannot see the colours still has the marks):

| Kind | Written | Looks |
|---|---|---|
| In-app, to another article | `[[Professor Plum]]`, `[[Professor Plum\|Plum]]` | the red thread, `--accent`, as every link in the app is now |
| Wikipedia | `[[w:Dempster-Shafer theory\|Dempster-Shafer theory]]` | a blue of its own (`--wiki-out`, ink-blue on case-file light, pale blue on gaslight dark) with a small superscript mark; opens in a new tab |
| Source | a footnote, `[^glossary-scarlett]` | a superscript number; References links the doc on GitHub, or names the book and section |

**Red links.** A link to an article not yet written renders as a red link in the Wikipedia sense (dotted, faint) while the wiki is being built, and `Special:WantedPages` lists them. A test counts them, and the count must be zero before 1.0.0.

### 3.4 Pictures

- **The method diagrams** from `DIAGRAMS`, rendered once to classed SVG and committed (section 2.1). More keys as articles need them: Plum's search tree, Peacock's mass function, Green's arms, White's two-state chain.
- **The real board**, whole and in details, from `board_svg`.
- **Drawn figures**, as uncoloured SVG the stylesheet dresses: the notepad after a worked suggestion; belief bars before and after an update; Peacock's belief-and-plausibility interval (the two-tone bar of the original design notes); Beta curves for Green's Thompson sampling; the leash as a band around a character's own scores.
- **Charts** of the measured numbers (log-loss by checkpoint for the six methods, win and wrong-accusation rates), drawn from the same table of facts the text quotes (3.6).

Every figure has a caption and alt text, sits in a Wikipedia-style thumb frame, and is readable at 390 px.

### 3.5 Mechanics

- **Articles are Markdown files with a front-matter block**, one per article, in `clude_web/wiki/articles/`. Markdown because the sources are Markdown, because you can edit an article in VS Code and read the diff, and because Python-Markdown's own extensions give footnotes (References), the table of contents, tables and definition lists for nothing.
- **One new dependency: `markdown`** (pure Python), added to both requirements files. Wikilinks, the infobox, figures and the fact table are a small extension of ours in `clude_web/wiki/render.py`.
- **Mathematics**: written as LaTeX between `$...$`, rendered on the server to MathML, which every current browser draws natively: no script, no web font, nothing for a phone to download. That needs one more pure-Python package, `latex2mathml`. **If it looks poor on a phone when we see the first article, the fallback is KaTeX, vendored and self-hosted like the fonts.** I would rather show you both on Plum's article than argue it in the abstract.
- **Everything is rendered once, at start-up**, into an in-memory index: articles, redirects, categories, backlinks, the search index. A page view is a dictionary lookup. A malformed article fails the app's start and a test, not a reader.
- **Routes**, all behind the login like the rest of the app: `/wiki` (the Main Page), `/wiki/<title>`, `/wiki/Category:<name>`, `/wiki/Special:AllPages`, `/wiki/Special:Random`, `/wiki/Special:WhatLinksHere/<title>`, `/wiki/Special:WantedPages`, `/wiki/Special:Search`.
- **Layout.** At 390 px: the infobox full width under the lead's first paragraph, the contents collapsed, tables scrolling sideways inside their own frame. From about 900 px: a contents rail on the left, the article in a measure of about 70 characters, the infobox floated right, as Wikipedia has it.
- **Developer look.** The same pages on `legacy.css`'s tokens. No separate markup.

### 3.6 Keeping it true

- **Numbers come from one table.** `clude_web/wiki/facts.py` holds every measured number an article quotes, each with the glossary heading it came from; articles write `{{fact:plum.logloss.50}}`, never a literal. A test checks every fact's value appears under its heading in `docs/strategy-glossary.md`. This is 10i's old gate ("the featured article's numbers match the glossary"), made mechanical. When a number is re-measured, one line changes and every article follows.
- **Constants come from the modules**, the way the diagrams already do: Scarlett's boost and decay, Plum's budgets, the presets' dials are read from the code at render time, so an article cannot disagree with it.
- **Tests** (`tests/test_wiki.py`): every article parses; has a lead, a category, at least one reference; every in-app link resolves or is counted as wanted; every figure key exists; every page renders under all three looks; the stylesheet obeys `chrome.css`'s rules; and, under `CLUDE_WIKI_LIVE=1` only, every Wikipedia title we link to exists (run on Orbit, since this workspace cannot reach Wikipedia).
- **Screenshots**: `clude_shots.py` learns the wiki pages, so every look and both widths are looked at, not assumed.

## 4. The articles

About seventy, in eight categories. Titles are provisional; redirects make the short names work (`Plum`, `Scarlett`, `DS`).

| Category | Articles |
|---|---|
| **The game** | Clue; Rules of play; The board; Rooms (nine, one article with a section each); Secret passages; Suspects, weapons and rooms (the cards); The envelope; The deal; Suggestion; Disproof; Accusation; Detective notepad; Bluffing; Table talk |
| **The characters** | Miss Scarlett; Colonel Mustard; Mrs. White; Mr. Green; Mrs. Peacock; Professor Plum; The floor bot; The random bot; Claude (the chat seat) |
| **The methods** | Deduction floor; Constraint propagation; Naive Bayes; Exact posterior enumeration; Dempster-Shafer theory; Decision tree; Bandit ensemble; Thompson sampling; Markov chain; Belief; Uniform baseline |
| **The mathematics** | Probability; Conditional probability and Bayes' theorem; Independence; Counting deals (the combinatorics of a Clue deal); Log-loss; Entropy and bits; Softmax and temperature; Beta distribution |
| **Personality** | Personality dials; Accusation threshold; Bluff rate; Curiosity; Secrecy; Presets; Persona; The leash; Chattiness |
| **Memory** | Logbook; Method memory; The debrief; The memory dial |
| **Measurement** | Belief benchmark; Arena; Dial sweeps; Twin comparison; The landing rule (Plum's parking); Self-play; Determinism and seeds; The ring board (history) |
| **The app and the project** | clude; History of clude; The table; The lobby; Watch; Replay; Looks; The certainty tag; A seat over MCP; What a game costs; AIX Laboratories; and, later, the classwork archive (reinforcement learning, Markov decision processes, Q-learning, DQN) |

## 5. Sub-phases

| | What | Gate |
|---|---|---|
| **W1** | The engine (loader, renderer, routes, index), `wiki.css` in all three looks, the Main Page, and **three exemplar articles, one of each kind**: *Professor Plum* (a character), *Naive Bayes* (a method, the two diagrams that exist), *Suggestion* (a game concept), plus stubs for what they link to | David reads the three on his phone in both themes and says what to change. The style is settled here, before it is multiplied by seventy |
| **W2** | The other five characters, the other five methods, Deduction floor, Belief | Every character and method has its article; all numbers through `facts.py` |
| **W3** | The game | A newcomer can learn to play from the wiki alone |
| **W4** | Personality, the LLM wrapper, memory | |
| **W5** | Measurement and the mathematics | |
| **W6** | The app and the project; the classwork archive begun | |
| **W7** | The featured-article pass: every article reread against 3.1 and 3.2, "Did you know" filled, navboxes, zero red links, the live Wikipedia-link check | Zero wanted pages; the suite green; shots looked at |

W1 is the day's work that matters; W2 to W6 are mostly writing and go quickly once the style is fixed.

## 6. Files

New:

- `clude_web/wiki/__init__.py`, `render.py`, `index.py`, `facts.py`, `figures.py`
- `clude_web/wiki/articles/*.md`
- `clude_web/wiki/figures/*.svg` (committed renders of `DIAGRAMS` and the drawn figures)
- `clude_web/templates/wiki/` (`article.html`, `main.html`, `category.html`, `special.html`)
- `clude_web/static/styles/wiki.css`
- `scripts/build_wiki_figures.py` (the Playwright render of `DIAGRAMS` to classed SVG)
- `tests/test_wiki.py`

Changed: `clude_web/views.py` (the routes), `clude_web/templates/wiki.html` (removed), `requirements-web.txt` and `requirements.txt` (`markdown`, `latex2mathml`), `scripts/clude_shots.py`, `docs/ux/diagrams/build_diagrams.py` (new keys), `tests/test_web.py` (the placeholder assertion), `docs/web.md`, `CLAUDE.md`, `docs/phase10-plan.md`.

## 7. Decisions for David

- **W-D1. How the work reaches the repo.** This session is a cloud workspace with a read-only clone; you commit from VS Code. Either I push a `wikiclude` branch for you to pull and merge (needs push access granted to this session), or I hand you a patch to apply, or you open this chat from Orbit so I write into your working tree.
- **W-D2. The first slice.** W1 as above (engine and three exemplars, then your review), or straight on through W2 before you look.
- **W-D3. Who can read it.** Behind the login, as now, or public like Privacy.
- **W-D4. The textbook** is Sutton and Barto, 2nd edition (2.2). Confirm, or name it.

**David's answers (2026-10-01).** W-D1: push a branch. W-D2: W1, then his review. W-D3: **public**, reversing the plan's 3.5 ("behind the login like the rest of the app"). W-D4: yes, Sutton and Barto.

Assumed unless you say otherwise: British spelling; `markdown` and `latex2mathml` as the two new dependencies; MathML first with KaTeX as the fallback; red links allowed until W7; character articles under their full names with redirects from the short ones.

## 8. Out of scope

- Editing in the browser. Articles are files in the repo, edited like any other.
- Talk pages, revision history, user pages. `git log` is the history.
- The help layer (10h): tooltips, the welcome card and "How to play" are their own sub-phase, though "How to play" will mostly be a link into the wiki's Rules of play.
- Anything that shows a live game's hidden state.

## 9. As implemented: W1 (2026-10-01)

Built on the branch `wikiclude` in a cloud workspace, pushed for David to pull; the suite green there (9.6). Three full articles, thirty stubs, the engine, the stylesheet, the figures and the tests.

### 9.1 What is there

- **The engine**, `clude_web/wiki/`: `render.py` (the markup), `index.py` (`load()`, the `Wiki`), `facts.py`, `figures.py`, `sources.py`. `create_app` calls `wiki.load()`, so every article is rendered once per process and a broken one stops the app starting.
- **The routes**, in `views.py`, all `@public` (W-D3): `/wiki`, and `/wiki/<path:title>` for articles, `Category:`, `Figure:` and `Special:` (AllPages, Random, WantedPages, WhatLinksHere, Search). A page that does not exist answers 404 with what a search for its name finds.
- **The dress**, `static/styles/wiki.css`, loaded only on wiki pages after the look's sheet and `chrome.css`; `base.html` gained a `{% block head %}` for it. All three looks, light and dark, 390 px and wide, looked at in screenshots.
- **Three exemplar articles**: *Professor Plum* (a character), *Naive Bayes* (a method), *Suggestion* (a game concept), each layered as 3.2 has it.
- **Thirty stubs** (`kind: stub`), so that every link in the three leads somewhere: the other five characters (with infoboxes read from the code and the arena), the other five methods, Deduction floor, Belief, Uniform baseline, Log-loss, Belief benchmark, Arena, Landing rule, Clue, Accusation, The envelope, Detective notepad, Bluffing, Classic board, Personality dials, Leash, Persona, Table talk, Logbook, Claude, clude. Each is a hundred to two hundred words, sourced, and marked as a stub on the page. **Wanted pages: none.**
- **Figures**: six pawns; the worked example's deals and Scarlett's overshoot, computed by the real agents; two log-loss charts drawn from `facts.TABLES`; a suggestion going round a table; and the five `DIAGRAMS`, drawn by `scripts/build_wiki_figures.py` and committed under `clude_web/wiki/figures/`.
- **`scripts/clude_shots.py --wiki`** shoots the wiki's eleven kinds of page in every look and needs no stored games; the ordinary run shoots them too.
- **`tests/test_wiki.py`**, nineteen tests, one of them the live Wikipedia check.

### 9.2 Where it departs from the plan

- **Public, not gated** (W-D3). `tests/test_web.py`'s walk of the url map now excepts `main.wiki` and `main.wiki_page` beside the login and the privacy page.
- **Stubs were not in the plan's W1** beyond "stubs for what they link to"; there turned out to be thirty. They cost little and make the three articles navigable, and they are honest about being stubs. W2 to W6 replace them.
- **The worked example is not from a seeded game.** The plan (3.2) said "from a real seeded game". A position small enough to check by hand does not occur in a real game until every other card is placed, and building one through the engine proved nothing extra. Instead the example ("the Rope question": four open cards, one overheard answer) is a hand-built position run through the real `ExactEnumAgent` and `NaiveBayesAgent` (`facts.rope_question`), and its numbers reach the articles only through `{{code:...}}`. The same position serves Plum's article and Scarlett's, which is its point: one piece of evidence, two answers.
- **`{{table:...}}`** was added: a measured table is rendered whole from `facts.TABLES`, each row the literal line of the doc, which is both the data and what the test looks for.
- **Citations are checked**, which the plan did not ask for: every `{{cite:path|heading}}` must name a file in the repository and a heading in it.
- **References are renumbered** in the order the text cites them (Python-Markdown numbers them in the order they are defined).
- **`facts.py` holds copies**, with a test, rather than reading the glossary when the app starts: `docs/` is not in the image.
- **Method diagrams scroll, never shrink below three-quarters size.** Two of the five (`floor-then-method`, `scarlett-update`) are redrawn top-down for the wiki (`DIRECTION` in the build script): left to right they are over 1,200 px wide.
- **Not done in W1**: the board as a figure (it is drawn per look, dressed or not, and the wiki renders once; W3 needs it and will have to render both); a chart with all six methods (Mrs. White's token colour is the panel's colour in case-file light, so a White line needs an outline); `Special:Search` is plain word-matching.

### 9.3 Mathematics

MathML from `latex2mathml`, as planned. In desktop Chromium it is good. **It has not been seen on a real phone**, which is the open question of 3.5: a phone draws MathML with whatever mathematics font it has. If David's phone draws the *Naive Bayes* article's "Formally" section badly, the fallback is KaTeX, vendored; the articles' LaTeX would not change.

### 9.4 What I could not check from here

- **Wikipedia.** The workspace's network policy refuses it. The 61 Wikipedia titles the articles link to are ones I am confident exist, and none has been verified. Run the live check on Orbit before deploying: `$env:CLUDE_WIKI_LIVE = "1"; & .venv\Scripts\python.exe -m pytest tests\test_wiki.py -k wikipedia`.
- **The textbook.** `RL text.pdf` would not open (89 MB). It is cited as Sutton and Barto (2018), by chapter, once so far (the *Bandit ensemble* stub, Chapter 2). The other two books and two papers cited (Russell and Norvig; Domingos and Pazzani; Hand and Yu) are cited from memory at the level of the work or the chapter, with no page numbers.
- **Python 3.14.** The workspace has 3.13.

### 9.5 Three places the glossary disagrees with itself

Found while checking the articles against it; the wiki follows the tables. None is changed here.

1. "Plum -- Exact posterior enumeration" says he is "the best or joint-best belief at every checkpoint". The Phase 5 table under "Belief benchmark, FloorBot regime" has White ahead at 50% (1.28 to his 1.49) and Mustard at 25% (1.52 to 1.55). The later text has it right: "the best or joint-best method at 75% and 100%".
2. "Scarlett -- Naive Bayes" says she is worse than uniform at every checkpoint, "the only method that is". In the same table Peacock is too (1.68, 1.45, 1.10, 0.41 against 1.60, 1.36, 1.03, 0.40), as the Peacock paragraph two below it says.
3. The grid section says of Plum's fallback that "on the ring's FloorBot snapshots the budget held"; his own section and the Phase 5 findings say that on the ring he "falls back to sampling in nearly half of his calls" on early snapshots.

### 9.6 Tests

`tests/test_wiki.py`: 18 passed, 1 skipped (the live check). The whole suite: 563 passed, 33 skipped (545 and 32 before), and the 30 browser tests pass under `CLUDE_WEB_BROWSER=1`. Run on Python 3.13 in the cloud workspace.
