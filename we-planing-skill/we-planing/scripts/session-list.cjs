#!/usr/bin/env node

const path = require("path");
const { parseArgs, readThreads, usage } = require("./weplaning-utils.cjs");

const help = `
Usage:
  node session-list.cjs <project-root> [options]

Options:
  --all       Show full session ids
`;

const args = parseArgs(process.argv.slice(2));
usage(!args.help, "", help);

const root = path.resolve(args._[0] || process.cwd());
const threads = readThreads(root);

for (const row of threads.rows) {
  const marker = row.id === threads.mainline ? " <- mainline" : "";
  const id = args.all ? row.id : row.id.split("-").at(-1);
  const role = row.role.padEnd(11);
  const status = row.status.padEnd(9);
  console.log(`${id.padEnd(8)} ${role} ${status} ${row.summary}${marker}`);
}
