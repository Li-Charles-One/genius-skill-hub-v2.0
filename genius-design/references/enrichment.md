# Evidence-Aware Enrichment

Apply to a staged candidate, never to the destination in place. Read the template, contract, rules, relevant anti-patterns and checklist before enrichment.

## 1. Reconcile the Brief and Evidence

Preserve supplied brand decisions and observed site facts. Identify product versus marketing needs. Separate additions and adaptations from source descriptions. Resolve actual conflicts; do not reinterpret every brand through one house style.

## 2. Make the Specification Implementable

- **Color:** name background, surface, text, muted text, accent, border and focus roles for each requested theme. Extra accents and status/data palettes are allowed with usage rules. State contrast targets and measured/pending status.
- **Type:** choose hierarchy, sizes, line heights, language coverage, font availability and fallbacks. Scale ratios and display ceilings depend on content and viewport, not fixed prohibitions.
- **Spacing and shape:** define usable tokens and how grouping, radius and elevation support hierarchy. Avoid isolated arbitrary values; do not outlaw cards at high density.
- **Layout:** name the page/screen rhythm, enumerate regions and explain reading/task order. Cover relevant responsive behavior. No mandatory marketing hero for product screens.
- **Components:** define applicable variants and states. Tables, forms and drawers require different guidance from a publication masthead.
- **Motion:** explain purpose and reduced-motion behavior, including an intentional static experience. Unknown observed motion stays unknown.
- **Imagery:** identify necessary assets, provenance and labelled slots. Zero images is valid. Random stock images do not substitute for real product evidence.
- **Implementation:** respect the existing stack. Map an existing system honestly; do not install packages or build UI.

## 3. Review Contextual Anti-Patterns

Choose 3–5 warnings from `references/anti-patterns.md`, adapted to this brief. Ask:

1. Does each major choice follow from the audience, content, constraints or evidence?
2. Is the named rhythm an actual information structure, not just a new label?
3. Did attempts to look distinctive reduce fidelity, familiarity or usability?

A conventional solution with a clear reason is acceptable. Do not endlessly rework a palette because someone could guess the product category.

## 4. Check the Contract and Human Checklist

Fill the versioned frontmatter and readable sections. Record evidence and honest unknowns. Complete the 12 specification checks, distinguishing pending implementation validation from missing design decisions.

Run the bundled linter against the candidate. Fix structural errors, inspect warnings and read the whole document for contradictions. Do not claim that lint verifies contrast or visual quality.

## 5. Commit and Deliver

Use the safe commit command in `references/runtime-mapping.md`. It reruns validation before creating a unique backup and replacing the destination. Report paths, decisions, evidence status, overrides, lint warnings and remaining implementation checks. If validation or commit fails, report the draft and preserve the existing destination.
