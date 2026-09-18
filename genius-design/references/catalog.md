# Brand Catalog

Supplied brand evidence comes first. Live inventory is `scripts/fetch_design_md.py --list`, not this file. Catalog identity is not the design answer.

## Fetch

Order: Refero Styles → Design.md Store → VoltAgent. Pin with `--source refero|store|voltagent`. Write `<staging>/base.md` only; a destination named `DESIGN.md` is refused.

- Refero: https://styles.refero.design/api/styles (script synthesizes Markdown from JSON)
- Store: https://designmd-store.com/packs
- VoltAgent: https://raw.githubusercontent.com/VoltAgent/awesome-design-md/main/design-md

All three are unofficial snapshots and can lag a live brand. Inspect provenance rather than presenting their claims as observation.

VoltAgent aliases: `linear` → `linear.app`, `xai` / `xiai` → `x.ai`, `opencode` → `opencode.ai`, `mistral` → `mistral.ai`, `together` → `together.ai`, `cal.com` → `cal`, `dell` → `dell-1996`. Store aliases: `next.js` → `nextjs`, `disney+` → `disneyplus`, `booking.com` → `booking`.

## Selection

If you compare two or three catalog traits, explain why each (contrast, density, type character, motion restraint) fits THIS brief. Do not default developer tools to Linear, documentation to Mintlify, or marketing to Stripe. A named brand is a source of traits to evaluate, not a template to copy.

## Font substitutions

Catalogs may reference proprietary fonts. Substitutes are not equivalent metrics and not a mandate. Confirm cut, license, glyph coverage and fit; preserve a supplied licensed font when appropriate.

| Reference Font | Possible Alternative | Character |
| --- | --- | --- |
| Geist | A licensed geometric sans after confirming the actual cut and license; do not assume Google Fonts hosts an equivalent Geist | Geometric, compact |
| sohne-var (Stripe) | Source Sans 3 | Light, elegant |
| Airbnb Cereal | DM Sans | Rounded, friendly |
| Circular (Spotify) | DM Sans | Geometric, warm |
| figmaSans | Inter | Clean, humanist |
