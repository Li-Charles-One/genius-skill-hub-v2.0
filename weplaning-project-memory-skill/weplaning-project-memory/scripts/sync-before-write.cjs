#!/usr/bin/env node

const path = require("path");
const {
  extractField,
  parseArgs,
  readMemory,
  readThreads,
  required,
  runCheck,
  usage,
} = require("./weplaning-utils.cjs");

const help = `
Usage:
  node sync-before-write.cjs <project-root> [options]

Options:
  --based-on <id>    Expected current mainline before writing
  --session <id>     Session that intends to write; its Parent session is used when --based-on is omitted
  --no-check         Skip consistency gate
`;

const args = parseArgs(process.argv.slice(2));
usage(!args.help, "", help);

const root = path.resolve(args._[0] || process.cwd());
if (!args["no-check"]) runCheck(root, __dirname);

const threads = readThreads(root);
const current = readMemory(root, "CURRENT.md");
const currentMainline = extractField(current, "Mainline session");
if (currentMainline !== threads.mainline) {
  console.error(`Mainline mismatch before write: CURRENT.md=${currentMainline}, THREADS.md=${threads.mainline}`);
  process.exit(1);
}

let basedOn = args["based-on"];
if (!basedOn && args.session) {
  const sessionPath = path.join(root, ".agent-memory", "sessions", `${args.session}.md`);
  const sessionText = require("fs").readFileSync(sessionPath, "utf8");
  basedOn = extractField(sessionText, "Parent session");
}

if (basedOn && basedOn !== threads.mainline) {
  console.error(`Stale write blocked: based-on=${basedOn}, current mainline=${threads.mainline}`);
  process.exit(1);
}

console.log(threads.mainline);
