# Workflows A / B / C

## Workflow A: Brand Template (73 brands => deep DESIGN.md)

### Step A1: User Picks a Brand

Show the Selection Guide at the bottom of this file to help the user choose. Or they can name any brand from the catalog. The Brief Inference (Section 0) already produced a Design Read -- use it to recommend 2-3 best-fit brands before asking the user to pick.

### Step A2: Fetch the Base DESIGN.md

**Overwrite check:** If `./DESIGN.md` already exists, notify the user before proceeding. Either ask for confirmation to overwrite, or automatically back up the existing file as `./DESIGN.md.bak` and note that a backup was created.

```bash
# Primary: your fork
curl -sL "https://raw.githubusercontent.com/Li-Charles-One/awesome-design-md/main/design-md/<slug>/DESIGN.md" -o ./DESIGN.md

# Fallback: upstream
curl -sL "https://raw.githubusercontent.com/VoltAgent/awesome-design-md/main/design-md/<slug>/DESIGN.md" -o ./DESIGN.md
```

Alternatively, use the bundled script:
```bash
python scripts/fetch_design_md.py <brand> ./DESIGN.md
```

### Step A3: Infer Customizations

After fetching the base DESIGN.md, read it and infer:

1. **Dial values**: What VARIANCE / MOTION / DENSITY does this brand's aesthetic suggest? Use the Dial Inference Table above. Record these in the YAML frontmatter as `dial_values:`.
2. **Design system mapping**: Does this brand correspond to a real design system (Honesty Map above)? If so, note it. If not, note the honest implementation approach.
3. **Stack convention**: Note any overrides to the default code stack (rare for these brands, but possible).

### Step A4: Run Shared Enrichment Pipeline

Execute all five Enrichment Steps from the Shared Pipeline above.

---

## Workflow B: Reverse-Engineer a Website

### Step B1: Fetch the Page

Use `web_fetch` to grab the rendered page content. Extract HTML/CSS signals from the response. If a Firecrawl CLI is available, use it for richer extraction:

**B1-alt (Firecrawl if available):**
```bash
firecrawl scrape "<url>" --format rawHtml,branding,screenshot --only-main-content --wait-for 3000 -o .firecrawl/design-data.json --json --pretty
```

After scraping, spot-check with quick greps:
```bash
# Dominant font (Linux/GNU grep)
grep -oP "font-family:\s*[^;]+" .firecrawl/design-data.json | sort | uniq -c | sort -rn | head -5
# macOS (BSD grep, no -P): use -E instead
grep -oE "font-family:[^;]+" .firecrawl/design-data.json | sort | uniq -c | sort -rn | head -5

# Border-radius patterns (Linux)
grep -oP "border-radius:\s*\d+px" .firecrawl/design-data.json | sort | uniq -c | sort -rn
# macOS
grep -oE "border-radius:[[:space:]]*[0-9]+px" .firecrawl/design-data.json | sort | uniq -c | sort -rn

# All hex colors (Linux)
grep -oP "#[0-9a-fA-F]{3,8}" .firecrawl/design-data.json | sort | uniq -c | sort -rn | head -15
# macOS
grep -oE "#[0-9a-fA-F]{3,8}" .firecrawl/design-data.json | sort | uniq -c | sort -rn | head -15
```

If the page requires login or interaction:
```bash
firecrawl scrape "<url>"
firecrawl interact --prompt "Click the login button, then fill credentials"
firecrawl scrape "<url>" --format rawHtml,branding,screenshot --only-main-content --wait-for 3000 -o .firecrawl/design-data.json --json --pretty
```

### Step B2: Extract Design Tokens

Work through each dimension systematically. For every value, assign a **semantic role** -- never just "blue: #0064E0" but "Primary CTA (#0064E0) -- all purchase buttons, signup CTAs, active nav links."

**Colors**: Map recurring hex values to semantic roles. Count occurrences to separate signal from noise. Identify the color system: monochrome+accent, multi-accent, gradient-driven.

**Typography**: Identify dominant font family, build the size scale, note weight patterns, measure line-height. Detect if the site uses a proprietary font and note the CDN substitution.

**Spacing**: Extract section gaps, card padding, button padding. Detect grid base unit (8px, 10px, 12px).

**Components**: For buttons, cards, inputs, nav -- extract border-radius, min-height, padding, shadow formulas, focus ring styles. Note variants (solid vs outline vs ghost).

**Shapes & Elevation**: Map the 2-3 most common border-radius values to sm/md/lg. Count distinct box-shadow values to build an elevation scale.

**Dial inference**: Based on the extracted patterns, infer VARIANCE (layout symmetry vs asymmetry), MOTION (presence and intensity of animations), and DENSITY (information per viewport, section padding). Note: extraction can't always get MOTION -- infer from the brand category when uncertain.

**Design system detection**: Does the site use a recognizable design system (Material, Fluent, Carbon, Primer, GOV.UK)? If yes, note it for the Honesty Map.

### Step B3: Generate the Deep DESIGN.md

**Overwrite check:** If `./DESIGN.md` already exists, notify the user and back up as `./DESIGN.md.bak` before writing.

Use `reference/design-template.md` as the structure. Fill every section from the extracted tokens. Where extraction can't determine a value, apply the defaults from the template and mark with `<!-- inferred -->`.

### Step B4: Run Shared Enrichment Pipeline

Execute all five Enrichment Steps from the Shared Pipeline above.

### Limitations

- `web_fetch` extracts rendered text -- CSS values may be partial. Firecrawl gives richer data.
- Interactive states (hover, focus, active) are inferred from class name patterns, not directly observed.
- For highly dynamic SPAs, increase `--wait-for` or use `firecrawl interact`.
- The dial values for MOTION are the hardest to extract -- infer from the brand category when the site doesn't signal clearly.

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
3. **Dial values**: Set DESIGN_VARIANCE, MOTION_INTENSITY, VISUAL_DENSITY using the Dial Inference Table. Justify each value in one sentence tied to the product audience.
4. **Design system**: Does the product map to a real design system (Honesty Map)? If the brief reads "enterprise B2B dashboard," reach for Carbon or Fluent. If "modern SaaS," shadcn/ui or Tailwind v4. If "creative agency landing page," native CSS + aesthetic direction.
5. **Closest brand match**: Which brand(s) from the 73-brand catalog are closest in spirit? Name 2-3 with one-line justifications.

### Step C3: Generate the DESIGN.md

**Overwrite check:** If `./DESIGN.md` already exists, notify the user and back up as `./DESIGN.md.bak` before writing.

Two paths, based on closeness to existing brands:

- **Path C3a (close match exists)**: Fetch the closest brand's DESIGN.md via Workflow A Step A2, then adjust the token values to match the product's specific needs. Change the brand name, adjust accents, swap fonts if needed. Mark changed values with `<!-- adapted from <brand> -->`.

- **Path C3b (genuinely unique)**: Build a fresh DESIGN.md directly from `reference/design-template.md`. Fill every section with the recommended direction. Mark all values as `<!-- generated from product type -->`.

### Step C4: Run Shared Enrichment Pipeline

Execute all five Enrichment Steps from the Shared Pipeline above.

