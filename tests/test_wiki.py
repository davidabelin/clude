"""Wikiclude (D20, `docs/wikiclude-plan.md`): the encyclopaedia's own
tests.

Three kinds. The markup: wikilinks, Wikipedia links, facts, mathematics,
footnotes. The pages: public, under every look, with the wiki's own
bookkeeping pages. And the ones that keep it true, which matter most:
every measured number an article prints is found in the doc it cites,
every citation names a real file and heading, and the worked example
the articles walk through is what the real agents compute.

One test needs the network and is skipped without ``CLUDE_WIKI_LIVE=1``:
that every Wikipedia title the articles link to exists.
"""
from __future__ import annotations

import json
import os
import re
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

import pytest

from clude_storage import open_store
from clude_web import create_app, styles, users
from clude_web.wiki import WikiError, facts, figures, index, load, render, sources

ROOT = Path(__file__).resolve().parents[1]
NAME, PASSWORD = "David", "a-good-enough-password"

WANTED_BUDGET = 0
"""How many links may lead to articles nobody has written yet. Raise it
while a batch of articles is being written; it is 0 at a release
(`docs/wikiclude-plan.md` 3.3)."""


@pytest.fixture(scope="module")
def wiki():
    return load()


@pytest.fixture
def app(tmp_path):
    store = open_store(str(tmp_path))
    users.add_user(store, NAME, PASSWORD)
    users.mark_password_prompted(store, NAME)
    return create_app({"TESTING": True, "STORE_URI": str(tmp_path)})


def _csrf(client, path="/login") -> str:
    page = client.get(path).get_data(as_text=True)
    return re.search(r'name="csrf" value="([^"]+)"', page).group(1)


def _sign_in(client) -> None:
    client.post("/login", data={"name": NAME, "password": PASSWORD, "csrf": _csrf(client)})


def _squash(text: str) -> str:
    return " ".join(text.split())


def _section(doc: str, heading: str) -> str:
    """The text of `doc` under `heading`, up to the next heading at the
    same level or above, with white space squashed. The docs are
    hard-wrapped, so a phrase may straddle a line."""
    lines = (ROOT / doc).read_text(encoding="utf-8").splitlines()
    for i, line in enumerate(lines):
        match = re.match(r"(#+)\s+(.*?)\s*$", line)
        if match and match.group(2) == heading:
            level = len(match.group(1))
            body = []
            for later in lines[i + 1 :]:
                nxt = re.match(r"(#+)\s", later)
                if nxt and len(nxt.group(1)) <= level:
                    break
                body.append(later)
            return _squash("\n".join(body))
    raise AssertionError(f"{doc} has no heading {heading!r}")


# --- keeping it true --------------------------------------------------------


def test_every_measured_number_is_in_the_doc_it_cites():
    """`facts.FACTS` and `facts.TABLES` are copies: `docs/` is not in the
    image. Each must still be what its doc says, under the heading it
    names, so a re-measurement that changes the glossary fails here until
    the wiki follows."""
    for key, fact in facts.FACTS.items():
        needle = _squash(fact.find or fact.value)
        assert needle in _section(fact.doc, fact.heading), f"{key}: {needle!r} is not under {fact.heading!r} in {fact.doc}"
    for name, table in facts.TABLES.items():
        text = _section(table.doc, table.heading)
        assert len(table.columns) == len(table.keys) + 1, name
        for row, (_, literal) in table.rows.items():
            assert _squash(literal) in text, f"{name}.{row}: the row is not under {table.heading!r} in {table.doc}"
            assert len(table.cells(row)) >= len(table.keys), f"{name}.{row}"
            assert facts.fact(f"{name}.{row}.{table.keys[0]}") == table.cells(row)[0]


