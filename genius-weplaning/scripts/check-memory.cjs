#!/usr/bin/env node

const path = require("path");
const { checkMemory, parseArgs, usage } = require("./weplaning-utils.cjs");

const help = `
Usage:
  node check-memory.cjs <project-root> [--audit] [--strict]

Checks WePlaning 3.0 structural consistency.
  --audit    Warnings (mixed blockers, oversized CURRENT). Exit 0 unless --strict.
  --strict   With --audit: exit 1 when warnings exist.
`;

const args = parseArgs(process.argv.slice(2));
usage(!args.help, "", help);

const root = args._[0] ? path.resolve(args._[0]) : process.cwd();
const { errors, warnings } = checkMemory(root, { audit: Boolean(args.audit) });

if (errors.length > 0) {
  console.error("WePlaning memory check failed:");
  for (const error of errors) console.error(`- ${error}`);
  process.exit(1);
}

for (const warning of warnings) console.error(`[audit] ${warning}`);

if (warnings.length > 0) {
  console.error(`WePlaning memory check passed with ${warnings.length} audit warning(s).`);
  process.exit(args.strict ? 1 : 0);
}

console.log("WePlaning memory check passed.");
