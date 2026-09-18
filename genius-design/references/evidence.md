# Evidence for Reverse Engineering

## Evidence Ladder

| Evidence | Can establish | Cannot establish by itself |
| --- | --- | --- |
| Supplied brand guidelines | What the user/brand specifies | What a deployed site currently renders |
| Screenshot with viewport/state | Visible composition and appearance in that capture | Exact CSS values, unseen states, font identity |
| Computed styles with selector/viewport/state | Resolved properties on that element in that context | Every breakpoint, future state or semantic role |
| HTML/CSS source | Declared values and candidate patterns | Whether a rule wins the cascade, is used, or is visible |
| Catalog snapshot | The catalog's reported design summary | Official status or current live-site behavior |
| Rendered text/Markdown | Text and some document structure | Pixel geometry, motion or visual tokens |

Keep Observed claims as narrow as their evidence. Inferred connects evidence to an interpretation. Recommended proposes a target-project choice. The same value can be a source observation and a separately recommended implementation token; say which is which.

## Capture Format

When an available browser tool can collect computed styles, save this JSON structure. The extractor consumes it; it does not operate a browser itself or verify the capture's authenticity.

```json
{
  "schema_version": 1,
  "url": "https://example.com/",
  "viewport": {"width": 1280, "height": 800},
  "state": "default",
  "elements": [
    {
      "selector": "main h1",
      "properties": {
        "font-family": "Source Serif 4, serif",
        "font-size": "64px",
        "color": "rgb(35, 32, 28)",
        "text-align": "center"
      }
    }
  ]
}
```

Record additional states/viewport captures separately. Never fabricate captures to fill missing data. `evals/fixtures/capture.json` is synthetic test data, not a real-site observation.

## Source Extraction

The bundled extractor reads CSS, inline/style-block HTML, and page exports with `rawHtml`, `html`, `markdown` or a nested `data` object. It excludes script bodies and unrelated JSON metadata. Markdown/prose alone does not become CSS evidence.

Output is structured JSON with source-labelled signals, external stylesheet references, candidate color counts and limitations. Signals include typography, layout, spacing, radius, shadows, motion and custom properties where present. Modern color syntax and unresolved `var(...)` values remain intact.

This is deliberately a lightweight declaration scanner, not a full CSS parser. It does not resolve cascade, specificity, media/container queries, imports or variable values. Color frequencies count candidate occurrences, not visual prominence. Nested functional colors may require direct inspection. Follow external CSS only when useful and permitted; do not claim all styles were captured.

## Minimum Notes in DESIGN.md

- Source URL/file/catalog and locator for each meaningful observation.
- Relevant viewport/state for computed observations and screenshots.
- Which implementation tokens are inferred or proposed rather than measured.
- Missing external styles, mobile behavior, hover/focus, motion and assets where relevant.
- Accessibility issues observed in the source, with separately labelled remediation.

If only text is available, preserve textual structure and state visual unknowns. Ask for a screenshot/capture only when those unknowns prevent the user's requested result.
