"""Wikiclude's markup: Markdown, plus the handful of things a wiki needs.

An article is a Markdown file (`clude_web/wiki/articles/*.md`). On top of
Python-Markdown's own footnotes, tables, definition lists and table of
contents, this module adds:

``[[Professor Plum]]``, ``[[Professor Plum|Plum]]``, ``[[Suggestion#Disproof|shown]]``
    A link to another article: the red thread, like every link in the
    app. A title nobody has written yet renders as a "wanted" link.
``[[w:Bayes' theorem|Bayes' theorem]]``
    A link out to Wikipedia, in a colour of its own and marked, opening
    in a new tab.
``{{fact:plum.logloss.50}}``
    A measured number, from `facts.FACTS`; never a literal in the text.
``{{code:scarlett.boost}}``
    A constant read from the live module, from `facts.CODE`.
``{{cite:docs/strategy-glossary.md|Heading}}``, ``{{cite:sutton-barto|section 2.3}}``
    A formatted citation, for use inside a footnote.
``$x^2$`` and ``$$ ... $$``
    Mathematics, written as LaTeX and rendered here to MathML: nothing
    for a browser to download or run. A literal dollar is ``\\$``.
``{{figure:key|Caption}}``, ``{{figure:key|wide|Caption}}``
    A figure from `figures` in a thumb frame.
``{{table:key|Caption}}``
    A measured table from `facts.TABLES`, every cell as the doc has it.
``{{main:Title}}``, ``{{see also:A, B}}``, ``{{hatnote:text}}``
    Hatnotes.
``{{infobox`` ... ``}}``
    The box at the head of an article; one ``Label | value`` per line.
``{{navbox:name}}``, ``{{references}}``
    The navigation box and the reference list.

Everything is rendered once, when the app starts (`index.load`), so a
mistake in an article is an exception there and in the tests, never a
broken page in front of a reader.
"""
from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from typing import Callable, Optional
from urllib.parse import quote
from xml.etree import ElementTree as etree

import latex2mathml.converter
import markdown
from markdown.extensions import Extension
from markdown.inlinepatterns import InlineProcessor
from markdown.postprocessors import Postprocessor
from markdown.preprocessors import Preprocessor

from . import facts, figures, sources

WIKI_ROOT = "/wiki/"
"""Where the articles are served. The app is mounted at the root, and
articles are rendered once at start-up, outside any request, so the
prefix is a constant rather than a `url_for`."""

WIKIPEDIA = "https://en.wikipedia.org/wiki/"


class WikiError(ValueError):
    """An article that cannot be rendered: an unknown fact, figure or
    source, a malformed template. Raised at load, never at a reader."""


def slug_of(title: str) -> str:
    """The URL form of a title: spaces as underscores, as Wikipedia has
    it (``Professor Plum`` -> ``Professor_Plum``)."""
    return title.strip().replace(" ", "_")


def key_of(title: str) -> str:
    """The lookup form of a title or slug: case and underscores ignored,
    so ``professor_plum`` and ``Professor Plum`` are one article."""
    return " ".join(title.replace("_", " ").split()).casefold()


def anchor_of(heading: str) -> str:
    """The id a section heading gets, as the table of contents makes it."""
    from markdown.extensions.toc import slugify

    return slugify(heading, "-")


@dataclass
class Context:
    """What rendering one article needs to know, and what it finds out.

    Parameters
    ----------
    title : str
        The article being rendered (a link to itself renders bold).
    resolve : callable
        ``title -> (slug, exists)``: where a wikilink goes, following
        redirects, and whether anything is there.
    """

    title: str
    resolve: Callable[[str], tuple]
    links: set = field(default_factory=set)
    wanted: set = field(default_factory=set)
    wikipedia: set = field(default_factory=set)
    categories: set = field(default_factory=set)
    facts: set = field(default_factory=set)
    codes: set = field(default_factory=set)
    figures: list = field(default_factory=list)
    cites: list = field(default_factory=list)
    infobox: str = ""
    navboxes: list = field(default_factory=list)


# --- inline ----------------------------------------------------------------


