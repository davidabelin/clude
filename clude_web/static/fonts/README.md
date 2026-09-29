# The Engraved look's faces

Latin-subset variable woff2 files, fetched from Google Fonts on
2026-09-28 (Phase 10b) and served from here so the app makes no
third-party request. All four are published under the SIL Open Font
License 1.1 (<https://openfontlicense.org>), which permits bundling and
serving them unchanged provided the licence and the reserved font
names are respected; they are not modified here.

| File | Face | Copyright |
|---|---|---|
| `bodoni-moda-normal-400-900.woff2`, `bodoni-moda-italic-400-900.woff2` | Bodoni Moda (opsz, wght) | Indestructible Type, <https://github.com/indestructible-type/Bodoni> |
| `playfair-display-normal-400-900.woff2`, `playfair-display-italic-400-900.woff2` | Playfair Display (wght) | Claus Eggers Sorensen, <https://github.com/clauseggers/Playfair> |
| `inter-normal-400-700.woff2` | Inter (wght) | Rasmus Andersson, <https://github.com/rsms/inter> |
| `ibm-plex-mono-normal-400.woff2`, `ibm-plex-mono-normal-500.woff2`, `ibm-plex-mono-italic-400.woff2` | IBM Plex Mono | IBM, <https://github.com/IBM/plex> |

`styles/engraved.css` declares the `@font-face` rules; the roles are
in `docs/phase10-plan.md` 5.3 (Bodoni Moda the wordmark, Playfair
Display headings and captions, Inter the text, IBM Plex Mono the
numbers). `faces.txt` is the fetch's manifest.
