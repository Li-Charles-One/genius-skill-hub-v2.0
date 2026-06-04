---
name: brainstorming
description: Explore intent, requirements, and design before implementing complex features. Use for ambiguous multi-approach tasks or when user asks to brainstorm/plan. Skips automatically for clear-scope work. Outputs design spec, then hands off to writing-plans for implementation planning.
run_as: subagent
model: deepseek-v4-flash
allowed_tools:
  - read_file
  - search_content
  - search_files
  - directory_tree
  - glob
  - write_file
  - run_command
---

# Brainstorming Ideas Into Designs

## Relationship to writing-plans

Brainstorming explores WHAT to build and WHY. Writing-plans defines HOW to build it. They are sequential: brainstorm first (if needed), then write-plan. If the user already knows what they want, skip brainstorming and go straight to /write-plan. Brainstorming should NOT produce implementation details —that's writing-plans' job.

Help turn ideas into fully formed designs and specs through natural collaborative dialogue.

Start by understanding the current project context, then ask questions one at a time to refine the idea. Once you understand what you're building, present the design and get user approval.

<COMPLEXITY-GATE>
**When to require a design phase** (BOTH conditions must be true):
- Task touches 3+ files or introduces a new feature/component —AND —- The approach is ambiguous (multiple valid approaches with different trade-offs)

**Skip brainstorming when:**
- Task is clear in intent even if it touches many files (e.g., "rename X to Y across the codebase")
- Task touches 1-2 files with clear scope (bug fix, config change, simple addition)
- There's one obvious approach —just do it

**Always brainstorm when:**
- User explicitly asks to brainstorm or plan
- Task has multiple valid approaches and the wrong choice would be costly to reverse

**Use codebase-cartographer** to understand existing patterns before proposing designs —don't re-explore what's already mapped.
</COMPLEXITY-GATE>

## Anti-Pattern: "Everything Needs A Design"

Only tasks with genuine complexity or ambiguity benefit from the design process. A single-file bug fix, a config change, or adding a straightforward utility does NOT need a 9-step design phase. Save brainstorming for work where the upfront thinking genuinely prevents wasted effort.

## Speed-Tiered Checklist

NOT every brainstorm needs 9 steps. Match depth to task size:

### Lite Brainstorm (most tasks that clear the complexity gate)
For tasks where the design question is "which of 2-3 approaches?" —not "what are we building?"

1. **State the 2-3 approaches** —one sentence each with trade-off
2. **Recommend one** —with a one-line reason
3. **Get user pick** —then execute immediately

Total: 1 message, ~30 seconds. No design doc, no spec review, no visual companion.

### Full Brainstorm (only for genuinely complex, multi-component features)
Only use when the user explicitly asks to brainstorm OR the task involves a new system/architecture:

1. **Explore project context** —check files, docs, recent commits
2. **Offer visual companion** (if topic will involve visual questions) —this is its own message, not combined with a clarifying question. See the Visual Companion section below.
3. **Ask clarifying questions** —one at a time, understand purpose/constraints/success criteria
4. **Propose 2-3 approaches** —with trade-offs and your recommendation
5. **Present design** —in sections scaled to their complexity, get user approval after each section
6. **Write design doc** —save to `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md` and commit
7. **Spec review loop** —dispatch spec-document-reviewer subagent with precisely crafted review context (never your session history); fix issues and re-dispatch until approved (max 5 iterations, then surface to human)
8. **User reviews written spec** —ask user to review the spec file before proceeding
9. **Transition to implementation** —invoke writing-plans skill to create implementation plan

**Default to Lite.** Only escalate to Full when the user says "let's plan this out" or the task is genuinely architectural (new service, new data model, new integration pattern).

**Flow:** Explore context -> (offer visual companion if needed) -> clarify questions -> propose approaches -> present design sections (loop until approved) -> write spec doc -> spec review loop (fix until approved, max 5 iterations) -> user reviews spec -> invoke writing-plans.

**The terminal state is invoking writing-plans.** Do NOT invoke frontend-design, mcp-builder, or any other implementation skill. The ONLY skill you invoke after brainstorming is writing-plans.

## The Process

**Understanding the idea:**