def wikilink(ctx: Context, target: str, label: Optional[str]) -> etree.Element:
    """The element for ``[[target|label]]``."""
    target = target.strip()
    if target.lower().startswith("w:"):
        page = target[2:].strip()
        if not page:
            raise WikiError(f"{ctx.title}: an empty Wikipedia link")
        ctx.wikipedia.add(page)
        el = etree.Element("a")
        el.set("href", WIKIPEDIA + quote(page.replace(" ", "_"), safe="()/:,'!*-._~#"))
        el.set("class", "extw")
        el.set("title", f"Wikipedia: {page.split('#')[0]}")
        el.set("target", "_blank")
        el.set("rel", "noopener")
        el.text = (label or page.split("#")[0]).strip()
        return el

    if target.lower().startswith("category:"):
        name = " ".join(target[9:].replace("_", " ").split())
        ctx.categories.add(name)
        el = etree.Element("a")
        el.set("href", WIKI_ROOT + "Category:" + quote(slug_of(name)))
        el.set("class", "wl")
        el.set("title", f"Category: {name}")
        el.text = (label or name).strip()
        return el

    page, _, section = target.partition("#")
    page = page.strip()
    shown = (label or page).strip()
    page = page[:1].upper() + page[1:]  # [[suggestion]] is [[Suggestion]], as on Wikipedia
    if key_of(page) == key_of(ctx.title) and not section:
        el = etree.Element("strong")
        el.set("class", "selflink")
        el.text = shown
        return el
    slug, exists = ctx.resolve(page)
    el = etree.Element("a")
    href = WIKI_ROOT + quote(slug, safe="():,'!*-._~")
    if section:
        href += "#" + anchor_of(section)
    el.set("href", href)
    if exists:
        ctx.links.add(key_of(page))
        el.set("class", "wl")
        el.set("title", page)
    else:
        ctx.wanted.add(page)
        el.set("class", "wl new")
        el.set("title", f"{page} (not yet written)")
    el.text = shown
    return el


class _WikiLink(InlineProcessor):
    def __init__(self, md, ctx):
        super().__init__(r"\[\[([^\]\|\n]+?)(?:\|([^\]\n]+?))?\]\]", md)
        self.ctx = ctx

    def handleMatch(self, m, data):
        return wikilink(self.ctx, m.group(1), m.group(2)), m.start(0), m.end(0)


_VALUE_PATTERN = r"\{\{(fact|code):([\w.\-]+)\}\}"


def _value(ctx: Context, kind: str, key: str) -> str:
    try:
        text = facts.fact(key) if kind == "fact" else facts.code(key)
    except KeyError:
        raise WikiError(f"{ctx.title}: no {kind} named {key!r}") from None
    (ctx.facts if kind == "fact" else ctx.codes).add(key)
    return text


def _math_values(latex: str, ctx: Context) -> str:
    """Resolve numeric templates before MathML consumes their markup."""
    return re.sub(_VALUE_PATTERN, lambda m: _value(ctx, m.group(1), m.group(2)), latex)


class _Fact(InlineProcessor):
    """``{{fact:key}}`` and ``{{code:key}}``: text, from one table."""

    def __init__(self, md, ctx):
        super().__init__(_VALUE_PATTERN, md)
        self.ctx = ctx

    def handleMatch(self, m, data):
        text = _value(self.ctx, m.group(1), m.group(2))
        return text, m.start(0), m.end(0)


class _Cite(InlineProcessor):
    """``{{cite:key|locator}}``: a formatted citation, as raw HTML."""

    def __init__(self, md, ctx):
        super().__init__(r"\{\{cite:([^|}]+?)(?:\|([^}]*))?\}\}", md)
        self.ctx = ctx

    def handleMatch(self, m, data):
        key, locator = m.group(1).strip(), (m.group(2) or "").strip()
        try:
            text = sources.citation(key, locator)
        except KeyError:
            raise WikiError(f"{self.ctx.title}: no source named {key!r}") from None
        self.ctx.cites.append((key, locator))
        return self.md.htmlStash.store(text), m.start(0), m.end(0)


def mathml(latex: str, display: bool = False) -> str:
    """LaTeX as MathML, inline or as a displayed block."""
    try:
        out = latex2mathml.converter.convert(latex.strip(), display="block" if display else "inline")
    except Exception as error:  # latex2mathml raises its own assorted errors
        raise WikiError(f"mathematics that will not parse: {latex!r} ({error})") from None
    return out


