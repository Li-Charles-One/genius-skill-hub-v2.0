# Workflows A / B / C

Pointers (this file is steps only):

- Selection Guide and brand list: `reference/catalog.md`
- Dial Inference Table and Honesty Map: `reference/dials-and-stack.md`
- Shared Enrichment Pipeline: `reference/enrichment.md`
- Output skeleton: `reference/design-template.md`

## Workflow A: Brand Template (73 brands => deep DESIGN.md)

### Step A1: User Picks a Brand

Use the Selection Guide in `reference/catalog.md` to help the user choose. Or they can name any brand from that catalog. The Brief Inference already produced a Design Read -- use it to recommend 2-3 best-fit brands before asking the user to pick.

### Step A2: Fetch the Base DESIGN.md

**Overwrite check:** If `./DESIGN.md` already exists, notify the user before proceeding. The fetch script backs up an existing file as `./DESIGN.md.bak`.

Primary (Windows, macOS, Linux):

```powershell
python scripts/fetch_design_md.py <brand> ./DESIGN.md
```

```bash
python3 scripts/fetch_design_md.py <brand> ./DESIGN.md
```

`python scripts/fetch_design_md.py --list` prints all 73 slugs plus aliases (`linear` -> `linear.app`, `xai` -> `x.ai`, `opencode` -> `opencode.ai`).

Do not hand-curl unless the script cannot run. Templates: `https://raw.githubusercontent.com/VoltAgent/awesome-design-md/main/design-md/<slug>/DESIGN.md`.

### Step A3: Infer Customizations

After fetching the base DESIGN.md, read it and infer:

1. **Dial values**: What VARIANCE / MOTION / DENSITY does this brand's aesthetic suggest? Use the Dial Inference Table in `reference/dials-and-stack.md`. Record these in the YAML frontmatter as `dial_values:`.
2. **Design system mapping**: Does this brand correspond to a real design system (Honesty Map in `reference/dials-and-stack.md`)? If so, note it. If not, note the honest implementation approach.
3. **Stack convention**: Note any overrides to the default code stack (rare for these brands, but possible).

### Step A4: Run Shared Enrichment Pipeline

Execute all five Enrichment Steps in `reference/enrichment.md`.

---

## Workflow B: Reverse-Engineer a Website

### Step B1: Fetch the Page

Prefer Firecrawl when that CLI is available. Current flags (no `branding` format):

```powershell
firecrawl scrape "<url>" --format markdown,rawHtml --wait-for 3000 -o .firecrawl/design-data.json
```

```bash
firecrawl scrape "<url>" --format markdown,rawHtml --wait-for 3000 -o .firecrawl/design-data.json
```

If Firecrawl is missing, save the page with the runtime page-fetch tool to `.firecrawl/page.md` or `.firecrawl/page.html`. Do not call a tool named `web_fetch` unless that is the runtime's actual tool.

If the page needs clicks or login, use Firecrawl interact, then scrape again. Do not invent credentials.

### Step B2: Extract Design Tokens

Run the bundled extractor instead of OS-specific `grep -P`:

```powershell
python scripts/extract_design_signals.py .firecrawl/design-data.json
```

```bash
python3 scripts/extract_design_signals.py .firecrawl/design-data.json
```

Pass extra files if you saved markdown or HTML separately. Then work through each dimension. For every value, assign a **semantic role** -- never just "blue: #0064E0" but "Primary CTA (#0064E0) -- all purchase buttons, signup CTAs, active nav links."

**Colors**: Map recurring hex values to semantic roles. Count occurrences to separate signal from noise. Identify the color system: monochrome+accent, multi-accent, gradient-driven.

**Typography**: Identify dominant font family, build the size scale, note weight patterns, measure line-height. Detect if the site uses a proprietary font and note the CDN substitution.

**Spacing**: Extract section gaps, card padding, button padding. Detect grid base unit (8px, 10px, 12px).

