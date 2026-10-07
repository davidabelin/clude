"""Build the method diagrams: docs/ux/diagrams/index.html.

    .venv\\Scripts\\python.exe docs\\ux\\diagrams\\build_diagrams.py

One registry, one page per key, and a contact sheet that opens them all
in any browser. Mermaid is the vendored copy in docs/ux/vendor, so the
pages draw offline.

Everything factual is read from the modules being diagrammed -- the real
constants, the real docstrings, the real trained tree -- so a diagram
cannot quietly disagree with the code. That is the whole point of
generating them: `docs/ux/mustard/index.html` began as a hand-drawn
Mermaid block and was already wrong about its own thresholds.

`DIAGRAMS` is the seam Wikiclude (D20) is meant to use: an article asks
for a key, and this module hands back the source. The colours are
Mermaid's inline hex today; a Wikiclude build is expected to render each
key to classed SVG instead and let the look's stylesheet decide, the way
`clude_web/board_svg.py` and `clude_web/logo.py` already do.
"""
from __future__ import annotations

import inspect
import os
import sys
from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent.parent))

from clude_agents import naive_bayes  # noqa: E402
from clude_agents.decision_tree import DecisionTreeAgent, mermaid_tree  # noqa: E402
from clude_constraints import propagator  # noqa: E402

VENDOR = HERE.parent / "vendor" / "mermaid.min.js"

THEME = """theme: "base",
  themeVariables: { background: "#f6f2e8", primaryColor: "#efe7d5",
    primaryBorderColor: "#8d8878", primaryTextColor: "#22201a",
    lineColor: "#6b5d49", fontFamily: "Inter, system-ui, sans-serif",
    clusterBkg: "#ece5d4", clusterBorder: "#b3a98f" },"""


def _rule_label(fn) -> str:
    """A propagation rule's own first docstring line, so the diagram
    says what the code says. `_propagate_or_constraints` carries its
    explanation as an inline comment rather than a docstring, so it
    falls back to its name."""
    doc = inspect.getdoc(fn)
    if not doc:
        return fn.__name__.removeprefix("_propagate_").replace("_", " ")
    return doc.splitlines()[0].rstrip(".")


# --- the diagrams ---------------------------------------------------------


def scarlett_update() -> str:
    """Scarlett's fold: what she actually multiplies."""
    boost = naive_bayes.UNREFUTED_BOOST
    decay = naive_bayes.REFUTED_UNKNOWN_DECAY
    return f"""flowchart LR
    S(["every card starts at 1.0"]) --> L{{"each suggestion<br/>in the log"}}
    L --> U["nobody refuted<br/>(refuter is None)"]
    L --> R["refuted, card unseen<br/>(card_shown is None)"]
    L --> K["refuted, card seen"]
    U --> UB["all three cards<br/>&times; {boost}"]
    R --> RB["all three cards<br/>&times; {decay:.3f}"]
    K --> KB["no soft update:<br/>the floor has the fact"]
    UB --> M["mask by the floor"]
    RB --> M
    KB --> M
    M --> N["renormalise<br/>within each category"]
    N --> B(["ClueBelief"])
    classDef up fill:#8c2f16,stroke:#3c1206,color:#fff
    classDef down fill:#2f4f6b,stroke:#16283a,color:#eaf0f6
    classDef flat fill:#e8e4d8,stroke:#8d8878,color:#22201a
    class UB up
    class RB down
    class KB flat"""


def scarlett_net() -> str:
    """The independence assumption, and the edge that is missing."""
    decay = naive_bayes.REFUTED_UNKNOWN_DECAY
    return f"""flowchart TD
    H(["is Rope the envelope's?"])
    H --> E1["turn 4 &middot; Scarlett / Rope / Study<br/>P2 refuted, card unseen"]
    H --> E2["turn 9 &middot; Plum / Rope / Hall<br/>P2 refuted, card unseen"]
    H --> E3["turn 14 &middot; Green / Rope / Library<br/>P2 refuted, card unseen"]
    E1 --> M["Scarlett multiplies:<br/>&times; {decay:.3f} &times; {decay:.3f} &times; {decay:.3f} = &times; {decay ** 3:.3f}<br/>three independent witnesses"]
    E2 --> M
    E3 --> M
    E1 <-. "the edge she has no term for" .-> E2
    E2 <-. " " .-> E3
    E1 <-. " " .-> E3
    C["but P2 may hold Rope alone:<br/>one card, one fact, three times counted"]
    C -.-> E1
    C -.-> E2
    C -.-> E3
    classDef hyp fill:#c88a2c,stroke:#6b4610,color:#1a1208
    classDef ev fill:#efe7d5,stroke:#8d8878,color:#22201a
    classDef bad fill:#8c2f16,stroke:#3c1206,color:#fff
    classDef calc fill:#2f4f6b,stroke:#16283a,color:#eaf0f6
    class H hyp
    class E1,E2,E3 ev
    class M calc
    class C bad"""


