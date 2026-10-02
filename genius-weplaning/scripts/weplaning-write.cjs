#!/usr/bin/env node
/**
 * weplaning-write.cjs — patch CURRENT.md and/or append CHANGES/DECISIONS.
 *
 * Does not create sessions. Trivial oral notes (完成了/done/搞定) with no
 * CURRENT patches and no decision are a no-op.
 */

"use strict";

const fs = require("fs");
const path = require("path");
const {
  checkMemory,
  defaultAgent,
  emitResult,
  formatSectionItems,
  isTrivialNote,
  parseArgs,
  parseCurrentMd,
  readMemory,
  replaceField,
  runCheck,
  SCHEMA_VERSION,
  section,
  setSection,
  toList,
  truncateSummary,
  uniqueStamp,
  usage,
  utcNow,
  validateKnownMarkdown,
  withMemoryLock,
  writeMemory,
} = require("./weplaning-utils.cjs");

const help = `
Usage:
  node weplaning-write.cjs <project-root> [note] [options]

Patch accepted project state. One command replaces note + closeout.

Options:
  --agent <name>         Agent name (default: $WEPLANING_AGENT or inferred)
  --changed <text>       Ledger line(s). Repeat or separate with ";;"
  --replace <old>        Exact CURRENT.md text that occurs once; pair with --with
  --with <new>           Replacement for the matching --replace (repeat in order)
  --drop <text>          Remove the single CURRENT.md line containing this text
  --add-state <text>     Append Current State bullet(s) (";;")
  --state <text>         Replace Current State (";;" bullets)
  --next-step <text>     Replace Accepted Next Steps
  --blockers <text>      Replace Open Blockers
  --goal <text>          Replace Active Goal
  --understanding <text> Replace Current Understanding
  --decision <text>      Also append DECISIONS.md
  --rationale <text>     Rationale for --decision
  --file <path>          Optional files touched (repeat / ";;")
  --verification <text>  Optional verification notes (repeat / ";;")
  --note <text>          Extra ledger notes (repeat / ";;")
  --json                 Machine-readable JSON on stdout
`;

const args = parseArgs(process.argv.slice(2));
usage(!args.help, "", help);

const valueFlags = ["agent", "changed", "replace", "with", "drop", "add-state", "state", "next-step", "blockers", "goal", "understanding", "decision", "rationale", "file", "files", "verification", "note", "time"];
// Only these may span lines; every other value becomes one Markdown line or list item.
const multiLineFlags = ["goal", "understanding", "replace", "with"];
const HEADING = /^[ \t]{0,3}#{1,6}([ \t]|$)/m;
for (const [key, value] of Object.entries(args)) {
  if (key === "_") continue;
  usage(valueFlags.includes(key) || ["json", "help"].includes(key), `Unknown option: --${key}`, help);
  if (valueFlags.includes(key)) {
    const values = Array.isArray(value) ? value : [value];
    usage(values.every((item) => typeof item === "string" && toList(item).length > 0), `Missing value for --${key}`, help);
    if (["agent", "goal", "understanding", "decision", "rationale", "time"].includes(key)) {
      usage(values.length === 1, `--${key} accepts one value`, help);
    }
    usage(values.every((item) => !HEADING.test(item)), `--${key} must not contain Markdown headings`, help);
    if (!multiLineFlags.includes(key)) {
      usage(values.every((item) => !/[\r\n]/.test(item)), `--${key} must be one line; separate items with ";;"`, help);
    }
  } else {
    usage(value === true, `--${key} does not take a value`, help);
  }
}
usage(args._.length <= 2, "Unexpected positional arguments", help);

const root = path.resolve(args._[0] || process.cwd());
const positional = args._[1] ? String(args._[1]).trim() : "";
usage(!/[\r\n]/.test(positional) && !HEADING.test(positional), "Note must be one line without Markdown headings", help);
const changed = toList(args.changed);
if (positional && changed.length === 0) changed.push(positional);

const replaces = [].concat(args.replace ?? []);
const withs = [].concat(args.with ?? []);
const drops = [].concat(args.drop ?? []);
usage(replaces.length === withs.length, "Each --replace needs exactly one --with", help);

const hasPatch = Boolean(args.state || args["next-step"] || args.blockers || args.goal || args.understanding || args["add-state"] || replaces.length || drops.length);
const hasDecision = Boolean(args.decision && args.decision !== true);
const trivialOnly = changed.length > 0 && changed.every(isTrivialNote);

if (!hasPatch && !hasDecision && changed.length === 0) {
  usage(false, "Nothing to write. Pass --changed, a CURRENT patch flag, or --decision.", help);
}

const agent = args.agent || defaultAgent();
const now = args.time || utcNow();
const files = toList(args.file || args.files);
const verification = toList(args.verification);
const extraNotes = toList(args.note);
const currentPath = path.join(root, ".agent-memory", "CURRENT.md");
const changesPath = path.join(root, ".agent-memory", "CHANGES.md");

if (!fs.existsSync(currentPath) || !fs.existsSync(changesPath)) {
  console.error("Missing .agent-memory/CURRENT.md or CHANGES.md — run init-memory.cjs first.");
  process.exit(1);
}

if (!hasPatch && !hasDecision && trivialOnly) {
  emitResult(args, "nothing-to-persist", {
    persisted: false,
    reason: "trivial-note",
    message: "nothing to persist",
  });
  process.exit(0);
}

const patched = [];
const changeId = `${now} change ${uniqueStamp()}`;
let decisionRecorded = false;
let persisted = false;

// Empty ledger fields are left out instead of written as "none".
function listField(label, items) {
  return items.length ? `- ${label}:\n${items.map((item) => `  - ${item}`).join("\n")}\n` : "";
}

