# Anti-Patterns by Brand Category

When generating a DESIGN.md, inject 3-5 category-specific warnings into the "Anti-Patterns for This Brand" section. Each warning follows the format:

`**<title>**: <what the AI does wrong> → <what to do instead>.`

## Category: AI & LLM (Claude, OpenAI-style, ElevenLabs, Mistral, xAI...)

1. **AI-purple gradient abuse**: These brands avoid generic purple/blue glow. Use their actual brand accent (green for ElevenLabs, warm orange for Claude, cyan for OpenAI).
2. **Over-designed "futuristic" UI**: AI-tool landing pages don't need hex grids, particle backgrounds, or sci-fi chrome. Clean typography + sharp brand color does the work.
3. **Inter as default**: These brands use distinctive type (Claude → ABC Diatype, ElevenLabs → custom geometric sans). Never default to Inter.

## Category: Developer Tools (Linear, Vercel, Raycast, Cursor, Warp...)

1. **Too much decoration**: Developer tools need earned trust through clarity. No glassmorphism, no pointless micro-interactions, no "delightful" easter eggs.
2. **Over-rounding**: The codex tell — card radius > 16px, full-pill everything. Dev tools use 6-12px radii. Sharp is clean.
3. **Hero overflow**: Dev-tool heroes often try to cram a fake terminal + fake dashboard + tagline + CTA. Hero = one message.
4. **Dark mode as default**: These audiences live in dark mode. Design dark-first, add light as the alt.

## Category: Fintech (Stripe, Revolut, Coinbase, Wise, Mastercard...)

1. **Warm palette drift**: Fintech leans cool (blues, teals, clean whites) — warmth reads as "not trustworthy with money." No cream backgrounds.
2. **Playful typography**: No rounded, bouncy, or "friendly" fonts. Professional geometric sans (Söhne, Geist, ABC Diatype) or stay with brand's actual type.
3. **CTA overload**: Fintech pages often have 4-5 CTAs competing. One primary action. Audit for duplicate intent ("Get started" + "Sign up" + "Try free").

## Category: Premium Consumer / Luxury (Apple, BMW, Ferrari, Superhuman, Nike...)

1. **Beige+brass+oxblood palette**: THE single most-recurring AI tell for premium briefs. Banned hex families: #f5f1ea/bone bg, #b08947/brass accent, #1a1714/espresso text. Rotate to cold luxury, forest, cobalt+cream, or pure monochrome+pop.
2. **Over-glassmorphism**: One frosted-glass element per page max. The rest is solid layers with intentional contrast.
3. **Serif reflex**: AI defaults to Fraunces/Instrument_Serif for "premium." These brands use sans display (Söhne Breit, Geist Display, ABC Diatype) or their own proprietary type. Serif only with explicit brand justification.
4. **MOTION_INTENSITY > 8 without purpose**: Premium motion is restrained and motivated — not "everything animates because we can."

## Category: Minimalist / Editorial (Linear, Mintlify, Notion, Cal.com...)

1. **Adding decoration to "make it interesting"**: Minimalist interfaces earn their beauty through restraint. Don't add gradients, shadows, or decorative elements because the page looks "too simple."
2. **Under-scaled typography**: "Minimal" doesn't mean small. Bold weight contrast at large sizes (text-4xl to text-6xl) with generous whitespace. Small type on a sparse layout = empty, not minimal.
3. **Missing imagery**: Minimalist ≠ text-only. Even Linear-style sites need 2-3 real images. Generate B&W/minimalist photography.

## Category: Playful / Creative (Figma, PostHog, Lovable, Miro, Zapier...)

1. **Emoji overuse**: These brands use illustration systems, not emoji. Emoji defaults to "chat app," not "creative tool."
2. **All-sans palette**: Playful brands benefit from one unexpected color pairing. Don't play it safe with monochrome + single blue accent.
3. **Static pages**: If the brand is playful, the page should move. MOTION_INTENSITY 6-7 minimum. Not annoying — expressive.

## Category: Enterprise / B2B (IBM, HashiCorp, MongoDB, Sentry, ClickHouse...)

1. **Consumer visual language**: Glass cards, large hero type, cinematic scroll. Enterprise audiences need density, clarity, and trust signals — not visual spectacle.
2. **Too much whitespace**: Enterprise buyers want information density. VISUAL_DENSITY 5-7, not 2-3. Tighten section padding to py-16/py-20.
3. **Missing real design system**: If the brief reads "IBM-style B2B," install @carbon/react — don't hand-build a lookalike. Same for Fluent/Atlassian/GOV.UK.

## Category: Dark Mode (Linear, Cursor, ElevenLabs, Warp, Superhuman...)

1. **Pure #000000 backgrounds**: Off-black always (zinc-950, neutral-950, or a brand-tinted near-black).
2. **Low contrast body text**: Gray-on-black at 55% lightness is unreadable. Dark-mode body needs higher contrast than light-mode body. Test at #d4d4d4 minimum.
3. **Single-mode delivery**: If the brand is dark-mode native, ship dark mode. Don't deliver light-mode-only "because it's easier."

## Category: Public Sector / Accessibility-Critical (GOV.UK, USWDS, healthcare...)

1. **Design over accessibility**: The aesthetic IS the accessibility. Don't sacrifice contrast, focus states, or semantic HTML for "looking modern."
2. **Decorative-only motion**: MOTION_INTENSITY 2-3 max. Motion that doesn't serve accessibility or information hierarchy is noise.
3. **Trendy design language**: Glassmorphism, brutalism, kinetic type — inappropriate. This audience needs earned trust, not aesthetic experimentation.

## Category: E-commerce (Shopify, Nike, Airbnb, Starbucks...)

1. **Hero overstuffed**: E-commerce heroes try to fit: brand message + product shot + price + CTA + trust badges + promo code. Hero = one product, one message, one CTA.
2. **Fake precision on specs**: "5.8 mm thickness, 13.4 lb weight" without real product data. Either use real specs or don't show numbers.
3. **Missing product photography**: E-commerce IS product photography. If no image-gen tool is available, use explicit placeholder slots with aspect ratios noted. Never div-based fake product boxes.