def floor_propagation() -> str:
    """The deduction floor's seeding and its fixpoint loop."""
    or_rule = _rule_label(propagator._Working._propagate_or_constraints)
    cat_rule = _rule_label(propagator._Working._propagate_category_rule)
    hand_rule = _rule_label(propagator._Working._propagate_hand_sizes)
    return f"""flowchart TD
    O(["ClueObservation<br/>one seat's view"]) --> SEED["seed: every card<br/>could be anyone's or the envelope's"]
    SEED --> H1["own hand<br/>&rarr; assign to me"]
    H1 --> H2["passed over without refuting<br/>&rarr; eliminate those three"]
    H2 --> H3["a card was shown to me<br/>&rarr; assign to the refuter"]
    H3 --> H4["refuted, card unseen<br/>&rarr; record an OR-constraint"]
    H4 --> LOOP{{"anything changed?"}}
    LOOP -- yes --> R1["{or_rule}"]
    R1 --> R2["{cat_rule}"]
    R2 --> R3["{hand_rule}"]
    R3 --> LOOP
    LOOP -- no --> OUT(["ConstraintResult"])
    OUT --> P1["possible_holders<br/>per card"]
    OUT --> P2["or_constraints<br/>still open"]
    OUT --> P3["hand_sizes"]
    X["contradiction<br/>&rarr; ConstraintError"]
    R1 -.-> X
    R3 -.-> X
    classDef seedc fill:#e8e4d8,stroke:#8d8878,color:#22201a
    classDef rule fill:#2f4f6b,stroke:#16283a,color:#eaf0f6
    classDef out fill:#c88a2c,stroke:#6b4610,color:#1a1208
    classDef bad fill:#8c2f16,stroke:#3c1206,color:#fff
    class SEED,H1,H2,H3,H4 seedc
    class R1,R2,R3 rule
    class P1,P2,P3 out
    class X bad"""


def floor_then_method() -> str:
    """Where the floor sits relative to every method -- the invariant."""
    return """flowchart LR
    O(["ClueObservation"]) --> F["deduction floor<br/>propagate()"]
    F --> MASK["what is still possible"]
    MASK --> S["Scarlett<br/>naive Bayes"]
    MASK --> P["Plum<br/>trained network"]
    MASK --> K["Peacock<br/>Dempster-Shafer"]
    MASK --> U["Mustard<br/>decision tree"]
    MASK --> W["White<br/>Markov"]
    MASK --> G["Green<br/>bandit ensemble"]
    S --> R["raw scores"]
    P --> R
    K --> R
    U --> R
    W --> R
    G --> R
    R --> N["mask_and_normalize"]
    N --> B(["ClueBelief"])
    B --> C["Character<br/>+ personality dials"]
    C --> A(["the engine's four decisions"])
    classDef floorc fill:#2f4f6b,stroke:#16283a,color:#eaf0f6
    classDef method fill:#efe7d5,stroke:#8d8878,color:#22201a
    classDef gate fill:#c88a2c,stroke:#6b4610,color:#1a1208
    class F,MASK floorc
    class S,P,K,U,W,G method
    class N,C gate"""


def mustard_tree() -> str:
    """The real trained tree, from the live model."""
    return mermaid_tree(DecisionTreeAgent().tree)


def architecture() -> str:
    """The packages, and what crosses each seam (CLAUDE.md's
    architecture in brief)."""
    return """flowchart TD
    WEB["clude_web<br/>tables, lobby, Watch, wiki;<br/>browser and MCP seats"]
    CORE["clude_core<br/>rules and engine"]
    FLOOR["clude_constraints<br/>the deduction floor"]
    AG["clude_agents<br/>six methods, Character, dials"]
    LLM["clude_llm<br/>menus, leash, personas"]
    TR["clude_training<br/>benchmark, arena, rollout"]
    ST["clude_storage<br/>records and logbooks"]
    WEB -- "seats and moves" --> CORE
    TR -- "self-play, arenas" --> CORE
    CORE -- "one seat's redacted view" --> FLOOR
    FLOOR -- "what is certain" --> AG
    AG -- "belief and scores" --> LLM
    LLM -. "the action, back to the engine" .-> CORE
    CORE -- "the event log" --> ST
    ST -. "logbooks, read back" .-> AG
    classDef floorc fill:#2f4f6b,stroke:#16283a,color:#eaf0f6
    classDef method fill:#efe7d5,stroke:#8d8878,color:#22201a
    classDef gate fill:#c88a2c,stroke:#6b4610,color:#1a1208
    class CORE,FLOOR floorc
    class AG,LLM,TR method
    class WEB,ST gate"""