class _Math(InlineProcessor):
    """``$...$``, no space inside either dollar; ``\\$`` is a dollar."""

    def __init__(self, md, ctx):
        super().__init__(r"(?<![\\$\w])\$(?![\s$])([^$\n]+?)(?<![\s\\])\$(?![\w$])", md)
        self.ctx = ctx

    def handleMatch(self, m, data):
        latex = _math_values(m.group(1), self.ctx)
        return self.md.htmlStash.store(mathml(latex)), m.start(0), m.end(0)


# --- blocks ----------------------------------------------------------------


class _Blocks(Preprocessor):
    """The templates that stand on lines of their own."""

    def __init__(self, md, ctx, inline):
        super().__init__(md)
        self.ctx = ctx
        self.inline = inline
        self.indent = ""

    def _stash(self, text: str) -> list:
        """The HTML as a block of its own, at the indentation of the
        line it replaces, so a figure written inside a worked example
        stays inside it."""
        return ["", self.indent + self.md.htmlStash.store(text), ""]

    def run(self, lines):
        out, i = [], 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            self.indent = line[: len(line) - len(line.lstrip())]
            if stripped == "{{infobox":
                j = i + 1
                while j < len(lines) and lines[j].strip() != "}}":
                    j += 1
                if j == len(lines):
                    raise WikiError(f"{self.ctx.title}: an infobox that never closes")
                self.ctx.infobox = self._infobox(lines[i + 1 : j])
                i = j + 1
                continue
            if stripped.startswith("$$"):
                body = stripped[2:]
                j = i
                while not body.rstrip().endswith("$$"):
                    j += 1
                    if j == len(lines):
                        raise WikiError(f"{self.ctx.title}: display mathematics that never closes")
                    body += " " + lines[j].strip()
                latex = _math_values(body.rstrip()[:-2], self.ctx)
                out += self._stash(f'<div class="math-block">{mathml(latex, display=True)}</div>')
                i = j + 1
                continue
            m = re.fullmatch(r"\{\{(figure|table|main|see also|hatnote|navbox):(.*)\}\}", stripped)
            if m:
                out += self._template(m.group(1), m.group(2).strip())
                i += 1
                continue
            out.append(line)
            i += 1
        return out

    def _template(self, name: str, arg: str) -> list:
        ctx = self.ctx
        if name == "figure":
            key, _, rest = arg.partition("|")
            key, shape = key.strip(), ""
            head, sep, tail = rest.partition("|")
            if sep and head.strip() in ("wide", "left"):
                shape, rest = head.strip(), tail
            return self._stash(self._figure(key, shape, rest.strip()))
        if name == "table":
            key, _, caption = arg.partition("|")
            return self._stash(self._table(key.strip(), caption.strip()))
        if name == "main":
            links = _join([self._link(t) for t in arg.split(",") if t.strip()])
            word = "Main article" if "," not in arg else "Main articles"
            return self._stash(f'<div class="hatnote" role="note">{word}: {links}</div>')
        if name == "see also":
            links = _join([self._link(t) for t in arg.split(",") if t.strip()])
            return self._stash(f'<div class="hatnote" role="note">See also: {links}</div>')
        if name == "hatnote":
            return self._stash(f'<div class="hatnote" role="note">{self.inline(arg)}</div>')
        if name == "navbox":
            ctx.navboxes.append(arg)
            return []
        raise WikiError(f"{ctx.title}: unknown template {name!r}")

    def _link(self, title: str) -> str:
        return etree.tostring(wikilink(self.ctx, title, None), encoding="unicode")

    def _figure(self, key: str, shape: str, caption: str) -> str:
        try:
            fig = figures.figure(key)
        except KeyError:
            raise WikiError(f"{self.ctx.title}: no figure named {key!r}") from None
        self.ctx.figures.append(key)
        caption_html = self.inline(caption or fig.caption)
        classes = "thumb" + (f" {shape}" if shape else "")
        return (
            f'<figure class="{classes}" id="fig-{html.escape(key)}">'
            f'<div class="thumb-art">{fig.svg}</div>'
            f"<figcaption>{caption_html} "
            f'<a class="thumb-open" href="{WIKI_ROOT}Figure:{quote(key)}" title="Open this figure on its own page">enlarge</a>'
            f"</figcaption></figure>"
        )

    def _table(self, key: str, caption: str) -> str:
        """A measured table from `facts.TABLES`, every cell as the doc
        has it."""
        table = facts.TABLES.get(key)
        if table is None:
            raise WikiError(f"{self.ctx.title}: no table named {key!r}")
        self.ctx.facts.add(key)
        head = "".join(f'<th scope="col">{html.escape(c)}</th>' for c in table.columns)
        rows = []
        for name, (label, _) in table.rows.items():
            cells = "".join(
                f"<td>{'&ndash;' if c in ('-', '--') else html.escape(c)}</td>"
                for c in table.cells(name)[: len(table.keys)]
            )
            rows.append(f'<tr><th scope="row">{self.inline(label)}</th>{cells}</tr>')
        # The caption stands outside the frame that scrolls, so it wraps
        # to the page and not to a table wider than the page.
        note = f'<p class="table-caption">{self.inline(caption)}</p>' if caption else ""
        return (
            f'{note}<div class="table-wrap"><table class="wikitable measured">'
            f'<thead><tr>{head}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'
        )

    def _infobox(self, lines: list) -> str:
        """``key: value`` settings, then ``Label | value`` rows and
        ``= Heading`` rows."""
        title, css, figure_key, caption, rows = "", "", "", "", []
        for raw in lines:
            line = raw.strip()
            if not line:
                continue
            if line.startswith("="):
                rows.append(f'<tr><th colspan="2" class="infobox-head">{self.inline(line[1:].strip())}</th></tr>')
                continue
            if "|" in line and not re.match(r"^(title|class|figure|caption)\s*:", line):
                label, _, value = line.partition("|")
                rows.append(
                    f'<tr><th scope="row">{self.inline(label.strip())}</th>'
                    f"<td>{self.inline(value.strip())}</td></tr>"
                )
                continue
            name, _, value = line.partition(":")
            name, value = name.strip(), value.strip()
            if name == "title":
                title = value
            elif name == "class":
                css = value
            elif name == "figure":
                figure_key = value
            elif name == "caption":
                caption = value
            else:
                raise WikiError(f"{self.ctx.title}: an infobox line I cannot read: {line!r}")
        art = ""
        if figure_key:
            try:
                fig = figures.figure(figure_key)
            except KeyError:
                raise WikiError(f"{self.ctx.title}: no figure named {figure_key!r}") from None
            self.ctx.figures.append(figure_key)
            note = f'<div class="infobox-caption">{self.inline(caption)}</div>' if caption else ""
            art = f'<tr><td colspan="2" class="infobox-art">{fig.svg}{note}</td></tr>'
        classes = "infobox" + (f" {html.escape(css)}" if css else "")
        return (
            f'<table class="{classes}"><caption>{self.inline(title or self.ctx.title)}</caption>'
            f'<tbody>{art}{"".join(rows)}</tbody></table>'
        )


