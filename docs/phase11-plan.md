# Phase 11: maintainer documentation

## Scope and decisions

Review documentation and docstrings for a maintainer seeing the project for the first time. This pass does not establish release readiness or validate a trained Plum.

David's choices:

- Shorten completed phases; retain detail for current and future work.
- Condense `CLAUDE.md`, preserving working rules and settled decisions, with links to details.
- Shorten the strategy glossary's discussion while preserving measurement tables, dates, commands and limitations.
- Update executable persona prompts now; regenerate recordings only after separate spend approval.
- Leave Wikiclude outside the review. Its existing source citations must still resolve.

## Changes

README is the setup/reading entry point; the phase plan is a status index. Architecture owns package boundaries and observation/decision contracts, CLI owns commands and side effects, Web owns configuration/lifecycle/deployment, and Logbooks owns memory and persistence. Completed plans retain decisions, deviations and evidence links. Phase 10 keeps its brief, decision rounds and open help scope; Phase 12 keeps the training record and acceptance gates.

Current guides distinguish Plum's seeded network from historical PlumOG measurements. Corrections cover dependencies, board/record versions, account identity, new versus legacy remembering defaults, configuration sources, timeout/cost handling and reconstructed belief traces.

Module and API docstrings describe behavior, perspective, state and side effects without replaying phase history. MCP gameplay tool descriptions remain unchanged. CLI account-creation help now describes the default password accurately. Plum's persona follows the network; shared rules retain legal-choice and table-talk constraints in fewer words.

## Verification

Use the offline suite, Markdown target/anchor checks, and Wikiclude's existing source/fact tests. Compare Python syntax trees with docstrings removed: the intended executable differences are the CLI help text and explicit fixture skips. No gameplay implementation, stored recordings or weights change in this pass.

No live API, browser, deployment or training acceptance is implied by offline checks. The two recorded LLM game cases are pending refresh; fixture-independent prompt/menu/fallback tests remain active.

Local verification on 2026-10-06: **584 passed, 35 skipped** (`python -m pytest -q -n auto`); Wikiclude's offline source/citation checks passed. Current-guide CLI examples parse, four offline workflows run successfully, Markdown targets/anchors resolve, dependency specifications and MCP gameplay descriptions are unchanged, and `git diff --check` is clean. A concurrent implementation edit in `clude_training/rollout.py` is outside the documentation pass.

## Pending recording refresh

Both fixtures include exact system-prompt text in their request keys. Seed 2 was already stale after Phase 12 menu changes; the shared-rule rewrite also invalidates seed 1. Keep the old recordings as historical evidence, without editing keys to make them appear current.

After a separate cost estimate and spend approval, record with the current prompts, menus, model and weights:

```sh
python scripts/clude_cli.py play --seed 1 --players 3 --roster Scarlett,Peacock --llm --llm-backend record:tests/fixtures/llm_seed1.json --verbose
python scripts/clude_cli.py play --seed 2 --players 4 --roster Plum,Mustard,Green,White --llm --llm-backend record:tests/fixtures/llm_seed2.json --verbose
```

Confirm paths and game settings against `tests/test_llm.py` before running. Update `RECORDED_GAMES` outcomes/tallies from the new transcripts, restore the replay cases, and rerun the suite. A trained-weight replacement may change menus again; coordinate this refresh with Phase 12's validation.

Release help, public-release IP review, production checks and Phase 12 N1/N5-N7 work remain separate.
