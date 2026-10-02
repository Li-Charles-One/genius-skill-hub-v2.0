#!/usr/bin/env node
/**
 * weplaning-read.cjs — briefing from CURRENT.md + recent CHANGES.md
 */

"use strict";

const fs = require("fs");
const path = require("path");
const {
  parseArgs,
  parseCurrentMd,
  readMemory,
  runCheck,
  truncateSummary,
  usage,
  utcNow,
} = require("./weplaning-utils.cjs");

const help = `
Usage:
  node weplaning-read.cjs <project-root> [options]

Options:
  --handoff     Highlight next step #1
  --brief       Goal, next steps and blockers; long context/state items cut to their label (no ledger)
  --full        Also list archive files
  --json        Machine-readable JSON on stdout
  --next <N>    Focus Accepted Next Steps item N (1-based)
  --limit <K>   Number of recent change blocks (default: 3)
  --find <q>    Search memory (including archive); equivalent to weplaning-find.cjs
`;

const args = parseArgs(process.argv.slice(2));
usage(!args.help, "", help);

const root = path.resolve(args._[0] || process.cwd());
const memDir = path.join(root, ".agent-memory");
const limit = Math.max(1, Number(args.limit || 3) || 3);
const nextN = args.next === undefined ? null : Number(args.next);
usage(args.next === undefined || (typeof args.next === "string" && /^[1-9]\d*$/.test(args.next) && Number.isSafeInteger(nextN)), "--next requires a positive integer", help);
usage(args.find === undefined || (typeof args.find === "string" && args.find.trim()), "--find requires a query", help);

if (args.find && args.find !== true) {
  const finder = path.join(__dirname, "weplaning-find.cjs");
  const { spawnSync } = require("child_process");
  const extra = [];
  if (args.json) extra.push("--json");
  const result = spawnSync(process.execPath, [finder, root, String(args.find), ...extra], {
    cwd: root,
    encoding: "utf8",
  });
  if (result.stdout) process.stdout.write(result.stdout);
  if (result.stderr) process.stderr.write(result.stderr);
  process.exit(result.status || 0);
}

