# Vendored build-time libraries

| File | Version | Fetched | Licence |
|---|---|---|---|
| `mermaid.min.js` | 10.9.1 (UMD) | 2026-09-30 | MIT, Mermaid contributors, <https://github.com/mermaid-js/mermaid> |

SHA-256 `61B335A46DF05A7CE1C98378F60E5F3E77A7FB608A1056997E8A649304A936D6`,
3,335,717 bytes, from
`https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.min.js`.

Used by the generated diagram pages under `docs/ux/` -- currently
`docs/ux/mustard/index.html`, written by `clude_cli.py train-mustard
--mermaid PATH`. Vendored so those pages draw with no network, like
the Engraved look's faces in `clude_web/static/fonts/`.

## Why here and not `clude_web/static/`

This is a **build-time** dependency, not a served asset. Wikiclude
(D20) is to embed diagrams as pre-rendered, classed SVG -- generated on
a maintainer's machine under Playwright, stripped of Mermaid's inline
hex fills and coloured by the look's stylesheet, the way
`clude_web/board_svg.py` and `clude_web/logo.py` already emit
uncoloured SVG. Nothing ships this file to a player's browser, so it
stays out of the Cloud Run image: `.dockerignore` and `.gcloudignore`
exclude `docs/`, and 3.3 MB of it.

The UMD build, not the ESM one: a page opened over `file://` cannot
load an ES module (CORS), and these pages are meant to open by
double-clicking, as the Phase 10a artboards do.

## Updating

Fetch the same two paths from a pinned version, replace the file, and
update the version, date, hash and size above:

    Invoke-WebRequest -Uri "https://cdn.jsdelivr.net/npm/mermaid@<version>/dist/mermaid.min.js" -OutFile docs\ux\vendor\mermaid.min.js
    (Get-FileHash docs\ux\vendor\mermaid.min.js -Algorithm SHA256).Hash

Then regenerate the pages that use it and *look* at them -- a browser
is the only thing that renders these at all.