def test_every_citation_names_a_real_file_and_heading(wiki):
    """A doc cited by path must exist and have the heading cited; a
    module must exist; a book or paper must be in `sources.SOURCES`."""
    checked = 0
    for article in wiki.pages():
        assert article.cites, f"{article.title} cites nothing"
        for key, locator in article.cites:
            if key in sources.DOCS:
                assert (ROOT / key).is_file(), key
                if locator:
                    _section(key, locator)
            elif sources.is_path(key):
                assert (ROOT / key).is_file(), f"{article.title} cites {key}, which is not in the repository"
            else:
                assert key in sources.SOURCES, key
            checked += 1
    assert checked > 50
    assert sources.github_anchor("Scarlett -- Naive Bayes") == "scarlett----naive-bayes"
    assert sources.github_anchor("The deduction floor (`clude_constraints`)") == "the-deduction-floor-clude_constraints"


def test_the_worked_example_is_what_the_real_agents_compute():
    """The "Rope question" of the method articles, run through
    `ExactEnumAgent` and `NaiveBayesAgent`: three deals survive, Plum is
    exact at 2/3, and Scarlett starts short of it and passes it on the
    third hearing. The figure's own count of deals agrees with Plum's."""
    example = facts.rope_question()
    alive = [deal for deal in figures.rope_deals() if deal[2]]
    assert example["deals"] == len(alive) == 3
    assert example["plum"]["White"] == pytest.approx(2 / 3)
    assert example["plum"]["Rope"] == pytest.approx(1 / 3)
    assert example["uniform"]["White"] == pytest.approx(0.5)
    said = [example["scarlett"][n]["White"] for n in (1, 2, 3)]
    assert said == sorted(said)
    assert said[0] < 2 / 3 < said[1] < said[2]
    assert said[0] == pytest.approx(0.6) and said[2] == pytest.approx(27 / 35)
    assert facts.code("example.plum.White") == "2/3" and facts.code("example.scarlett.3.White") == "0.77"
    assert facts.code("envelopes") == "324"
    assert facts.code("deals.3") == "103,488"  # 4 x 4 x 7 envelopes, 924 ways to split twelve cards


def test_every_constant_an_article_prints_can_be_computed(wiki):
    """Each ``{{code:...}}`` key is a callable: all of them run, and the
    ones the articles use are among them."""
    for key in facts.CODE:
        assert isinstance(facts.code(key), str) and facts.code(key), key
    used = set().union(*(article.codes for article in wiki.pages()))
    assert used
    for key in used:  # the step keys of Mustard's path are computed on demand
        assert isinstance(facts.code(key), str) and facts.code(key), key


# --- the articles -----------------------------------------------------------


def test_every_article_has_a_lead_a_category_and_no_broken_link(wiki):
    """The plan's gates on an article (3.1, 3.6), and on the set: every
    in-app link leads to a page (or is counted against `WANTED_BUDGET`),
    every category linked has members, every figure asked for exists."""
    assert wiki.counts()["articles"] >= 3
    for article in wiki.pages():
        assert article.lead.strip().startswith("<p>"), f"{article.title} has no lead paragraph"
        assert "<strong>" in article.lead or 'class="selflink"' in article.lead, f"{article.title}: the title is not in bold in the lead"
        assert article.short, f"{article.title} has no short description"
        assert article.categories, f"{article.title} is in no category"
        assert article.navboxes == ["clude"], article.title
        rendered = article.hatnotes + article.infobox + article.lead + article.body
        assert "[[" not in rendered, f"{article.title} has an unrendered wikilink"
        for key in article.figures:
            assert key in figures.keys(), key
        if not article.is_stub:
            headings = [token["name"] for token in article.toc]
            assert headings[-2:] == ["See also", "References"], f"{article.title} ends {headings[-2:]}"
            # Length and an external-link quota encourage padding. Editorial
            # quality is reviewed; structure, sources and link integrity are checked.
    assert len(wiki.wanted) <= WANTED_BUDGET, sorted(wiki.wanted)
    for name, groups in ((n, g) for n, (_, g) in wiki.navboxes.items()):
        missing = [title for _, row in groups for title, _, exists in row if not exists]
        assert len(missing) <= WANTED_BUDGET, f"the {name} navbox wants {missing}"


