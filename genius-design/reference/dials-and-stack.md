# Dials, Honesty Map, and Code Stack

## The Three-Dial System (Integrated Into All Workflows)

Every DESIGN.md must set three dial values. These gate every layout, motion, density, and color decision downstream.

| Dial | Range | Meaning |
|---|---|---|
| `DESIGN_VARIANCE` | 1-10 | 1=Perfect Symmetry, 10=Artsy Chaos |
| `MOTION_INTENSITY` | 1-10 | 1=Static, 10=Cinematic/Physics |
| `VISUAL_DENSITY` | 1-10 | 1=Art Gallery/Airy, 10=Cockpit/Packed Data |

**Baseline: 7 / 6 / 4** (landing page default). Override based on the brief.

### Dial Inference Table

| Signal | VARIANCE | MOTION | DENSITY |
|---|---|---|---|
| "minimalist / clean / calm / editorial / Linear-style" | 5-6 | 3-4 | 2-3 |
| "premium consumer / Apple-y / luxury / brand" | 7-8 | 5-7 | 3-4 |
| "playful / wild / Dribbble / Awwwards / experimental / agency" | 9-10 | 8-10 | 3-4 |
| "landing page / portfolio / marketing site (default)" | 7-9 | 6-8 | 3-5 |
| "trust-first / public-sector / regulated / accessibility-critical" | 3-4 | 2-3 | 4-5 |
| "developer tool / SaaS / dashboard" | 5-6 | 4-5 | 4-6 |
| "redesign - preserve" | match existing | +1 | match |
| "redesign - overhaul" | +2 | +2 | match |

### How Dial Values Drive Output

Record these as the DESIGN.md's `dial_values` in the YAML frontmatter. Cross-reference them in every section:

- `VARIANCE` gates layout decisions: centered hero forbidden when >4, asymmetric layouts required when >=8, split-screen and scroll-pinned structures when >=9.
- `MOTION` gates animation depth: hover-only when <=3, scroll-triggered when >=6, magnetic/spring physics when >=9. Reduced-motion policy mandatory when >3.
- `DENSITY` gates whitespace and information packing: section gap py-32+ when <=3, py-16 when >=7. Card containers banned when >=7. Data metrics breathe in plain layout.

---

## Design System Honesty Map

Before generating tokens, decide: real design system, or aesthetic direction?

### When a Real Design System Applies (Use Official Packages)

| Brief reads as... | Reach for (official package) | Why |
|---|---|---|
| Microsoft / enterprise SaaS / dashboards | `@fluentui/react-components` | Official Fluent UI, accessibility done |
| Google-ish UI, Material-flavored product | `@material/web` + Material 3 tokens | Official, theme-able |
| IBM-style B2B / enterprise analytics | `@carbon/react` + `@carbon/styles` | Mature data-density patterns |
| Shopify app surfaces | `polaris.js` / Polaris React | Required for Shopify admin UI |
| Atlassian / Jira-style product | `@atlaskit/*` | Official Atlassian DS |
| GitHub-style devtool / community page | `@primer/css` or `@primer/react-brand` | Official Primer |
| Public-sector UK service | `govuk-frontend` | Legally expected |
| US public-sector / trust-first | `uswds` | Same |
| Modern accessible React foundation | `@radix-ui/themes` | Primitives + polished theme |
| Modern SaaS with full ownership | shadcn/ui | Owner code, easy to customise |
| Tailwind-based modern SaaS / AI marketing | Tailwind v4 utilities + `dark:` variant | Default for indie + small teams |

**Honesty rule:** if the brief reads as one of the systems above, install and use the **official** package. Do not recreate its CSS by hand. Do not import a system's tokens but then override 90% of them. **One system per project** -- do not mix Fluent React with Carbon in the same tree.

### When the Brief Is an Aesthetic, Not a System

For these directions, there is **no single official package**. Build with native CSS + Tailwind + a maintained component library. Be honest about what is borrowed inspiration vs. official material.

| Aesthetic | Honest implementation |
|---|---|
| Glassmorphism / "frosted glass" | `backdrop-filter`, layered borders, highlight overlays. Solid-fill fallback for `prefers-reduced-transparency`. |
| Bento (Apple-style tile grids) | CSS Grid with mixed cell sizes. No single library owns this. |
| Brutalism | Native CSS, monospace, raw borders. No library. |
| Editorial / magazine | Serif type, asymmetric grid, generous whitespace. No library. |
| Dark tech / hacker | Mono + accent neon, terminal motifs. No library. |
| Aurora / mesh gradients | SVG or layered radial gradients. No library. |
| Kinetic typography | Native CSS animations, scroll-driven animations, GSAP for hijacks. No library. |
| Apple Liquid Glass | Apple documents for Apple platforms only. **No official `liquid-glass.css`**. Web approximations use `backdrop-filter` + layered borders + highlights. Label as approximation. |

---

## Code Stack Conventions (For Implementation)

When the DESIGN.md is used to generate code (its intended purpose), the following defaults apply unless the Design System Map overrides them:

- **Framework:** React or Next.js. Default to Server Components (RSC). Wrap providers in `"use client"` components. Interactive components (Motion, scroll listeners, pointer physics) MUST be isolated leaves with `'use client'`.
- **Styling:** Tailwind v4 (default). v3 only if the existing project demands it. For v4: use `@tailwindcss/postcss` or the Vite plugin, NOT the `tailwindcss` plugin in `postcss.config.js`.
- **Animation:** Motion (`import { motion } from "motion/react"`). `framer-motion` still works as legacy alias -- prefer `motion/react` in new code.
- **Fonts:** Always `next/font` (Next.js) or self-host with `@font-face` + `font-display: swap`. Never link Google Fonts via `<link>` in production.
- **Icons (priority order):** `@phosphor-icons/react`, `hugeicons-react`, `@radix-ui/react-icons`, `@tabler/icons-react`. Discouraged: `lucide-react` (acceptable only when user explicitly asks or project depends on it). One family per project.
- **State:** Local `useState`/`useReducer` for isolated UI. Global state (Zustand, Jotai, React context) only for deep prop-drilling. **Never** `useState` for continuous values (mouse position, scroll progress) -- use Motion's `useMotionValue`/`useTransform`/`useScroll`.
- **Dependency Verification (mandatory):** Before importing any 3rd-party library, check `package.json`. If missing, output the install command first. Never assume a library exists.

---
