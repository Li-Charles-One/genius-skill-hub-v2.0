#!/usr/bin/env node
/**
 * weplaning-close.cjs — one-command mainline closeout
 *
 * Creates a session if --session is omitted, then runs safe-edit --close.
 * Defaults to --no-sync so curated CURRENT.md Current State is not replaced
 * by --changed. Pass --state / --replace-state / other CURRENT flags to sync.
 */

"use strict";

const path = require("path");
const { spawnSync } = require("child_process");
const { defaultAgent, emitResult, parseArgs, required, usage } = require("./weplaning-utils.cjs");

const help = `
Usage:
  node weplaning-close.cjs <project-root> --changed <text> --file <path> --verification <text> [options]

Options:
  --session <id>       Existing session. If omitted, create one from --changed
  --agent <name>       Agent name (default: $WEPLANING_AGENT or inferred)
  --role <role>        Session role when creating (default: ops)
  --goal <text>        Session goal when creating (default: --changed). Does not rewrite CURRENT Active Goal
  --changed <text>     Required. Change description (+ session Result)
  --file <path>        Required. Repeatable or ";;" separated
  --verification <text> Required. Repeatable or ";;" separated
  --note <text>        Extra work notes
  --state <text>       Replace CURRENT Current State (";;" bullets)
  --next-step <text>   Replace CURRENT Accepted Next Steps
  --blockers <text>    Replace CURRENT Open Blockers
  --understanding <text> Replace CURRENT Current Understanding
  --replace-state      Allow --changed to overwrite curated Current State
  --no-sync            Leave CURRENT.md prose untouched (default when no sync flags)
  --json               Machine-readable JSON on stdout
`;

const args = parseArgs(process.argv.slice(2));
usage(!args.help, "", help);

const root = path.resolve(args._[0] || process.cwd());
required(args, "changed", help);
if (!(args.file || args.files)) usage(false, "Missing required argument: --file", help);
if (!args.verification) usage(false, "Missing required argument: --verification", help);

const agent = args.agent || defaultAgent();
const role = args.role || "ops";
const goal = args.goal || args.changed;
const scriptDir = __dirname;

const hasSyncFlags = Boolean(
  args.state || args["next-step"] || args.blockers || args.understanding || args["replace-state"],
);
if (args["no-sync"] && hasSyncFlags) {
  usage(false, "Conflicting flags: --no-sync cannot be combined with CURRENT.md sync flags", help);
}

function run(label, script, argv, internalNoCheck = false) {
  const env = internalNoCheck
    ? { ...process.env, WEPLANING_INTERNAL_NO_CHECK: "1" }
    : process.env;
  const result = spawnSync(process.execPath, [script, ...argv], {
    cwd: root,
    env,
    encoding: "utf8",
    timeout: 60_000,
  });
  if (result.stdout) process.stderr.write(result.stdout);
  if (result.stderr) process.stderr.write(result.stderr);
  if (result.status !== 0) {
    console.error(`\n[weplaning-close] FAILED at step: ${label}`);
    process.exit(result.status || 1);
  }
  return result.stdout.trim().split(/\r?\n/).filter(Boolean).at(-1) || "";
}

function pushFlag(argv, name, value) {
  if (value === undefined || value === false) return;
  if (value === true) {
    argv.push(`--${name}`);
    return;
  }
  for (const item of Array.isArray(value) ? value : [value]) {
    argv.push(`--${name}`, String(item));
  }
}

let sessionId = args.session && args.session !== true ? String(args.session) : "";
if (!sessionId) {
  sessionId = run(
    "new-session",
    path.join(scriptDir, "new-session.cjs"),
    [root, "--agent", agent, "--role", role, "--summary", String(args.changed), "--goal", String(goal), "--no-check"],
    true,
  );
}

const closeArgv = [root, "--close", "--session", sessionId, "--changed", String(args.changed)];
pushFlag(closeArgv, "file", args.file || args.files);
pushFlag(closeArgv, "verification", args.verification);
pushFlag(closeArgv, "note", args.note);
pushFlag(closeArgv, "state", args.state);
pushFlag(closeArgv, "next-step", args["next-step"]);
pushFlag(closeArgv, "blockers", args.blockers);
pushFlag(closeArgv, "understanding", args.understanding);
if (args["replace-state"]) closeArgv.push("--replace-state");
if (!hasSyncFlags) closeArgv.push("--no-sync");

run("safe-edit --close", path.join(scriptDir, "safe-edit.cjs"), closeArgv);

emitResult(args, sessionId, {
  sessionId,
  changed: args.changed,
  synced: hasSyncFlags,
  message: `weplaning-close done: ${sessionId}`,
});