def decision_pathway() -> str:
    """One decision of a character's seat, from the engine's question
    to its answer, with and without a model in the seat."""
    return """flowchart TD
    E(["the engine asks a seat:<br/>move, suggest, accuse or show"]) --> OBS["that seat's view:<br/>own hand, the public log"]
    OBS --> F["deduction floor:<br/>what is certain"]
    F --> M["the character's method:<br/>belief, and its own scores"]
    M --> C["Character: the dials<br/>threshold, bluff, secrecy"]
    C --> Q{"a model<br/>in the seat?"}
    Q -- no --> H["headless: sample<br/>at the temperature"]
    Q -- yes --> MENU["menu: the options<br/>within the leash"]
    MENU --> ONE{"only one<br/>allowed?"}
    ONE -- yes --> AUTO["played without asking"]
    ONE -- no --> ASK["the model chooses,<br/>in the persona's voice"]
    ASK -. "no valid answer" .-> H
    H --> A(["the action, back to the engine"])
    AUTO --> A
    ASK --> A
    classDef floorc fill:#2f4f6b,stroke:#16283a,color:#eaf0f6
    classDef method fill:#efe7d5,stroke:#8d8878,color:#22201a
    classDef gate fill:#c88a2c,stroke:#6b4610,color:#1a1208
    class F floorc
    class M,C,H,AUTO method
    class MENU,ASK gate"""


def plum_training_loop() -> str:
    """Plum's training (scripts/train_plum.py): one iteration of
    regularised Nash dynamics, and the checkpoints around it."""
    return """flowchart TD
    W(["the network's weights"]) --> R["play 512 games: half against itself,<br/>half among the other characters"]
    R --> EP["each network seat's record:<br/>states, choices, outcome, true envelope"]
    EP --> RR["regularise the reward:<br/>r − η log π/πref"]
    RR --> L["one loss: NeuRD policy, value,<br/>belief from a replay buffer, entropy"]
    L --> U["one gradient step"]
    U --> W
    U -. "every few iterations" .-> REF["πref ← a copy of π"]
    REF -.-> RR
    U -. "every ten iterations" .-> EV["measure: benchmark,<br/>his table, six characters"]
    EV --> CK["checkpoint"]
    CK --> SEL{"the run's best,<br/>on 96 games?"}
    SEL -- yes --> EX(["export: plum.npz"])
    classDef floorc fill:#2f4f6b,stroke:#16283a,color:#eaf0f6
    classDef method fill:#efe7d5,stroke:#8d8878,color:#22201a
    classDef gate fill:#c88a2c,stroke:#6b4610,color:#1a1208
    class R,EP method
    class RR,L,U floorc
    class EV,CK,EX gate"""


def gpi() -> str:
    """Generalised policy iteration (Sutton and Barto, 4.6)."""
    return """flowchart TD
    P(["policy π"]) -- "evaluate" --> V(["value V"])
    V -- "improve: greedy in V" --> P
    P -.-> OPT(["both settle: π* and v*"])
    V -.-> OPT
    classDef floorc fill:#2f4f6b,stroke:#16283a,color:#eaf0f6
    classDef method fill:#efe7d5,stroke:#8d8878,color:#22201a
    classDef gate fill:#c88a2c,stroke:#6b4610,color:#1a1208
    class P,V method
    class OPT gate"""


def mcts_phases() -> str:
    """The four phases of one Monte Carlo tree search simulation."""
    return """flowchart TD
    S["1. selection<br/>walk down by the UCB rule"] --> E["2. expansion<br/>add one untried move"]
    E --> R["3. simulation<br/>play to the end, fast and random"]
    R --> B["4. backup<br/>add the result along the path"]
    B -- "next simulation" --> S
    B -. "budget spent" .-> M(["play the most-visited move"])
    classDef floorc fill:#2f4f6b,stroke:#16283a,color:#eaf0f6
    classDef method fill:#efe7d5,stroke:#8d8878,color:#22201a
    classDef gate fill:#c88a2c,stroke:#6b4610,color:#1a1208
    class S,E,R,B method
    class M gate"""


