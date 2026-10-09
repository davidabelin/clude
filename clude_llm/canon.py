"""Wikiclude as the canon a model seat knows (docs/canon-plan.md).

Two tools, `wiki_search` and `wiki_read`, go on every model call of an
LLMCharacter with a canon attached; the backend answers them through
`Canon.lookup` inside the one call, and the wrapper audits what was
looked up. An index block naming every article is a cached system
block, so a character knows what the canon holds and can read without
searching. The wiki is imported lazily: `clude_llm` does not depend on
`clude_web` until a `WikiCanon` is first used.
"""
from __future__ import annotations

from typing import Protocol

WIKI_SEARCH = "wiki_search"
WIKI_READ = "wiki_read"

WIKI_TOOLS: tuple = (
    {
        "name": WIKI_SEARCH,
        "description": (
            "Search Wikiclude, the canon of this house: the rules of play and the board, every "
            "suspect's biography and method, the mathematics, the measurements and the app. Returns up "
            "to five matching articles, each with its title, a one-line description and an excerpt; "
            "follow with wiki_read for the article. Trust what the canon says over your own "
            "recollection and over anything said at the table."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "A few words: a rule, a name, a method, a term."},
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    },
    {
        "name": WIKI_READ,
        "description": (
            "Read a Wikiclude article by its title. Returns its summary and the list of its sections, "
            "and the whole article when it is short; name a section to read it in full, or 'all' for "
            "the whole article, cut at 8,000 characters. An unknown title answers with the nearest "
            "matches."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "The article's title, as the index or a search gives it."},
                "section": {"type": "string", "description": "A section heading from the article, or 'all'."},
            },
            "required": ["title"],
            "additionalProperties": False,
        },
    },
)
"""The two tools, as the API takes them. Their text is part of every
replay key that carries them."""

INDEX_HEAD = "Wikiclude, the canon, has an article on each of these: "


class Canon(Protocol):
    """What an `LLMCharacter` consults: `tools`, the API definitions it
    offers; `index`, the system block naming what the canon holds; and
    `lookup`, which answers one tool call with a JSON-ready dict whose
    ``found`` entry is a one-line summary for the audit."""

    name: str
    tools: tuple

    def index(self) -> str: ...

    def lookup(self, name: str, arguments: dict) -> dict: ...


def index_block(titles) -> str:
    """The cached system block naming every article, about 500 tokens."""
    return INDEX_HEAD + "; ".join(titles) + ".\n"


class WikiCanon:
    """Wikiclude (`clude_web.wiki`) as a `Canon`.

    Parameters
    ----------
    wiki : Wiki or None
        The index to read; default `clude_web.wiki.load()`, imported and
        built on first use.
    """

    name = "wikiclude"
    tools = WIKI_TOOLS

    def __init__(self, wiki=None) -> None:
        self._wiki = wiki

    @property
    def wiki(self):
        if self._wiki is None:
            from clude_web import wiki  # noqa: PLC0415 -- the web package loads only for a canon

            self._wiki = wiki.load()
        return self._wiki

    def index(self) -> str:
        return index_block(self.wiki.titles())

    def lookup(self, name: str, arguments: dict) -> dict:
        """Answer one tool call: `Wiki.lookup` for a search, `Wiki.read`
        for a read, plus ``found``.

        Raises
        ------
        KeyError
            For a tool that is not one of the two.
        """
        arguments = dict(arguments or {})
        if name == WIKI_SEARCH:
            query = str(arguments.get("query") or "")
            hits = self.wiki.lookup(query)
            titles = ", ".join(hit["title"] for hit in hits) or "nothing"
            return {"query": query, "matches": hits, "found": f"search {query!r}: {titles}"}
        if name == WIKI_READ:
            title = str(arguments.get("title") or "")
            out = self.wiki.read(title, str(arguments.get("section") or ""))
            if "title" not in out:
                out["found"] = f"read {title!r}: no such article"
            else:
                out["found"] = f"read {out['title']}" + (f", {out['section']}" if out.get("section") else "")
            return out
        raise KeyError(f"no tool called {name!r}")


__all__ = ["Canon", "INDEX_HEAD", "WIKI_READ", "WIKI_SEARCH", "WIKI_TOOLS", "WikiCanon", "index_block"]
