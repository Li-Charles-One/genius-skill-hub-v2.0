#!/usr/bin/env node

const fs = require("fs");
const path = require("path");
const { spawnSync } = require("child_process");
const {
  compactTimestamp,
  parseArgs,
  required,
  usage,
  utcNow,
} = require("./weplaning-utils.cjs");

const help = `
Usage:
  node safe-edit.cjs <project-root> --session <id> --changed <text> [options]

Runs the full closeout pipeline in one atomic call:
  sync-before-write → check-memory(pre) → append-change → merge-session → check-memory(post)

Options:
  --session <id>        Required. Session to close and merge.
  --changed <text>      Required. Change description (same as append-change.cjs).
  --file <path>         Repeatable or ";;" separated. Files touched.
  --verification <text> Repeatable or ";;" separated. Verification steps.
  --note <text>         Repeatable or ";;" separated. Notes.
  --no-merge            Skip merge-session step (only append change, no mainline update).
  --dry-run             Print steps without executing.
`;

const args = parseArgs(process.argv.slice(2));
usage(!args.help, "", help);

const root = path.resolve(args._[0] || process.cwd());
const sessionId = required(args, "session", help);
const changed = required(args, "changed", help);

function runStep(label, command, argv) {
  if (args["dry-run"]) {
    console.log(`[DRY-RUN] ${label}: ${command} ${argv.join(" ")}`);
    return { ok: true, output: "(dry-run)" };
  }
  process.stderr.write(`\n▶ ${label}...\n`);
  const result = spawnSync(process.execPath, [command, ...argv], {
    cwd: root,
    encoding: "utf8",
    timeout: 30_000,
  });
  const out = (result.stdout || "").trim();
  const err = (result.stderr || "").trim();
  if (out) process.stderr.write(out + "\n");
  if (err) process.stderr.write(err + "\n");
  const ok = result.status === 0;
  const statusIcon = ok ? "✅" : "❌";
  const combined = [out, err].filter(Boolean).join("\n");
  console.log(`${statusIcon} ${label} — ${ok ? "OK" : `FAILED (exit ${result.status})`}`);
  return { ok, output: combined };
}

const scriptDir = __dirname;

// Step 1: sync-before-write
const syncResult = runStep("sync-before-write", path.join(scriptDir, "sync-before-write.cjs"), [
  root,
  "--session", sessionId,
  "--no-check",
]);
if (!syncResult.ok) {
  console.error("❌ Pipeline aborted: sync-before-write failed. Fix the session parent / mainline mismatch first.");
  process.exit(1);
}

// Step 2: check-memory (pre)
const preCheckResult = runStep("check-memory (pre)", path.join(scriptDir, "check-memory.cjs"), [root]);
if (!preCheckResult.ok) {
  console.error("❌ Pipeline aborted: pre-check failed. Run repair-memory.cjs first.");
  process.exit(1);
}

// Step 3: append-change (with --no-check to avoid nested check)
const appendArgv = [
  root,
  "--session", sessionId,
  "--changed", changed,
  "--no-check",
];
const files = args.file || args.files;
if (files) {
  const values = Array.isArray(files) ? files : [files];
  for (const v of values) appendArgv.push("--file", v);
}
const verification = args.verification;
if (verification) {
  const values = Array.isArray(verification) ? verification : [verification];
  for (const v of values) appendArgv.push("--verification", v);
}
const notes = args.note;
if (notes) {
  const values = Array.isArray(notes) ? notes : [notes];
  for (const v of values) appendArgv.push("--note", v);
}

const appendResult = runStep("append-change", path.join(scriptDir, "append-change.cjs"), appendArgv);
if (!appendResult.ok) {
  console.error("❌ Pipeline aborted: append-change failed.");
  process.exit(1);
}

// Step 4: merge-session (unless --no-merge)
if (!args["no-merge"]) {
  const mergeResult = runStep("merge-session", path.join(scriptDir, "merge-session.cjs"), [
    root,
    "--session", sessionId,
    "--no-check",
  ]);
  if (!mergeResult.ok) {
    console.error("❌ Pipeline aborted: merge-session failed.");
    process.exit(1);
  }
} else {
  console.log("⏭️  merge-session — SKIPPED (--no-merge)");
}

// Step 5: check-memory (post)
const postCheckResult = runStep("check-memory (post)", path.join(scriptDir, "check-memory.cjs"), [root]);
if (!postCheckResult.ok) {
  console.error("❌ Pipeline aborted: post-check failed. Run repair-memory.cjs to fix.");
  process.exit(1);
}

console.log("\n🎉 safe-edit pipeline completed successfully.");
process.exit(0);
