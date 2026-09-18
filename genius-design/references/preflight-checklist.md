# Twelve Specification Checks

Copy these 12 items into Pre-Ship Checklist, adding concrete results. `[x]` means the **specification** was checked, not that a UI passed tests. Leave unresolved items `[ ]` with a reason; lint warns and delivery must disclose them. An inapplicable requirement gets `N/A: <reason>`, never an unexplained tick.

- [ ] **Brief fidelity:** audience, page/screen type, language, stack and explicit user constraints are reflected.
- [ ] **Rule priority:** brand observations and requirements are preserved; departures and aesthetic preferences have reasons.
- [ ] **Evidence:** Observed/Inferred/Recommended claims have sources and context; unavailable evidence is explicit.
- [ ] **Dials:** all three values are 1–10 with scenario-specific rationales; no invented motion measurement.
- [ ] **Color and themes:** semantic roles are usable, scoped themes are complete, functional statuses are distinguished from brand accents.
- [ ] **Type and spacing:** named tokens, readable hierarchy, language fallbacks and responsive spacing are specified.
- [ ] **Rhythm:** actual regions and their content rationale are documented; repeated layouts are justified where useful.
- [ ] **Components:** relevant interactive, disabled, validation and async states are specified; irrelevant state families are not forced.
- [ ] **Accessibility:** contrast targets, keyboard/focus, zoom/reflow and non-color cues are specified; measured checks and pending UI checks are distinguished.
- [ ] **Motion and assets:** motion has a purpose and reduced-motion behavior; asset needs are justified with honest provenance or labelled slots.
- [ ] **Honesty and anti-patterns:** no fabricated proof or official-system claims; 3–5 context-specific failure modes are actionable.
- [ ] **Handoff:** contract lint passed; source gaps and implementation checks are disclosed; safe commit and backup paths are recorded in the delivery report.

This checklist is not a visual inspection substitute. Contrast ratios, viewport fit, responsive states and keyboard behavior require checking the eventual implementation in its intended environment.
