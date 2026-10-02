"""What Wikiclude cites, and how a citation is printed.

Three kinds of source, one template (``{{cite:key|locator}}``):

- **The project's own docs**, by path: ``{{cite:docs/strategy-glossary.md|Heading}}``
  links the doc on GitHub at that heading. The docs are the primary
  source for everything clude has measured.
- **The code**, by path: ``{{cite:clude_agents/exact_enum.py}}`` links
  the module; a locator names what to look at in it.
- **Books and papers**, by the keys of `SOURCES`.

`docs/` is not in the Cloud Run image, so a doc's title is recorded here
(`DOCS`) rather than read from the file; `tests/test_wiki.py` checks
every cited path, title and heading against the repository.
"""
from __future__ import annotations

import html
import re

REPO = "https://github.com/davidabelin/clude/blob/main/"

DOCS: dict = {
    "docs/strategy-glossary.md": "Strategy glossary",
    "docs/architecture.md": "Architecture",
    "docs/llm-wrapper.md": "The LLM wrapper",
    "docs/logbooks.md": "Logbooks: playerbot memory",
    "docs/board.md": "Board",
    "docs/web.md": "The web app",
    "docs/cli.md": "Maintainer CLI",
    "docs/phase-plan.md": "Phase plan",
    "docs/phase5-plan.md": "Phase 5 plan",
    "docs/phase6-plan.md": "Phase 6 plan: the LLM wrapper",
    "docs/phase7-plan.md": "Phase 7 plan: playerbot memory, the logbooks",
    "docs/phase8-plan.md": "Phase 8 to completion",
    "docs/phase10-plan.md": "Phase 10 plan",
    "CLAUDE.md": "clude (working notes)",
}
"""Each citable doc and the title a citation gives it."""

