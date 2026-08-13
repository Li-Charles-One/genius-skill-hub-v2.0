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
  parseThreads,
  readMemory,
  truncateSummary,
  usage,
  utcNow,
} = require("./weplaning-utils.cjs");

const help = `
Usage:
  node weplaning-read.cjs <project-root> [options]

Options:
  --handoff     Highlight next step #1
  --brief       Goal, state, next steps and blockers only
  --full        Also list leftover 2.3 sessions and archive files
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
const nextN = args.next === undefined || args.next === true ? null : Number(args.next);

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
    const session = (body.match(/^- Session:\s*(.+)$/m) || [])[1]?.trim() || null;
    const agent = (body.match(/^- Agent:\s*(.+)$/m) || [])[1]?.trim() || null;
    const changed = [];
    const changedSection = body.match(/^- Changed:\n((?:  - .+\n?)*)/m);
    if (changedSection) {
      for (const line of changedSection[1].split("\n")) {
        const item = line.match(/^\s+- (.+)$/);
        if (item) changed.push(item[1].trim());
      }
    }
    blocks.push({ id, session, agent, changed, body });
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

const currentText = readMemory(root, "CURRENT.md");
const current = parseCurrentMd(currentText);

let threads = { rows: [], mainline: null };
const threadsPath = path.join(memDir, "THREADS.md");
if (fs.existsSync(threadsPath)) {
  threads = parseThreads(fs.readFileSync(threadsPath, "utf8"));
}

const changesPath = path.join(memDir, "CHANGES.md");
let recentChanges = [];
if (fs.existsSync(changesPath)) {
  recentChanges = parseChangeBlocks(fs.readFileSync(changesPath, "utf8")).slice(-limit).reverse();
}

const archiveDir = path.join(memDir, "archive");
const archives = fs.existsSync(archiveDir)
  ? fs
      .readdirSync(archiveDir)
      .filter((name) => /^(CHANGES|THREADS)-.*\.md$/.test(name))
      .sort()
      .reverse()
      .map((name) => {
        const text = fs.readFileSync(path.join(archiveDir, name), "utf8");
        const count = Number((text.match(/^(?:Blocks|Rows):\s*(\d+)$/m) || [])[1] || 0);
        return { file: `archive/${name}`, kind: name.startsWith("CHANGES") ? "changes" : "threads", count };
      })
  : [];

const closedNotes = threads.rows.filter((r) => r.status === "closed").slice(-8).reverse();
const activeSessions = threads.rows.filter((r) => r.status === "active" || r.status === "paused").slice(-8).reverse();

const nextSteps = parseNextSteps(current.acceptedNextSteps);
const focusIndex = nextN === null || Number.isNaN(nextN) ? null : Math.trunc(nextN);
const focusNextStep =
  focusIndex && focusIndex >= 1 && focusIndex <= nextSteps.length ? nextSteps[focusIndex - 1] : null;

const payload = {
  ok: true,
  generatedAt: utcNow(),
  schema: current.schemaVersion,
  handoff: Boolean(args.handoff),
  goal: current.activeGoal,
  currentState: current.currentState,
  understanding: current.currentUnderstanding,
  projectConfig: current.projectConfig || "",
  nextSteps,
  focusNextStep: focusNextStep
    ? { index: focusIndex, text: focusNextStep }
    : args.handoff && nextSteps[0]
      ? { index: 1, text: nextSteps[0] }
      : null,
  blockers: current.openBlockers,
  recentChanges: recentChanges.map((c) => ({
    id: c.id,
    agent: c.agent,
    changed: c.changed,
  })),
  archives,
  leftoverSessions: {
    closed: closedNotes.map((r) => ({ id: r.id, summary: r.summary, agent: r.agent })),
    active: activeSessions.map((r) => ({ id: r.id, summary: r.summary, status: r.status })),
  },
  truth: "CURRENT.md is accepted truth. CHANGES.md is the ledger. Leftover 2.3 sessions are not truth.",
};

if (args.json) {
  console.log(JSON.stringify(payload, null, args.handoff ? 2 : 0));
  process.exit(0);
}

const D = "─".repeat(52);
let out = `\n${D}\n WePlaning · ${payload.generatedAt}${args.handoff ? " · HANDOFF" : ""}\n${D}\n`;

out += `\n📌 Goal:\n${payload.goal}\n`;
if (payload.projectConfig) {
  out += `\n⚙ Project Config:\n${payload.projectConfig}\n`;
}
out += `\n📊 Current State:\n${payload.currentState}\n`;

if (payload.focusNextStep) {
  out += `\n🎯 Focus Next Step #${payload.focusNextStep.index}:\n${payload.focusNextStep.text}\n`;
}

out += `\n✅ Accepted Next Steps:\n${current.acceptedNextSteps}\n`;

const hasBlockers = String(payload.blockers || "")
  .split(/\r?\n/)
  .map((line) => line.replace(/^\s*[-*]\s*/, "").trim())
  .filter(Boolean)
  .some((line) => !/^(none|unknown|no blockers?|unblocked|无阻塞|没有阻塞|暂无阻塞)\s*[。.]?$/i.test(line));
if (hasBlockers) {
  out += `\n🚧 Blockers:\n${payload.blockers}\n`;
}

if (args.brief) {
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
    out += `\n`;
  }
}

if (args.full) {
  if (closedNotes.length > 0) {
    out += `\n📝 Leftover 2.3 closed notes (not truth):\n`;
    for (const row of closedNotes) {
      out += `  · ${row.id}  ${truncateSummary(row.summary)}\n`;
    }
  }
  if (activeSessions.length > 0) {
    out += `\n🔧 Leftover 2.3 active sessions (not truth):\n`;
    for (const row of activeSessions) {
      out += `  · ${row.id}  [${row.status}]  ${truncateSummary(row.summary)}\n`;
    }
  }
  if (archives.length > 0) {
    out += `\n🗄 Archive:\n`;
    for (const item of archives) {
      const unit = item.kind === "changes" ? "change blocks" : "session rows";
      out += `  · ${item.file}${item.count ? `  (${item.count} ${unit})` : ""}\n`;
    }
  }
}

out += `\n${D}\n`;
process.stdout.write(out);
