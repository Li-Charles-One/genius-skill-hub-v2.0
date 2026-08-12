#!/usr/bin/env node
/**
 * weplaning-read.cjs — One-command session briefing
 *
 * Usage:
 *   node weplaning-read.cjs <project-root> [--handoff] [--json] [--next N] [--limit K]
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
  --handoff     Handoff briefing: highlight next step #1 and truth hierarchy
  --brief       Goal, state, next steps and blockers only (cheap session opener)
  --all         Also list abandoned sessions (hidden by default)
  --json        Machine-readable JSON on stdout
  --next <N>    Focus Accepted Next Steps item N (1-based)
  --limit <K>   Number of recent complete change blocks (default: 5)
`;

const args = parseArgs(process.argv.slice(2));
usage(!args.help, "", help);

const root = path.resolve(args._[0] || process.cwd());
const memDir = path.join(root, ".agent-memory");
const limit = Math.max(1, Number(args.limit || 5) || 5);
const nextN = args.next === undefined || args.next === true ? null : Number(args.next);

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
    const changed = [];
    const changedSection = body.match(/^- Changed:\n((?:  - .+\n?)*)/m);
    if (changedSection) {
      for (const line of changedSection[1].split("\n")) {
        const item = line.match(/^\s+- (.+)$/);
        if (item) changed.push(item[1].trim());
      }
    }
    blocks.push({ id, session, changed, body });
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
const threadsText = readMemory(root, "THREADS.md");
const threads = parseThreads(threadsText);

const changesPath = path.join(memDir, "CHANGES.md");
let recentChanges = [];
if (fs.existsSync(changesPath)) {
  recentChanges = parseChangeBlocks(fs.readFileSync(changesPath, "utf8")).slice(-limit).reverse();
}

// Archived blocks leave CHANGES.md, so surface the archive files or that history
// becomes invisible to every later session.
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

const closedNotes = threads.rows
  .filter((r) => r.status === "closed")
  .slice(-8)
  .reverse();
const activeSessions = threads.rows
  .filter((r) => r.status === "active" || r.status === "paused")
  .slice(-8)
  .reverse();
const otherUnmerged = threads.rows
  .filter((r) => !["merged", "closed", "active", "paused"].includes(r.status))
  .slice(-8)
  .reverse();

const nextSteps = parseNextSteps(current.acceptedNextSteps);
const focusIndex = nextN === null || Number.isNaN(nextN) ? null : Math.trunc(nextN);
const focusNextStep =
  focusIndex && focusIndex >= 1 && focusIndex <= nextSteps.length ? nextSteps[focusIndex - 1] : null;

const truth = {
  order: [
    "merged CURRENT.md (mainline)",
    "closed quick notes (supplemental, not mainline)",
    "active/paused sessions (in progress only)",
  ],
  note: "On conflict, trust mainline CURRENT over notes. Active sessions are not accepted truth.",
};

const payload = {
  ok: true,
  generatedAt: utcNow(),
  handoff: Boolean(args.handoff),
  mainlineSession: current.mainlineSession,
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
  closedNotes: closedNotes.map((r) => ({ id: r.id, summary: r.summary, agent: r.agent })),
  activeSessions: activeSessions.map((r) => ({
    id: r.id,
    summary: r.summary,
    agent: r.agent,
    status: r.status,
  })),
  otherUnmerged: otherUnmerged.map((r) => ({
    id: r.id,
    summary: r.summary,
    status: r.status,
  })),
  recentChanges: recentChanges.map((c) => ({
    id: c.id,
    session: c.session,
    changed: c.changed,
  })),
  archives,
  truth,
};

if (args.json) {
  console.log(JSON.stringify(payload, null, args.handoff ? 2 : 0));
  process.exit(0);
}

const D = "─".repeat(52);
let out = `\n${D}\n WePlaning · ${payload.generatedAt}${args.handoff ? " · HANDOFF" : ""}\n${D}\n`;

out += `\n📌 Goal:\n${payload.goal}\n`;
out += `\n🏷 Mainline session: ${payload.mainlineSession}\n`;
if (payload.projectConfig) {
  out += `\n⚙ Project Config:\n${payload.projectConfig}\n`;
}
out += `\n📊 Current State (mainline — accepted truth):\n${payload.currentState}\n`;

if (payload.focusNextStep) {
  out += `\n🎯 Focus Next Step #${payload.focusNextStep.index}:\n${payload.focusNextStep.text}\n`;
}

out += `\n✅ Accepted Next Steps:\n${current.acceptedNextSteps}\n`;

// "- none" is the schema's own placeholder, so a plain !== "none" test always printed it.
const hasBlockers = String(payload.blockers || "")
  .split(/\r?\n/)
  .map((line) => line.replace(/^\s*[-*]\s*/, "").trim())
  .filter(Boolean)
  .some((line) => !/^(none|unknown|no blockers?|unblocked|无阻塞|没有阻塞|暂无阻塞)\s*[。.]?$/i.test(line));
if (hasBlockers) {
  out += `\n🚧 Blockers:\n${payload.blockers}\n`;
}

if (args.brief) {
  out += `\n⚖ Truth order: mainline CURRENT > closed notes > active sessions.\n${D}\n`;
  process.stdout.write(out);
  process.exit(0);
}

if (closedNotes.length > 0) {
  out += `\n📝 Closed quick notes (supplemental, not mainline):\n`;
  for (const row of closedNotes) {
    out += `  · ${row.id}  ${truncateSummary(row.summary)}\n`;
  }
}

if (activeSessions.length > 0) {
  out += `\n🔧 Active/paused sessions (in progress — not accepted truth):\n`;
  for (const row of activeSessions) {
    out += `  · ${row.id}  [${row.status}]  ${truncateSummary(row.summary)}\n`;
  }
}

if (otherUnmerged.length > 0) {
  if (args.all) {
    out += `\n⚠ Other non-merged sessions:\n`;
    for (const row of otherUnmerged) {
      out += `  · ${row.id}  [${row.status}]  ${truncateSummary(row.summary)}\n`;
    }
  } else {
    // Abandoned work is not truth and never becomes truth; keep it one line.
    out += `\n⚠ ${otherUnmerged.length} abandoned session(s) hidden — pass --all to list them.\n`;
  }
}

out += `\n📋 Recent Changes (complete blocks, newest first):\n`;
if (recentChanges.length === 0) {
  out += `(no changes yet)\n`;
} else {
  for (const change of recentChanges) {
    out += `## ${change.id}\n`;
    if (change.session) out += `- Session: ${change.session}\n`;
    if (change.changed.length) {
      out += `- Changed:\n`;
      for (const item of change.changed) out += `  - ${item}\n`;
    } else {
      out += `${change.body}\n`;
    }
    out += `\n`;
  }
}

if (archives.length > 0) {
  out += `\n🗄 Older history moved to archive/ (read these files directly if needed):\n`;
  for (const item of archives) {
    const unit = item.kind === "changes" ? "change blocks" : "session rows";
    out += `  · ${item.file}${item.count ? `  (${item.count} ${unit})` : ""}\n`;
  }
}

out += `\n⚖ Truth order: mainline CURRENT > closed notes > active sessions.\n`;
out += `${D}\n`;

process.stdout.write(out);