- Check out the current project state first (files, docs, recent commits)
- Before asking detailed questions, assess scope: if the request describes multiple independent subsystems (e.g., "build a platform with chat, file storage, billing, and analytics"), flag this immediately. Don't spend questions refining details of a project that needs to be decomposed first.
- If the project is too large for a single spec, help the user decompose into sub-projects: what are the independent pieces, how do they relate, what order should they be built? Then brainstorm the first sub-project through the normal design flow. Each sub-project gets its own spec 鈫?plan 鈫?implementation cycle.
- For appropriately-scoped projects, ask questions one at a time to refine the idea
- Prefer multiple choice questions when possible, but open-ended is fine too
- Only one question per message - if a topic needs more exploration, break it into multiple questions
- Focus on understanding: purpose, constraints, success criteria

**Exploring approaches:**

- Propose 2-3 different approaches with trade-offs
- Present options conversationally with your recommendation and reasoning
- Lead with your recommended option and explain why

**Presenting the design:**

- Once you believe you understand what you're building, present the design
- Scale each section to its complexity: a few sentences if straightforward, up to 200-300 words if nuanced
- Ask after each section whether it looks right so far
- Cover: architecture, components, data flow, error handling, testing
- Be ready to go back and clarify if something doesn't make sense

**Design for isolation and clarity:**

- Break the system into smaller units that each have one clear purpose, communicate through well-defined interfaces, and can be understood and tested independently
- For each unit, you should be able to answer: what does it do, how do you use it, and what does it depend on?
- Can someone understand what a unit does without reading its internals? Can you change the internals without breaking consumers? If not, the boundaries need work.
- Smaller, well-bounded units are also easier for you to work with - you reason better about code you can hold in context at once, and your edits are more reliable when files are focused. When a file grows large, that's often a signal that it's doing too much.

**Working in existing codebases:**

- Explore the current structure before proposing changes. Follow existing patterns.
- Where existing code has problems that affect the work (e.g., a file that's grown too large, unclear boundaries, tangled responsibilities), include targeted improvements as part of the design - the way a good developer improves code they're working in.
- Don't propose unrelated refactoring. Stay focused on what serves the current goal.

## After the Design

**Documentation:**

- Write the validated design (spec) to `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md`
  - (User preferences for spec location override this default)

- Commit the design document to git

**Spec Review Loop:**
After writing the spec document:

1. Dispatch spec-document-reviewer subagent (see spec-document-reviewer-prompt.md)
2. If Issues Found: fix, re-dispatch, repeat until Approved
3. If loop exceeds 5 iterations, surface to human for guidance

**User Review Gate:**
After the spec review loop passes, ask the user to review the written spec before proceeding:

> "Spec written and committed to `<path>`. Please review it and let me know if you want to make any changes before we start writing out the implementation plan."

Wait for the user's response. If they request changes, make them and re-run the spec review loop. Only proceed once the user approves.

**Implementation:**

- Invoke the writing-plans skill to create a detailed implementation plan
- Do NOT invoke any other skill. writing-plans is the next step.

## Key Principles

- **One question at a time** - Don't overwhelm with multiple questions
- **Multiple choice preferred** - Easier to answer than open-ended when possible
- **YAGNI ruthlessly** - Remove unnecessary features from all designs
- **Explore alternatives** - Always propose 2-3 approaches before settling
- **Incremental validation** - Present design, get approval before moving on
- **Be flexible** - Go back and clarify when something doesn't make sense

## Visual Companion

A browser-based companion for showing mockups, diagrams, and visual options during brainstorming. Available as a tool —not a mode. Accepting the companion means it's available for questions that benefit from visual treatment; it does NOT mean every question goes through the browser.

**Offering the companion:** When you anticipate that upcoming questions will involve visual content (mockups, layouts, diagrams), offer it once for consent:

> "Some of what we're working on might be easier to explain if I can show it to you in a web browser. I can put together mockups, diagrams, comparisons, and other visuals as we go. This feature is still new and can be token-intensive. Want to try it? (Requires opening a local URL)"

**This offer MUST be its own message.** Do not combine it with clarifying questions, context summaries, or any other content. The message should contain ONLY the offer above and nothing else. Wait for the user's response before continuing. If they decline, proceed with text-only brainstorming.

**Per-question decision:** Even after the user accepts, decide FOR EACH QUESTION whether to use the browser or the terminal. The test: **would the user understand this better by seeing it than reading it?**

- **Use the browser** for content that IS visual —mockups, wireframes, layout comparisons, architecture diagrams, side-by-side visual designs
- **Use the terminal** for content that is text —requirements questions, conceptual choices, tradeoff lists, A/B/C/D text options, scope decisions

A question about a UI topic is not automatically a visual question. "What does personality mean in this context?" is a conceptual question —use the terminal. "Which wizard layout works better?" is a visual question —use the browser.
