"""Wikiclude: the encyclopaedia of clude (D20; `docs/wikiclude-plan.md`).

Wikipedia-style articles on the characters, their methods, the game and
what the measurements found, written for every reader at once and
served under ``/wiki``. The articles are Markdown files in
``articles/``; this package renders them once at start-up and keeps the
result in memory.

- `render` -- the markup: wikilinks, Wikipedia links, facts, citations,
  mathematics, figures, infoboxes.
- `index` -- `load()` and the `Wiki` it returns: articles, redirects,
  categories, backlinks, wanted pages, search.
- `facts` -- every number an article quotes, each traced to the doc or
  the module it came from.
- `figures` -- the pictures, as uncoloured SVG the stylesheet dresses.
- `sources` -- what is cited, and how a citation reads.

Lives under `clude_web` because `docs/` is not in the Cloud Run image.
"""
from __future__ import annotations

from .index import Article, Wiki, load
from .render import WikiError, key_of, slug_of

__all__ = ["Article", "Wiki", "WikiError", "key_of", "load", "slug_of"]