def test_the_three_kinds_of_exemplar_are_there_with_their_redirects(wiki):
    plum, came_from = wiki.get("plum")
    assert plum.title == "Professor Plum" and came_from == "plum" and plum.featured
    assert wiki.featured() is plum
    assert wiki.get("Professor_Plum") == (plum, "")
    assert wiki.get("Scarlett's method")[0].title == "Naive Bayes"
    assert wiki.get("Disproof")[0].title == "Suggestion"
    assert wiki.get("Nothing at all") == (None, "")
    # W6 expands the project overview while retaining its established aliases.
    project, _ = wiki.get("clude")
    assert not project.is_stub and project in wiki.categories["The app"]
    assert wiki.get("The project")[0] is project
    # What links here, and the hooks on the Main Page.
    assert plum in wiki.linking_to(wiki.get("Naive Bayes")[0])
    assert any("Professor Plum" in hook for hook in wiki.did_you_know())
    hits = wiki.search("envelope")
    assert hits and hits[0][0].title == "The envelope"
    assert wiki.search("zzzz") == [] and wiki.search("  ") == []


def test_every_character_and_method_has_its_article(wiki):
    """W2's gate (docs/wikiclude-plan.md 5): the six characters, the six
    methods, the floor and Belief are full articles with their numbers
    through `facts`; and the Rope question, answered by every method on
    the real code, is what the articles say it is. The tree's path is
    pinned because the prose narrates it: regrow the tree and this says
    which articles to reread."""
    for title in (
        "Miss Scarlett", "Colonel Mustard", "Mrs. White", "Mr. Green", "Mrs. Peacock", "Professor Plum",
        "Naive Bayes", "Decision tree", "Markov chain", "Bandit ensemble", "Dempster-Shafer theory",
        "Exact posterior enumeration", "Deduction floor", "Belief",
    ):
        article, _ = wiki.get(title)
        assert article is not None and not article.is_stub, title
        assert article.facts or article.codes, title
    example = facts.rope_question()
    search = facts.plum_search()
    assert search["deals"] == example["deals"] == 3 and search["nodes"] == example["nodes"] == 20
    assert example["peacock_belief"]["White"] == pytest.approx(0.5)
    assert example["peacock_plausibility"]["White"] == pytest.approx(1.0)
    assert example["peacock"]["White"] == pytest.approx(0.75)
    # Mustard's tree sends all four open cards to one leaf, by these six questions.
    assert [step["feature"] for step in example["mustard_path"]] == [
        "times_named_total", "times_named_unrefuted", "distinct_namers",
        "possible_holders_frac", "possible_holders_frac", "turn_fraction",
    ]
    assert all(example["mustard"][card] == pytest.approx(0.5) for card in facts.ROPE_CARDS)
    # White reads the asking, not the answer, and goes the other way.
    assert example["white"]["White"] == pytest.approx(0.4) and example["white"]["Peacock"] == pytest.approx(0.6)
    assert set(example["green_arms"]) == {"Scarlett", "Plum", "Peacock", "Mustard", "White"}
    assert sorted(example["green_arms"], key=lambda a: -example["green_arms"][a][2])[0] == facts.code("example.green.best")
    assert str(facts.chain_example()["stationary"]) == "9/14"
    assert facts.code("example.ds.two.conflict") == "1/4" and facts.code("example.ds.two.white") == "1/3"
    assert facts.code("certainty.triples") == "324" and facts.code("certainty.half.one_in") == "18"
    assert float(facts.code("certainty.scarlett")) < float(facts.code("certainty.plum")) < 1
    with pytest.raises(KeyError):
        facts.code("example.mustard.step.8.threshold")


