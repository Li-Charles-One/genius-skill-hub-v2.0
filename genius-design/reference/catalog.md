# Brand Catalog, Fonts, Selection, Fallback

Workflow A is not a 73-brand menu. Fetch order: Refero Styles, then Design.md Store, then the VoltAgent static list below. The 73 names are the last-resort snapshot. `python scripts/fetch_design_md.py --list` prints all three catalogs.

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

Brand DESIGN.md files reference proprietary fonts. Use these CDN-available alternatives:

| Original Font | CDN Alternative | Character |
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

Primary: `python scripts/fetch_design_md.py <brand> ./DESIGN.md` pulls from `https://raw.githubusercontent.com/VoltAgent/awesome-design-md/main/design-md`.

First source: [Refero Styles](https://styles.refero.design) (`/api/styles`; the script writes a DESIGN.md from JSON because Refero has no file download). Second: [Design.md Store](https://designmd-store.com/packs). Third: VoltAgent static list. `fetch_design_md.py --list` prints all three. Pin with `--source refero`, `--source store`, or `--source voltagent`.

VoltAgent aliases: `linear` -> `linear.app`, `xai` / `xiai` -> `x.ai`, `opencode` -> `opencode.ai`, `mistral` -> `mistral.ai`, `together` -> `together.ai`, `cal.com` -> `cal`, `dell` -> `dell-1996`. Store aliases: `next.js` -> `nextjs`, `disney+` -> `disneyplus`, `booking.com` -> `booking`. Once a DESIGN.md is in the project root, it has zero external dependencies. All three sources are unofficial snapshots; they can lag the live brand site.

