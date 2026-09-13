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
  allowNoCheck,
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
  toList,
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
  --no-check             Internal use only
`;

const args = parseArgs(process.argv.slice(2));
usage(!args.help, "", help);
allowNoCheck(args, "weplaning-write.cjs");

const valueFlags = ["agent", "changed", "state", "next-step", "blockers", "goal", "understanding", "decision", "rationale", "file", "files", "verification", "note", "time"];
for (const [key, value] of Object.entries(args)) {
  if (key === "_") continue;
  usage(valueFlags.includes(key) || ["json", "no-check", "help"].includes(key), `Unknown option: --${key}`, help);
  if (valueFlags.includes(key)) {
    const values = Array.isArray(value) ? value : [value];
    usage(values.every((item) => typeof item === "string" && toList(item).length > 0), `Missing value for --${key}`, help);
    if (["agent", "goal", "understanding", "decision", "rationale", "time"].includes(key)) {
      usage(values.length === 1, `--${key} accepts one value`, help);
    }
  } else {
    usage(value === true, `--${key} does not take a value`, help);
  }
}
usage(args._.length <= 2, "Unexpected positional arguments", help);

const root = path.resolve(args._[0] || process.cwd());
const positional = args._[1] ? String(args._[1]).trim() : "";
const changed = toList(args.changed);
if (positional && changed.length === 0) changed.push(positional);

const hasPatch = Boolean(args.state || args["next-step"] || args.blockers || args.goal || args.understanding);
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

function listBlock(items, fallback) {
  const values = items.length ? items : [fallback];
  return values.map((item) => `  - ${item}`).join("\n");
}

withMemoryLock(root, () => {
  if (!args["no-check"]) runCheck(root, __dirname);
  let currentText = readMemory(root, "CURRENT.md").replace(/\r\n/g, "\n");
  const current = parseCurrentMd(currentText);
  const patches = [];
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
    current[field] = value;
    patches.push([heading, value]);
    patched.push(flag);
  }

  const ledgerItems = trivialOnly ? [] : [...changed];
  if (!ledgerItems.length) {
    for (const [heading, value] of patches) ledgerItems.push(`Updated ${heading}: ${value.replace(/\s+/g, " ")}`);
    if (hasDecision) ledgerItems.push(`Decision: ${args.decision}`);
  }
  if (!ledgerItems.length) return;

  const summary = ledgerItems[0];
  current.lastUpdated = now;
  const keptBasedOn = String(current.basedOn || "")
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line && !/^- Last change:/.test(line) && !/^- Session:/.test(line));
  current.basedOn = [`- Last change: ${now} ${summary}`, ...keptBasedOn].join("\n");
  patches.push(["Based On", current.basedOn]);
  for (const [heading, value] of patches) {
    const pattern = new RegExp(`^##[ \\t]+${heading}[ \\t]*\\n[\\s\\S]*?(?=\\n##[ \\t]+|$(?![\\s\\S]))`, "m");
    if (pattern.test(currentText)) currentText = currentText.replace(pattern, () => `## ${heading}\n${value}\n`);
    else currentText = `${currentText.trimEnd()}\n\n## ${heading}\n${value}\n`;
  }
  currentText = replaceField(currentText, "Schema version", SCHEMA_VERSION).replace(/^Mainline session:[^\n]*\n?/m, "");
  currentText = /^Last updated:/m.test(currentText)
    ? replaceField(currentText, "Last updated", now)
    : currentText.replace(/^(Schema version:[^\n]*)/m, (line) => `${line}\nLast updated: ${now}`);

  const existing = readMemory(root, "CHANGES.md").replace(/\s*$/, "\n");
  const entry = `
## ${changeId}
- Agent: ${agent}
- Change ID: ${changeId}
- Changed:
${listBlock(ledgerItems, "unknown")}
- Files touched:
${listBlock(files, "none")}
- Verification:
${listBlock(verification, "none")}
- Notes:
${listBlock(extraNotes, "none")}
`;
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
  if (!args["no-check"]) runCheck(root, __dirname);
});

if (!persisted) {
  emitResult(args, "nothing-to-persist", { persisted: false, reason: "unchanged", patched: [], message: "nothing to persist" });
  process.exit(0);
}

emitResult(args, changeId, {
  persisted: true,
  changeId,
  patched,
  decision: decisionRecorded,
  upgradedSchema: SCHEMA_VERSION,
  message: `weplaning-write done: ${changeId}`,
});