const oneLine = (text) => String(text).replace(/\s+/g, " ").trim();

withMemoryLock(root, () => {
  runCheck(root);
  const original = readMemory(root, "CURRENT.md").replace(/\r\n/g, "\n");
  const basedOn = section(original, "Based On");
  // Based On is regenerated below, so exact edits must not match its copied summary.
  let currentText = setSection(original, "Based On", "");
  const descriptions = [];

  // Exact edits first: the same contract as an editor's old/new string replacement.
  replaces.forEach((oldText, index) => {
    const count = currentText.split(oldText).length - 1;
    usage(count === 1, `--replace text must occur exactly once in CURRENT.md (found ${count}): ${oldText}`, help);
    if (withs[index] === oldText) return;
    currentText = currentText.replace(oldText, () => withs[index]);
    if (!patched.includes("replace")) patched.push("replace");
    descriptions.push(`Replaced in CURRENT: ${oneLine(oldText)} → ${oneLine(withs[index])}`);
  });
  for (const text of drops) {
    const lines = currentText.split("\n");
    const hits = lines.flatMap((line, index) => (line.includes(text) ? [index] : []));
    usage(hits.length === 1, `--drop text must match exactly one CURRENT.md line (found ${hits.length}): ${text}`, help);
    descriptions.push(`Removed from CURRENT: ${oneLine(lines[hits[0]])}`);
    lines.splice(hits[0], 1);
    currentText = lines.join("\n");
    if (!patched.includes("drop")) patched.push("drop");
  }

  const current = parseCurrentMd(currentText);
  const fields = {
    goal: ["activeGoal", "Active Goal"],
    understanding: ["currentUnderstanding", "Current Understanding"],
    state: ["currentState", "Current State"],
    "next-step": ["acceptedNextSteps", "Accepted Next Steps"],
    blockers: ["openBlockers", "Open Blockers"],
  };
  for (const [flag, [field, heading]] of Object.entries(fields)) {
    if (args[flag] === undefined) continue;
    const value = ["goal", "understanding"].includes(flag)
      ? args[flag].trim()
      : formatSectionItems(args[flag], { numbered: flag === "next-step" });
    if (value === current[field]) continue;
    currentText = setSection(currentText, heading, value);
    patched.push(flag);
    descriptions.push(`Updated ${heading}: ${oneLine(value)}`);
  }
  if (args["add-state"] !== undefined) {
    const added = formatSectionItems(args["add-state"]);
    currentText = setSection(currentText, "Current State", `${section(currentText, "Current State")}\n${added}`);
    patched.push("add-state");
    descriptions.push(`Added to Current State: ${oneLine(added.replace(/^- /gm, ""))}`);
  }
  const steps = section(currentText, "Accepted Next Steps");
  if (steps !== section(original, "Accepted Next Steps")) {
    let number = 0;
    const renumbered = steps.replace(/^\d+\.(?=\s)/gm, () => `${(number += 1)}.`);
    if (renumbered !== steps) currentText = setSection(currentText, "Accepted Next Steps", renumbered);
  }

  const ledgerItems = trivialOnly ? [] : [...changed];
  if (!ledgerItems.length) {
    ledgerItems.push(...descriptions);
    if (hasDecision) ledgerItems.push(`Decision: ${args.decision}`);
  }
  if (!ledgerItems.length) return;

  const keptBasedOn = basedOn
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line && !/^- Last change:/.test(line));
  currentText = setSection(currentText, "Based On", [`- Last change: ${now} ${truncateSummary(ledgerItems[0])}`, ...keptBasedOn].join("\n"));
  currentText = /^Last updated:/m.test(currentText)
    ? replaceField(currentText, "Last updated", now)
    : currentText.replace(/^(Schema version:[^\n]*)/m, (line) => `${line}\nLast updated: ${now}`);

  const existing = readMemory(root, "CHANGES.md").replace(/\s*$/, "\n");
  const entry = `
## ${changeId}
- Agent: ${agent}
${listField("Changed", ledgerItems)}${listField("Files touched", files)}${listField("Verification", verification)}${listField("Notes", extraNotes)}`;
  const outputs = [["CURRENT.md", currentText], ["CHANGES.md", `${existing}${entry}`]];

  if (hasDecision) {
    const decisionsPath = path.join(root, ".agent-memory", "DECISIONS.md");
    let text = fs.existsSync(decisionsPath)
      ? fs.readFileSync(decisionsPath, "utf8").replace(/\s*$/, "")
      : `# Decisions\nSchema version: ${SCHEMA_VERSION}`;
    if (!/^Schema version:/m.test(text)) {
      text = `# Decisions\nSchema version: ${SCHEMA_VERSION}\n${text}`;
    }
    const entry = `
## ${now} decision
- Agent: ${agent}
- Decision: ${args.decision}
- Rationale: ${args.rationale ? String(args.rationale) : "none"}
`;
    outputs.push(["DECISIONS.md", `${text}\n${entry}`]);
    decisionRecorded = true;
  }
  for (const [file, content] of outputs) validateKnownMarkdown(file, content);
  for (const [file, content] of outputs) writeMemory(root, file, content);
  persisted = true;
  runCheck(root);
});

if (!persisted) {
  emitResult(args, "nothing-to-persist", { persisted: false, reason: "unchanged", patched: [], message: "nothing to persist" });
  process.exit(0);
}

// Warn at the moment CURRENT grows; warnings never block the write.
for (const warning of checkMemory(root, { audit: true }).warnings) console.error(`[audit] ${warning}`);

emitResult(args, changeId, {
  persisted: true,
  changeId,
  patched,
  decision: decisionRecorded,
  message: `weplaning-write done: ${changeId}`,
});