def test_w3_w5_topics_are_articles_and_all_public_pages_load(wiki, app):
    """Full W3-W5 topics and established aliases."""
    titles = (
        "Rules of play", "Clue", "Classic board", "Rooms", "The deal", "The envelope",
        "Accusation", "Detective notepad", "Bluffing", "Floor player", "Random bot",
        "Personality dials", "Leash", "LLM wrapper", "Persona", "Table talk", "Claude",
        "Logbook", "Method memory", "The debrief", "Memory dial",
        "Probability", "Conditional probability and Bayes' theorem", "Independence",
        "Combinatorics of a deal", "Log-loss", "Entropy and bits", "Softmax and temperature",
        "Beta distribution", "Belief benchmark", "Uniform baseline", "Arena", "Dial sweeps",
        "Twin comparison", "Landing rule", "Self-play", "Determinism and seeds",
    )
    for title in titles:
        article, _ = wiki.get(title)
        assert article is not None and not article.is_stub, title
    assert not [a.title for a in wiki.pages() if a.is_stub]
    client = app.test_client()
    for article in wiki.pages():
        response = client.get(f"/wiki/{article.slug}")
        assert response.status_code == 200, article.title
        text = response.get_data(as_text=True)
        assert "{{code:" not in text and "{{fact:" not in text and "<merror" not in text
    for alias, title in (
        ("Disproof", "Suggestion"), ("Secret passages", "Classic board"),
        ("Ring board", "Classic board"), ("FloorBot", "Deduction floor"),
        ("Counting deals", "Exact posterior enumeration"), ("Debrief", "Logbook"),
        ("Chattiness", "Table talk"), ("Accusation threshold", "Personality dials"),
    ):
        assert wiki.get(alias)[0].title == title


def test_w6_app_archive_and_measurement_coverage(wiki):
    """The W6 catalogue resolves, and the complete sweep data stays reachable.

    The existing citation/value tests independently check these stored tables
    against their named source sections; this checks their place in the wiki.
    """
    for title in (
        "clude", "History of clude", "The lobby", "The table", "Watch", "Replay",
        "Looks", "The certainty tag", "A seat over MCP", "What a game costs", "AIX Laboratories",
        "Game records", "Maintainer CLI", "Character training", "Measurement record",
        "Classwork archive", "Reinforcement learning", "Markov decision process", "Q-learning",
        "Deep Q-network", "DeepNash",
    ):
        page, _ = wiki.get(title)
        assert page is not None and not page.is_stub, title
    # Keep the earlier Certainty tag alias, whose subject was introduced in Belief.
    assert wiki.get("Certainty tag")[0].title == "Belief"
    sweeps, _ = wiki.get("Dial sweeps")
    for board in ("ring", "grid"):
        for dial in ("accuse_threshold", "bluff_rate", "curiosity", "secrecy", "temperature"):
            key = "sweep.bluff" if (board, dial) == ("ring", "bluff_rate") else f"sweep.{board}.{dial}"
            assert key in sweeps.facts, key
    measurements, _ = wiki.get("Measurement record")
    assert "ladder.plum" in measurements.facts
    for key in ("sutton-barto", "mnih-2015", "wang-2016", "schaul-2016", "perolat-2022"):
        assert 'drive.google.com/file/d/' in sources.SOURCES[key]
        assert 'Archive copy' in sources.SOURCES[key]
    assert "Classwork" in wiki.categories


def test_every_internal_section_link_resolves(wiki):
    """Title checks alone miss stale fragments and duplicate figure ids."""
    class LinksAndIds(HTMLParser):
        def __init__(self, article):
            super().__init__()
            self.ids = {"top"}
            self.links = []
            self.feed(article.hatnotes + article.lead + article.infobox + article.body)

        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs)
            if "id" in attrs:
                assert attrs["id"] not in self.ids, f"duplicate id: {attrs['id']}"
                self.ids.add(attrs["id"])
            if tag == "a" and "href" in attrs:
                self.links.append(attrs["href"])

    parsed = {a.slug: LinksAndIds(a) for a in wiki.pages()}
    for article in wiki.pages():
        for href in parsed[article.slug].links:
            url = urllib.parse.urlsplit(href)
            if url.netloc or not url.fragment:
                continue
            target = wiki.get(urllib.parse.unquote(url.path.removeprefix("/wiki/")))[0] if url.path else article
            assert target is not None, (article.title, href)
            assert urllib.parse.unquote(url.fragment) in parsed[target.slug].ids, (article.title, href)


