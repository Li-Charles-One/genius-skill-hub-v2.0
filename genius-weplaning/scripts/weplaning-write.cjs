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
  renderCurrentMd,
  runCheck,
  SCHEMA_VERSION,
  toList,
  usage,
  utcNow,
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
const changeId = `${now} change`;
let decisionRecorded = false;

function listBlock(items, fallback) {
  const values = items.length ? items : [fallback];
  return values.map((item) => `  - ${item}`).join("\n");
}

withMemoryLock(root, () => {
  const current = parseCurrentMd(readMemory(root, "CURRENT.md"));
  if (args.goal && args.goal !== true) {
    current.activeGoal = String(args.goal).trim();
    patched.push("goal");
  }
  if (args.understanding && args.understanding !== true) {
    current.currentUnderstanding = String(args.understanding).trim();
    patched.push("understanding");
  }
  if (args.state) {
    current.currentState = formatSectionItems(args.state, { fallback: current.currentState });
    patched.push("state");
  }
  if (args["next-step"]) {
    current.acceptedNextSteps = formatSectionItems(args["next-step"], {
      numbered: true,
      fallback: current.acceptedNextSteps,
    });
    patched.push("next-step");
  }
  if (args.blockers) {
    current.openBlockers = formatSectionItems(args.blockers, { fallback: "none" });
    patched.push("blockers");
  }

  const summary = changed[0] || patched.join(", ") || String(args.decision || "update");
  current.lastUpdated = now;
  const keptBasedOn = String(current.basedOn || "")
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line && !/^- Last change:/.test(line) && !/^- Session:/.test(line));
  current.basedOn = [`- Last change: ${now} ${summary}`, ...keptBasedOn].join("\n");
  writeMemory(root, "CURRENT.md", renderCurrentMd(current));

  if (changed.length && !trivialOnly) {
    const existing = readMemory(root, "CHANGES.md").replace(/\s*$/, "\n");
    const header = /^Schema version:/m.test(existing)
      ? existing
      : `# Changes\nSchema version: ${SCHEMA_VERSION}\n\n${existing}`;
    const entry = `
## ${changeId}
- Agent: ${agent}
- Change ID: ${changeId}
- Changed:
${listBlock(changed, "unknown")}
- Files touched:
${listBlock(files, "none")}
- Verification:
${listBlock(verification, "none")}
- Notes:
${listBlock(extraNotes, "none")}
`;
    writeMemory(root, "CHANGES.md", `${header.replace(/\s*$/, "\n")}${entry}`);
  }

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
    writeMemory(root, "DECISIONS.md", `${text}\n${entry}`);
    decisionRecorded = true;
  }
});

if (!args["no-check"]) runCheck(root, __dirname);

emitResult(args, changeId, {
  persisted: true,
  changeId,
  patched,
  decision: decisionRecorded,
  upgradedSchema: SCHEMA_VERSION,
  message: `weplaning-write done: ${changeId}`,
});
