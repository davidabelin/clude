# Wikiclude (D20, was 10i): the plan

Status: **W1–W5 built; W6 and W7 remain.** Proposed 2026-10-01, with David's four answers recorded that day (section 7). W1 was built on `wikiclude`, merged and made live as `clude-00021-fmb` (section 9); W2 followed on `claude/great-knuth-e8o5tl` (section 10). The editorial pass and W3–W5 were completed locally on 2026-10-02 (sections 11–12). Where the implementation records differ from the original design, the later records describe what was built.

Current local status (2026-10-02): **52 full articles and one project stub, with no wanted pages.** W3–W5 article creation and local verification are complete (section 12). W6, the app and project, is next. These changes have not been deployed; sections 9–11 retain the earlier implementation and editorial records.

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
- **Portraits**: `clude_web/wiki/portraits.py` draws six cartoon busts as classed SVG, the clothes in each suspect's colour from the look, skin, hair and props in a fixed `pt-*` palette (`wiki.css`). Registered as `portrait-<suspect>`; the contact sheet is `docs/ux/portraits/index.html` (`build_portraits.py`). **Not yet in the infoboxes: awaiting David's review.**
- Screenshots of every new or rewritten page and figure in Case-file light and Gaslight dark, 1440 and 390 px; edge labels that Mermaid clipped or crossed were shortened until the diagrams read cleanly.

### 13.3 Pseudocode and the Algorithms entries

- **Algorithm boxes**: `!!! algorithm "Title"` around an indented code block, styled in `wiki.css` (no renderer change: Python-Markdown's fenced blocks cannot nest in an admonition, indented ones can). Boxes added to the six method articles, *Regularised Nash dynamics*, *Exact posterior enumeration*, *Deduction floor*, *Q-learning* (with a new *Double Q-learning* section) and *Deep Q-network*; each paraphrases the live code or the source, never copies it.
- **21 Algorithms entries** (`kind: stub`, category *Algorithms*, a navbox group each for the textbook line and for `rps`): *Mixed-strategy Nash equilibrium*, *Reactive strategies*, *Frequency counter*, *Pattern memory*, *Transition-matrix predictor*, *Ensemble voting*, *Multilayer perceptron*; *Bandit action selection*, *Dynamic programming*, *Monte Carlo methods*, *Temporal-difference learning*, *Sarsa*, *Dyna-Q*, *Monte Carlo tree search*, *Function approximation*, *Policy gradient*, *Actor-critic*; *Dueling network architecture*, *Prioritised experience replay*, *Generative adversarial network*, *Proximal policy optimisation*. Section numbers were checked against the archive copy of Sutton and Barto's contents; the cheatsheet's algorithms 1-15 are the dynamic-programming, Monte Carlo and TD boxes. New sources: `rps`, `schulman-2017`, `goodfellow-2014`. The stub banner now describes these entries; the W5 test allows stubs only in *Algorithms*.

### 13.4 Left

The portraits' placement after review; the live Wikipedia-title check for the new `[[w:...]]` links; W7's corpus-wide pass. Nothing here is deployed.
