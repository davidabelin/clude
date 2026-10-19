# Wikiclude (D20, was 10i): the plan

Wikiclude is clude's own encyclopaedia: one article per subject, written
for family and friends at every level of expertise at once, in Wikipedia's
organisation and clude's looks. It is public, it is the house reference the
model seats read, and its articles are Markdown files in the repo.

## Where it stands (2026-10-19)

**Built, live and public.** 96 articles across ten categories, zero wanted
pages, 98 distinct Wikipedia titles all confirmed to exist, one featured
article and 58 "Did you know" entries. Deployed and serving: `/wiki`
answers 200 without a login, as W-D3 decided (section 7).

| Category | Articles | | Category | Articles |
|---|---|---|---|---|
| Algorithms (all stubs, by design) | 21 | | Mathematics | 8 |
| The app | 16 | | Characters | 8 |
| The game | 10 | | Classwork | 6 |
| Measurement | 9 | | Personality | 5 |
| Methods | 9 | | Memory | 4 |

**W7 is complete.** Phase 14 finished the corpus-wide reread, live-link,
fact/citation and responsive gates on 2026-10-18 (section 17). The post-release
review on 2026-10-19 updates the statistics, guides and API descriptions
against the saved run evidence and current code; section 18 records its scope
and final checks.

**W8, the Phase 13 alignment pass, is done** (2026-10-16): section 14 was
its brief and [section 15](#15-as-implemented-w8-2026-10-16) is its
record. The encyclopaedia now describes the characters as Phase 13 left
them, and has an article on itself.

**W6 is done** in substance, though it was never formally closed: every
article it listed exists, including the classwork archive. W1–W5 are built
and verified.

**How to read the rest of this document.** Sections 1–8 are the original
design of 2026-10-01 and are still the style guide: section 3 in particular
governs every article and has not been superseded. Sections 9–13 are dated
records of what was actually built, and where they differ from the design
they win. Section 14 was the brief for W8 and section 15 its record. Stale
claims in sections 1–8 carry a dated correction where they would otherwise
mislead.

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

> **Both resolved since.** David confirmed Sutton and Barto the same day
> (W-D4), and Phase 12's pass checked the chapter and section numbers
> against the archive copy of the contents (13.3). The Wikipedia check runs
> on Orbit and **passed on 2026-10-15**: all 98 distinct titles the articles
> link to exist. Run it with `CLUDE_WIKI_LIVE=1` against
> `tests/test_wiki.py`.

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
- **Mathematics**: written as LaTeX between `$...$`, rendered on the server to MathML, which every current browser draws natively: no script, no web font, nothing for a phone to download. That needs one more pure-Python package, `latex2mathml`. **If it looks poor on a phone when we see the first article, the fallback is KaTeX, vendored and self-hosted like the fonts.** I would rather show you both on Plum's article than argue it in the abstract. *(Server-rendered MathML shipped and stayed: `latex2mathml` is in both requirements files and the KaTeX fallback was never needed.)*
- **Everything is rendered once, at start-up**, into an in-memory index: articles, redirects, categories, backlinks, the search index. A page view is a dictionary lookup. A malformed article fails the app's start and a test, not a reader.
- **Routes.** `/wiki` (the Main Page), `/wiki/<title>`, `/wiki/Category:<name>`, `/wiki/Special:AllPages`, `/wiki/Special:Random`, `/wiki/Special:WhatLinksHere/<title>`, `/wiki/Special:WantedPages`, `/wiki/Special:Search`. This originally said
  "all behind the login like the rest of the app"; W-D3 reversed that the
  same day and the pages are public, which is what shipped and what
  `test_wikiclude_is_public_and_every_kind_of_page_answers` holds.
- **Layout.** At 390 px: the infobox full width under the lead's first paragraph, the contents collapsed, tables scrolling sideways inside their own frame. From about 900 px: a contents rail on the left, the article in a measure of about 70 characters, the infobox floated right, as Wikipedia has it.
- **Developer look.** The same pages on `legacy.css`'s tokens. No separate markup.

### 3.6 Keeping it true

- **Numbers come from one table.** `clude_web/wiki/facts.py` holds every measured number an article quotes, each with the glossary heading it came from; articles write `{{fact:plum.logloss.50}}`, never a literal. A test checks every fact's value appears under its heading in `docs/strategy-glossary.md`. This is 10i's old gate ("the featured article's numbers match the glossary"), made mechanical. When a number is re-measured, one line changes and every article follows.
- **Constants come from the modules**, the way the diagrams already do: Scarlett's boost and decay, Plum's budgets, the presets' dials are read from the code at render time, so an article cannot disagree with it.
- **Tests** (`tests/test_wiki.py`): every article parses; has a lead, a category, at least one reference; every in-app link resolves or is counted as wanted; every figure key exists; every page renders under all three looks; the stylesheet obeys `chrome.css`'s rules; and, under `CLUDE_WIKI_LIVE=1` only, every Wikipedia title we link to exists (run on Orbit, since this workspace cannot reach Wikipedia).
- **Screenshots**: `clude_shots.py` learns the wiki pages, so every look and both widths are looked at, not assumed.

## 4. The articles

> **Superseded as an inventory, 2026-10-15.** The table below is the
> original forecast: about seventy articles in eight categories. What was
> built is 95 articles in ten, the two extra categories being *Algorithms*
> and *Classwork*, which Phase 12 added (13.3). Several titles changed in
> the writing -- *Counting deals* became *Combinatorics of a deal*, *The
> ring board* became part of *History of clude*. For what exists, read
> `clude_web/wiki/articles/` or the counts under **Where it stands**; the
> table is kept because it records the original shape of the thing and the
> reasoning behind the categories.

Titles are provisional; redirects make the short names work (`Plum`,
`Scarlett`, `DS`).

| Category | Articles |
|---|---|
| **The game** | Clue; Rules of play; The board; Rooms (nine, one article with a section each); Secret passages; Suspects, weapons and rooms (the cards); The envelope; The deal; Suggestion; Disproof; Accusation; Detective notepad; Bluffing; Table talk |
| **The characters** | Miss Scarlett; Colonel Mustard; Mrs. White; Mr. Green; Mrs. Peacock; Professor Plum; The floor bot; The random bot; Claude (the chat seat) |
| **The methods** | Deduction floor; Constraint propagation; Naive Bayes; Exact posterior enumeration; Dempster-Shafer theory; Decision tree; Bandit ensemble; Thompson sampling; Markov chain; Belief; Uniform baseline |
| **The mathematics** | Probability; Conditional probability and Bayes' theorem; Independence; Counting deals (the combinatorics of a Clue deal); Log-loss; Entropy and bits; Softmax and temperature; Beta distribution |
| **Personality** | Personality dials; Accusation threshold; Bluff rate; Curiosity; Secrecy; Presets; Persona; The leash; Chattiness |
| **Memory** | Logbook; Method memory; The debrief; The memory dial |
| **Measurement** | Belief benchmark; Arena; Dial sweeps; Twin comparison; The landing rule (Plum's parking); Self-play; Determinism and seeds; The ring board (history) |
| **The app and the project** | clude; History of clude; The table; The lobby; Watch; Replay; Looks; The certainty tag; A seat over MCP; What a game costs; AIX Protodyne (was AIX Laboratories); and, later, the classwork archive (reinforcement learning, Markov decision processes, Q-learning, DQN) |

## 5. Sub-phases

| | What | Gate | Status |
|---|---|---|---|
| **W1** | The engine (loader, renderer, routes, index), `wiki.css` in all three looks, the Main Page, and **three exemplar articles, one of each kind**: *Professor Plum* (a character), *Naive Bayes* (a method, the two diagrams that exist), *Suggestion* (a game concept), plus stubs for what they link to | David reads the three on his phone in both themes and says what to change. The style is settled here, before it is multiplied by seventy | Done 2026-10-01 (section 9) |
| **W2** | The other five characters, the other five methods, Deduction floor, Belief | Every character and method has its article; all numbers through `facts.py` | Done 2026-10-02 (section 10) |
| **W3** | The game | A newcomer can learn to play from the wiki alone | Done 2026-10-02 (section 12) |
| **W4** | Personality, the LLM wrapper, memory | | Done 2026-10-02 (section 12) |
| **W5** | Measurement and the mathematics | | Done 2026-10-02 (section 12) |
| **W6** | The app and the project; the classwork archive begun | | Done in substance: every article listed exists, the archive among them |
| **W7** | The featured-article pass: every article reread against 3.1 and 3.2, "Did you know" filled, navboxes, zero red links, the live Wikipedia-link check | Zero wanted pages; the suite green; shots looked at | Partly done: no wanted pages, the Wikipedia check passes (2026-10-15), navboxes and 47 "Did you know" entries in place. **Left: the corpus-wide reread, and the shots** |
| **W8** | The Phase 13 alignment pass: the six characters as people, table talk as conversation, the encyclopaedia's own fallibility, and the memory articles (section 14) | Every article agrees with the deployed prompts; a character reading its own article finds nothing that contradicts what it was told, and nothing that reinstates a retired instruction | **Next.** Brief in section 14 |

W1 was the day's work that mattered; W2 to W6 were mostly writing and went
quickly once the style was fixed. W8 arrived later, from Phase 13, and is
writing of the same kind: the style is long settled, so the work is all in
getting the substance to agree with the characters as they now are. Do W8
before W7's reread, so the reread sees the finished text once.

## 6. Files

> **As built it is larger, 2026-10-15.** `clude_web/wiki/` also holds
> `sources.py` (the bibliography) and `portraits.py` (the six engraved
> plates, Phase 12), and `clude_web/templates/wiki/` also holds
> `layout.html` and `figure.html`. `scripts/build_portraits.py` draws the
> contact sheet. No article work needs a new file: an article is one
> Markdown file in `clude_web/wiki/articles/`, and the renderer, the fact
> table and the tests already handle it.

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

**David's answers (2026-10-01).** W-D1: push a branch. W-D2: W1, then his review. W-D3: **public**, reversing the plan's 3.5 ("behind the login like the rest of the app"). W-D4: yes, Sutton and Barto. All four are settled and implemented; nothing in section 7 is an open question. Work now happens in David's working tree on Orbit rather than on a pushed branch.

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
4. (W2.) "Mustard -- Decision tree on game logs" describes the tree as splitting "ten times on `turn_fraction`, six on `possible_holders_frac`, twice on `distinct_namers`, and not yet on `named_beside_located`", and `docs/cli.md`'s `train-mustard` example shows 2,347 rows and 45 nodes; the tree as trained on the Classic board has 1,951 rows, splits seven, three, two and once on those features, and the wiki reads it from the code.

### 9.6 Tests

`tests/test_wiki.py`: 18 passed, 1 skipped (the live check). The whole suite: 563 passed, 33 skipped (545 and 32 before), and the 30 browser tests pass under `CLUDE_WEB_BROWSER=1`. Run on Python 3.13 in the cloud workspace.

## 10. As implemented: W2 (2026-10-02)

Built on the branch `claude/great-knuth-e8o5tl` in a cloud workspace, the day after W1 went live as `clude-00021-fmb`, and pushed for David to pull. Twelve of W1's thirty stubs became articles: the other five characters, the other five methods, *Deduction floor* and *Belief*. The suite green (10.5).

### 10.1 What is there

- **Twelve articles**, each in the shape section 3.2 fixed and W1's exemplars set: the five methods (*Exact posterior enumeration*, *Dempster-Shafer theory*, *Decision tree*, *Bandit ensemble*, *Markov chain*) as lead, at the table, how it works, formally, in clude, measured, limitations; the five characters (*Miss Scarlett*, *Colonel Mustard*, *Mrs. White*, *Mr. Green*, *Mrs. Peacock*) as biographies on *Professor Plum*'s pattern; and the two foundations, *Deduction floor* (the rules, the floor bot, soundness and incompleteness, what a person is told) and *Belief* (the contract, masking, P(correct) and its shortcut, the certainty tag, log-loss). 2,100 to 3,400 words each, 6 to 17 Wikipedia links each, every number through `facts.py`. Fifteen articles and eighteen stubs, about 39,000 words; wanted pages none.
- **One worked example, six answers.** The Rope question of W1 is now answered by every method on the real code: `facts.rope_question` runs `DempsterShaferAgent`, `DecisionTreeAgent`, `MarkovAgent` and `BanditAgent` beside Plum and Scarlett, scores Green's five arms against a revealed envelope and applies his one-lesson update; `facts.plum_search` traces the real `_Search` node by node; `facts.chain_example` fits White's chain to a stated sequence through the module; `facts.mustard_tree` reads the trained tree's size and splits. The *Belief* article's table is the six answers side by side (0.40 to 0.75 for one card, the count's 2/3 among them).
- **Eight new drawn figures** in `figures.py`, each computed from the code: `belief-six` (the six answers as columns), `plum-search` (the backtracking tree, 20 steps and 3 deals), `peacock-interval` (belief to plausibility, BetP marked), `mustard-path` (the questions down the tree), `white-chain` (the two-state chain on the sequence), `green-arms` (Beta curves after one lesson), `green-trust` (the arms' means from the glossary), `floor-notepad` (the floor's grid for the position). Looked at on a phone and wide in both themes.
- **`facts.py`**: nine new measured tables (`green.threshold`, `curiosity.grid`, `arena.ring.first`, `arena.ring`, `arena.grid.first`, `twin.ring`, `ladder.mustard`, `landing.repeats`) and about seventy new facts, each still checked against its heading in the doc; the glossary headings named once at the top. New `{{code:...}}` keys for the tree (its training set, size and splits per feature), Green's step and decay, White's prior, the certainty tag at each character's threshold, and the worked examples.
- **`sources.py`**: the founding works (Dempster 1967, Shafer 1976, Smets and Kennes 1994, Breiman et al. 1984, Thompson 1933, Norris 1997), and the Phase 5, 6 and 7 plans citable by heading.
- **The wooden question mark is every wiki page's logo** (David, 2026-10-02): in the side panel's home link beside the wordmark on every page, and above the welcome on the Main Page; `wiki.css` dresses it as `chrome.css` dresses the header bar's.
- **"Did you know"** draws eight hooks at random on each visit (`Wiki.hooks`), since fifteen articles now carry thirty.
- **Tests**: a W2 gate (`test_every_character_and_method_has_its_article`: the fourteen titles are full articles, and the six answers, the search's 20 steps and 3 deals, White's 9/14, the Dempster conflict of 1/4 and the tree's six-question path are what the articles say); the stub assertions moved to *Accusation*; the logo on the pages; `test_every_constant_an_article_prints_can_be_computed` now checks the keys the articles use rather than the static table. `clude_shots.py --wiki` shoots *Accusation* as the stub and *Deduction floor* as a twelfth page.

### 10.2 Where it departs from the plan

- **No new Mermaid diagrams.** Section 3.4 listed Plum's search tree, Peacock's mass function, Green's arms and White's chain as keys for `DIAGRAMS`. They were drawn in `figures.py` instead, because each is a *computed* figure, the real agents' numbers on the Rope question, which a Mermaid source written by hand could not be. The build script and the five committed diagrams are untouched.
- **The tree in prose.** *Decision tree* narrates the six questions Mustard's tree asks on the example, with the thresholds. Those are the trained tree's, so they reach the text as `{{code:example.mustard.step.N.threshold}}` and the like, computed on demand (`facts.code` resolves the pattern; a step the path does not have is a load error), and the path's six features are pinned in the gate test. Regrow the tree and the test says which articles to reread.
- **The glossary is stale about the tree.** Its Mustard paragraph and `docs/cli.md`'s `train-mustard` example describe the ring-era tree (ten splits on the turn, six on holders, 2,347 rows); the live tree has 45 nodes, 23 leaves, 1,951 rows and splits seven times on the turn. The articles read the tree, not the paragraph. A fourth item for 9.5's list.
- **A finding the articles are built on.** On the Rope question Mustard's tree sends all four open cards to one leaf (0.5 each: its path never asks whether a card is in an open fact), and White's chain goes the opposite way from the count (0.4 for the card the count puts at 2/3), because she reads the asking and not the answer. Both are the character, and both are now stated, measured and pinned.
- *Deduction floor* and *Belief* stay in the Methods category, as their stubs were.

### 10.3 What I could not check from here

- **Wikipedia**, as in 9.4: the articles now link to about a hundred titles, none verified from this workspace. Run the live check on Orbit before deploying: `$env:CLUDE_WIKI_LIVE = "1"; & .venv\Scripts\python.exe -m pytest tests\test_wiki.py -k wikipedia`.
- **The six founding works** are cited from memory at the level of the work or the chapter, like 9.4's; Norris is cited to Chapter 1, Shafer to Chapters 1-3, Sutton and Barto to Chapter 2.
- **A real phone**: 390 px in Chromium only. Python 3.11 here (3.13 for W1, 3.14 on Orbit); the suite passes on it.

### 10.4 Open

- W3, the game, is next in section 5's table; nothing in W2 changed its scope.
- The certainty-tag and spectator rules are now stated in *Belief* from `CLAUDE.md`; when 10h's help layer is written it can link there.

### 10.5 Tests

`tests/test_wiki.py`: 19 passed, 1 skipped (the live check). The whole suite: 565 passed, 33 skipped, about three minutes with `-n auto` (564 and 33 after W1's merge), and the 30 browser tests pass under `CLUDE_WEB_BROWSER=1`. Run on Python 3.11 in the cloud workspace, Playwright on the pre-installed Chromium.

## 11. Editorial pass before W3–W5 (2026-10-02)

Edited all fifteen full articles and eighteen stubs locally. *Suggestion*, *Deduction floor*, *Belief*, *Professor Plum*, *Exact posterior enumeration* and *Naive Bayes* received the deepest review. The target is clear, engaging encyclopaedic prose, guided by Wikipedia's [Manual of Style](https://en.wikipedia.org/wiki/Wikipedia:Manual_of_Style), [featured article criteria](https://en.wikipedia.org/wiki/Wikipedia:Featured_article_criteria) and [technical accessibility guidance](https://en.wikipedia.org/wiki/Wikipedia:Make_technical_articles_understandable), within Wikiclude's existing sourcing conventions.

### 11.1 Conventions for the next articles

- Start with a self-contained lead: what the subject is, its role in clude, and its main limitations. Explain the basic idea before introducing formal notation or implementation details.
- Use direct sentences, British spelling and third-person narration. Keep generous links, define technical terms and symbols at first use, and avoid rhetorical flourishes or unsupported superlatives.
- Follow plain explanation with an independently understandable example, then the mathematics, implementation and measurements. Preserve existing headings and section anchors when editing published articles.
- Character pages explain persona, playing behaviour and relevant history. Attribute persona descriptions and selected quotations; link to method articles for detailed algorithms. Technical explanations use the narrator's direct prose.
- Distinguish logical deductions, model assumptions and heuristics. An exact result is exact under stated assumptions; a method's score or confidence need not be a calibrated probability.
- Identify the board, benchmark or arena, checkpoint and recorded games behind a comparison. Use past tense for measurements. A recorded absence of wrong accusations does not establish that a character can never accuse wrongly.
- Review short descriptions, infoboxes, hooks, captions and stub summaries with the body. Keep measured values and current constants in `{{fact:...}}` and `{{code:...}}`, and retain equation, figure and citation markup.

### 11.2 Corrections made

- The Rope question is explicitly a constructed position evaluated by the real agents, as recorded in 9.2. Method comparisons use one observer's private information; character names identify algorithms, not separate seats with different views. The naive Bayes repetition example now states that Green holds the Hall and keeps the rest of the position fixed.
- Enumeration's exact card probabilities require a completed search and equal weighting of consistent deals. Its evidence model does not account for opponents' choice policies. Sampling frequency is a count of benchmark calls, not a fraction of each game spent sampling.
- Exact card marginals do not make the shared accusation score exact. In the Rope question, White and the Wrench each have probability 2/3; their product is 4/9, while their joint probability is 1/3. Scarlett's fixed-factor heuristic is distinguished from textbook naive Bayes.
- Peacock's pignistic probability is generally not the midpoint of belief and plausibility. Her bounds describe evidential support within her model, and their product is not a guaranteed lower bound on the true accusation probability. Green's decayed Beta records guide selection without calibrating which arm is best. Figure captions and accessible descriptions follow these distinctions.
- Benchmark and arena summaries now identify their measurement context. The floor's soundness-test description follows the actual completed-game checks; timing infoboxes identify the Classic-board halfway checkpoint. Five links to nonexistent Suggestion section labels now point to its existing "In the rules" heading.
- Stubs distinguish narrative logbooks from learned method state, explain that a zero leash permits tied top options, and describe historical model costs as historical. No W3–W5 stub became a full article.
- Screenshot review found that the renderer consumed fact and code templates inside mathematics before resolving their values. Both inline and display equations now substitute and track those values before MathML conversion, with regression checks for valid and unknown keys. The article equations remain unchanged.

Article titles, routes, redirects, categories and section headings are unchanged. All original fact, code, figure and measured-table keys and display equations remain. Changes to `figures.py` affect explanatory strings only; public APIs and game behaviour are unchanged.

### 11.3 Verification

- `tests/test_wiki.py` and `tests/test_web.py`: **67 passed, 1 skipped**. These cover loading, citations, measured values, computed examples, links, figures and public routes. The wiki suite is now 21 passed and one live check skipped; the two added cases cover substitutions in inline and display mathematics.
- The separate opt-in Wikipedia-title check: **1 passed, 21 deselected** with `CLUDE_WIKI_LIVE=1`. Wikipedia access succeeded and no missing titles were reported. This checks titles and redirects, not Wikipedia section fragments.
- A corpus audit checked all 33 articles' internal section links and confirmed stable titles, redirects, categories, headings, substitutions and display equations.
- The six priority articles were rendered in Chromium at 1440 px and 390 px in Case-file light, Gaslight dark, and Developer light and dark: **48 page/layout combinations**. Screenshots were reviewed for leads, infoboxes, examples, equations, tables and captions; navigation and local anchors were checked. No browser errors, missing images, MathML error elements, unresolved mathematical templates or page-wide horizontal overflow were found. Wide tables, long equations and diagrams retain their existing horizontal scrolling containers; their right edges were confirmed reachable at 390 px.
- All 33 edited pages also loaded publicly without authentication. Mobile verification remains Chromium at 390 px, rather than a physical phone, as in 9.3 and 10.3. The prose was reread for terminology, repetition, relevance and unsupported claims; editorial quality was assessed through review rather than article length.

W3, W4 and W5 remain the subsequent writing phases in section 5. This pass establishes the voice and accuracy conventions for them without changing their scope.

## 12. As implemented: W3–W5 (2026-10-02)

Written locally after David approved section 11's editorial pass. Seventeen remaining stubs became full articles and twenty new articles were added: **37 articles written or expanded, 52 full articles in total, one stub (*clude*) and no wanted pages.** The six characters and their method articles retain the preceding editorial pass.

### 12.1 Article inventory

| Phase | Expanded stubs | New articles |
|---|---|---|
| W3: the game | Clue; Classic board; The envelope; Accusation; Detective notepad; Bluffing | Rules of play; Rooms; The deal; Floor player; Random bot |
| W4: personality, wrapper and memory | Personality dials; Leash; Persona; Table talk; Claude; Logbook | LLM wrapper; Method memory; The debrief; Memory dial |
| W5: mathematics and measurement | Log-loss; Uniform baseline; Belief benchmark; Arena; Landing rule | Probability; Conditional probability and Bayes' theorem; Independence; Combinatorics of a deal; Entropy and bits; Softmax and temperature; Beta distribution; Dial sweeps; Twin comparison; Self-play; Determinism and seeds |

*Rules of play* gives a newcomer the setup, turn sequence, movement, private disproofs, notepad, accusation and elimination rules. *Rooms* has one section for each of the nine rooms. The remaining articles explain the controls and experiments with checkable examples before their notation and implementation details, following section 11.1.

### 12.2 Organisation and compatibility

The catalogue in section 4 was provisional. Closely related small topics stay together where a separate page would repeat the same explanation: cards in *Clue*, passages and ring-board history in *Classic board*, the five decision dials and presets in *Personality dials*, chattiness in *Table talk*, constraint propagation in *Deduction floor*, and Thompson sampling in *Bandit ensemble*.

All existing titles, redirects, categories and section anchors are preserved. In particular, *FloorBot* still redirects to *Deduction floor*, *Debrief* to *Logbook*, and *Counting deals* to *Exact posterior enumeration*. The new titles *Floor player*, *The debrief* and *Combinatorics of a deal* provide the additional depth without changing those established destinations. New links connect the complementary articles.

The shared navbox now includes game rules, other players, personality, memory, mathematics and measurement. `scripts/clude_shots.py --wiki` includes nine additional W3–W5 pages and uses *clude* as the remaining stub exemplar. Public APIs, game decisions and recorded measurements are unchanged.

### 12.3 Accuracy and illustrations

- Movement follows the current engine: a full roll except on room entry, explicit door-facing squares, no route revisits, occupied corridor blocking, passages as a movement alternative, and the one-turn stay permission after an actual summoning. Eliminated players retain their cards and refutation duty; the last active player still needs a correct accusation.
- The leash explanation follows the current menu code, including its held-card bluff exception and the absence of an upper confidence boundary forcing accusation at positive leash. Zero leash does not generally reproduce headless softmax or bluff choices; an always-failing backend is the tested identical-event control.
- Narrative memory, numerical method state and immutable game records have separate explanations. Memory depth zero still supplies the logbook head. The debrief sees the revealed deal only after play, and its tally counts successfully written entries rather than all participation.
- The Rope-question articles state Green's Hall ownership and the remaining hand capacities. They distinguish marginals of 2/3 from a joint probability of 1/3 and the product approximation of 4/9. Enumeration's exactness remains conditional on completed search and its uniform consistent-deal model.
- Benchmark checkpoints count suggestion prefixes, not elapsed turns. The articles explain that snapshots reconstruct card evidence rather than a full historical board state, and that Green receives revealed-outcome feedback between snapshots, including later views of the same game. His benchmark row describes that adaptive evaluation.
- Arena metrics identify their denominators, including seat-games, actual accusations, calls and accepted model choices. Historical tables name their board, seeds, recorded dates and configuration; the major grid tables precede the landing-rule change. Sampling-call frequency remains distinct from time spent sampling during a game.
- `facts.py` adds live setup, dial, memory-depth, loss and softmax examples. The softmax example reads the actual sampler's weights; the tests independently check its formula. New source entries link Shannon's entropy paper, the Thompson-sampling tutorial, the scoring-rule paper and NIST's Beta-distribution reference.
- Four new SVG figures show the production Classic board, an enlarged Conservatory door, the leash score band, and historical arena win/wrong-accusation rates. The board carries plain and dressed variants selected by the current look, with names enlarged for phone reading and namespaced floor-pattern references. `legacy.css` is untouched.

### 12.4 Verification and remaining work

- `tests/test_wiki.py` and `tests/test_web.py`: **70 passed, 1 skipped**. The wiki suite is 24 passed and one opt-in live check skipped. New checks cover the W3–W5 inventory, every public article route, internal section links, duplicate HTML/SVG identifiers, and independently computed examples. A rendered-markup assertion catches wikilinks accidentally split by Markdown tables. The old minimum-length and external-link quotas were removed; editorial quality is reviewed through the content.
- Separate `CLUDE_WIKI_LIVE=1` Wikipedia-title check: **1 passed, 24 deselected**. Access succeeded, with no missing titles reported. This does not validate Wikipedia section fragments.
- Compatibility review checked all 33 pre-existing articles against the committed baseline: titles, redirects, categories and heading anchors remain. All 53 article pages loaded publicly without authentication.
- Twelve representative W3–W5 pages were inspected in Chromium at 1440 px and 390 px in Case-file light, Gaslight dark, Developer light and Developer dark: **96 page/layout combinations**. Leads, tables, equations, captions, figures and navigation were reviewed. No page-wide horizontal overflow, browser errors, missing images, MathML errors, unresolved mathematical substitutions, broken local anchors or missing board-pattern references were found. Wide equations and result tables retain their scrolling containers.
- Screenshot review caught two labelled links split by Markdown table delimiters and board labels too small at phone width. After correction, the board, personality-dial and benchmark pages passed another **24 layout checks** across the same looks and widths. Phone verification remains Chromium at 390 px, not a physical device.
- The 37 authored articles were reread for terminology, grammar, relevance, assumptions and unsupported claims. The existing measured-value checks still agree with the recorded source tables. This completes W3–W5 locally; it does not constitute deployment or a final featured-article assessment.

W6 remains the app and project articles, followed by W7's corpus-wide featured-article pass. The *clude* stub is deliberately left for W6. The historical records in sections 9–11 remain unchanged.

## 13. As implemented: Phase 12's pass, visuals and algorithms (2026-10-07)

David's brief for Phase 12's wiki work (N7), the same day: more visuals (architecture diagrams, flowcharts of pathways, neural networks, images), starting with quick cartoon sketches of the characters; pseudocode, in the textbook's boxed style; and a short entry, with a little mathematics and pseudocode, for every heuristic and method of the classwork and of the `rps` project, used by clude or not. His answers: busts in the wiki first, reviewed on a contact sheet; a curated list of about twenty; textbook-style boxes; linking `github.com/davidabelin/rps` is fine.

### 13.1 Plum

- **New: *Regularised Nash dynamics***, Plum's method since 5 October: the network, what it reads and answers, the training rule (NeuRD, the regularised reward, the mixed population, the replay buffer), the three lessons of the trial runs, the measured record and its limits.
- ***Professor Plum* rewritten** for the network; PlumOG's record (counting, the budgets, Claude in the seat, the parking, his logbook) condensed into a *PlumOG* section, so every earlier fact stays cited. *Exact posterior enumeration* is now PlumOG's archived method (and the target of the `PlumOG` redirect); *DeepNash* gains an "In clude" section.
- **The Rope question was internally inconsistent** since N3: Green's Plum arm is the network, but *Bandit ensemble* still called it "Plum's count". `facts.rope_question()` now also runs the network (`example.policy.*`); the network gives Mrs. White 0.06 where the count gives 2/3, and the prose in *Bandit ensemble*, *Mr. Green*, *Belief*, *Markov chain* and the method articles says so. `tests/test_wiki.py` pins the best and worst arms so new weights cannot silently contradict the prose.
- Every measured table before Phase 12 labels its Plum row `[[PlumOG]]`; new tables (`bench.policy`, `arena.policy`, `sweep.policy.accuse`, `leash.width`, `plum.run1`, `plum.run2`) quote the glossary's *The new Plum* section and `docs/deepnash-plan.md`, now a citable doc. About twenty articles had one-line tense or attribution fixes.

### 13.2 Visuals

- **Mermaid diagrams** (in `docs/ux/diagrams/build_diagrams.py`, drawn by `scripts/build_wiki_figures.py`): `architecture`, `decision-pathway`, `plum-training-loop`, and for the algorithm pages `gpi`, `mcts-phases`, `actor-critic` and `gan`. `floor-then-method` now names Plum's network. Mermaid's layout varies with the machine's fonts, so only the diagrams whose content changed were recommitted.
- **Drawn figures** (`figures.py`): `plum-network` (sizes read from `deep_nash`), `plum-policy-logloss` and `plum-checkpoints` (from the fact tables).
- **Portraits**: `clude_web/wiki/portraits.py` draws the six as engraved plates in classed SVG: hatching computed by `_hatch` (no patterns or ids), a muted fixed `pt-*` palette (`wiki.css`), brass-and-leather props and suspicious faces. The first pass, flat cartoon busts in the looks' suspect colours, was redrawn at David's request ("more etched, muted colors, steampunk feel; sinister, suspicious expressions"), and Plum's mortarboard dropped ("it's a party"). Registered as `portrait-<suspect>`, they are the character infoboxes' figures; each token moved to the top of its article's Character section. Contact sheet: `docs/ux/portraits/index.html` (`build_portraits.py`).
- Screenshots of every new or rewritten page and figure in Case-file light and Gaslight dark, 1440 and 390 px; edge labels that Mermaid clipped or crossed were shortened until the diagrams read cleanly.

### 13.3 Pseudocode and the Algorithms entries

- **Algorithm boxes**: `!!! algorithm "Title"` around an indented code block, styled in `wiki.css` (no renderer change: Python-Markdown's fenced blocks cannot nest in an admonition, indented ones can). Boxes added to the six method articles, *Regularised Nash dynamics*, *Exact posterior enumeration*, *Deduction floor*, *Q-learning* (with a new *Double Q-learning* section) and *Deep Q-network*; each paraphrases the live code or the source, never copies it.
- **21 Algorithms entries** (`kind: stub`, category *Algorithms*, a navbox group each for the textbook line and for `rps`): *Mixed-strategy Nash equilibrium*, *Reactive strategies*, *Frequency counter*, *Pattern memory*, *Transition-matrix predictor*, *Ensemble voting*, *Multilayer perceptron*; *Bandit action selection*, *Dynamic programming*, *Monte Carlo methods*, *Temporal-difference learning*, *Sarsa*, *Dyna-Q*, *Monte Carlo tree search*, *Function approximation*, *Policy gradient*, *Actor-critic*; *Dueling network architecture*, *Prioritised experience replay*, *Generative adversarial network*, *Proximal policy optimisation*. Section numbers were checked against the archive copy of Sutton and Barto's contents; the cheatsheet's algorithms 1-15 are the dynamic-programming, Monte Carlo and TD boxes. New sources: `rps`, `schulman-2017`, `goodfellow-2014`. The stub banner now describes these entries; the W5 test allows stubs only in *Algorithms*.

### 13.4 Left

The live Wikipedia-title check for the new `[[w:...]]` links; W7's corpus-wide pass. Nothing here is deployed.

> **Updated 2026-10-15.** The Wikipedia-title check has been run and passes
> for all 98 titles. Everything here is deployed: the wiki went out with
> the Phase 13 step 4 release (`clude-00029-8k8`, 2026-10-14) and `/wiki`
> serves publicly. At this checkpoint W7's corpus-wide pass was pending; it followed
> W8 so it rereads the finished text.

## 14. W8: the Phase 13 alignment pass

> **Done, 2026-10-16.** This section is the brief as it was written on
> 2026-10-15; [section 15](#15-as-implemented-w8-2026-10-16) records what
> was built and where it departs.

**This is the brief for the next write.** Everything needed to start is in
this section; sections 1-8 remain the style guide, and section 3 in
particular still governs every article.

### 14.1 Why W8 exists

[Phase 13](phase13-plan.md) spent two weeks developing the six characters:
they were given interests, histories and opinions, told something about
their own nature, encouraged to listen and reply to each other, and allowed
to doubt the encyclopaedia instead of obeying it. Their memory now records
the evening as an occasion as well as the play. All of it is implemented;
step 4 has been live since 2026-10-14 and steps 5 and 6 are committed.

Wikiclude describes the arrangement that preceded all that. Nothing in it is
*wrong* about the game, and the three articles that actively contradicted
the new prompts were corrected on 2026-10-15 (14.2). But a reader meeting
Mrs. Peacock here still meets a probability method with a voice, not a woman
who keeps a ledger and watches FOX News, and *Table talk* still describes
conversation as something the game tolerates.

W8 closes that gap. It is writing, not engineering: no new file, no renderer
change, no new dependency. An article is one Markdown file in
`clude_web/wiki/articles/`.

### 14.2 What has already been done -- do not redo it

Phase 13's step 5 required the script and wiki changes to ship together, so
that a lookup could not hand a character back an instruction the prompts had
retired. Three articles *stated* the retired brief, and exactly those
sentences were changed on 2026-10-15:

- ***A seat over MCP***: the tool-table row, and the summary of the server's
  instructions.
- ***Claude***: the canon, in both the wrapped-model and the chat-seat
  paragraphs.
- ***LLM wrapper***: the paragraph that told the reader the rules trust the
  canon over recollection and table talk and never cite it aloud. It now
  carries the distinction in 14.3.

Section headings and `[[wiki links]]` were deliberately left alone, so
nothing else moved and no link broke. That was the minimum that keeps a
lookup honest. All three articles still need the rest of their alignment.

### 14.3 The three things to get right

Everything in W8 follows from these. Each is a decision David settled, not a
suggestion.

**1. The characters are people who also play Clue.** Shared background: all
six listen to NPR in the car, and a recent *New Yorker* is lying around
half-read. Mustard is a proud, coy Freemason -- jewels, winks, discretion --
and he and Peacock watch FOX News and believe it. Green is a movie buff;
Scarlett shares the interest, differently. Plum reads *The Economist*. White
follows French news. They have been told they are models playing parts, and
their belief, doubt, concern or indifference about that varies by
temperament; none owes anyone a speech about it. Gentle strokes: an ordinary
interest can fill a whole evening without a word about the fourth wall.

**2. Conversation is part of the evening, not a tactical expense.** Holding
back a decisive inference can be shrewd; an evening spent silent is not
thereby better played, and the company is not a cost to be minimised. In the
mechanics: an on-turn line a seat writes is now spoken, because it arrives
in the same reply as the decision and dropping it bought nothing;
`chattiness` governs the off-turn reply draws alone, tapered by reply depth.

**3. The encyclopaedia is fallible.** This is the subtlest of the three, and
the prompts draw a three-way line that the articles must match:

- **On how this house plays** -- the board, movement, how a suggestion is
  disproved, what a wrong accusation costs -- Wikiclude is the better source
  than a model's own recollection of Clue, which differs from clude in
  places. This half was never authority over the characters; it was about a
  chatbot's memory of a different game, and it is kept.
- **On everything else** -- a biography, a method description, a reputation,
  an article about the character itself -- it may be doubted and disputed
  roughly as Wikipedia may be. Nothing in it outranks a card a character was
  shown, or what it watched someone do at the table.
- **Formal legality is the engine's**, in the menu a seat is given. No
  article decides it.

A character may now mention, quote or argue with the encyclopaedia. Knowing
a thing without parade remains the style; the prohibition is gone.

### 14.4 The worklist

| Article | What to bring in |
|---|---|
| *Miss Scarlett*, *Colonel Mustard*, *Mrs. White*, *Mr. Green*, *Mrs. Peacock*, *Professor Plum* | The lives in 14.3's first point, in each biography. The infobox and the method sections stay as they are: the methods did not change. Phase 13 also gave each a settled attitude to its own nature and to the encyclopaedia -- Mustard has never read it and does not intend to start, unless someone quotes it against him; Plum consults it by reflex and is the first to notice an article wrong about him; Peacock looks a thing up before she speaks; Scarlett skimmed it once; White reads the biographies rather than the mathematics |
| *Persona* | The scripts now carry lives as well as methods, with a light and individual fourth-wall premise. Say that the responses vary by temperament and are changeable, rather than fixing six answers |
| *Table talk* | 14.3's second point. The on-turn gate is gone; `chattiness` is the off-turn draw, tapered by depth; the reaction queue's caps (`MAX_QUEUED`, two served a turn, forty a game) are what actually bound an exchange |
| *Logbook*, *The debrief* | The debrief asks for the evening as an occasion as well as the play -- company, what an opponent was like to play with, the person as well as the player -- and tells a character not to write itself a rule against speaking. The cap is 8,192 tokens, covering the thinking and the reply together. Entries now record the company, and the live logbooks have good examples |
| *Memory dial*, *Method memory* | Check only: Phase 13 did not change either mechanism. Fix anything that implies memory is about tactics alone |
| *LLM wrapper* | Beyond 14.2's paragraph: one set of participant names across a seat's own turn, its off-turn replies and its debrief, where the on-turn prompt used to fall back to bare suspect tokens; and every model line cleaned as a person's is |
| *A seat over MCP* | Beyond 14.2's two sentences, the fuller account of what a chat seat is told, including the fallibility distinction |
| *Claude* | Beyond 14.2's two paragraphs, the same |
| *Personality dials* | `chattiness` is now the off-turn draw only. Say so, and keep `focus` out of it entirely |
| A fourth-wall article | **Optional**, and only if it serves the characters and the readers. If written, keep it modest, and do not copy long persona instructions into it |

### 14.5 Constraints that carry over from Phase 13

- **Do not invent a specific current headline** and present it as retrieved
  news. The media habits are fictional background; the application fetches
  no broadcasts or articles.
- **The additional interests floated in discussion** -- gardening,
  restaurants, gadgets, music -- are candidates, not settled facts. Choose
  only enough to make each part playable, and avoid filling six templates
  with matching numbers of quirks.
- **Do not name the Director** in shared material, or imply there is only
  one human the characters will ever meet.
- **A character editing Wikiclude stays deferred**, and so does the `focus`
  dial. Neither gets a field, a control, a schema or a placeholder here.
- **Do not copy long persona instructions** into several authorities at
  once. An article describes; the persona file instructs.

### 14.6 How to work, and how to know it is done

**Write against what is deployed, from the prompts themselves.** The source
of truth is `clude_llm/personas/*.md`, `clude_llm/personas/rules.md`,
`clude_llm/canon.py`, `clude_llm/logbook.py` and the MCP instructions in
`clude_web/mcp.py`. A paraphrase that drifts from them is precisely the
failure this pass exists to prevent, because a character can look the
article up. Phase 13's implementation record, the entries for 2026-10-14 and
2026-10-15, holds the exact wording and the evidence behind each change. The
live logbooks are worth reading too: the entries written after 2026-10-14
show the characters' own voices on the company, which is better material
than anything invented for them.

Section 3.6's rules are unchanged: every measured number through
`facts.py`, every constant read from the modules, every claim checkable.

**Gates.** Every article agrees with the deployed prompts. A character
reading its own article finds nothing that contradicts what it was told, and
nothing that reinstates a retired instruction. No wanted pages. The suite
green, including `tests/test_wiki.py`. The screenshots looked at.

**No paid work is needed.** The replay fixtures key on the prompts, not on
the encyclopaedia's prose; both were re-recorded on 2026-10-15 once the
prompts settled, so W8 can proceed without spend unless it changes a prompt,
which it should not. If an article change does require a prompt change, that
is a Phase 13 decision reopened, and it needs David before it needs writing.

**Then W7**, the corpus-wide reread, so it sees the finished text once.

## 15. As implemented: W8 (2026-10-16)

The Phase 13 alignment pass, written against the deployed prompts: Cloud
Run's active revision on 2026-10-16 is `clude-00032-bvr` (16:25 UTC), which
carries steps 5 and 6, and the working tree's persona, rules, canon, debrief
and MCP text is what was cited. The live logbooks were read first (entries of
14-16 October 2026, the first written under the broadened debrief), as 14.6
suggests; a few phrases that the Phase 13 record already quotes are used, no
entry is copied, and no person is named.

### 15.1 What changed

- **The six biographies** gain a section, *In company*, between *Character*
  and *How they think*: the interests and the shared background, what the
  character wants from company, its attitude to being told it is a model
  playing a part, and how readily it reads the encyclopaedia, each sentence
  from the persona file and cited to it. The *Character* sections were
  corrected where they quoted text the scripts no longer carry: White's "You
  read people, not cards" and "Cards do not lie" are gone from her script,
  Scarlett's confidence "meant to survive being wrong" is now a licence to own
  a remark that hurt, and the Phase 6 rule Peacock's looping prompted survives
  softened. The *Memory* sections say what the debrief now records and what
  each live standing-instruction list closes on. One "Did you know" each.
- ***Persona***, rewritten: voice and self-image; a life beyond the cards
  (14.3's first point, with the candidate interests left as candidates); the
  parts (the premise, six temperaments, nothing fixed, identity not inferred
  from a token); the shared rules as they now read; names; the five-scene
  rehearsal with its numbers.
- ***Table talk***, rewritten: conversation as part of the evening; what the
  characters are told; the on-turn line published as written, with the
  measured cost of the old gate; the reaction queue described from `chat.py`
  with its caps and delay as code values; chattiness as the off-turn draw
  alone, with the two games' reaction counts and why the taper was left;
  cleaning; what the debrief now asks about the talk.
- ***Logbook*** and ***The debrief***: the broadened fields with their caps as
  code values, the 2026-10-14 audit, the deployed outcome, the 8,192-token cap
  covering thinking and reply, Plum's lost and re-run entry, one set of names.
- ***Memory dial***, ***Method memory***, ***Personality dials***: one
  sentence each; `chattiness` is the off-turn draw and `focus` is not
  mentioned.
- ***LLM wrapper***, ***A seat over MCP***, ***Claude***: the published
  on-turn line and the cleaning, one set of participant names, the chat seat's
  instructions in full (a new section, *What the chat seat is told*), and links
  to the new article.
- ***Wikiclude***, the optional article, written as the encyclopaedia's entry
  on itself: what it holds, who reads it (people, wrapped characters through
  the index and two tools, chat seats through two more), the three-way line on
  how far to trust it, a table of what each character makes of it, and how it
  is kept true. Redirects *The encyclopaedia*, *Canon*, *The canon*, *House
  encyclopaedia* and *Wiki*; in the navbox's app row; linked from *clude*.
- **`facts.py`** carries the measured numbers the new text quotes, from the
  Phase 13 record (the gate's 81 written, 39 spoken, 42 dropped; the two
  games' 22 and 41 reaction lines and the twelve runs of three; the
  rehearsal's 30 lines, 22 free of game terms, 73%, $0.1373; Plum's re-run at
  3,407 output tokens and $0.1281; the audit's 78 entries and six clauses) and
  the canon plan's 41 calls, each checked under its heading by the existing
  test, and the live constants the articles print: the reaction queue's caps
  and delay, the 240-character line, the eight-remark window, and the
  logbook's word and list caps. `sources.py` makes `docs/phase13-plan.md` and
  `docs/canon-plan.md` citable.

### 15.2 Where it departs from the brief

- **The fourth-wall article became *Wikiclude*.** The fourth wall itself is
  one section of *Persona* (*The parts*), and a separate article would have
  duplicated it; what the encyclopaedia lacked was an article about itself,
  which is where a character's lookup of "the encyclopaedia" now lands, with
  the trust line and the six attitudes in one place. It is modest, copies no
  persona instruction, and cites the rules file for every claim about what a
  character is told.
- **Two more docs are citable.** 14.6 says every measured number goes through
  `facts.py`, and the numbers this pass quotes are in the Phase 13 record and
  the canon plan, so both joined `sources.DOCS`; the test that checks each
  fact under its heading covers them.
- **The biographies' infoboxes and method sections are untouched**, as 14.4
  asks; the "Memory" row of each infobox still names the mechanism, and the
  prose beneath says what it now holds.
- **The new article moved the replay fixtures.** 14.6 said W8 needed no
  paid work because the recordings key on the prompts, not the prose. True
  of the prose, but not of a *title*: the canon's index block names every
  article and is a cached system block on every request, so a new article
  changes every replay key exactly as a persona edit does, and both
  exact-game recordings started missing the moment *Wikiclude* existed.
  14.6 did not foresee this, and the brief for any later new article should.
  Both rows in `tests/test_llm.py` carried a pending-refresh skip for the
  hour it took David to decide; he approved the refresh the same day rather
  than folding the article into another, and both games were re-recorded
  (15.4). The article itself says what happened, under *Keeping it true*.

### 15.3 Gates

- Every article was written from the deployed prompt files and the Phase 13
  record and cites them; nothing reinstates the retired authority brief or a
  rule against talking, and a character reading its own article finds the
  attitude its script gives it.
- 96 articles (75 full, 21 algorithm stubs), no wanted
  pages, 58 "Did you know" entries, 86,688 words.
- `tests/test_wiki.py` passes; the whole offline suite and the screenshots
  are recorded in 15.4.

### 15.4 Verification

- **The replay fixtures are refreshed** (approved by David, 2026-10-16),
  the same two games as 2026-10-15, neither making a lookup and no seat
  falling back, which is what makes the replay strict:
    - Seed 1, `Scarlett,Peacock` at three players: envelope
      `Mustard/Rope/Ballroom` as the seed dictates, winner `P1 Mustard
      (floor)`, 35 turns and 14 suggestions where the 2026-10-15 row had 29
      and 13; 17 remarks across the two model seats. $0.1602.
    - Seed 2, `Plum,Mustard,Green,White` at four: envelope
      `Scarlett/Candlestick/Ballroom`, winner `P1 White`, 10 turns and 2
      suggestions, the row unchanged for the third recording running.
      $0.0362.
    - $0.1964 together. A first attempt ran the CLI without the API key
      (the CLI does not read `.env`), so every call fell back and the
      fixtures were overwritten with fallback recordings; they were
      restored from git before the real run. Nothing was spent on it.
- `python -m pytest -q -n 4` on the whole offline suite: 622 passed, 34
  skipped, the two exact-game replays among the passing. Before the
  refresh those two were the only failures. A first run with `-n auto`
  crashed its workers with a `MemoryError` while the screenshot browser
  was starting beside it; run on its own it passes.
- `tests/test_wiki.py` passes: every citation names a real file and heading,
  including the Phase 13 record's and the canon plan's; every measured
  number is found under its heading; every constant computes; no wanted
  pages; every page renders under every look.
- Screenshots: `clude_shots.py --wiki --phone --dark` run after the suite (its
  browser cannot start inside the agent sandbox, and starting it beside a
  `-n auto` suite is what crashed the workers). Looked at: *Professor Plum*
  wide and phone, with *In company* between *Character* and *How he
  thinks* and in the contents rail; *Logbook* on Gaslight dark, with the
  new section and the Phase 13 citations resolving; *A seat over MCP* on
  the phone, with the tool names wrapping inside the measure; and the Main
  Page, which lists *Wikiclude* under The app and counts 75 articles and
  21 stubs. The script's fixed page list has no slot for *Wikiclude*,
  *Persona* or *Table talk*; those three were proofread as rendered text.
- $0.1964 of approved paid recording; no cloud write, no deployment. The
  live store and Cloud Run were read only.

**Left:** W7, the corpus-wide reread against sections 3.1 and 3.2, now that
the text is finished.

### 15.5 The ring board leaves the players' pages (2026-10-16)

David's instruction, after W8: the ring board should never have been in the
encyclopaedia as a point of reference, so take it out wherever an article
makes sense without it, and leave it only where it is needed.

- **The six biographies** lose their ring-board benchmark table, the
  ring-board arena and twin-comparison numbers, and Green's arm-trust figure
  (which is drawn from the ring run); the Classic-board numbers that made the
  same point stay, and three footnotes per page that only the ring numbers
  cited are gone. Where a historical fact is the point, the board is "the
  earlier board": Scarlett's first threshold, Mustard's leash ladder, Plum's
  replacement and PlumOG's logbook experiment, and the first arena's wrong
  rate for Mustard.
- **The method pages** follow: *Naive Bayes*, *Decision tree*, *Markov chain*,
  *Bandit ensemble* and *Dempster-Shafer theory* drop the ring table (D-S gets
  the Classic one it lacked) and say "the earlier benchmark" where the ring
  result is the only evidence for a claim. *Exact posterior enumeration* keeps
  its "two boards" section, since PlumOG's story is the move between them.
- **Shared pages** with an incidental mention (*Logbook*, *The debrief*,
  *Personality dials*, *Method memory*) say "the earlier board".
- **Kept as they are**, because the board is their subject or the record is
  the point: *Classic board* (its history and the *Ring board* redirect),
  *History of clude*, *Dial sweeps*, *Measurement record*, *Leash*'s ladders,
  *Belief*'s two-board comparison, *Belief benchmark*, *Arena*, *Bluffing* and
  *Suggestion*'s ring-only bluff sweep, *Character training* and
  *Determinism and seeds*.
- `facts.py` is untouched: the ring-keyed facts and tables remain for the
  pages that still cite them, and no key is renamed.

`tests/test_wiki.py` passes and the whole offline suite with it; no title
changed, so the replay fixtures are unaffected.

## 16. Phase 14 Run 3 update (2026-10-18)

David selected Phase 14 Run 3 as the new headless Plum network. The public
Plum, regularised-Nash, character-training, belief, benchmark and history
pages now describe the fresh two-stage training and the balanced 26-line-up
tournament. Current tables come from the Phase 14 evidence; Phase 12's detailed
measurements remain in the maintainer glossary as a clearly superseded record,
not as claims about the committed file. Article titles did not change.

The live worked examples are evaluated through the new weights. The Rope
question still demonstrates the network's learned-distribution failure, but
the prose no longer generalises from an old benchmark to call the current
network the best of every method. `facts.py` adds Phase 14 tournament,
table-size and belief-benchmark facts, all checked against the current-results
section of the strategy glossary.

Run 3 moved one exact-game prompt path. With separate paid approval,
`llm_seed2` was re-recorded on 2026-10-18: six calls, no fallbacks or lookups,
$0.0348 estimated, with the same envelope, White winner, ten turns and two
suggestions. `llm_seed1` contains no Plum, still replayed exactly and was not
re-recorded. This was local documentation and test acceptance, not production
deployment.

## 17. Phase 14 recalibration and W7 final gate (2026-10-18)

The encyclopaedia now treats Phase 14 as the current calibration record.
*Dial sweeps* and *Measurement record* were rewritten around the frozen
post-landing-rule corpus, Run 3, the complete headless grids and the reconciled
paid screen. The five dial articles, adaptive-method pages and all six
biographies use the same current facts. Detailed superseded tables and their
unused fact keys were removed from public articles; a short archive note keeps
the historical boundary visible, while the evidence remains in maintainer
plans, the strategy glossary and git.

The paid run was not discarded after its provider-credit interruption. Valid
leash, chattiness and memory rows were retained, the compromised memory-0.5
attempt was recorded but excluded, and only the missing memory values resumed.
The sole shortlist, Plum leash 0.60, failed a separate 24-pair confirmation,
so no public preset changed.

W7's final gate passed. The offline corpus, fact and citation suite reported
28 passed with its network check skipped; the explicit live-link run reported
29 passed. Fresh screenshots of *Dial sweeps*, *Measurement record*,
*Professor Plum* and *Leash* at 390 and 1440 pixels showed the current tables
fitting in Case-file, Gaslight and Developer looks. The screenshots and test
results establish the local documentation gate. The same current pages were
verified over HTTPS after revision `clude-00038-jws` reached 100% traffic.

## 18. Post-release documentation review (2026-10-19)

This review includes the entire 96-article corpus, the 136 tracked Markdown
files and the 1,394 Python docstrings across 144 tracked Python files. The
corpus pass checks current implementation claims, dated measurements,
worked examples, article metadata, citations, facts, internal links and
rendering. The secondary pass checks guide ownership, plan status, CLI
examples, API contracts and side effects; it leaves valid historical records
dated rather than rewriting them as current results. Executable persona/rule
text and MCP gameplay instructions retain their existing behaviour.

Corrections include White's arena delta (1.25 points lost, rather than 3.1),
Green's frozen former live comparator (candidates themselves start fresh),
White's remembered-prior mass reduction from 4 to 2, and the distinction
between pooled seat-game rates and game-weighted paired intervals. New
doc-checked validation tables show where Mustard improved, where White stayed
close and where Green traded final-checkpoint loss for earlier improvements.
The public summary distinguishes a selected replacement from a uniquely best
network, candidate selection from independent confirmation, and point-estimate
guardrails from statistical non-inferiority. Eight all-model memory games do
not estimate individual win-rate benefit or establish equivalent depths.

The final-comment lifecycle now appears in the table, MCP, talk, records,
debrief, wrapper and cost articles, with fifteen registered MCP tools. Current
guides no longer present completed Phase 13/W7 work or the current fixtures as
pending. Old enumeration timings are identified as PlumOG evidence, and
historical table captions are explicit. Article titles, redirects and index
metadata remain stable, preserving the current recorded request keys.

Validation:

- Complete offline suite: **651 passed, 34 skipped** (`python -m pytest -q -n auto`), including both recorded LLM games.
- Focused wiki suite after the final source updates: **28 passed, 1 skipped**; the separate `CLUDE_WIKI_LIVE=1` Wikipedia-title check passed (**1 passed, 28 deselected**).
- Local Markdown audit: **170 file/anchor links**, no missing targets; wiki checks cover its separate wikilink, citation, fact and worked-example syntax, with zero wanted pages.
- Chromium audit: **111 pages at eight layouts, 888 checks**, no status, anchor, duplicate-ID, image, unresolved-markup, maths, page-overflow or scroll-reachability failures, and no browser errors. Layouts were 390 and 1440 pixels in Case-file light, Gaslight dark and Developer light/dark. Representative screenshots and table crops were inspected.
- Python syntax-tree comparison, with docstrings removed, finds executable changes only in wiki measurement data and the historical PlumOG figure label. Article metadata, persona/rules text, MCP gameplay instructions and stored LLM fixtures are unchanged.
- `git diff --check` passes. Audit scripts, JSON reports and screenshots remain under ignored `data/doc-review/`.

This review did not retrain, make paid calls, promote method state or deploy.
