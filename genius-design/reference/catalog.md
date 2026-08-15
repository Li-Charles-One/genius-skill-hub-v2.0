# Brand Catalog, Fonts, Selection, Fallback

## Brand Catalog (73 brands)

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

Source: `python scripts/fetch_design_md.py <brand> ./DESIGN.md` pulls from `https://raw.githubusercontent.com/VoltAgent/awesome-design-md/main/design-md`. `fetch_design_md.py --list` is the slug source of truth (73). Aliases: `linear` -> `linear.app`, `xai` / `xiai` -> `x.ai`, `opencode` -> `opencode.ai`, `mistral` -> `mistral.ai`, `together` -> `together.ai`, `cal.com` -> `cal`, `dell` -> `dell-1996`. Once a DESIGN.md is in the project root, it has zero external dependencies.