**Components**: For buttons, cards, inputs, nav -- extract border-radius, min-height, padding, shadow formulas, focus ring styles. Note variants (solid vs outline vs ghost).

**Shapes & Elevation**: Map the 2-3 most common border-radius values to sm/md/lg. Count distinct box-shadow values to build an elevation scale.

**Dial inference**: Based on the extracted patterns, infer VARIANCE (layout symmetry vs asymmetry), MOTION (presence and intensity of animations), and DENSITY (information per viewport, section padding). Extraction can't always get MOTION -- infer from the brand category when uncertain. Use `reference/dials-and-stack.md`.

**Design system detection**: Does the site use a recognizable design system (Material, Fluent, Carbon, Primer, GOV.UK)? If yes, note it for the Honesty Map in `reference/dials-and-stack.md`.

### Step B3: Generate the Deep DESIGN.md

**Overwrite check:** If `./DESIGN.md` already exists, notify the user and back up as `./DESIGN.md.bak` before writing.

Use `reference/design-template.md` as the structure. Fill every section from the extracted tokens. Where extraction can't determine a value, apply the defaults from the template and mark with `<!-- inferred -->`.

### Step B4: Run Shared Enrichment Pipeline

Execute all five Enrichment Steps in `reference/enrichment.md`.

### Limitations

- Page-fetch tools often return rendered text. Firecrawl markdown+rawHtml is richer, but CSS may still be partial.
- Interactive states (hover, focus, active) are inferred from class name patterns, not directly observed.
- For highly dynamic SPAs, increase `--wait-for` or use Firecrawl interact.
- MOTION dials are the hardest to extract -- infer from the brand category when the site doesn't signal clearly.

---

## Workflow C: AI Recommendation (No Brand Reference)

### Step C1: Understand the Product

If not already captured during Brief Inference, ask for: industry, product type, target audience. Examples:
- Medical SaaS platform, admin backend for doctors
- Sports brand e-commerce, selling running shoes and fitness gear
- Children's education app, targeting parents

### Step C2: Reason Through the Design Direction

Based on the product description and Brief Inference, systematically reason:

1. **Register**: Is this brand (design IS the product -- landing page, marketing) or product (design SERVES the product -- dashboard, tool, app)?
2. **Vibe**: What aesthetic family fits? Pick from: minimalist/Linear-style, premium-consumer/Apple-y, playful/creative, editorial/luxury, dark-tech, trust-first/public-sector, brutalist/industrial, soft/warm-consumer.
3. **Dial values**: Set DESIGN_VARIANCE, MOTION_INTENSITY, VISUAL_DENSITY using the Dial Inference Table in `reference/dials-and-stack.md`. Justify each value in one sentence tied to the product audience.
4. **Design system**: Does the product map to a real design system (Honesty Map in `reference/dials-and-stack.md`)? If the brief reads "enterprise B2B dashboard," reach for Carbon or Fluent. If "modern SaaS," shadcn/ui or Tailwind v4. If "creative agency landing page," native CSS + aesthetic direction.
5. **Closest brand match**: Which brand(s) from the 73-brand catalog are closest in spirit? Name 2-3 with one-line justifications.

### Step C3: Generate the DESIGN.md

**Overwrite check:** If `./DESIGN.md` already exists, notify the user and back up as `./DESIGN.md.bak` before writing.

Two paths, based on closeness to existing brands:

- **Path C3a (close match exists)**: Fetch the closest brand's DESIGN.md via Workflow A Step A2, then adjust the token values to match the product's specific needs. Change the brand name, adjust accents, swap fonts if needed. Mark changed values with `<!-- adapted from <brand> -->`.

- **Path C3b (genuinely unique)**: Build a fresh DESIGN.md directly from `reference/design-template.md`. Fill every section with the recommended direction. Mark all values as `<!-- generated from product type -->`.

### Step C4: Run Shared Enrichment Pipeline

Execute all five Enrichment Steps in `reference/enrichment.md`.
