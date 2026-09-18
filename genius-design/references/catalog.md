# Brand Catalog, Fonts, Selection, Fallback

Supplied brand evidence comes first. When a catalog is useful, fetch order is Refero Styles, then Design.md Store, then VoltAgent. This is not a fixed 73-brand menu; the list below is a bundled snapshot. `scripts/fetch_design_md.py --list` prints available inventories. Resolve commands as described in `references/runtime-mapping.md`.

## VoltAgent static catalog (73 brands)

### AI & LLM
Claude, Cohere, ElevenLabs, Minimax, Mistral AI, Ollama, OpenCode AI, Replicate, RunwayML, Together AI, VoltAgent, xAI

### Developer Tools
Cursor, Expo, Lovable, Raycast, Superhuman, Vercel, Warp

### Backend & DevOps
ClickHouse, Composio, HashiCorp, MongoDB, PostHog, Sanity, Sentry, Supabase

### Productivity & SaaS
Cal.com, Intercom, Linear, Mintlify, Notion, Resend, Slack, Zapier

### Design Tools
Airtable, Clay, Figma, Framer, Miro, Webflow

### Fintech
Binance, Coinbase, Kraken, Mastercard, Revolut, Stripe, Wise

### E-commerce
Airbnb, Meta, Nike, Shopify, Starbucks

### Media & Tech
Apple, Dell (1996), HP, IBM, NVIDIA, Pinterest, PlayStation, SpaceX, Spotify, The Verge, Uber, Vodafone, WIRED

### Automotive
BMW, BMW M, Bugatti, Ferrari, Lamborghini, Renault, Tesla

---

## Font Substitutions

Catalogs may reference proprietary fonts. The table is a reminder that a licensed substitute may be needed — not equivalent metrics, not a visual match, and not a mandate. Confirm the actual available cut, license, glyph coverage and fit; preserve a supplied licensed font when appropriate. Do not assume a webfont host carries the same family.

| Reference Font | Possible Alternative | Character |
|:--|:--|:--|
| Geist | A licensed geometric sans after confirming the actual cut and license; do not assume Google Fonts hosts an equivalent Geist | Geometric, compact |
| sohne-var (Stripe) | Source Sans 3 | Light, elegant |
| Airbnb Cereal | DM Sans | Rounded, friendly |
| Circular (Spotify) | DM Sans | Geometric, warm |
| figmaSans | Inter | Clean, humanist |

---

## Selection Guide

The lists above are inventory, not a picker menu. Catalog identity is not the design answer.

If you compare two or three catalog traits, explain why each trait (contrast, density, type character, motion restraint) fits THIS brief. Do not default developer tools to Linear, documentation to Mintlify, or marketing to Stripe. A named brand is a source of traits to evaluate, not a template to copy, and category membership is not a recommendation.

---

## Fallback Strategy

Fetch a catalog snapshot to a staged `base.md` only. The fetch CLI requires that output path; a destination whose filename is `DESIGN.md` is refused. Never fetch onto the delivered spec. Adapt the staged base to the output contract, enrich, lint, then commit with `design_io.py`.

Auto source order: [Refero Styles](https://styles.refero.design) first (`/api/styles`; the script synthesizes Markdown from JSON because Refero has no file download), then [Design.md Store](https://designmd-store.com/packs), then VoltAgent. VoltAgent is last, not first. `fetch_design_md.py --list` prints all three. Pin with `--source refero`, `--source store`, or `--source voltagent`.

VoltAgent aliases: `linear` -> `linear.app`, `xai` / `xiai` -> `x.ai`, `opencode` -> `opencode.ai`, `mistral` -> `mistral.ai`, `together` -> `together.ai`, `cal.com` -> `cal`, `dell` -> `dell-1996`. Store aliases: `next.js` -> `nextjs`, `disney+` -> `disneyplus`, `booking.com` -> `booking`. Reading a delivered DESIGN.md is offline; validating it requires the documented local parser. All three catalogs are unofficial snapshots and can lag a live brand site. Inspect provenance rather than presenting their claims as direct observation.