function parseChangeBlocks(text) {
  const normalized = text.replace(/\r?\n/g, "\n").trim();
  if (!normalized) return [];
  const parts = normalized.split(/\n(?=## )/);
  const blocks = [];
  for (const part of parts) {
    const match = part.match(/^##\s+(.+?)\s*\n([\s\S]*)$/);
    if (!match) continue;
    const id = match[1].trim();
    const body = match[2].trim();
    const agent = (body.match(/^- Agent:\s*(.+)$/m) || [])[1]?.trim() || null;
    function items(label) {
      const match = body.match(new RegExp(`^- ${label}:\\n((?:  - .+\\n?)*)`, "m"));
      return match ? match[1].split("\n").map((line) => line.replace(/^\s+- /, "").trim()).filter(Boolean) : [];
    }
    blocks.push({ id, agent, changed: items("Changed"), verification: items("Verification"), files: items("Files touched"), body });
  }
  return blocks;
}

function parseNextSteps(text) {
  const lines = String(text || "")
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
  const items = [];
  for (const line of lines) {
    const match = line.match(/^\d+\.\s*(.+)$/);
    if (match) items.push(match[1].trim());
    else items.push(line.replace(/^[-*]\s*/, "").trim());
  }
  return items;
}

runCheck(root, { quiet: true });
const currentText = readMemory(root, "CURRENT.md");
const current = parseCurrentMd(currentText);

const changesPath = path.join(memDir, "CHANGES.md");
let recentChanges = [];
if (fs.existsSync(changesPath)) {
  recentChanges = parseChangeBlocks(fs.readFileSync(changesPath, "utf8")).slice(-limit).reverse();
}

const archiveDir = path.join(memDir, "archive");
const archives = (args.full || args.json) && fs.existsSync(archiveDir)
  ? fs
      .readdirSync(archiveDir)
      .filter((name) => /^CHANGES-.*\.md$/.test(name))
      .sort()
      .reverse()
      .map((name) => {
        const text = fs.readFileSync(path.join(archiveDir, name), "utf8");
        const count = Number((text.match(/^Blocks:\s*(\d+)$/m) || [])[1] || 0);
        return { file: `archive/${name}`, kind: "changes", count };
      })
  : [];

const isNoTask = (text) => /^(none|no (?:pending )?tasks?|no (?:accepted )?next steps?|无|无待办|无待执行事项|暂无待办|暂无待执行事项)[。.]?$/i.test(text);
const isUnknown = (text) => /^(unknown|unavailable|未知|待确认|未确定)[。.]?$/i.test(text);
const rawSteps = parseNextSteps(current.acceptedNextSteps);
const nextStepsStatus = rawSteps.every(isNoTask) ? "none" : rawSteps.every(isUnknown) ? "unknown" : "ready";
const nextSteps = nextStepsStatus === "none" ? [] : rawSteps;
if (nextN !== null) {
  usage(nextN <= nextSteps.length, `Next step #${nextN} does not exist (${nextSteps.length} recorded)`, help);
  usage(!isNoTask(nextSteps[nextN - 1]) && !isUnknown(nextSteps[nextN - 1]), `Next step #${nextN} is not an actionable task`, help);
}
const focusIndex = nextN ?? (args.handoff && nextStepsStatus === "ready" && !isNoTask(nextSteps[0]) && !isUnknown(nextSteps[0]) ? 1 : null);

const payload = {
  ok: true,
  generatedAt: utcNow(),
  lastUpdated: current.lastUpdated,
  schema: current.schemaVersion,
  handoff: Boolean(args.handoff),
  goal: current.activeGoal,
  currentState: current.currentState,
  understanding: current.currentUnderstanding,
  projectConfig: current.projectConfig || "",
  nextSteps,
  nextStepsStatus,
  focusNextStep: focusIndex === null ? null : { index: focusIndex, text: nextSteps[focusIndex - 1] },
  blockers: current.openBlockers,
  recentChanges: recentChanges.map((c) => ({
    id: c.id,
    agent: c.agent,
    changed: c.changed,
    verification: c.verification,
    files: c.files,
  })),
  archives,
  truth: "CURRENT.md is accepted truth. CHANGES.md is the ledger.",
};

if (args.json) {
  console.log(JSON.stringify(payload, null, args.handoff ? 2 : 0));
  process.exit(0);
}

// --brief keeps short items whole and cuts long ones down to their label.
let shortened = 0;
function shown(text) {
  if (!args.brief) return text;
  return String(text)
    .split(/\r?\n/)
    .map((line) => {
      const [, marker = "", body] = line.match(/^(\s*(?:[-*]|\d+\.)\s+)?(.*)$/);
      if (body.length <= 80) return line;
      shortened += 1;
      const label = body.match(/^[^：:]{1,40}(?=：|:\s)/);
      return `${marker}${label ? label[0] : body.slice(0, 40)}…`;
    })
    .join("\n");
}

const D = "─".repeat(52);
let out =`\n${D}\n WePlaning · Read at: ${payload.generatedAt}${args.handoff ? " · HANDOFF" : ""}\n${D}\n`;
out += `\nMemory last updated: ${payload.lastUpdated}\nRecorded state; not a live verification.\n`;

out += `\n📌 Goal:\n${payload.goal}\n`;
if (payload.projectConfig) {
  out += `\n⚙ Project Config:\n${payload.projectConfig}\n`;
}
if (payload.understanding && !isUnknown(payload.understanding)) {
  out += `\n🧭 Current Understanding:\n${shown(payload.understanding)}\n`;
}
out += `\n📊 Current State:\n${shown(payload.currentState)}\n`;

if (payload.focusNextStep) {
  out += `\n🎯 Focus Next Step #${payload.focusNextStep.index}:\n${payload.focusNextStep.text}\n`;
}

out += `\n✅ Accepted Next Steps:\n${nextStepsStatus === "none" ? "No pending tasks." : current.acceptedNextSteps}\n`;
if (nextStepsStatus === "unknown") out += "Next steps are unknown; clarify before continuing.\n";

const hasBlockers = String(payload.blockers || "")
  .split(/\r?\n/)
  .map((line) => line.replace(/^\s*[-*]\s*/, "").trim())
  .filter(Boolean)
  .some((line) => !/^(none|no blockers?|unblocked|无阻塞|没有阻塞|暂无阻塞)\s*[。.]?$/i.test(line));
if (hasBlockers) {
  out += `\n🚧 Blockers:\n${payload.blockers}\n`;
}

if (args.brief) {
  if (shortened) out += `\n${shortened} long item(s) shortened to their label; run a full read before acting on them.\n`;
  out += `\n${D}\n`;
  process.stdout.write(out);
  process.exit(0);
}

out += `\n📋 Recent Changes (newest first, last ${limit}):\n`;
if (recentChanges.length === 0) {
  out += `(no changes yet)\n`;
} else {
  for (const change of recentChanges) {
    out += `## ${change.id}\n`;
    if (change.changed.length) {
      for (const item of change.changed) out += `- ${truncateSummary(item)}\n`;
    } else {
      out += `${truncateSummary(change.body)}\n`;
    }
    if (args.handoff) {
      for (const item of change.verification.filter((value) => !/^(none|无)[。.]?$/i.test(value))) {
        out += `  Verification (recorded): ${item}\n`;
      }
      for (const file of change.files.filter((value) => !/^(none|无)[。.]?$/i.test(value))) out += `  File: ${file}\n`;
    }
    out += `\n`;
  }
}

if (args.full && archives.length > 0) {
  out += `\n🗄 Archive:\n`;
  for (const item of archives) {
    out += `  · ${item.file}${item.count ? `  (${item.count} change blocks)` : ""}\n`;
  }
}

out += `\n${D}\n`;
process.stdout.write(out);
