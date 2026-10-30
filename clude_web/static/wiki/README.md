# Character artwork

`card-*.webp` are high-quality exports of the six collector's cards approved by David in the card-design chat. The local PNG masters preserve the original generated pixels. The cards were made with the built-in image generation/editing tool. Green and White use their final painted revisions. Peacock's card reads “Madam Peacock”; her wiki article retains its canonical Mrs. Peacock title.

`token-*.webp` are generated photoreal product-style illustrations, not photographs of an existing physical set. They were made with the built-in image tool on 2026-10-29. Their transparent backgrounds let them sit on each wiki look's figure panel. They replace only the wiki token illustrations, not live board pieces.

## Wooden-piece prompts

Base prompt (Scarlett, no input image):

> Create a photoreal studio product image of ONE classic Clue wooden game pawn for Miss Scarlett. A small real hand-turned wooden object, NOT a character figurine: spherical ball head, narrow neck, gently tapering bell/conical body flaring into a broad round circular foot with a small bevel. Upright, full piece visible, centred, modest three-quarter elevated view showing roundness, generous transparent margin. Hand-painted rich crimson red enamel with subtle brush marks, slight paint irregularity at edges, faint wood grain and small realistic wear. Tasteful satin lustre, clearly actual painted wood not plastic or metal. No letter, logo, face, text, or decorations. Soft warm neutral studio lighting, delicate contact shadow only, isolated on truly TRANSPARENT background. No table, scene, card, frame, border, extra objects. Pawn fills about 75 percent of image height. This is documentary object photography for a wiki, not a painted illustration.

Matching-piece prompt, with the generated Scarlett pawn as the sole shape/lighting reference and transparent-background output enabled:

> Create a matching photoreal studio product image of this same classic hand-turned wooden board-game pawn, hand-painted COLOR instead of red. Preserve exactly the spherical head, narrow neck, tapering bell body, broad round bevelled foot, full upright composition, perspective, lighting and scale of reference. Real hand-painted wood with subtle brush marks and wood grain, slight edge wear, satin enamel. All painted surfaces uniformly COLOR, no residual red. Single piece isolated on genuinely transparent background with soft minimal contact shadow. No text, letters, face, logo, extra objects, scenery or frame. Entire pawn visible with margin. Documentary object photography, not painted illustration.

COLOR values: mustard yellow (Mustard), warm ivory white (White), bottle green (Green), sapphire blue (Peacock), plum purple (Plum).


## Runtime encoding and display

Runtime assets use WebP, encoded at quality 92 with Pillow's method 6,
without resizing. Original dimensions and token alpha channels are preserved.
The twelve PNG files total 24,540,866 bytes; their WebP derivatives total
4,227,492 bytes (82.8% smaller). For comparison, the six cards total
3,006,066 bytes as WebP versus 4,636,734 bytes as JPEG at quality 92 with
4:4:4 chroma sampling. Lossy format quality scales are not equivalent;
the comparison is a practical export comparison, not a quality benchmark.
The exported cards and transparency were checked visually and in Chromium.

PNG masters remain local. `.gcloudignore` and `.dockerignore` exclude
`clude_web/wiki/card_*.png`, `clude_web/wiki/articles/piece_*.png`, and
`clude_web/static/wiki/*.png` so duplicate source images do not enter the
upload or app image. WebP files remain included. No runtime image library
is needed: the app serves these pre-encoded assets directly.

The card and a small labelled Game token share the character infobox,
each with an enlargement link. Card detail pages show the larger artwork;
token detail pages show the wooden piece over a faint decorative board.