def test_new_computed_examples_agree_with_engine_and_scoring():
    """Check setup/loss examples against live interfaces and count the joint
    example independently rather than multiplying the article's marginals.
    """
    import math
    import random
    from clude_core import engine
    from clude_core.domain import SUSPECTS, WEAPONS, ROOMS
    from clude_training.benchmark import _Accumulator, EPS
    from clude_llm.menu import within_leash

    for n in range(3, 7):
        state = engine.setup(n, random.Random(17))
        assert facts.code(f"deal.hands.{n}") == ", ".join(str(len(state.hands[i])) for i in range(n))
        assert sum(len(h) for h in state.hands.values()) == int(facts.code("cards.dealt"))
    scores = {c: 0.0 for c in SUSPECTS + WEAPONS + ROOMS}
    for category in (SUSPECTS, WEAPONS, ROOMS):
        scores.update({category[0]: 0.5, category[1]: 0.5})
    accumulator = _Accumulator()
    accumulator.update(scores, (SUSPECTS[0], WEAPONS[0], ROOMS[0]))
    assert round(accumulator.log_loss, 2) == float(facts.code("loss.half"))
    accumulator = _Accumulator()
    accumulator.update(scores, (SUSPECTS[2], WEAPONS[2], ROOMS[2]))
    assert accumulator.log_loss == pytest.approx(-math.log(EPS))
    assert within_leash([0.8, 0.65, 0.5], 0.25) == [True, True, False]
    assert facts.softmax_example(0.1) == pytest.approx(1 / (1 + math.exp(-2)))
    assert facts.softmax_example(0.5) == pytest.approx(1 / (1 + math.exp(-0.4)))
    deals = [env for env, _, alive in figures.rope_deals() if alive]
    white = sum("White" in env for env in deals) / len(deals)
    wrench = sum("Wrench" in env for env in deals) / len(deals)
    joint = sum("White" in env and "Wrench" in env for env in deals) / len(deals)
    assert white == wrench == pytest.approx(2 / 3)
    assert joint == pytest.approx(1 / 3) and joint != pytest.approx(white * wrench)


# --- the markup -------------------------------------------------------------


def _render(text: str, known=("Professor Plum",)):
    titles = {render.key_of(t): render.slug_of(t) for t in known}

    def resolve(name):
        slug = titles.get(render.key_of(name))
        return (slug, True) if slug else (render.slug_of(name), False)

    return render.render("Test page", text, resolve)


def test_the_three_kinds_of_link_are_told_apart():
    out = _render(
        "See [[Professor Plum|Plum]], [[professor plum]], [[Nobody yet]], "
        "[[w:Bayes' theorem|Bayes]] and [[Test page]]. Also [[Professor Plum#How he plays|his dials]]."
    )
    html = out.html
    assert '<a class="wl" href="/wiki/Professor_Plum" title="Professor Plum">Plum</a>' in html
    assert '<a class="wl" href="/wiki/Professor_Plum" title="Professor plum">professor plum</a>' in html
    assert 'class="wl new" href="/wiki/Nobody_yet" title="Nobody yet (not yet written)"' in html
    assert 'class="extw" href="https://en.wikipedia.org/wiki/Bayes\'_theorem"' in html and 'target="_blank"' in html
    assert '<strong class="selflink">Test page</strong>' in html
    assert 'href="/wiki/Professor_Plum#how-he-plays"' in html
    assert out.ctx.wanted == {"Nobody yet"} and out.ctx.wikipedia == {"Bayes' theorem"}
    assert out.ctx.links == {"professor plum"}


