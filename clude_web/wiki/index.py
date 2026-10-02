"""Wikiclude's index: every article, rendered once and held in memory.

`load()` reads ``articles/*.md``, renders each (`render.render`) and
builds what a wiki needs around them: redirects, categories, "what
links here", the wanted pages (links to articles nobody has written
yet), a search, and the Main Page's featured article and "Did you
know". A page view is then a dictionary lookup.

An article file is a front-matter block and a body::

    ---
    title: Professor Plum
    short: The character who counts every deal still possible
    categories: Characters
    redirects: Plum, Prof. Plum
    featured: yes
    dyk: ...that [[Professor Plum]] has to guess for half the game?
    ---
    **Professor Plum** is ...

``kind: stub`` marks a placeholder: a page that exists so links to it
resolve, says what it will cover and where the facts are for now, and
is listed as a stub rather than as an article.
"""
from __future__ import annotations

import random
import re
from collections import Counter
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from . import render
from .render import WikiError, key_of, slug_of

ARTICLES = Path(__file__).resolve().parent / "articles"

NAVBOXES: dict = {
    "clude": (
        "clude",
        [
            ("The characters", ["Miss Scarlett", "Colonel Mustard", "Mrs. White", "Mr. Green", "Mrs. Peacock", "Professor Plum"]),
            ("Their methods", ["Naive Bayes", "Decision tree", "Markov chain", "Bandit ensemble", "Dempster-Shafer theory", "Exact posterior enumeration"]),
            ("What they share", ["Deduction floor", "Belief", "Uniform baseline", "Personality dials", "Logbook"]),
            ("The game", ["Clue", "Rules of play", "Classic board", "Rooms", "The deal", "Suggestion", "Accusation", "The envelope", "Detective notepad", "Bluffing"]),
            ("Other players", ["Floor player", "Random bot", "Claude"]),
            ("Personality", ["Personality dials", "Persona", "Leash", "LLM wrapper", "Table talk"]),
            ("Memory", ["Logbook", "Method memory", "The debrief", "Memory dial"]),
            ("Mathematics", ["Probability", "Conditional probability and Bayes' theorem", "Independence", "Combinatorics of a deal", "Log-loss", "Entropy and bits", "Softmax and temperature", "Beta distribution"]),
            ("Measurement", ["Belief benchmark", "Arena", "Dial sweeps", "Twin comparison", "Landing rule", "Self-play", "Determinism and seeds"]),
        ],
    ),
}
"""The navigation boxes an article can end with (``{{navbox:clude}}``):
a title and groups of article titles, in the order shown."""

CATEGORY_ORDER = (
    "The game", "Characters", "Methods", "Mathematics", "Personality", "Memory", "Measurement", "The app",
)
"""The order the Main Page lists categories in; any other follows."""

CATEGORY_BLURBS: dict = {
    "The game": "Clue as clude plays it: the board, the cards, a turn.",
    "Characters": "The six suspects, and who else can take a seat.",
    "Methods": "Six ways of reasoning about hidden cards, and the one floor under them all.",
    "Mathematics": "The probability and the counting behind the methods.",
    "Personality": "The dials that turn a belief into a way of playing.",
    "Memory": "What a character carries from one game to the next.",
    "Measurement": "How the methods and the characters were tested, and what was found.",
    "The app": "The table, the replay, and the project itself.",
}


@dataclass
class Article:
    """One article, rendered."""

    title: str
    slug: str
    short: str
    kind: str
    categories: list
    redirects: list
    featured: bool
    dyk: list
    hatnotes: str
    lead: str
    body: str
    infobox: str
    toc: list
    navboxes: list
    links: set = field(default_factory=set)
    wanted: set = field(default_factory=set)
    wikipedia: set = field(default_factory=set)
    category_links: set = field(default_factory=set)
    facts: set = field(default_factory=set)
    codes: set = field(default_factory=set)
    figures: list = field(default_factory=list)
    cites: list = field(default_factory=list)
    text: str = ""

    @property
    def key(self) -> str:
        return key_of(self.title)

    @property
    def is_stub(self) -> bool:
        return self.kind == "stub"

    @property
    def words(self) -> int:
        return len(self.text.split())


