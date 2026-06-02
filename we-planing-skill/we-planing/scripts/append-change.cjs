#!/usr/bin/env node

const path = require("path");
const {
  compactTimestamp,
  extractField,
  parseArgs,
  readMemory,
  readSession,
  readThreads,
  required,
  runCheck,
  toList,
  usage,
  utcNow,
  writeMemory,
} = require("./weplaning-utils.cjs");

const help = `
Usage:
  node append-change.cjs <project-root> --session <id> --changed <text> [options]

Options:
  --agent <name>          Defaults to session Agent field
  --role <role>           Defaults to session Role field
  --based-on <id>         Defaults to session Parent session field
  --change-id <id>        Defaults to "<now> <short>"
  --changed <text>        Repeat or separate with ";;"
  --file <path>           Repeat or separate with ";;"
  --verification <text>   Repeat or separate with ";;"
  --note <text>           Repeat or separate with ";;"
  --no-check              Skip consistency check
`;

const args = parseArgs(process.argv.slice(2));
usage(!args.help, "", help);

const root = path.resolve(args._[0] || process.cwd());
const sessionId = required(args, "session", help);
const changed = toList(required(args, "changed", help));
const sessionText = readSession(root, sessionId);
const threads = readThreads(root);
const agent = args.agent || extractField(sessionText, "Agent") || "unknown";
const role = args.role || extractField(sessionText, "Role") || "unknown";
const basedOn =
  args["based-on"] ||
  threads.mainline ||
  extractField(sessionText, "Parent session") ||
  "unknown";
const now = args.time || utcNow();
const short = args.short || "change";
const changeId = args["change-id"] || `${now} ${short}`;
const files = toList(args.file || args.files);
const verification = toList(args.verification);
const notes = toList(args.note);

function list(items, fallback) {
  const values = items.length ? items : [fallback];
  return values.map((item) => `  - ${item}`).join("\n");
}

if (!files.length) {
  console.warn("Warning: --file not provided. CHANGES.md entry will show Files touched: unknown.");
  console.warn("  Tip: node append-change.cjs ... --file path/to/file1 --file path/to/file2");
}
if (!verification.length) {
  console.warn("Warning: --verification not provided. CHANGES.md entry will show Verification: unknown.");
  console.warn("  Tip: node append-change.cjs ... --verification \"ls -la backup/\"");
}

const entry = `
## ${changeId}
- Session: ${sessionId}
- Agent: ${agent}
- Role: ${role}
- Based on: ${basedOn}
- Change ID: ${changeId}
- Changed:
${list(changed, "unknown")}
- Files touched:
${list(files, "unknown")}
- Verification:
${list(verification, "unknown")}
- Notes:
${list(notes, "none")}
`;

const current = readMemory(root, "CHANGES.md").replace(/\s*$/, "\n");
writeMemory(root, "CHANGES.md", `${current}${entry}`);

if (!args["no-check"]) runCheck(root, __dirname);
console.log(compactTimestamp(now));
