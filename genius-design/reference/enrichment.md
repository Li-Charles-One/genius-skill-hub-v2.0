# Shared Enrichment Pipeline

## Shared Enrichment Pipeline (Steps A3-A5 / B4-B6 / C4-C6)

**Preflight check (run before any enrichment step):** Verify all three reference files exist:
- `reference/design-template.md`
- `reference/anti-patterns.md`
- `reference/preflight-checklist.md`

If any file is missing, stop and report which file(s) are absent. Do not attempt enrichment with incomplete references — the output will be structurally incomplete.

After the base DESIGN.md exists (fetched, extracted, or generated), run this shared pipeline.

### Enrichment Step 1: Expand Every Section

Read `reference/design-template.md`. For each section of the base DESIGN.md, add the following depth:

- **Colors**: Add semantic roles for every hex value (never "blue: #0064E0" -- always "Primary CTA (#0064E0): all purchase buttons, signup CTAs, active nav links"). Add forbidden hex families from the Absolute Refusals above. Document the neutral system choice (cool-zinc / warm-stone / true-slate) and chroma tint (0.005-0.015 toward brand hue). Enforce one-accent constraint.
- **Typography**: Add scale ratio (>=1.25 between steps), hero clamp ceiling (max 6rem = ~96px), tracking floor (>= -0.04em), banned defaults (Inter, Fraunces, Instrument_Serif), serif discipline rules, italic descender clearance (leading-[1.1] + pb-1 for y/g/j/p/q in display italic). Cap font families at 3. Set body max-width at 65ch.
- **Shape & Elevation**: Document corner-radius scale (one system per page: all-sharp / all-soft-12-16px / all-pill). Shadow tint rule (tint to background hue, never pure black). Card usage constraint: cards only when elevation communicates real hierarchy; banned entirely when VISUAL_DENSITY > 7. Forbidden: border-radius > 16px on cards/sections, ghost-card pattern (1px border + soft wide shadow on the same element).
- **Spacing**: Document base unit (8px default, 4px dense, 10px editorial). Hero top padding cap: pt-24 max at desktop. Section gap defaults (py-24 to py-32). Card padding range (p-6 to p-8).
- **Layout**: Document max-width container (max-w-[1400px] or max-w-7xl), breakpoints (sm 640, md 768, lg 1024, xl 1280, 2xl 1536). Viewport stability: min-h-[100dvh] never h-screen. Grid over flex-math: CSS Grid for 2D, Flexbox for 1D, never complex flexbox percentage math. Hero constraints: headline <=2 lines, subtext <=20 words/<=4 lines, max 4 text elements (eyebrow OR brand strip + headline + subtext + CTAs). Forbidden layout patterns: centered hero when VARIANCE > 4, 3 equal cards, zigzag beyond 2 consecutive, eyebrow on >1/3 of sections, split-header as default.
- **Components**: For buttons: 44-48px height, verb+object label <=3 words fits one line, WCAG AA contrast check, active tactile feedback (scale-[0.98]), no duplicate CTA intent. For inputs: label above input, never placeholder-as-label, WCAG AA on all parts. For cards: omit in favor of spacing; bento cells need real visual variation in 2-3 cells. Logo wall: under hero never inside, logos only no category labels, SVG from Simple Icons CDN. Navigation: 64-72px height cap 80px, single line at desktop.
- **Motion**: Document intensity (from dial), exponential ease-out curve (cubic-bezier(0.16, 1, 0.3, 1)), no bounce/elastic. Reduced-motion policy mandatory when intensity > 3. Animate only transform + opacity (never top/left/width/height). No window.addEventListener('scroll') -- use Motion useScroll / ScrollTrigger / IntersectionObserver. Max one marquee per page. Every animation must have a one-sentence purpose.
- **Imagery**: Priority: gen-tool -> Picsum seed (https://picsum.photos/seed/{descriptive-seed}/{w}/{h}) -> explicit placeholder slots. Minimum 2-3 real images even for minimalist sites. Logo source: Simple Icons CDN (https://cdn.simpleicons.org/{slug}/ffffff). Banned: div-based fake screenshots, hand-rolled decorative SVGs, text+gradient blob as hero, fake-engineering-precise numbers.
- **Dark Mode**: Required. Strategy: Tailwind `dark:` variant or CSS variables. One theme per page, no section-level inversion. No pure black, no pure white.
- **Theme Lock**: One accent across all sections. One corner-radius system. One palette (don't fluctuate between warm and cool grays). One theme per page.

### Enrichment Step 2: Inject Anti-Patterns

Read `reference/anti-patterns.md`. Match the brand to its category (a brand may belong to multiple categories -- e.g., Linear = Developer Tools + Dark Mode + Minimalist). Merge the warnings and pick the 3-5 most relevant. Inject as:

```markdown
## Anti-Patterns for This Brand

When using this DESIGN.md, the most common AI mistakes are:
1. **<title>**: <what the AI does wrong> -> <what to do instead>.
...
```

### Enrichment Step 3: Append Pre-Ship Checklist

Read `reference/preflight-checklist.md`. Append the complete 12-item checklist. If any item cannot be ticked for the current DESIGN.md, fix it before delivering.

### Enrichment Step 4: Run the AI Slop Test

Before delivering, run the two-altitude reflex check:

**First-order:** If someone could guess the theme + palette from the category alone (e.g., "fintech = blue + white, AI = purple glow, premium consumer = beige + brass"), rework the color strategy until the answer isn't obvious from the domain.

**Second-order:** If someone could guess the aesthetic family from category-plus-anti-references ("AI workflow tool that's not SaaS-cream -> editorial-typographic", "fintech that's not navy-and-gold -> terminal-native dark mode"), rework until both answers are not obvious.

If either check fails, redo the color selection or aesthetic direction. This is not optional.

### Enrichment Step 5: Lint, then Deliver

```powershell
python scripts/lint_design_md.py ./DESIGN.md
```

```bash
python3 scripts/lint_design_md.py ./DESIGN.md
```

Fix every `FAIL` before delivering. Review `WARN` lines.

Tell the user:
- The key design decisions (primary color, font stack, vibe, dial values)
- Where the file was saved (`./DESIGN.md`)
- If any values were inferred (mark them clearly)
- Any decisions the user may want to override
- Lint result (clean, or which warnings remain)