SOURCES: dict = {
    "gneiting-raftery-2007": (
        'Gneiting, Tilmann; Raftery, Adrian E. (2007). '
        '<a class="src" href="https://sites.stat.washington.edu/raftery/Research/PDF/Gneiting2007jasa.pdf" '
        'target="_blank" rel="noopener"><cite>Strictly Proper Scoring Rules, Prediction, and Estimation</cite></a>. '
        '<cite>Journal of the American Statistical Association</cite>. <b>102</b> (477): 359-378.'
    ),
    "nist-beta": (
        'NIST/SEMATECH. <a class="src" href="https://www.itl.nist.gov/div898/handbook/eda/section3/eda366h.htm" '
        'target="_blank" rel="noopener"><cite>e-Handbook of Statistical Methods</cite></a>, section 1.3.6.6.17, Beta Distribution.'
    ),
    "shannon-1948": (
        'Shannon, Claude E. (1948). <a class="src" href="https://people.math.harvard.edu/~ctm/home/text/others/shannon/entropy/entropy.pdf" '
        'target="_blank" rel="noopener"><cite>A Mathematical Theory of Communication</cite></a>. '
        '<cite>Bell System Technical Journal</cite>. <b>27</b>: 379-423, 623-656.'
    ),
    "russo-2018": (
        'Russo, Daniel; Van Roy, Benjamin; Kazerouni, Abbas; Osband, Ian; Wen, Zheng (2018). '
        '<a class="src" href="https://web.stanford.edu/~bvr/pubs/TS_Tutorial.pdf" target="_blank" rel="noopener">'
        '<cite>A Tutorial on Thompson Sampling</cite></a>. '
        '<cite>Foundations and Trends in Machine Learning</cite>. <b>11</b> (1): 1-96.'
    ),
    "sutton-barto": (
        "Sutton, Richard S.; Barto, Andrew G. (2018). <cite>Reinforcement Learning: An Introduction</cite> "
        "(2nd ed.). Cambridge, Massachusetts: MIT Press."
    ),
    "russell-norvig": (
        "Russell, Stuart; Norvig, Peter (2021). <cite>Artificial Intelligence: A Modern Approach</cite> "
        "(4th ed.). Pearson."
    ),
    "domingos-pazzani": (
        "Domingos, Pedro; Pazzani, Michael (1997). \"On the Optimality of the Simple Bayesian Classifier "
        "under Zero-One Loss\". <cite>Machine Learning</cite>. <b>29</b>: 103-130."
    ),
    "hand-yu": (
        "Hand, David J.; Yu, Keming (2001). \"Idiot's Bayes: Not So Stupid after All?\". "
        "<cite>International Statistical Review</cite>. <b>69</b> (3): 385-398."
    ),
    "perolat-2022": (
        "Perolat, Julien; De Vylder, Bart; et al. (2022). \"Mastering the Game of Stratego with Model-Free "
        "Multiagent Reinforcement Learning\". arXiv:2206.15378."
    ),
    "mnih-2015": (
        "Mnih, Volodymyr; Kavukcuoglu, Koray; Silver, David; et al. (2015). \"Human-level control through "
        "deep reinforcement learning\". <cite>Nature</cite>. <b>518</b>: 529-533."
    ),
    "dempster-1967": (
        "Dempster, Arthur P. (1967). \"Upper and Lower Probabilities Induced by a Multivalued Mapping\". "
        "<cite>The Annals of Mathematical Statistics</cite>. <b>38</b> (2): 325-339."
    ),
    "shafer-1976": (
        "Shafer, Glenn (1976). <cite>A Mathematical Theory of Evidence</cite>. Princeton, New Jersey: "
        "Princeton University Press."
    ),
    "smets-kennes-1994": (
        "Smets, Philippe; Kennes, Robert (1994). \"The transferable belief model\". "
        "<cite>Artificial Intelligence</cite>. <b>66</b> (2): 191-234."
    ),
    "breiman-1984": (
        "Breiman, Leo; Friedman, Jerome H.; Olshen, Richard A.; Stone, Charles J. (1984). "
        "<cite>Classification and Regression Trees</cite>. Belmont, California: Wadsworth."
    ),
    "thompson-1933": (
        "Thompson, William R. (1933). \"On the Likelihood that One Unknown Probability Exceeds Another "
        "in View of the Evidence of Two Samples\". <cite>Biometrika</cite>. <b>25</b> (3-4): 285-294."
    ),
    "norris-1997": (
        "Norris, James R. (1997). <cite>Markov Chains</cite>. Cambridge: Cambridge University Press."
    ),
}
"""Books and papers, each as its citation reads. The first two are
textbooks; `perolat-2022` and `mnih-2015` are among the classwork papers
David keeps; the rest are the founding works of the methods (W2)."""


def github_anchor(heading: str) -> str:
    """The fragment GitHub gives a Markdown heading: lower case,
    punctuation dropped, each space a hyphen."""
    kept = re.sub(r"[^\w\- ]", "", heading.strip().lower())
    return kept.replace(" ", "-")


def is_path(key: str) -> bool:
    """Whether a citation key names a file in the repository."""
    return key in DOCS or "/" in key or key.endswith((".py", ".md"))


def citation(key: str, locator: str = "") -> str:
    """One citation as HTML.

    Parameters
    ----------
    key : str
        A doc or code path, or a key of `SOURCES`.
    locator : str
        A doc's section heading, or free text locating the passage
        (a chapter, a function name).

    Raises
    ------
    KeyError
        If `key` is neither a path nor a known source.
    """
    where = re.sub(r"`([^`]+)`", r"<code>\1</code>", html.escape(locator))
    if key in DOCS:
        url = REPO + key + (f"#{github_anchor(locator)}" if locator else "")
        section = f', section "{where}"' if locator else ""
        return (
            f'clude documentation: <a class="src" href="{url}" target="_blank" rel="noopener">'
            f"<cite>{html.escape(DOCS[key])}</cite></a>{section}."
        )
    if is_path(key):
        if key.endswith(".md") and key.startswith("docs/"):
            raise KeyError(key)  # a doc nobody has given a title: add it to DOCS
        detail = f", {where}" if locator else ""
        return (
            f'clude source: <a class="src" href="{REPO}{key}" target="_blank" rel="noopener">'
            f"<code>{html.escape(key)}</code></a>{detail}."
        )
    text = SOURCES[key]
    return text + (f" {where}." if locator else "")
