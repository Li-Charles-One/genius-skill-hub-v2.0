# Dials and Implementation Handoff

## Three Dials

All are integers 1–10. Explain each in Design Read. These are communication aids, not objective aesthetic scores or automatic CSS rules.

| Dial | Low | High |
| --- | --- | --- |
| DESIGN_VARIANCE | Regular, repeatable organization | More varied composition and expressive hierarchy |
| MOTION_INTENSITY | Static or essential feedback only | Extensive choreography justified by the experience |
| VISUAL_DENSITY | Sparse, single-task content | Many simultaneously useful controls/data points |

Starting ranges, overridden by the brief or existing evidence:

| Scenario | Variance | Motion | Density |
| --- | --- | --- | --- |
| Marketing or portfolio | 4–7 | 2–5 | 3–5 |
| Dense operational dashboard | 2–5 | 1–3 | 6–9 |
| Public service or clinical workflow | 2–4 | 1–2 | 4–8, task-dependent |
| Editorial or publication | 3–7 | 1–3 | 3–7 |
| Experimental/expressive experience | 6–9 | 4–8 | Content-dependent |

- Low variance can still be distinctive through typography and content.
- High variance does not require asymmetry, scroll pinning or breaking reading order.
- Dense screens can use cards when grouping improves scanning. Density does not remove touch, zoom or keyboard requirements.
- Preserve-mode redesign starts by matching current behavior, including motion. No automatic dial increments.
- In reverse work, mark these interpretations Inferred. If motion was not captured, record it as unknown; a proposed implementation dial is Recommended.

## Official System or Aesthetic Direction?

Record whether the project uses an existing official system, a component foundation, or bespoke styling. A brand resemblance alone does not authorize installing that brand's implementation stack.

Examples to investigate when relevant: Fluent, Material, Carbon, Polaris, Atlassian, Primer, GOV.UK and USWDS. Verify current official documentation and compatibility during an actual implementation task; do not hardcode package/API assumptions in a design specification.

If the project already uses a system, map semantic roles to its documented tokens rather than recreating an incompatible parallel system. Record intentional exceptions. Glass effects, editorial style, bento layouts or an Apple-inspired aesthetic are not themselves official web packages.

## Handoff

- Respect the existing framework, CSS approach and component library. Do not default every project to React/Next.js/Tailwind.
- Keep the specification implementation-neutral unless the user or repository provides a stack.
- Give semantic token names and usage rules. Downstream code should consume them or explicitly add a missing token rather than improvise inline values.
- Document font licensing/availability and language coverage. For Chinese/CJK, specify a usable fallback; do not assume a Latin display font covers body copy.
- Reuse the project's icon family. Self-hosting/font loading and performance choices belong to the actual deployment context.
- Describe motion purpose, duration range and reduced-motion alternative. Library selection is optional and requires current dependency verification later.
- No package installation or code changes are performed by this skill.