def test_facts_mathematics_and_a_literal_dollar():
    out = _render(r"Plum scored {{fact:bench.grid.Plum.50}} and waits for {{code:preset.Plum.accuse_threshold}}. It cost \$0.25, and $x^2$ is mathematics.")
    assert "Plum scored 1.75 and waits for 0.9." in out.html
    assert "It cost $0.25" in out.html
    assert "<math" in out.html and "<msup>" in out.html
    assert out.ctx.facts == {"bench.grid.Plum.50"} and out.ctx.codes == {"preset.Plum.accuse_threshold"}
    block = _render("Before.\n\n$$ \\frac{a}{b} $$\n\nAfter.")
    assert '<div class="math-block"><math' in block.html and 'display="block"' in block.html


@pytest.mark.parametrize("delimiter", ("$", "$$"))
def test_values_in_mathematics_are_resolved_and_tracked(delimiter):
    latex = "N = {{code:certainty.triples}}, x = {{fact:bench.grid.Plum.50}}"
    text = f"$$ {latex} $$" if delimiter == "$$" else f"${latex}$"
    out = _render(text)
    assert "<mn>324</mn>" in out.html and "<mn>1.75</mn>" in out.html
    assert out.ctx.codes == {"certainty.triples"}
    assert out.ctx.facts == {"bench.grid.Plum.50"}
    assert "code:" not in out.html and "fact:" not in out.html
    for kind in ("code", "fact"):
        bad = "{{" + kind + ":no.such.value}}"
        with pytest.raises(WikiError, match="no " + kind):
            _render(delimiter + bad + delimiter)


def test_a_mistake_in_an_article_is_an_error_not_a_broken_page():
    for bad in (
        "A fact {{fact:no.such.fact}}.",
        "A constant {{code:no.such.constant}}.",
        "{{figure:no-such-figure|A caption}}",
        "{{table:no.such.table|A caption}}",
        "Cited[^a].\n\n[^a]: {{cite:no-such-book}}",
        "Cited and never defined.[^missing]",
        "Never cited.\n\n[^spare]: A note.",
        "{{infobox\ntitle: Never closed",
    ):
        with pytest.raises(WikiError):
            _render(bad)
    with pytest.raises(WikiError):
        index.parse("no front matter", "x.md")
    with pytest.raises(WikiError):
        index.parse("---\nshort: no title\n---\nbody", "x.md")


def test_references_are_numbered_in_the_order_they_are_cited():
    out = _render(
        "First.[^b] Second.[^a] First again.[^b]\n\n## References\n\n{{references}}\n\n"
        "[^a]: {{cite:sutton-barto|Chapter 2}}\n[^b]: {{cite:docs/board.md|Movement rules}}"
    )
    notes = re.findall(r'<li id="fn-(\w)">', out.html)
    assert notes == ["b", "a"]
    assert "Reinforcement Learning: An Introduction" in out.html and "Chapter 2." in out.html
    assert 'href="https://github.com/davidabelin/clude/blob/main/docs/board.md#movement-rules"' in out.html
    assert out.ctx.cites == [("docs/board.md", "Movement rules"), ("sutton-barto", "Chapter 2")]
    # The mark is joined to the word before it, so it never starts a line.
    assert "First.&#8288;<sup" in out.html


def test_the_lead_the_infobox_and_the_hatnotes_come_apart():
    out = _render(
        "{{hatnote:For the other thing, see [[Professor Plum]].}}\n\n{{infobox\ntitle: A box\nclass: suspect-plum\n"
        "figure: token-plum\nMethod | [[Professor Plum]]\n= A heading\nBluff rate | {{code:preset.Plum.bluff_rate}}\n}}\n\n"
        "**Test page** is a test.\n\n## A section\n\n{{main:Professor Plum}}\n\nBody.\n\n"
        "| a | b |\n|---|---|\n| 1 | 2 |\n"
    )
    assert out.hatnotes.strip().startswith('<div class="hatnote"') and "For the other thing" in out.hatnotes
    assert out.lead.strip().startswith("<p><strong>Test page</strong>")
    assert out.body.startswith("<h2") and "Main article:" in out.body
    assert out.infobox.startswith('<table class="infobox suspect-plum">') and "<caption>A box</caption>" in out.infobox
    assert 'class="infobox-head"' in out.infobox and "<td>0.05</td>" in out.infobox and "<svg" in out.infobox
    assert '<div class="table-wrap"><table class="wikitable">' in out.body and "</table></div>" in out.body
    assert [token["name"] for token in out.toc] == ["A section"]


