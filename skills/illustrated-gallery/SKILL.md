---
name: illustrated-gallery
description: "Art-direct complete illustrated websites and write project-specific image-generation prompts. Use when the user requests Illustrated Gallery, a gallery-inspired visual style, or $illustrated-gallery. Covers visual direction, original artwork, and page-wide composition; not a fixed website clone, standalone image task, or generic dashboard skill."
---

# Illustrated Gallery

This is an art-direction and image-prompting guide, not a ready-made website.
It ships no images, brand, page markup, or fixed asset list. Create the visual
language and artwork for the user's project; never import a previous project's
pictures or content simply because it used this skill.

## Start with the project

Identify the audience, primary task, actual content, and requested scope. Respect
existing integration requirements. When the user rejects the current UI, inspect
only what is needed to preserve data and behavior, not to reuse its appearance.

Choose a visual direction using [direction examples](references/art-direction.md).
These are starting points, not presets or a closed menu. Palette, medium, subjects,
composition, density, and motion can vary independently. State the chosen direction
briefly and proceed; do not turn routine design choices into an approval interview.

Keep the useful qualities of a gallery: considered composition, strong type
hierarchy, expressive artwork, and enough quiet space to read. Blue botanicals,
serif headlines, floating cards, dark backgrounds, and carousels are optional,
not requirements. Let the subject and user task determine their use.

## Design the whole page

Before implementing, give every requested section a purpose and layout. A complete
redesign includes navigation, the main content, search and filters if present,
onboarding, supporting sections, empty states, and the footer. Changing a hero
image while leaving the rest of the rejected UI intact is not a complete redesign.

Carry a coherent palette, typographic scale, spacing, and visual motifs through
the page, while varying composition to suit each section. A directory may need a
category index and readable resource rows; a portfolio may need large project
images. Do not impose portfolio cards or a studio contact form on unrelated tasks.
Preserve collected content and useful behavior when reorganizing an existing site.

Do not decorate every row with an unrelated generated image. Put artwork where it
helps explain a concept or orient the reader; use typography and layout for dense
information. Do not invent project screenshots, ratings, test results, or endorsements.

## Generate original artwork

Use user-provided project assets where appropriate, otherwise use an available
image-generation tool. Follow its documented workflow. Choose image count and
aspect ratios from the actual layout, never from a fixed sample collection.

For each asset, write a prompt covering:

- **Role and meaning:** its page section and the project idea it should express.
- **Subject:** a concrete scene or visual metaphor relevant to that idea.
- **Medium:** illustration, collage, material study, photography, or another chosen treatment.
- **Palette and light:** how it belongs to this page's visual direction.
- **Composition:** focal point, text-safe areas, framing, and likely mobile crop.
- **Constraints:** no baked-in UI text, invented logos, or misleading product depictions.

Write actual project-specific prompts, not unfilled templates. Across a set, keep
shared medium, material, or lighting coherent while changing subjects and framing.
A style reference guides composition and treatment; it is not an asset to deliver
unless the user explicitly requests that particular image.

Inspect generated images before integrating them. Adjust composition or regenerate
if a subject conflicts with text, a mobile crop loses the focal point, or the result
has misleading labels. Describe conceptual artwork as artwork, not a real product
screenshot or measurement. Store final images in the target project, never in this
skill; record the generation prompts and asset sources in the project's existing
source notes when available.

If suitable images or the generation capability are unavailable, report the missing
asset and continue independent layout work. Ask for the needed asset or an alternative;
do not silently substitute old sample images or claim the design is complete.

## Interaction and implementation

Use the project's existing stack. A static page does not need a framework solely
for this design. Keep content readable without depending on decorative effects.

Choose motion to fit the composition. A still illustration needs no animation.
When a gallery and ASCII dissolve are requested, render a roughly 1.5-second
full-frame transition, sampling the outgoing and incoming image into character
cells; keep the artwork still between changes. Do not substitute a wipe or add
warping, parallax, or continuous zoom without a reason grounded in the brief.

For a carousel, provide pause, previous/next, direct selection, keyboard-operable
controls, touch navigation, and reduced-motion support. Pause stops autoplay but
not manual selection. Separate image movement, transitions, and scrolling behavior.
Load only the initial artwork eagerly; defer other full-size images as appropriate.

## Gotchas and completion checks

Use the target project's checks and inspect the complete page in a browser.

- Artwork, wording, and section purposes fit this project; no copied sample content.
- Every section in the requested scope has been reviewed, including the lower page.
- Desktop and mobile layouts preserve the focal point, readable contrast, and usable controls.
- Navigation, search, filtering, empty states, and any gallery interactions work.
- Images load, transitions are actually observed if used, and reduced motion is respected.
- Resource records and useful existing functionality survive the redesign.
- There are no unrelated images in the published output and no horizontal overflow.

Report any unverified behavior rather than treating syntax checks as visual proof.
Perform authorized local edits and checks directly. Reuse existing authorization for
image generation and deployment; request missing authorization only when the next
action exceeds the user's scope. Never publish to an unrelated site.