def _join(items: list) -> str:
    """``a``, ``a and b``, ``a, b and c``."""
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


class _Tables(Postprocessor):
    """Every Markdown table in a frame that scrolls sideways on a
    phone rather than widening the page, and every reference mark
    joined to the word before it."""

    def run(self, text):
        # A word joiner before each reference mark, so "[3]" never
        # starts a line on its own.
        text = text.replace('<sup id="fnref', '&#8288;<sup id="fnref')
        text = text.replace("<table>", '<div class="table-wrap"><table class="wikitable">')
        return re.sub(r"</table>(?!</div>)", "</table></div>", text) if 'class="wikitable"' in text else text


class WikiExtension(Extension):
    """Everything above, registered on one Markdown instance."""

    def __init__(self, ctx: Context, inline=None):
        super().__init__()
        self.ctx = ctx
        self.inline = inline

    def extendMarkdown(self, md):
        ctx = self.ctx
        if "$" not in md.ESCAPED_CHARS:
            md.ESCAPED_CHARS.append("$")  # so a price can be written \\$0.25
        md.inlinePatterns.register(_Math(md, ctx), "wiki-math", 185)
        md.inlinePatterns.register(_Cite(md, ctx), "wiki-cite", 195)  # before code spans: a locator may hold one
        md.inlinePatterns.register(_Fact(md, ctx), "wiki-fact", 177)
        md.inlinePatterns.register(_WikiLink(md, ctx), "wiki-link", 176)
        if self.inline is not None:
            md.preprocessors.register(_Blocks(md, ctx, self.inline), "wiki-blocks", 15)
            md.postprocessors.register(_Tables(md), "wiki-tables", 5)


REFERENCES = "{{references}}"


