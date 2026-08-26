# Visual Explanation Contract

The page should teach one causal model, not display research inventory.

## Teaching Priorities

- Lead with the shortest accurate answer.
- Pre-teach only the terms needed to read the visual.
- Show the causal structure at its natural level of detail; do not force a step count.
- Place evidence close to the relationship it supports.
- Make important failure boundaries, limitations, or counterexamples easy to find.
- Provide direct sources without turning the page into a research inventory.

## Two Depths, One Explanation

When there is substantial implementation or research evidence, show the same causal model twice at different depths.

The orientation layer is the entry point. It should answer the teaching question in plain language and make one causal picture visually dominant. A reader who stops there should still leave with the right model. Research process, packaging facts, function names, source lists, and secondary branches must not displace this answer from the first view.

The evidence layer serves the reader who keeps going. It may expose exact symbols, requests, storage paths, branches, failure behavior, citations, and uncertainty. Put it after the orientation layer or behind an obvious disclosure control when simultaneous display would dilute the focus.

Both layers must describe the same mechanism. Do not simplify by changing causality, and do not create a separate technical report that never reconnects to the opening picture. Let subject complexity determine length and structure rather than enforcing numeric limits.

## Choose the Visual Grammar

| Relationship | Preferred visual |
|---|---|
| Transformation or pipeline | Left-to-right flow |
| Ordered interaction between actors | Sequence diagram |
| Modes and transitions | State machine |
| Components and ownership | Architecture diagram |
| Cause and propagation over time | Timeline |
| Similar options or tradeoffs | Comparison table or aligned panels |
| Behavior changes with one or two inputs | Small simulator with visible state |

Do not use a chart when there is no quantitative relationship. Do not use a network graph merely because several nouns are connected.

## Multimedia Rules

- Coherence: remove decoration that does not teach a relationship.
- Signaling: emphasize the active step, decision, and failure boundary.
- Spatial contiguity: place labels and citations next to the relevant visual element.
- Segmentation: let the reader reveal or step through a complex mechanism when simultaneous display would overload it.
- Pretraining: define unfamiliar parts before showing their interaction.
- Personalization: use plain direct language without childish metaphors or condescension.

## Composition

Let the mechanism determine the page structure. A short concept may need one visual and a few annotations; an application trace may need lanes, branches, platform differences, or a failure path. The bundled templates are optional visual references, not output contracts. Change or ignore them whenever their fixed layout would distort the explanation.

## HTML Rules

- One self-contained UTF-8 HTML document with inline CSS and inline SVG or canvas.
- Semantic headings, visible focus states, `lang`, viewport metadata, accessible SVG labels, and system fonts.
- Default body text at least 16px with readable line length and contrast.
- No remote fonts, scripts, stylesheets, iframes, or images. Direct source links are allowed.
- No `innerHTML`, `eval`, or unnecessary framework/runtime.
- Keep exact code snippets short; escape markup and never place secrets in the artifact.
- JavaScript must use safe DOM APIs and exist only when interaction teaches the mechanism.

## Render Check

Inspect at a wide desktop viewport and a narrow mobile viewport. Confirm:

- no horizontal clipping or overlapping labels;
- every SVG or canvas label's rendered bounding box stays inside its own container and the viewBox — SVG text never reflows, and a page-level overflow check will not catch it;
- full-bleed or negative-margin blocks are re-checked at the narrow width, the classic source of silent horizontal overflow;
- the main causal path remains visually dominant;
- text is legible without zooming;
- controls work by keyboard and update visible state;
- source links point to the recorded direct URLs; and
- the page remains understandable if animation is disabled.

Use ordinary browser, syntax, accessibility, or link checks when available. When no interactive renderer is at hand, `scripts/render-check.sh` captures desktop and mobile screenshots with any installed headless Chromium. Do not infer semantic correctness from a custom validator or encode explanation quality as fixed HTML selectors.