def actor_critic() -> str:
    """One-step actor-critic (Sutton and Barto, 13.5)."""
    return """flowchart TD
    ENV(["environment"]) -- "S" --> A["actor<br/>policy π(a | s)"]
    A -- "A" --> ENV
    ENV -- "R, S′" --> C["critic<br/>value v(s)"]
    C -- "TD error δ" --> A
    classDef floorc fill:#2f4f6b,stroke:#16283a,color:#eaf0f6
    classDef method fill:#efe7d5,stroke:#8d8878,color:#22201a
    classDef gate fill:#c88a2c,stroke:#6b4610,color:#1a1208
    class A gate
    class C floorc
    class ENV method"""


def gan() -> str:
    """A generative adversarial network's two players."""
    return """flowchart TD
    Z(["random noise z"]) --> G["generator<br/>forges an example"]
    X(["real examples"]) --> D["discriminator<br/>real or forged?"]
    G --> D
    D -. "judgement" .-> G
    classDef floorc fill:#2f4f6b,stroke:#16283a,color:#eaf0f6
    classDef method fill:#efe7d5,stroke:#8d8878,color:#22201a
    classDef gate fill:#c88a2c,stroke:#6b4610,color:#1a1208
    class G gate
    class D floorc
    class Z,X method"""


DIAGRAMS: dict = {
    "floor-then-method": (
        "The deduction floor, and where every method sits",
        "CLAUDE.md's first invariant, as a picture: <em>the floor masks every belief before it "
        "is used. Agents differ in how they reason under uncertainty, never in what is logically "
        "certain.</em> Six methods, one gate in front of them and one after. Every method "
        "article needs this one.",
        floor_then_method,
    ),
    "floor-propagation": (
        "Inside the floor: seeding and the fixpoint",
        "What <code>propagate()</code> does to one seat's observation. The four seeding steps run "
        "once; the three rules then run in a loop until a pass changes nothing. Rule labels are "
        "read from the methods' own docstrings, so they cannot drift. Recomputed from scratch "
        "every call -- no agent can act on a stale mask.",
        floor_propagation,
    ),
    "scarlett-update": (
        "Scarlett: the multiplicative fold",
        "Her whole method. Three kinds of suggestion, two soft updates, then the same mask and "
        "renormalise every method ends with. The two factors are read live from "
        "<code>naive_bayes.py</code>.",
        scarlett_update,
    ),
    "scarlett-net": (
        "Scarlett: the independence assumption, and what it costs",
        "The left panel is the net her arithmetic implies -- each suggestion an independent "
        "witness, no edges between them. The right is the same three suggestions when one player "
        "refuted all three: they are coupled, because a single card in that hand can answer all "
        "of them. Scarlett multiplies her decay three times as if she had learned three separate "
        "things. <strong>The missing edges are the character.</strong>",
        scarlett_net,
    ),
    "mustard-tree": (
        "Mustard: the trained tree",
        "Grown from the live model, not transcribed. Leaves are banded by how sure they are: "
        "cold under 0.10, cool to 0.35, warm to 0.65, hot above.",
        mustard_tree,
    ),
    "architecture": (
        "clude's packages",
        "The seven packages and what crosses each seam: the engine hands a seat its redacted "
        "view, the floor settles what is certain, a method and its character turn that into "
        "an action, and the store keeps what happened.",
        architecture,
    ),
    "decision-pathway": (
        "One decision, end to end",
        "The path of one of a character's decisions, from the engine's question to its answer, "
        "headless or with a model in the seat.",
        decision_pathway,
    ),
    "plum-training-loop": (
        "Plum's training loop",
        "One iteration of regularised Nash dynamics as <code>scripts/train_plum.py</code> runs it, "
        "and the checkpoints around it.",
        plum_training_loop,
    ),
    "gpi": ("Generalised policy iteration", "Evaluation and improvement, each making the other out of date, until both settle.", gpi),
    "mcts-phases": ("Monte Carlo tree search", "The four phases of one simulation.", mcts_phases),
    "actor-critic": ("Actor-critic", "The actor acts; the critic's TD error trains them both.", actor_critic),
    "gan": ("A generative adversarial network", "The generator forges, the discriminator judges, and each learns from the judgement.", gan),
}


# --- page scaffolding -----------------------------------------------------