@dataclass(frozen=True)
class Rendered:
    """One article's HTML and everything rendering it turned up."""

    hatnotes: str
    lead: str
    body: str
    infobox: str
    toc: list
    ctx: Context

    @property
    def html(self) -> str:
        return self.hatnotes + self.lead + self.body


def render(title: str, text: str, resolve) -> Rendered:
    """Render one article's Markdown.

    Parameters
    ----------
    title : str
        The article's title.
    text : str
        Its body, front matter already removed.
    resolve : callable
        ``title -> (slug, exists)``, from the index.

    Returns
    -------
    Rendered
        The hatnotes the article opens with, the lead (everything
        before the first section heading) and the rest as HTML, the
        infobox, the table of contents as Python-
        Markdown's nested tokens, and the context with every link,
        fact, figure and source the article used.

    Raises
    ------
    WikiError
        For an unknown fact, figure or source, or a malformed template.
    """
    ctx = Context(title=title, resolve=resolve)
    text = order_footnotes(title, text)

    inline_md = markdown.Markdown(extensions=[WikiExtension(ctx)], output_format="html")

    def inline(fragment: str) -> str:
        if not fragment:
            return ""
        out = inline_md.reset().convert(fragment)
        return re.sub(r"^<p>|</p>$", "", out.strip())

    md = markdown.Markdown(
        extensions=[
            "tables", "footnotes", "toc", "def_list", "attr_list", "admonition", "sane_lists",
            WikiExtension(ctx, inline),
        ],
        extension_configs={
            "footnotes": {"PLACE_MARKER": REFERENCES, "BACKLINK_TEXT": "^", "SEPARATOR": "-"},
            "toc": {"toc_depth": "2-4"},
        },
        output_format="html",
    )
    out = md.convert(text)
    cut = out.find("<h2")
    lead, body = (out, "") if cut < 0 else (out[:cut], out[cut:])
    hat = re.match(r'(?:\s*<div class="hatnote"[^>]*>.*?</div>)+', lead, flags=re.S)
    hatnotes, lead = (hat.group(0), lead[hat.end():]) if hat else ("", lead)
    return Rendered(
        hatnotes=hatnotes, lead=lead, body=body, infobox=ctx.infobox,
        toc=list(getattr(md, "toc_tokens", [])), ctx=ctx,
    )


_NOTE = re.compile(r"^\[\^([^\]]+)\]:[ \t]*(.*)$", flags=re.M)


def order_footnotes(title: str, text: str) -> str:
    """Move an article's footnote definitions to its end, in the order
    the text first cites them, so References is numbered as it is read
    whatever order the definitions were written in.

    Raises
    ------
    WikiError
        For a note cited and never defined, or defined and never cited.
    """
    notes = dict(_NOTE.findall(text))
    body = _NOTE.sub("", text)
    cited = list(dict.fromkeys(re.findall(r"\[\^([^\]]+)\]", body)))
    missing = [n for n in cited if n not in notes]
    unused = [n for n in notes if n not in cited]
    if missing or unused:
        what = f"cites [^{missing[0]}] and never defines it" if missing else f"defines [^{unused[0]}] and never cites it"
        raise WikiError(f"{title}: {what}")
    return body.rstrip() + "\n\n" + "\n".join(f"[^{n}]: {notes[n]}" for n in cited) + "\n"


def plain(markup: str) -> str:
    """HTML as plain text, for the search index and for excerpts."""
    text = re.sub(r"<(math|svg|style|script)\b.*?</\1>", " ", markup, flags=re.S)
    text = re.sub(r'<a class="thumb-open"[^>]*>.*?</a>', " ", text, flags=re.S)  # a figure's "enlarge"
    text = re.sub(r"<[^>]+>", " ", text)
    return " ".join(html.unescape(text).split())


_H2 = re.compile(r'<h2\b[^>]*\bid="([^"]+)"[^>]*>(.*?)</h2>', flags=re.S)


def sections(body: str) -> list:
    """An article's body as ``(id, heading, text)`` per ``h2`` section,
    in order, each text as `plain` makes it: what a player's model is
    handed a section at a time (`index.Wiki.read`). Subsections stay
    inside their section."""
    marks = list(_H2.finditer(body))
    out = []
    for i, mark in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(body)
        out.append((mark.group(1), plain(mark.group(2)), plain(body[mark.end():end])))
    return out
