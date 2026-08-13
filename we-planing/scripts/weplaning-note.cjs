#!/usr/bin/env node
/**
 * weplaning-note.cjs — compatibility wrapper around weplaning-write.cjs
 */

"use strict";

const path = require("path");
const { spawnSync } = require("child_process");
const { defaultAgent, parseArgs, usage } = require("./weplaning-utils.cjs");

const help = `
Usage:
  node weplaning-note.cjs <project-root> "<note>" [options]

Writes a durable fact to the change ledger. Trivial oral notes
(完成了 / done / 搞定) with no --decision are a no-op.

Options:
  --agent <name>
  --decision <text>
  --rationale <text>
  --json
`;

const args = parseArgs(process.argv.slice(2));
usage(!args.help, "", help);

const root = path.resolve(args._[0] || process.cwd());
const note = args._[1];
usage(!!note, "Missing required positional argument: <note>", help);

const agent = args.agent || defaultAgent();
const argv = [path.join(__dirname, "weplaning-write.cjs"), root, "--changed", String(note), "--agent", agent];
if (args.decision) argv.push("--decision", String(args.decision));
if (args.rationale) argv.push("--rationale", String(args.rationale));
if (args.json) argv.push("--json");

const result = spawnSync(process.execPath, argv, { cwd: root, encoding: "utf8" });
if (result.stdout) process.stdout.write(result.stdout);
if (result.stderr) process.stderr.write(result.stderr);
process.exit(result.status || 0);
