#!/usr/bin/env node

const path = require("path");
const fs = require("fs");
const {
  allowNoCheck,
  emitResult,
  hasSupportedSchema,
  parseArgs,
  parseCurrentMd,
  renderCurrentMd,
  runCheck,
  SCHEMA_VERSION,
  usage,
  utcNow,
  withMemoryLock,
  writeMemory,
} = require("./weplaning-utils.cjs");

const help = `
Usage:
  node repair-memory.cjs <project-root> [options]

Repairs WePlaning 3.0 drift:
  - recreate a missing CHANGES.md header
  - add a supported schema line when CURRENT/CHANGES still parse

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
const changesPath = path.join(memoryDir, "CHANGES.md");

if (!fs.existsSync(currentPath)) {
  console.error("CURRENT.md is missing; refuse to invent accepted state. Run init-memory.cjs.");
  process.exit(1);
}

withMemoryLock(root, () => {
  let currentText = fs.readFileSync(currentPath, "utf8");
  if (!hasSupportedSchema(currentText)) {
    repairs.push(`CURRENT.md add Schema version: ${SCHEMA_VERSION}`);
    if (!/^Schema version:/m.test(currentText)) {
      currentText = currentText.replace(/^(# Current Mainline\n)/, `$1Schema version: ${SCHEMA_VERSION}\n`);
    }
  }

  if (!fs.existsSync(changesPath)) {
    repairs.push("CHANGES.md recreate missing ledger");
    if (!args["dry-run"]) {
      writeMemory(
        root,
        "CHANGES.md",
        `# Changes\nSchema version: ${SCHEMA_VERSION}\n\n## ${now} repair\n- Agent: repair\n- Change ID: ${now} repair\n- Changed:\n  - Recreated missing CHANGES.md\n- Files touched:\n  - .agent-memory/CHANGES.md\n- Verification:\n  - repair-memory.cjs\n- Notes:\n  - none\n`,
      );
    }
  } else {
    let changesText = fs.readFileSync(changesPath, "utf8");
    if (!hasSupportedSchema(changesText)) {
      repairs.push(`CHANGES.md add Schema version: ${SCHEMA_VERSION}`);
      if (!args["dry-run"]) {
        if (!/^Schema version:/m.test(changesText)) {
          changesText = changesText.replace(/^(# Changes\n)?/, `# Changes\nSchema version: ${SCHEMA_VERSION}\n\n`);
        }
        writeMemory(root, "CHANGES.md", changesText);
      }
    }
  }

  if (args["dry-run"]) return;

  if (repairs.some((item) => item.startsWith("CURRENT.md"))) {
    const parsed = parseCurrentMd(currentText);
    parsed.lastUpdated = parsed.lastUpdated === "unknown" ? now : parsed.lastUpdated;
    writeMemory(root, "CURRENT.md", renderCurrentMd(parsed));
  }
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

if (!args["no-check"]) runCheck(root, __dirname);

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