STYLE = """
body { margin: 0; padding: 32px; background: #2b282c; color: #d9d3c7;
  font: 14px/1.5 Inter, system-ui, sans-serif; }
h1 { font: 600 24px/1.2 Georgia, serif; color: #f0c67e; margin: 0 0 6px; }
h2 { font: 600 17px/1.25 Georgia, serif; color: #f0c67e; margin: 0 0 6px; }
p.lede { color: #a9a090; margin: 0 0 32px; max-width: 62em; }
p.note { color: #a9a090; margin: 0 0 12px; max-width: 62em; }
code { font-family: "IBM Plex Mono", ui-monospace, monospace; color: #f0c67e; }
section { margin: 0 0 40px; }
.chart { background: #f6f2e8; border: 1px solid #6b5d49; border-radius: 3px;
  padding: 16px; overflow: auto; }
details { margin-top: 12px; }
summary { cursor: pointer; color: #f0c67e; font-size: 13px; }
details pre { background: #201e22; border: 1px solid #4a4348; padding: 12px;
  overflow: auto; font-size: 12px; color: #d9d3c7; }
pre.mermaid { margin: 0; background: none; border: 0; }
pre.mermaid svg { max-width: none; height: auto; }
pre.mermaid .edgeLabel, pre.mermaid .edgeLabel p { background: #f6f2e8 !important; }
nav { margin: 0 0 32px; }
nav a { color: #f0c67e; margin-right: 16px; font-size: 13px; }
"""


def build(out_dir: Path = HERE) -> Path:
    """Write the contact sheet; returns its path."""
    out_dir.mkdir(parents=True, exist_ok=True)
    index = out_dir / "index.html"
    try:
        library = Path(os.path.relpath(VENDOR, index.parent)).as_posix()
    except ValueError:  # a different drive: no relative path exists
        library = VENDOR.as_uri()

    nav = " ".join(f'<a href="#{key}">{escape(key)}</a>' for key in DIAGRAMS)
    sections = []
    for key, (title, note, builder) in DIAGRAMS.items():
        source = builder()
        sections.append(
            f'<section id="{key}">\n'
            f"<h2>{escape(title)}</h2>\n"
            f'<p class="note">{note}</p>\n'
            f'<div class="chart"><pre class="mermaid">{source}</pre></div>\n'
            f"<details><summary>Source &middot; {escape(key)}</summary>"
            f"<pre>{escape(source)}</pre></details>\n"
            f"</section>"
        )

    index.write_text(
        f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>clude &middot; method diagrams</title>
<style>{STYLE}</style>
</head>
<body>
<h1>clude &middot; method diagrams</h1>
<p class="lede">
Generated by <code>docs/ux/diagrams/build_diagrams.py</code> -- regenerate rather than edit.
Constants, docstrings and the trained tree are read from the live modules, so nothing here can
quietly disagree with the code. Drawn with the vendored Mermaid in <code>docs/ux/vendor</code>,
so this page needs no network.
</p>
<nav>{nav}</nav>
{chr(10).join(sections)}
<script src="{library}"></script>
<script>
mermaid.initialize({{ startOnLoad: true, securityLevel: "loose",
  {THEME}
  flowchart: {{ useMaxWidth: false, nodeSpacing: 28, rankSpacing: 44 }} }});
</script>
</body>
</html>
""",
        encoding="utf-8",
    )
    return index


def check(index: Path) -> list:
    """Parse every diagram in a real browser and return the keys that
    failed. Mermaid's grammar has traps a generator cannot see -- a
    `direction` line inside a subgraph is rejected, and a syntax error
    renders as a small "Syntax error in text" box rather than raising --
    so a page can look built and be broken. Needs Playwright."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page()
            page.goto(index.as_uri())
            page.wait_for_timeout(2500)
            return page.evaluate(
                """() => [...document.querySelectorAll("section")]
                    .filter((s) => {
                      const svg = s.querySelector("pre.mermaid svg");
                      return !svg || [...svg.querySelectorAll("text")]
                        .some((t) => t.textContent.includes("Syntax error"));
                    })
                    .map((s) => s.id)"""
            )
        finally:
            browser.close()


def main() -> None:
    index = build()
    print(f"{index}: {len(DIAGRAMS)} diagrams -- open it in a browser")
    if not VENDOR.exists():
        print(f"  WARNING: {VENDOR} is missing -- see its README to refetch")
        return
    try:
        broken = check(index)
    except ImportError:
        print("  (install playwright to check that every diagram parses)")
        return
    if broken:
        raise SystemExit(f"  FAILED to render: {', '.join(broken)}")
    print(f"  all {len(DIAGRAMS)} parse and render")


if __name__ == "__main__":
    main()