def parse(text: str, path: str = "") -> tuple:
    """Split an article file into its front matter and its body.

    Returns
    -------
    tuple
        ``(meta, body)``: `meta` maps each key to a list of its values
        (a key may repeat, as ``dyk`` does).

    Raises
    ------
    WikiError
        If the file does not open with a ``---`` block, or has no title.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise WikiError(f"{path}: an article starts with a '---' front-matter block")
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        raise WikiError(f"{path}: the front-matter block never closes") from None
    meta: dict = {}
    for line in lines[1:end]:
        if not line.strip():
            continue
        name, sep, value = line.partition(":")
        if not sep:
            raise WikiError(f"{path}: a front-matter line without a colon: {line!r}")
        meta.setdefault(name.strip().lower(), []).append(value.strip())
    if not meta.get("title") or not meta["title"][0]:
        raise WikiError(f"{path}: an article needs a title")
    return meta, "\n".join(lines[end + 1 :])


def _list(meta: dict, name: str) -> list:
    return [item.strip() for value in meta.get(name, []) for item in value.split(",") if item.strip()]


class Wiki:
    """Every article, and the lookups built over them."""

    def __init__(self, directory: Path = ARTICLES):
        sources = []
        self._titles: dict = {}  # lookup key -> the article's own key
        for path in sorted(directory.glob("*.md")):
            meta, body = parse(path.read_text(encoding="utf-8"), path.name)
            title = meta["title"][0]
            if path.stem != slug_of(title):
                raise WikiError(f"{path.name}: the file of {title!r} must be {slug_of(title)}.md")
            for name in [title] + _list(meta, "redirects"):
                if key_of(name) in self._titles:
                    raise WikiError(f"{path.name}: {name!r} is already an article or a redirect")
                self._titles[key_of(name)] = key_of(title)
            sources.append((meta, body, title))
        slugs = {key_of(title): slug_of(title) for _, _, title in sources}

        def resolve(name: str) -> tuple:
            target = self._titles.get(key_of(name))
            return (slugs[target], True) if target else (slug_of(name), False)

        self.articles: dict = {}
        for meta, body, title in sources:
            out = render.render(title, body, resolve)
            ctx = out.ctx
            unknown = [n for n in ctx.navboxes if n not in NAVBOXES]
            if unknown:
                raise WikiError(f"{title}: no navbox named {unknown[0]!r}")
            self.articles[key_of(title)] = Article(
                title=title, slug=slug_of(title), short=(meta.get("short") or [""])[0],
                kind=(meta.get("kind") or ["article"])[0], categories=_list(meta, "categories"),
                redirects=_list(meta, "redirects"), featured=(meta.get("featured") or [""])[0].lower() in ("yes", "true"),
                dyk=[render.render(title, hook, resolve).lead for hook in meta.get("dyk", [])],
                hatnotes=out.hatnotes, lead=out.lead, body=out.body, infobox=out.infobox, toc=out.toc, navboxes=list(ctx.navboxes),
                links=ctx.links, wanted=ctx.wanted, wikipedia=ctx.wikipedia, category_links=ctx.categories, facts=ctx.facts, codes=ctx.codes,
                figures=ctx.figures, cites=ctx.cites, text=render.plain(out.html),
            )

        self.categories: dict = {}
        self.backlinks: dict = {key: [] for key in self.articles}
        self.wanted: Counter = Counter()
        for article in self.pages():
            for category in article.categories:
                self.categories.setdefault(category, []).append(article)
            for target in article.links:
                self.backlinks[self._titles[target]].append(article)
            self.wanted.update(article.wanted)
        for article in self.pages():
            missing = sorted(article.category_links - set(self.categories))
            if missing:
                raise WikiError(f"{article.title}: links to a category nobody is in: {missing[0]!r}")
        self.navboxes = {name: self._navbox(name) for name in NAVBOXES}

    # --- lookups ---

    def pages(self) -> list:
        """Every article and stub, by title."""
        return sorted(self.articles.values(), key=lambda a: a.title.casefold())

    def get(self, title: str):
        """``(article, redirected_from)`` for a title, slug or redirect;
        ``(None, "")`` if there is no such page."""
        key = key_of(title)
        target = self._titles.get(key)
        if target is None:
            return None, ""
        article = self.articles[target]
        return article, ("" if key == target else " ".join(title.replace("_", " ").split()))

    def linking_to(self, article: Article) -> list:
        """The articles that link to this one, by title."""
        seen = {a.key: a for a in self.backlinks.get(article.key, []) if a.key != article.key}
        return sorted(seen.values(), key=lambda a: a.title.casefold())

    def category_names(self) -> list:
        """Every category, in the Main Page's order."""
        rank = {name: i for i, name in enumerate(CATEGORY_ORDER)}
        return sorted(self.categories, key=lambda name: (rank.get(name, len(rank)), name))

    def featured(self):
        """The Main Page's featured article: the one marked, else the longest."""
        marked = [a for a in self.pages() if a.featured]
        full = [a for a in self.pages() if not a.is_stub]
        return (marked or sorted(full, key=lambda a: -a.words) or [None])[0]

    def did_you_know(self) -> list:
        """Every article's hooks, as HTML."""
        return [hook for a in self.pages() for hook in a.dyk]

    def hooks(self, n: int = 8) -> list:
        """Up to `n` of the hooks for the Main Page, a different draw on
        each visit, as Wikipedia rotates its own."""
        hooks = self.did_you_know()
        return random.sample(hooks, n) if len(hooks) > n else hooks

    def random(self):
        full = [a for a in self.pages() if not a.is_stub] or self.pages()
        return random.choice(full) if full else None

    def figure_uses(self, key: str) -> list:
        """The articles a figure appears in."""
        return [a for a in self.pages() if key in a.figures]

    def search(self, query: str) -> list:
        """Articles matching every word of `query`, best first.

        Returns
        -------
        list
            ``(article, excerpt)`` pairs: title matches before matches
            in the short description, before matches in the text; the
            excerpt is the text around the first word found.
        """
        words = [w for w in re.findall(r"\w+", query.casefold()) if w]
        if not words:
            return []
        hits = []
        for article in self.pages():
            title, short, text = article.title.casefold(), article.short.casefold(), article.text.casefold()
            names = " ".join([title] + [r.casefold() for r in article.redirects])
            if not all(w in names or w in short or w in text for w in words):
                continue
            score = sum(100 if w in names else 10 if w in short else 1 for w in words) + min(text.count(words[0]), 9)
            at = text.find(words[0])
            start = max(0, at - 70) if at >= 0 else 0
            excerpt = ("..." if start else "") + article.text[start : start + 220].strip() + "..."
            hits.append((score, article, excerpt if at >= 0 else article.short))
        hits.sort(key=lambda hit: (-hit[0], hit[1].title.casefold()))
        return [(article, excerpt) for _, article, excerpt in hits]

    # --- pieces of a page ---

    def _navbox(self, name: str) -> list:
        """A navbox as ``(title, [(group, [(title, slug, exists)])])``."""
        title, groups = NAVBOXES[name]
        out = []
        for group, titles in groups:
            row = []
            for t in titles:
                target = self._titles.get(key_of(t))
                row.append((t, self.articles[target].slug if target else slug_of(t), bool(target)))
            out.append((group, row))
        return [title, out]

    def counts(self) -> dict:
        full = [a for a in self.pages() if not a.is_stub]
        return {
            "articles": len(full), "stubs": len(self.articles) - len(full), "wanted": len(self.wanted),
            "words": sum(a.words for a in full),
        }


@lru_cache(maxsize=1)
def load() -> Wiki:
    """The wiki, built on first use and kept.

    Raises
    ------
    WikiError
        If any article cannot be rendered. `create_app` calls this, so
        a broken article stops the app starting rather than reaching a
        reader.
    """
    return Wiki()
