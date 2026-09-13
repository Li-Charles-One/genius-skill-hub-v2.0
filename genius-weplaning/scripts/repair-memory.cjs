#!/usr/bin/env node

const path = require("path");
const fs = require("fs");
const {
  allowNoCheck,
  emitResult,
  findMemoryConflicts,
  hasSupportedSchema,
  parseArgs,
  runCheck,
  SCHEMA_VERSION,
  usage,
  utcNow,
  validateKnownMarkdown,
  withMemoryLock,
  writeMemory,
} = require("./weplaning-utils.cjs");

const help = `
Usage:
  node repair-memory.cjs <project-root> [options]

Repairs WePlaning 3.0 drift:
  - recreate a missing CHANGES.md header
  - add a missing schema line when CURRENT/CHANGES are structurally valid

Does not rebuild 2.3 session trees. Leftover THREADS.md / sessions/ are ignored.

Options:
  --dry-run    Print intended repairs without writing
  --json
  --no-check   Internal use only
`;

const args = parseArgs(process.argv.slice(2));
usage(!args.help, "", help);
allowNoCheck(args, "repair-memory.cjs");

if (args.prefer) {
  console.error("WePlaning 3.0 repair no longer takes --prefer current|threads (session trees are not truth).");
  process.exit(1);
}

const root = path.resolve(args._[0] || process.cwd());
const now = args.time || utcNow();
const memoryDir = path.join(root, ".agent-memory");
const repairs = [];

if (!fs.existsSync(memoryDir)) {
  console.error("Missing .agent-memory — run init-memory.cjs first.");
  process.exit(1);
}

const currentPath = path.join(memoryDir, "CURRENT.md");
if (!fs.existsSync(currentPath)) {
  console.error("CURRENT.md is missing; refuse to invent accepted state. Run init-memory.cjs.");
  process.exit(1);
}

withMemoryLock(root, () => {
  const conflicts = findMemoryConflicts(root);
  usage(!conflicts.length, `Sync conflict copies found: ${conflicts.join(", ")}. Resolve them before repair.`, help);
  const outputs = [];
  for (const file of ["CURRENT.md", "CHANGES.md"]) {
    const filePath = path.join(memoryDir, file);
    if (!fs.existsSync(filePath)) {
      repairs.push("CHANGES.md recreate missing ledger");
      outputs.push([file, `# Changes\nSchema version: ${SCHEMA_VERSION}\n\n## ${now} repair\n- Agent: repair\n- Change ID: ${now} repair\n- Changed:\n  - Recreated missing CHANGES.md\n- Files touched:\n  - .agent-memory/CHANGES.md\n- Verification:\n  - repair-memory.cjs\n- Notes:\n  - none\n`]);
      continue;
    }
    let text = fs.readFileSync(filePath, "utf8").replace(/\r\n/g, "\n");
    if (!hasSupportedSchema(text)) {
      usage(!/^Schema version:/m.test(text), `${file} has an unsupported schema; refusing to rewrite it.`, help);
      repairs.push(`${file} add Schema version: ${SCHEMA_VERSION}`);
      text = /^#[ \t]+[^\n]*\n/.test(text)
        ? text.replace(/^(#[ \t]+[^\n]*\n)/, (heading) => `${heading}Schema version: ${SCHEMA_VERSION}\n`)
        : `Schema version: ${SCHEMA_VERSION}\n${text}`;
      outputs.push([file, text]);
    }
    validateKnownMarkdown(file, text);
  }
  const decisionsPath = path.join(memoryDir, "DECISIONS.md");
  if (fs.existsSync(decisionsPath)) validateKnownMarkdown("DECISIONS.md", fs.readFileSync(decisionsPath, "utf8"));
  for (const [file, text] of outputs) validateKnownMarkdown(file, text);
  if (args["dry-run"]) return;
  for (const [file, text] of outputs) writeMemory(root, file, text);
  if (!args["no-check"]) runCheck(root, __dirname);
});

if (args["dry-run"]) {
  if (args.json) {
    console.log(JSON.stringify({ ok: true, dryRun: true, repairs }));
  } else if (repairs.length === 0) {
    console.log("No repairs needed.");
  } else {
    repairs.forEach((item) => console.log(item));
  }
  process.exit(0);
}

if (args.json) {
  emitResult(args, repairs.length ? repairs.join("; ") : "No repairs needed.", {
    repairs,
    message: repairs.length ? `Applied ${repairs.length} repair(s).` : "No repairs needed.",
  });
} else if (repairs.length === 0) {
  console.log("No repairs needed.");
} else {
  repairs.forEach((item) => console.log(item));
}
