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
    "docs/wikiclude-plan.md": "Wikiclude: the plan",
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
        'Sutton, Richard S.; Barto, Andrew G. (2018). '
        '<a class="src" href="https://incompleteideas.net/book/the-book-2nd.html" target="_blank" rel="noopener">'
        '<cite>Reinforcement Learning: An Introduction</cite></a> '
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
        'Perolat, Julien; De Vylder, Bart; et al. (2022). '
        '<a class="src" href="https://arxiv.org/abs/2206.15378" target="_blank" rel="noopener">'
        '<cite>Mastering the Game of Stratego with Model-Free Multiagent Reinforcement Learning</cite></a>. '
        'arXiv:2206.15378.'
    ),
    "mnih-2015": (
        'Mnih, Volodymyr; Kavukcuoglu, Koray; Silver, David; et al. (2015). '
        '<a class="src" href="https://doi.org/10.1038/nature14236" target="_blank" rel="noopener">'
        '<cite>Human-level control through deep reinforcement learning</cite></a>. '
        '<cite>Nature</cite>. <b>518</b>: 529-533.'
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


def _source_link(url: str, title: str) -> str:
    """A reference link using the same external-link treatment as citations."""
    return (f'<a class="src" href="{html.escape(url, quote=True)}" '
            f'target="_blank" rel="noopener">{html.escape(title)}</a>')


SOURCES.update({
    "wang-2016": (
        'Wang, Ziyu; Schaul, Tom; Hessel, Matteo; van Hasselt, Hado; Lanctot, Marc; de Freitas, Nando (2016). '
        + _source_link('https://proceedings.mlr.press/v48/wangf16.html', 'Dueling Network Architectures for Deep Reinforcement Learning')
        + '. Proceedings of Machine Learning Research. 48: 1995-2003.'
    ),
    "schaul-2016": (
        'Schaul, Tom; Quan, John; Antonoglou, Ioannis; Silver, David (2016). '
        + _source_link('https://arxiv.org/abs/1511.05952', 'Prioritized Experience Replay')
        + '. ICLR 2016; arXiv:1511.05952.'
    ),
    "heess-2017": (
        'Heess, Nicolas; et al. (2017). '
        + _source_link('https://arxiv.org/abs/1707.02286', 'Emergence of Locomotion Behaviours in Rich Environments')
        + '. arXiv:1707.02286.'
    ),
    "radford-2016": (
        'Radford, Alec; Metz, Luke; Chintala, Soumith (2016). '
        + _source_link('https://arxiv.org/abs/1511.06434', 'Unsupervised Representation Learning with Deep Convolutional Generative Adversarial Networks')
        + '. arXiv:1511.06434, version 2.'
    ),
    "boeing-2017": (
        'Boeing, Geoff (2017). '
        + _source_link('https://geoffboeing.com/publications/osmnx-complex-street-networks/', 'OSMnx: New Methods for Acquiring, Constructing, Analyzing, and Visualizing Complex Street Networks')
        + '. Computers, Environment and Urban Systems. 65: 126-139.'
    ),
    "drive-classwork": (
        'Project reference archive: '
        + _source_link('https://drive.google.com/drive/u/0/folders/1na-qeb9nW2tTbX2S88vR7yjAoryEdoZv', 'Google Drive classwork folder')
        + '. Inventory and cited PDF text checked 2 October 2026; Drive copies may require access.'
    ),
    "drive-cheatsheet": (
        'Project reference archive: '
        + _source_link('https://drive.google.com/file/d/1jqEAFVJ5MB9LVSHOl5DtTBc9irV0X6m0/view', 'RL cheatsheet.pdf')
        + '. Author and date not established; used as a revision aid alongside Sutton and Barto.'
    ),
})

# Preserve a route to the particular copies supplied for W6, alongside public originals.
for _key, _file_id in {
    "sutton-barto": "1tb7worcFX4I1mdNOhcs0hQV2hhP_pvEn",
    "mnih-2015": "1Llmwg8vFgN1bs_m9JR-sHyszNlZXmLVW",
    "wang-2016": "1Ymfhr3SCOQLigDxUWfzNGzdgrqDmxEMD",
    "schaul-2016": "1kC2KuQk6e7absi1hs11TECE5t8Ss2WU7",
    "perolat-2022": "1YLN22GCyOxPtXpoA2G1tINWh0Az5yObh",
    "heess-2017": "1G5a8rF-Sx4ywwVmjlyUt6IKRmo4htyd8",
    "radford-2016": "1CGR4o4C619joUOIkdjFggzXOKqZC720D",
    "boeing-2017": "15F5tvT_q0dSfhN-ykRUUr6TywzqOVaY3",
}.items():
    SOURCES[_key] += ' ' + _source_link(f'https://drive.google.com/file/d/{_file_id}/view', 'Archive copy') + '.'


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
