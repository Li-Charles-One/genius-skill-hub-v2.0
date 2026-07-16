#!/usr/bin/env node

const fs = require("fs");
const path = require("path");
const {
  emitResult,
  parseArgs,
  readMemory,
  usage,
  utcNow,
  withMemoryLock,
  writeMemory,
} = require("./weplaning-utils.cjs");

const help = `
Usage:
  node archive-changes.cjs <project-root> [options]

Moves older CHANGES.md blocks into .agent-memory/archive/, keeping the newest N.

Options:
  --keep <N>     Number of newest complete change blocks to keep (default: 30)
  --dry-run      Print plan without writing
  --json         Machine-readable JSON on stdout
`;

const args = parseArgs(process.argv.slice(2));
usage(!args.help, "", help);

const root = path.resolve(args._[0] || process.cwd());
const keep = Math.max(1, Number(args.keep || 30) || 30);
const now = utcNow();

function splitBlocks(text) {
  const normalized = text.replace(/\r?\n/g, "\n");
  const headerMatch = normalized.match(/^([\s\S]*?)(?=\n## |$)/);
  const header = (headerMatch ? headerMatch[1] : "# Changes\nSchema version: 2.3\n").replace(/\s*$/, "");
  const rest = normalized.slice(header.length).replace(/^\n+/, "");
  if (!rest.trim()) return { header, blocks: [] };
  const parts = rest.split(/\n(?=## )/).filter((part) => part.trim());
  return { header, blocks: parts };
}

let archived = 0;
let kept = 0;
let archivePath = null;

withMemoryLock(root, () => {
  const changes = readMemory(root, "CHANGES.md");
  const { header, blocks } = splitBlocks(changes);
  kept = Math.min(keep, blocks.length);
  archived = Math.max(0, blocks.length - keep);
  if (archived === 0) return;

  const toArchive = blocks.slice(0, blocks.length - keep);
  const toKeep = blocks.slice(blocks.length - keep);
  const stamp = now.replace(/[:.]/g, "").slice(0, 15);
  archivePath = path.join(root, ".agent-memory", "archive", `CHANGES-${stamp}.md`);

  if (args["dry-run"]) return;

  fs.mkdirSync(path.dirname(archivePath), { recursive: true });
  const archiveBody = `# Archived Changes
Schema version: 2.3
Archived at: ${now}
Source: CHANGES.md
Blocks: ${toArchive.length}

${toArchive.join("\n").replace(/\s*$/, "")}
`;
  fs.writeFileSync(archivePath, archiveBody.replace(/\r?\n/g, "\n"), "utf8");

  const nextChanges = `${header}\n\n${toKeep.join("\n").replace(/\s*$/, "")}\n`;
  writeMemory(root, "CHANGES.md", nextChanges);
});

if (args["dry-run"]) {
  emitResult(args, archived ? `Would archive ${archived} block(s), keep ${kept}` : "Nothing to archive", {
    dryRun: true,
    archived,
    kept,
    archivePath,
  });
  process.exit(0);
}

emitResult(args, archived ? `Archived ${archived} block(s), kept ${kept}` : "Nothing to archive", {
  archived,
  kept,
  archivePath,
});
