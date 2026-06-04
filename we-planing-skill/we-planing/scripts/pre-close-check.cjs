#!/usr/bin/env node

const path = require("path");
const {
  allowNoCheck,
  parseArgs,
  readMemory,
  readThreads,
  runCheck,
  usage,
  utcNow,
} = require("./weplaning-utils.cjs");

const help = `
Usage:
  node pre-close-check.cjs <project-root> [options]

Options:
  --session <id>     Current session id. Default: first active, else mainline.
  --fix              Attempt auto-fix for common issues (repair-memory).
  --no-check         Internal use only; external callers must run consistency checks.
`;

const args = parseArgs(process.argv.slice(2));
usage(!args.help, "", help);
allowNoCheck(args, "pre-close-check.cjs");

const root = path.resolve(args._[0] || process.cwd());
const threads = readThreads(root);

const sessionId =
  args.session ||
  (threads.rows.find((r) => r.status === "active") || {}).id ||
  threads.mainline;

const issues = [];
const ok = [];

// 1. Check hard invariants (same as check-memory) ---------------------------------
const mainline = threads.mainline;
const lastMerged = threads.lastMerged;

const currentText = readMemory(root, "CURRENT.md");
const currentMainline = (currentText.match(/^Mainline session:\s*(.+)$/m) || [])[1];

const weplaningText = readMemory(root, "WePlaning.md");
const snapMainline = (weplaningText.match(/^\|\s*Mainline session\s*\|\s*([^|]+)\s*\|/m) || [])[1]?.trim();
const snapActive = (weplaningText.match(/^\|\s*Active sessions\s*\|\s*([^|]+)\s*\|/m) || [])[1]?.trim();
const activeCount = threads.rows.filter((r) => r.status === "active").length;
const mainlineRow = threads.rows.find((r) => r.id === mainline);
const mainlineFileExists = (() => {
  try { readMemory(root, `sessions/${mainline}.md`); return true; }
  catch { return false; }
})();

if (currentMainline !== mainline) {
  issues.push(`CURRENT.md mainline (${currentMainline}) ≠ THREADS.md (${mainline})`);
} else {
  ok.push("CURRENT.md mainline = THREADS.md mainline");
}

if (snapMainline !== mainline) {
  issues.push(`WePlaning.md snapshot mainline (${snapMainline}) ≠ THREADS.md (${mainline})`);
} else {
  ok.push("WePlaning.md snapshot mainline = THREADS.md mainline");
}

if (lastMerged && lastMerged !== mainline) {
  issues.push(`THREADS.md last-merged (${lastMerged}) ≠ mainline (${mainline})`);
} else {
  ok.push("THREADS.md last-merged = mainline");
}

if (mainlineRow) {
  if (mainlineRow.status !== "merged") {
    issues.push(`Mainline session ${mainline} status = ${mainlineRow.status} (should be "merged")`);
  } else {
    ok.push(`Mainline session status = merged`);
  }
} else {
  issues.push(`Mainline session ${mainline} MISSING from THREADS.md row`);
}

if (!mainlineFileExists) {
  issues.push(`Mainline session file sessions/${mainline}.md MISSING`);
} else {
  ok.push("Mainline session file exists");
}

if (String(activeCount) !== String(snapActive)) {
  issues.push(`Active sessions: THREADS.md=${activeCount} WePlaning.md=${snapActive}`);
} else {
  ok.push(`Active sessions count match: ${activeCount}`);
}

// 2. Check TOOLS.md for unknowns -----------------------------------------------
const toolsText = readMemory(root, "TOOLS.md");
const toolSessions = toolsText
  .split("\n")
  .filter((line) => line.startsWith("| ") && line.includes("|"))
  .filter((line) => line.split("|").length >= 7);

for (const row of toolSessions) {
  const cells = row.split("|").slice(1, -1).map((c) => c.trim());
  if (cells.length < 7) continue;
  const [sid, , , , tools, mcp, skills] = cells;
  if (!sid || sid.includes(":--") || sid === "Session ID") continue;
  if (tools === "unknown") {
    issues.push(`TOOLS.md: session ${sid} tools = "unknown"`);
  }
  if (mcp === "unknown") {
    issues.push(`TOOLS.md: session ${sid} MCP = "unknown"`);
  }
  if (skills === "unknown") {
    issues.push(`TOOLS.md: session ${sid} Skills = "unknown"`);
  }
}

// 3. Check CHANGES.md for unknowns ----------------------------------------------
const changesText = readMemory(root, "CHANGES.md");
const changeBlocks = changesText.split("\n## ").filter((b) => b.trim());
for (const block of changeBlocks) {
  if (block.includes("- Files touched:\n  - unknown")) {
    const id = block.split("\n")[0].trim();
    issues.push(`CHANGES.md: entry "${id}" has Files touched: unknown`);
  }
  if (block.includes("- Verification:\n  - unknown")) {
    const id = block.split("\n")[0].trim();
    issues.push(`CHANGES.md: entry "${id}" has Verification: unknown`);
  }
}

// 4. Check CURRENT.md Based On vs mainline -----------------------------------
const basedOnSession = (currentText.match(/Session:\s*(.+)$/m) || [])[1];
if (basedOnSession && basedOnSession !== mainline) {
  issues.push(`CURRENT.md Based-On session (${basedOnSession}) ≠ mainline (${mainline}) from a prior merge?`);
}

// 5. Output -------------------------------------------------------------------
console.log("");
console.log("┌─────────────────────────────────────────────┐");
console.log("│     WePlaning Pre-Close Checklist           │");
console.log("├─────────────────────────────────────────────┤");
if (sessionId) console.log(`│  Session: ${sessionId.padEnd(34)}│`);
console.log(`│  Mainline: ${(mainline || "none").padEnd(32)}│`);
console.log(`│  Active: ${String(activeCount).padEnd(35)}│`);
console.log(`│  Time: ${utcNow().padEnd(36)}│`);
console.log("├─────────────────────────────────────────────┤");

for (const item of ok) {
  console.log(`│  ✅ ${item.slice(0, 40).padEnd(40)}│`);
}
for (const item of issues) {
  console.log(`│  ⚠️  ${item.slice(0, 40).padEnd(40)}│`);
}

const hasIssues = issues.length > 0;
console.log("├─────────────────────────────────────────────┤");
if (hasIssues) {
  console.log(`│  ${String(ok.length).padEnd(2)} passed · ${String(issues.length).padEnd(2)} warnings              │`);
  console.log("├─────────────────────────────────────────────┤");
  console.log("│  Fix actions:                               │");
  console.log("│  1. Fill unknown TOOLS fields               │");
  console.log("│  2. Re-run append-change with --file/--verif│");
  console.log("│  3. Run merge-session or repair-memory      │");
} else {
  console.log("│  All clear — ready to merge                 │");
}
console.log("└─────────────────────────────────────────────┘");
console.log("");

if (args.fix && hasIssues) {
  const { spawnSync } = require("child_process");
  const repairScript = path.join(__dirname, "repair-memory.cjs");
  const result = spawnSync(process.execPath, [repairScript, root], {
    cwd: root,
    encoding: "utf8",
    stdio: "pipe",
  });
  if (result.stdout) process.stdout.write(result.stdout);
  if (result.stderr) process.stderr.write(result.stderr);
  console.log(result.status === 0 ? "[auto-fix] repair-memory complete" : "[auto-fix] repair-memory failed — check above");
}

if (!args["no-check"]) {
  runCheck(root, __dirname);
}

process.exit(hasIssues ? 1 : 0);
