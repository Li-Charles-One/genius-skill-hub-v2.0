#!/usr/bin/env node

const path = require("path");
const {
  parseArgs,
  readMemory,
  readSession,
  readThreads,
  section,
  usage,
} = require("./weplaning-utils.cjs");

const help = `
Usage:
  node audit-memory.cjs <project-root>

Audits semantic WePlaning drift that can pass structural consistency checks.
This script is read-only.
`;

const args = parseArgs(process.argv.slice(2));
usage(!args.help, "", help);

const root = path.resolve(args._[0] || process.cwd());
const findings = [];
const ok = [];

function snapshotValue(text, key) {
  const escaped = key.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const match = text.match(new RegExp(`^\\|\\s*${escaped}\\s*\\|\\s*([^|]+?)\\s*\\|`, "m"));
  return match ? match[1].trim() : "";
}

function hasNoBlockerPhrase(text) {
  return /(^|\n|\s)(none|no blockers?|unblocked|无阻塞|没有阻塞|暂无阻塞)(\.|。|\s|$)/i.test(text);
}

function hasRealBlocker(text) {
  const normalized = text.trim();
  if (!normalized) return false;
  if (/^(none|unknown|unavailable|无阻塞|没有阻塞|暂无阻塞)[。.\s]*$/i.test(normalized)) return false;
  return true;
}

function addFinding(message) {
  findings.push(message);
}

const threads = readThreads(root);
const currentText = readMemory(root, "CURRENT.md");
const weplaningText = readMemory(root, "WePlaning.md");

const blockerSnapshot = snapshotValue(weplaningText, "Blocker") || "unknown";
const openBlockers = section(currentText, "Open Blockers") || "";
const basedOnSession = (section(currentText, "Based On").match(/^- Session:\s*(.+)$/m) || [])[1]?.trim();

if (hasNoBlockerPhrase(blockerSnapshot) && hasRealBlocker(openBlockers)) {
  addFinding("WePlaning.md Blocker says none, but CURRENT.md Open Blockers contains a real blocker.");
} else {
  ok.push("Blocker snapshot does not contradict CURRENT.md Open Blockers");
}

if (hasRealBlocker(openBlockers) && hasNoBlockerPhrase(openBlockers)) {
  addFinding("CURRENT.md Open Blockers mixes a real blocker with a no-blocker phrase.");
} else {
  ok.push("CURRENT.md Open Blockers has no internal no-blocker contradiction");
}

if (basedOnSession && basedOnSession !== threads.mainline) {
  addFinding(`CURRENT.md Based On session (${basedOnSession}) differs from mainline (${threads.mainline}).`);
} else {
  ok.push("CURRENT.md Based On points at the current mainline");
}

const mainlineSessionText = readSession(root, threads.mainline);
const result = section(mainlineSessionText, "Result").trim();
const nextStep = section(mainlineSessionText, "Exact Next Step").trim();
if (/^(Session opened\.?|unknown)$/i.test(result)) {
  addFinding(`Mainline session ${threads.mainline} has placeholder Result: ${result || "empty"}.`);
} else {
  ok.push("Mainline session Result is not a placeholder");
}
if (/^unknown$/i.test(nextStep)) {
  addFinding(`Mainline session ${threads.mainline} has placeholder Exact Next Step.`);
} else {
  ok.push("Mainline session Exact Next Step is not a placeholder");
}

const toolsText = readMemory(root, "TOOLS.md");
for (const line of toolsText.split(/\r?\n/)) {
  if (!line.startsWith("| ") || line.includes(":--")) continue;
  const cells = line.split("|").slice(1, -1).map((cell) => cell.trim());
  if (cells.length < 7 || cells[0] === "Session ID") continue;
  const [sessionId, , , , tools, mcp, skills] = cells;
  if (tools === "unknown" || mcp === "unknown" || skills === "unknown") {
    addFinding(`TOOLS.md session ${sessionId} still has unknown capability fields.`);
  }
}
if (!findings.some((item) => item.startsWith("TOOLS.md session "))) {
  ok.push("TOOLS.md has no unknown capability fields");
}

console.log("");
console.log("WePlaning semantic audit");
console.log(`Project: ${root}`);
console.log(`Mainline: ${threads.mainline || "unknown"}`);
console.log("");

for (const item of ok) console.log(`[ok] ${item}`);
for (const item of findings) console.log(`[warn] ${item}`);

if (findings.length > 0) {
  console.log("");
  console.log(`WePlaning semantic audit found ${findings.length} warning(s).`);
  process.exit(1);
}

console.log("");
console.log("WePlaning semantic audit passed.");
