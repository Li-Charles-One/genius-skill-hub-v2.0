# Brand Catalog (73 Brands)

For brand direction (Mode A), use supplied guidelines first.
When the user mentions a known brand and references are needed, read its `DESIGN.md` directly from the VoltAgent open source repository:

- **Base URL pattern:** `https://raw.githubusercontent.com/VoltAgent/awesome-design-md/main/design-md/<slug>/DESIGN.md`
- **Fetching & Fallback:** Use the native `webfetch` tool directly. If network access to `raw.githubusercontent.com` times out or fails, fall back immediately to model prior knowledge to infer the brand's typical color palette, typography, and density; mark claims `Inferred` / `Recommended`. Do not loop or retry endlessly.

## Available Brands (73)

| Category | Brand Slugs |
| --- | --- |
| **Dev & AI Tools** | `claude`, `cursor`, `elevenlabs`, `linear.app`, `minimax`, `mistral.ai`, `ollama`, `opencode.ai`, `posthog`, `raycast`, `replicate`, `resend`, `sentry`, `supabase`, `superhuman`, `together.ai`, `vercel`, `warp`, `x.ai` |
| **Design & Creative** | `figma`, `framer`, `lovable`, `miro`, `runwayml`, `sanity`, `webflow` |
| **Cloud & Infrastructure** | `airtable`, `clickhouse`, `cohere`, `composio`, `expo`, `hashicorp`, `mongodb`, `notion`, `slack`, `zapier` |
| **Tech Giants & Hardware** | `apple`, `dell-1996`, `hp`, `ibm`, `meta`, `nvidia`, `playstation`, `spacex`, `tesla` |
| **Commerce, Travel & Media** | `airbnb`, `intercom`, `mastercard`, `mintlify`, `nike`, `pinterest`, `revolut`, `shopify`, `spotify`, `starbucks`, `stripe`, `theverge`, `uber`, `vodafone`, `voltagent`, `wired`, `wise` |
| **Automotive** | `bmw`, `bmw-m`, `bugatti`, `ferrari`, `lamborghini`, `renault` |
| **Fintech & Crypto** | `binance`, `coinbase`, `kraken` |
| **Others** | `cal`, `clay` |

## Common Aliases

- `linear` → `linear.app`
- `xai` / `xiai` → `x.ai`
- `opencode` → `opencode.ai`
- `mistral` → `mistral.ai`
- `together` → `together.ai`
- `cal.com` → `cal`
- `dell` → `dell-1996`

## External Brand Inspiration Websites (User-Curated)

If the requested brand is not among the 73 presets or the user seeks broader inspiration, directly recommend these two sites for the user to explore and download from:

1. **Design.md Store:** https://designmd-store.com/
2. **Refero Styles:** https://styles.refero.design/

**Workflow:**
- Recommend the links to the user.
- The user browses, picks, downloads the pack/style, and pastes or uploads the file/content in the chat.
- The agent ingests the content as `supplied-guideline` and proceeds with the standard contract workflow.