# --- the pages --------------------------------------------------------------


def test_wikiclude_is_public_and_every_kind_of_page_answers(app):
    """David, 2026-10-01: the encyclopaedia is open like the privacy
    page. Nobody is signed in here."""
    client = app.test_client()
    main = client.get("/wiki").get_data(as_text=True)
    assert "Welcome to" in main and "From the featured article" in main and "Did you know" in main
    assert 'href="/static/styles/wiki.css"' in main and 'href="/wiki/Category:Characters"' in main

    page = client.get("/wiki/Professor_Plum")
    assert page.status_code == 200
    text = page.get_data(as_text=True)
    assert "<h1>Professor Plum</h1>" in text and 'class="infobox suspect-plum"' in text
    assert 'class="wiki-toc-rail"' in text and '<details class="wiki-toc">' in text
    assert 'class="navbox"' in text and 'href="/wiki/Category:Characters"' in text
    assert "Redirected from" not in text
    assert "Redirected from <em>Plum</em>" in client.get("/wiki/Plum").get_data(as_text=True)
    assert 'class="wiki-notice"' not in client.get("/wiki/clude").get_data(as_text=True)
    # The wooden question mark is every wiki page's logo (David, 2026-10-02).
    assert 'class="wiki-logo" src="/static/questionmark-wood.png"' in text
    assert main.count('class="wiki-logo"') == 2  # the masthead and the welcome

    for path, words in (
        ("/wiki/Category:Methods", "Naive Bayes"),
        ("/wiki/Figure:rope-deals", "Used in"),
        ("/wiki/Special:AllPages", "Professor Plum"),
        ("/wiki/Special:WantedPages", "Wanted pages"),
        ("/wiki/Special:WhatLinksHere/Naive_Bayes", "Professor Plum"),
        ("/wiki/Special:Search?q=envelope&go=0", "The envelope"),
    ):
        response = client.get(path)
        assert response.status_code == 200, path
        assert words in response.get_data(as_text=True), path

    # A search for an exact title goes straight there; Random goes somewhere.
    assert client.get("/wiki/Special:Search?q=professor+plum").headers["Location"].endswith("/wiki/Professor_Plum")
    assert "/wiki/" in client.get("/wiki/Special:Random").headers["Location"]
    for path in ("/wiki/No_such_article", "/wiki/Category:Nothing", "/wiki/Figure:nothing", "/wiki/Special:Nothing"):
        response = client.get(path)
        assert response.status_code == 404, path
        assert "does not have a page" in response.get_data(as_text=True)
    # Nothing else became public with it.
    assert client.get("/").status_code == 302


@pytest.mark.parametrize("key", list(styles.STYLES))
def test_an_article_renders_under_every_look(app, key):
    client = app.test_client()
    _sign_in(client)
    client.post("/style", data={"csrf": _csrf(client, "/wiki"), "style": key, "next": "/wiki"})
    page = client.get("/wiki/Naive_Bayes").get_data(as_text=True)
    assert f'data-style="{key}"' in page and styles.STYLES[key].stylesheet in page
    assert "styles/wiki.css" in page and "<math" in page and 'class="fig fig-mermaid"' in page
    assert page.index(styles.STYLES[key].stylesheet) < page.index("styles/chrome.css") < page.index("styles/wiki.css")


# --- the stylesheet and the figures -----------------------------------------


def _wiki_css() -> str:
    return (ROOT / "clude_web" / "static" / "styles" / "wiki.css").read_text(encoding="utf-8")


