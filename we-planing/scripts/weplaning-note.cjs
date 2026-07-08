#!/usr/bin/env node
/**
 * weplaning-note.cjs — Quick Lite-flow one-liner
 *
 * Usage:
 *   node weplaning-note.cjs <project-root> "<note>" [options]
 *
 * Replaces the two-step Lite flow (new-session + safe-edit --lite) with a
 * single command. Also auto-closes the session after writing, so sessions
 * don't accumulate as "active" forever.
 *
 * Options:
 *   --agent <name>   Agent name. Default: $WEPLANING_AGENT or "Agent"
 *   --role <role>    Session role. Default: ops
 *   --goal <text>    Session goal. Default: same as <note>
 */

"use strict";

const path = require("path");
const { spawnSync } = require("child_process");
const {
  defaultAgent,
  parseArgs,
  parseSessionMd,
  renderSessionMd,
  readSession,
  writeSession,
  readThreads,
  writeThreads,
  usage,
  utcNow,
  withMemoryLock,
} = require("./weplaning-utils.cjs");

const help = `
Usage:
  node weplaning-note.cjs <project-root> "<note>" [options]

Options:
  --agent <name>   Agent name (default: $WEPLANING_AGENT or "Agent")
  --role <role>    Session role (default: ops)
  --goal <text>    Session goal (default: same as <note>)

Example:
  node weplaning-note.cjs . "genius-vision SKILL.md optimized: 9 fixes, commit abc1234" --agent ZCode
`;

const args = parseArgs(process.argv.slice(2));
usage(!args.help, "", help);

const root = path.resolve(args._[0] || process.cwd());
const note = args._[1];
usage(!!note, "Missing required positional argument: <note>", help);

const agent = args.agent || defaultAgent();
const role = args.role || "ops";
const goal = args.goal || note;
const scriptDir = __dirname;

function run(label, script, argv, internalNoCheck = false) {
  const env = internalNoCheck
    ? { ...process.env, WEPLANING_INTERNAL_NO_CHECK: "1" }
    : process.env;
  const result = spawnSync(process.execPath, [script, ...argv], {
    cwd: root,
    env,
    encoding: "utf8",
    timeout: 30_000,
  });
  if (result.stdout) process.stdout.write(result.stdout);
  if (result.stderr) process.stderr.write(result.stderr);
  if (result.status !== 0) {
    console.error(`\n[weplaning-note] FAILED at step: ${label}`);
    process.exit(result.status || 1);
  }
  return result.stdout.trim();
}

// Step 1: create session — skip check via internal env flag; safe-edit runs pre+post check
const sessionId = run(
  "new-session",
  path.join(scriptDir, "new-session.cjs"),
  [root, "--agent", agent, "--role", role, "--summary", note, "--goal", goal, "--no-check"],
  true // WEPLANING_INTERNAL_NO_CHECK=1
);

// Step 2: write note + run pre/post consistency check
run(
  "safe-edit --lite",
  path.join(scriptDir, "safe-edit.cjs"),
  [root, "--lite", "--session", sessionId, "--changed", note]
);

// Step 3: auto-close session — prevents active session accumulation
withMemoryLock(root, () => {
  const sessionText = readSession(root, sessionId);
  const session = parseSessionMd(sessionText);
  session.status = "closed";
  session.closed = utcNow();
  writeSession(root, sessionId, renderSessionMd(session));

  const threads = readThreads(root);
  const row = threads.rows.find((r) => r.id === sessionId);
  if (row) row.status = "closed";
  writeThreads(root, threads, utcNow());
});

console.log(`\n[weplaning-note] Done. Session: ${sessionId}`);
