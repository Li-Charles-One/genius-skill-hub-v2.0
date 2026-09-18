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

Catalogs may reference proprietary fonts. These are possible substitutes, not equivalent metrics or verified brand facts. Confirm availability, license, glyph coverage and visual fit; preserve a supplied licensed font when appropriate.

| Reference Font | Possible Alternative | Character |
|:--|:--|:--|
| Geist | Geist (Google Fonts) | Geometric, compact |
| sohne-var (Stripe) | Source Sans 3 | Light, elegant |
| Airbnb Cereal | DM Sans | Rounded, friendly |
| Circular (Spotify) | DM Sans | Geometric, warm |
| figmaSans | Inter | Clean, humanist |

---

## Selection Guide

- **Developer tools / dashboards**: Linear, Vercel, Supabase, Raycast, Sentry
- **Documentation / content sites**: Mintlify, Notion, Sanity, MongoDB
- **Marketing / landing pages**: Stripe, Framer, Apple, SpaceX
- **Dark mode**: Linear, Cursor, ElevenLabs, Warp, Superhuman
- **Light / clean**: Vercel, Stripe, Notion, Cal.com
- **Playful / friendly**: PostHog, Figma, Lovable, Zapier, Miro
- **Premium / luxury**: Apple, BMW, Stripe, Superhuman, Revolut

---

## Fallback Strategy

Fetch to a staged `base.md`, not directly over the final DESIGN.md. A catalog base must be adapted to the output contract, enriched and validated before safe commit.

First source: [Refero Styles](https://styles.refero.design) (`/api/styles`; the script writes a DESIGN.md from JSON because Refero has no file download). Second: [Design.md Store](https://designmd-store.com/packs). Third: VoltAgent static list. `fetch_design_md.py --list` prints all three. Pin with `--source refero`, `--source store`, or `--source voltagent`.

VoltAgent aliases: `linear` -> `linear.app`, `xai` / `xiai` -> `x.ai`, `opencode` -> `opencode.ai`, `mistral` -> `mistral.ai`, `together` -> `together.ai`, `cal.com` -> `cal`, `dell` -> `dell-1996`. Store aliases: `next.js` -> `nextjs`, `disney+` -> `disneyplus`, `booking.com` -> `booking`. Reading a delivered DESIGN.md is offline; validating it requires the documented local parser. All three catalogs are unofficial snapshots and can lag a live brand site. Inspect provenance rather than presenting their claims as direct observation.