def test_the_wiki_stylesheet_keeps_the_shared_sheets_rules():
    """wiki.css is shared by every look, like chrome.css: ASCII, no
    motion of its own, and no token read without a fallback unless every
    look's sheet, or wiki.css itself, defines it."""
    css = _wiki_css()
    assert css.isascii()
    assert not re.search(r"(?:animation|transition)\s*:", css)
    own = set(re.findall(r"(--[a-z-]+)\s*:", css))
    bare = set(re.findall(r"var\((--[a-z-]+)\)", css))
    static = ROOT / "clude_web" / "static"
    for key, style in styles.STYLES.items():
        defined = set(re.findall(r"(--[a-z-]+)\s*:", (static / style.stylesheet).read_text(encoding="utf-8")))
        assert not bare - defined - own, f"{key} lacks {sorted(bare - defined - own)}"
    malformed = re.findall(r"--[a-z-]+:\s*#[0-9a-fA-F]*[^0-9a-fA-F;\s][^;]*;", css)
    assert not malformed, malformed


def test_every_class_a_figure_uses_is_styled():
    """The figures set no colour, as `board_svg` sets none: a class with
    no rule in wiki.css is an invisible shape. The method diagrams carry
    Mermaid's own bookkeeping classes too; of theirs, the ones that must
    have a rule are the node classes the diagrams define (classDef)."""
    css = _wiki_css()
    for key in figures.keys():
        svg = figures.figure(key).svg
        assert svg.startswith("<svg") and "<style" not in svg and "fill=\"#" not in svg, key
        used = {name for group in re.findall(r'class="([^"]+)"', svg) for name in group.split()}
        if "fig-mermaid" in used:
            assert not re.findall(r'\sstyle="(?!min-width:\d+px")', svg), f"{key} kept an inline style"
            used = {name for group in re.findall(r'class="node default ([^"]+)"', svg) for name in group.split()}
            used -= {"default", "flowchart-label"}
        painted = css
        if "fig-board" in used:
            # Production board classes are painted by the look sheets; the
            # wiki selects a plain or dressed variant without changing them.
            painted += "\n".join(
                (ROOT / "clude_web" / "static" / s.stylesheet).read_text(encoding="utf-8")
                for s in styles.STYLES.values()
            )
        unstyled = sorted(name for name in used if f".{name}" not in painted)
        assert not unstyled, f"{key}: classes with no rule in wiki.css: {unstyled}"


def test_every_diagram_in_the_registry_is_drawn_and_committed():
    """`scripts/build_wiki_figures.py` draws the `DIAGRAMS` registry of
    docs/ux/diagrams; each key needs its file and its caption here."""
    import sys

    sys.path.insert(0, str(ROOT / "docs" / "ux" / "diagrams"))
    try:
        import build_diagrams
    finally:
        sys.path.pop(0)
    assert set(build_diagrams.DIAGRAMS) == set(figures.DIAGRAM_TEXT)
    for key in build_diagrams.DIAGRAMS:
        assert (figures.FILES / f"{key}.svg").is_file(), f"{key} is not drawn: run scripts/build_wiki_figures.py"


# --- the network ------------------------------------------------------------


@pytest.mark.skipif(not os.environ.get("CLUDE_WIKI_LIVE"), reason="set CLUDE_WIKI_LIVE=1 to ask Wikipedia")
def test_every_wikipedia_title_we_link_to_exists(wiki):
    """Asks Wikipedia's API, fifty titles at a time, following redirects."""
    titles = sorted(set().union(*(article.wikipedia for article in wiki.pages())))
    titles = sorted({title.split("#")[0] for title in titles})
    missing = []
    for start in range(0, len(titles), 50):
        batch = titles[start : start + 50]
        query = urllib.parse.urlencode({"action": "query", "format": "json", "redirects": 1, "titles": "|".join(batch)})
        request = urllib.request.Request(
            "https://en.wikipedia.org/w/api.php?" + query,
            headers={"User-Agent": "clude-wiki-link-check/1.0 (https://github.com/davidabelin/clude)"},
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            pages = json.load(response)["query"]["pages"]
        missing += [page["title"] for page in pages.values() if "missing" in page or "invalid" in page]
    assert not missing, f"Wikipedia has no article called: {missing}"
