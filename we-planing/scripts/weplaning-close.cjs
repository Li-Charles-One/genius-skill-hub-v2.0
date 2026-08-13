#!/usr/bin/env node
/**
 * weplaning-close.cjs — compatibility wrapper around weplaning-write.cjs
 *
 * --file and --verification are optional. Without --state, Current State is left intact.
 */

"use strict";

const path = require("path");
const { spawnSync } = require("child_process");
const { defaultAgent, parseArgs, required, usage } = require("./weplaning-utils.cjs");

const help = `
Usage:
  node weplaning-close.cjs <project-root> --changed <text> [options]

Options:
  --agent <name>
  --changed <text>     Required ledger text
  --file <path>        Optional
  --verification <text> Optional
  --state <text>       Replace Current State
  --next-step <text>
  --blockers <text>
  --understanding <text>
  --goal <text>        Replace Active Goal
  --json
`;

const args = parseArgs(process.argv.slice(2));
usage(!args.help, "", help);

const root = path.resolve(args._[0] || process.cwd());
required(args, "changed", help);

const agent = args.agent || defaultAgent();
const argv = [path.join(__dirname, "weplaning-write.cjs"), root, "--changed", String(args.changed), "--agent", agent];

function pushFlag(name, value) {
  if (value === undefined || value === false) return;
  if (value === true) {
    argv.push(`--${name}`);
    return;
  }
  for (const item of Array.isArray(value) ? value : [value]) {
    argv.push(`--${name}`, String(item));
  }
}

pushFlag("file", args.file || args.files);
pushFlag("verification", args.verification);
pushFlag("note", args.note);
pushFlag("state", args.state);
pushFlag("next-step", args["next-step"]);
pushFlag("blockers", args.blockers);
pushFlag("understanding", args.understanding);
pushFlag("goal", args.goal);
pushFlag("decision", args.decision);
pushFlag("rationale", args.rationale);
if (args.json) argv.push("--json");

const result = spawnSync(process.execPath, argv, { cwd: root, encoding: "utf8" });
if (result.stdout) process.stdout.write(result.stdout);
if (result.stderr) process.stderr.write(result.stderr);
process.exit(result.status || 0);
