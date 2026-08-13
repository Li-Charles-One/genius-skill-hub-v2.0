#!/usr/bin/env node

const fs = require("fs");
const os = require("os");
const path = require("path");
const { spawnSync } = require("child_process");

const repoRoot = path.resolve(__dirname, "..", "..");
const skillRoot = path.resolve(__dirname, "..");
const scripts = path.join(skillRoot, "scripts");

function run(args, options = {}) {
  const result = spawnSync(process.execPath, args, {
    cwd: repoRoot,
    encoding: "utf8",
    ...options,
  });
  if (options.expectFail) {
    if (result.status === 0) {
      throw new Error(`Expected failure: node ${args.join(" ")}\n${result.stdout}${result.stderr}`);
    }
    return result;
  }
  if (result.status !== 0) {
    throw new Error(`Command failed: node ${args.join(" ")}\n${result.stdout}${result.stderr}`);
  }
  return result;
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

function tempRoot(name) {
  return fs.mkdtempSync(path.join(os.tmpdir(), `weplaning-${name}-`));
}

function script(name) {
  return path.join(scripts, name);
}

function init(root) {
  const result = run([
    script("init-memory.cjs"),
    root,
    "--project",
    "Smoke",
    "--goal",
    "Validate WePlaning 3.0",
    "--agent",
    "CI",
    "--started",
    "2026-06-06T00:00:00Z",
  ]);
  return result.stdout.trim().split(/\r?\n/).at(-1);
}

function read(root, relativePath) {
  return fs.readFileSync(path.join(root, ".agent-memory", relativePath), "utf8");
}

function write(root, relativePath, text) {
  fs.writeFileSync(path.join(root, ".agent-memory", relativePath), text, "utf8");
}

function writeCmd(root, extra) {
  return run([script("weplaning-write.cjs"), root, "--agent", "CI", ...extra]);
}

function seedLegacy23(root) {
  fs.mkdirSync(path.join(root, ".agent-memory", "sessions"), { recursive: true });
  write(
    root,
    "CURRENT.md",
    `# Current Mainline
Schema version: 2.3
Last updated: 2026-06-06T00:00:00Z
Mainline session: 20260606T0000-ci-root

## Active Goal
Legacy goal

## Current Understanding
legacy

## Current State
- Fact keep me

## Accepted Next Steps
1. Stay compatible

## Open Blockers
- none

## Based On
- Session: 20260606T0000-ci-root
- Last change: 2026-06-06T00:00:00Z init
`,
  );
  write(
    root,
    "THREADS.md",
    `# Threads
Schema version: 2.3
Last updated: 2026-06-06T00:00:00Z

Mainline session: 20260606T0000-ci-root
Last merged session: 20260606T0000-ci-root

## Session Tree

| Session ID | Parent | Agent | OS | Role | Status | Summary |
|:--|:--|:--|:--|:--|:--|:--|
| 20260606T0000-ci-root | root | CI | linux | creator | merged | Bootstrap |
`,
  );
  write(
    root,
    "CHANGES.md",
    `# Changes
Schema version: 2.3

## 2026-06-06T00:00:00Z init
- Session: 20260606T0000-ci-root
- Changed:
  - Bootstrapped
`,
  );
  write(
    root,
    path.join("sessions", "20260606T0000-ci-root.md"),
    `# Session 20260606T0000-ci-root

Schema version: 2.3
Session ID: 20260606T0000-ci-root
Agent: CI
Adapter: Smoke
OS: linux
Role: creator
Parent session: root
Status: merged
Started: 2026-06-06T00:00:00Z
Closed: 2026-06-06T00:00:00Z

## Goal
g

## Context Read
- x

## Work Notes
- y

## Files Touched
- z

## Decisions
- none yet

## Result
ok

## Exact Next Step
next
`,
  );
}

function testInitShape() {
  const root = tempRoot("init");
  const line = init(root);
  assert(line === "initialized", `init stdout was ${line}`);
  assert(fs.existsSync(path.join(root, ".agent-memory", "CURRENT.md")), "CURRENT.md missing");
  assert(fs.existsSync(path.join(root, ".agent-memory", "CHANGES.md")), "CHANGES.md missing");
  assert(fs.existsSync(path.join(root, ".agent-memory", "DECISIONS.md")), "DECISIONS.md missing");
  assert(!fs.existsSync(path.join(root, ".agent-memory", "THREADS.md")), "init must not create THREADS.md");
  assert(!fs.existsSync(path.join(root, ".agent-memory", "sessions")), "init must not create sessions/");
  assert(!fs.existsSync(path.join(root, ".agent-memory", "WePlaning.md")), "init should not create WePlaning.md");
  const current = read(root, "CURRENT.md");
  assert(current.includes("Schema version: 3.0"), "CURRENT schema is not 3.0");
  assert(!/^Mainline session:/m.test(current), "CURRENT still has Mainline session");
  run([script("check-memory.cjs"), root]);
}

function testWritePatchesAndLedger() {
  const root = tempRoot("write");
  init(root);
  writeCmd(root, [
    "--changed", "shipped A",
    "--state", "A done;;B next",
    "--next-step", "Ship B",
    "--file", "a.ts",
    "--verification", "smoke",
  ]);
  const current = read(root, "CURRENT.md");
  assert(current.includes("A done"), "write --state did not write Current State");
  assert(current.includes("Ship B"), "write --next-step did not write next steps");
  assert(read(root, "CHANGES.md").includes("shipped A"), "ledger missed --changed");
  run([script("check-memory.cjs"), root]);
}

function testWriteDoesNotClobberState() {
  const root = tempRoot("noclobber");
  init(root);
  writeCmd(root, ["--changed", "seed", "--state", "Fact A;;Fact B;;Fact C"]);
  writeCmd(root, ["--changed", "later work"]);
  const after = read(root, "CURRENT.md");
  assert(after.includes("Fact A") && after.includes("Fact C"), "ledger-only write clobbered Current State");
  assert(read(root, "CHANGES.md").includes("later work"), "second write missed ledger");
}

function testTrivialNoteNoop() {
  const root = tempRoot("noop");
  init(root);
  const beforeChanges = read(root, "CHANGES.md");
  const beforeCurrent = read(root, "CURRENT.md");
  const result = run([script("weplaning-note.cjs"), root, "完成了", "--agent", "CI"]);
  assert(result.stdout.includes("nothing-to-persist"), "trivial note should no-op");
  assert(read(root, "CHANGES.md") === beforeChanges, "trivial note mutated CHANGES.md");
  assert(read(root, "CURRENT.md") === beforeCurrent, "trivial note mutated CURRENT.md");
}

function testDurableNote() {
  const root = tempRoot("note");
  init(root);
  run([script("weplaning-note.cjs"), root, "us-one Hy2 recovered", "--agent", "CI"]);
  assert(read(root, "CHANGES.md").includes("us-one Hy2 recovered"), "note wrapper did not append ledger");
  assert(!fs.existsSync(path.join(root, ".agent-memory", "THREADS.md")), "note created a session tree");
}

function testLegacy23CheckPasses() {
  const root = tempRoot("legacy23");
  fs.mkdirSync(path.join(root, ".agent-memory"), { recursive: true });
  seedLegacy23(root);
  run([script("check-memory.cjs"), root]);
  write(
    root,
    "CURRENT.md",
    read(root, "CURRENT.md").replace(/^Mainline session:\s*.+$/m, "Mainline session: bogus"),
  );
  run([script("check-memory.cjs"), root]);
}

function testLegacyWePlaningIgnored() {
  const root = tempRoot("legacy");
  init(root);
  fs.writeFileSync(path.join(root, ".agent-memory", "WePlaning.md"), "legacy stale content\n", "utf8");
  run([script("check-memory.cjs"), root]);
}

function testWriteUpgradesSchemaKeepsState() {
  const root = tempRoot("upgrade");
  fs.mkdirSync(path.join(root, ".agent-memory"), { recursive: true });
  seedLegacy23(root);
  writeCmd(root, ["--changed", "first 3.0 write"]);
  const current = read(root, "CURRENT.md");
  assert(current.includes("Schema version: 3.0"), "write did not upgrade schema");
  assert(current.includes("Fact keep me"), "upgrade dropped Current State");
  assert(!/^Mainline session:/m.test(current), "upgrade kept Mainline session");
  assert(current.includes("Stay compatible"), "upgrade dropped next steps");
  run([script("check-memory.cjs"), root]);
}

function testMissingCurrentFails() {
  const root = tempRoot("nocurrent");
  init(root);
  fs.rmSync(path.join(root, ".agent-memory", "CURRENT.md"));
  run([script("check-memory.cjs"), root], { expectFail: true });
}

function testConflictMarkersFail() {
  const root = tempRoot("conflict");
  init(root);
  write(root, "CURRENT.md", `${read(root, "CURRENT.md")}\n<<<<<<< HEAD\n=======\n>>>>>>> other\n`);
  run([script("check-memory.cjs"), root], { expectFail: true });
}

function testCheckDetectsSyncConflict() {
  const root = tempRoot("syncconflict");
  init(root);
  const conflict = path.join(root, ".agent-memory", "CURRENT.sync-conflict-20260806-141658-DVXBQ4P.md");
  fs.writeFileSync(conflict, "# Current Mainline\n", "utf8");
  const failed = run([script("check-memory.cjs"), root], { expectFail: true });
  assert((failed.stderr + failed.stdout).includes("Sync conflict copies found"), "conflict copy not reported");
  fs.rmSync(conflict);
  run([script("check-memory.cjs"), root]);
}

function testRepairMissingChanges() {
  const root = tempRoot("repair");
  init(root);
  fs.rmSync(path.join(root, ".agent-memory", "CHANGES.md"));
  run([script("repair-memory.cjs"), root]);
  assert(read(root, "CHANGES.md").includes("Schema version: 3.0"), "repair did not recreate CHANGES.md");
  run([script("check-memory.cjs"), root]);
}

function testRepairRefusesPrefer() {
  const root = tempRoot("prefer");
  init(root);
  run([script("repair-memory.cjs"), root, "--prefer", "current"], { expectFail: true });
}

function testJsonOutput() {
  const root = tempRoot("json");
  const initJson = JSON.parse(run([
    script("init-memory.cjs"), root, "--project", "Smoke", "--goal", "json", "--agent", "CI", "--json",
  ]).stdout.trim());
  assert(initJson.ok === true && initJson.schema === "3.0", "init --json missing schema");
  const written = JSON.parse(writeCmd(root, ["--changed", "json fact", "--json"]).stdout.trim());
  assert(written.persisted === true, "write --json not persisted");
  const noop = JSON.parse(run([
    script("weplaning-write.cjs"), root, "--changed", "done", "--agent", "CI", "--json",
  ]).stdout.trim());
  assert(noop.persisted === false, "trivial write --json should not persist");
}

function testReadHandoffAndJson() {
  const root = tempRoot("read");
  init(root);
  writeCmd(root, ["--changed", "alpha", "--next-step", "Do the thing;;Then stop"]);
  const briefing = run([script("weplaning-read.cjs"), root, "--handoff"]).stdout;
  assert(briefing.includes("Focus Next Step #1"), "handoff missing focus");
  assert(briefing.includes("Do the thing"), "handoff missing next step text");
  const payload = JSON.parse(run([script("weplaning-read.cjs"), root, "--json"]).stdout.trim());
  assert(payload.goal.includes("Validate WePlaning 3.0"), "read json lost goal");
  assert(payload.nextSteps[0] === "Do the thing", "read json lost next steps");
  const brief = run([script("weplaning-read.cjs"), root, "--brief"]).stdout;
  assert(!brief.includes("Recent Changes"), "--brief should omit ledger");
}

function testReadTruncatesLedger() {
  const root = tempRoot("truncate");
  init(root);
  const longNote = `Durable note ${"x".repeat(200)} UNIQUE_TAIL_SHOULD_NOT_LEAK`;
  run([script("weplaning-note.cjs"), root, longNote, "--agent", "CI"]);
  assert(read(root, "CHANGES.md").includes("UNIQUE_TAIL_SHOULD_NOT_LEAK"), "ledger lost the full note");
  const briefing = run([script("weplaning-read.cjs"), root]).stdout;
  assert(!briefing.includes("UNIQUE_TAIL_SHOULD_NOT_LEAK"), "read briefing dumped the full ledger line");
}

function testProjectConfigAndDecisions() {
  const root = tempRoot("config");
  init(root);
  assert(read(root, "CURRENT.md").includes("Type:"), "Project Config missing");
  writeCmd(root, ["--changed", "chose sqlite", "--decision", "Use sqlite", "--rationale", "ops-doc"]);
  assert(read(root, "DECISIONS.md").includes("Use sqlite"), "decision not recorded");
}

function testArchiveChanges() {
  const root = tempRoot("archive");
  init(root);
  for (let index = 0; index < 5; index += 1) {
    writeCmd(root, ["--changed", `change ${index}`, "--file", `f${index}`, "--verification", "smoke"]);
  }
  const beforeBlocks = read(root, "CHANGES.md").split(/\n## /).length - 1;
  assert(beforeBlocks >= 5, "expected multiple change blocks");
  run([script("archive-changes.cjs"), root, "--keep", "2"]);
  const after = read(root, "CHANGES.md");
  const afterBlocks = after.split(/\n## /).length - 1;
  assert(afterBlocks === 2, `expected 2 kept blocks, got ${afterBlocks}`);
  const archives = fs.readdirSync(path.join(root, ".agent-memory", "archive")).filter((name) => name.startsWith("CHANGES-"));
  assert(archives.length === 1, "expected one archive file");
  assert(after.includes(`Archived: archive/${archives[0]}`), "CHANGES.md lost the archive breadcrumb");
  const full = run([script("weplaning-read.cjs"), root, "--full"]).stdout;
  assert(full.includes(`archive/${archives[0]}`), "--full hides archived history");

  const broken = tempRoot("archivebroken");
  init(broken);
  write(broken, "CHANGES.md", "## only block\n- Changed:\n  - x\n");
  const refused = run([script("archive-changes.cjs"), broken, "--keep", "1"], { expectFail: true });
  assert(
    (refused.stderr + refused.stdout).includes("no recognizable schema header"),
    "archive-changes rewrote a header-less CHANGES.md",
  );
}

function testBackupCap() {
  const root = tempRoot("backups");
  init(root);
  for (let index = 0; index < 15; index += 1) {
    writeCmd(root, ["--changed", `Backup ${index}`]);
  }
  const backups = fs.readdirSync(path.join(root, ".agent-memory", ".backups"));
  const currentBackups = backups.filter((name) => name.startsWith("CURRENT.md."));
  assert(currentBackups.length <= 10, "CURRENT.md backups were not capped");
}

function testBackupsNeverNest() {
  const root = tempRoot("nestbackups");
  init(root);
  for (let index = 0; index < 3; index += 1) {
    writeCmd(root, ["--changed", `nest change ${index}`]);
  }
  const memoryDir = path.join(root, ".agent-memory");
  const offenders = [];
  (function walk(dir) {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      const fullPath = path.join(dir, entry.name);
      const parts = path.relative(memoryDir, fullPath).split(path.sep);
      if (parts.filter((part) => part === ".backups").length > 1) offenders.push(parts.join("/"));
      else if (/\.bak\..*\.bak$/.test(entry.name)) offenders.push(parts.join("/"));
      if (entry.isDirectory()) walk(fullPath);
    }
  })(memoryDir);
  assert(offenders.length === 0, `nested backups: ${offenders.slice(0, 3).join(", ")}`);
}

function testLockReleasedAfterWrite() {
  const root = tempRoot("lock");
  init(root);
  writeCmd(root, ["--changed", "lock check"]);
  assert(!fs.existsSync(path.join(root, ".agent-memory", ".weplaning.lock")), "write leaked lock");
  run([script("weplaning-write.cjs"), tempRoot("nolock")], { expectFail: true });
}

function testFindSearchesArchivedHistory() {
  const root = tempRoot("find");
  init(root);
  writeCmd(root, ["--changed", "NEEDLE_IN_LEDGER value"]);
  const hit = run([script("weplaning-find.cjs"), root, "NEEDLE_IN_LEDGER"]).stdout;
  assert(hit.includes("CHANGES.md"), "find missed the live ledger");
  writeCmd(root, ["--changed", "later work"]);
  run([script("archive-changes.cjs"), root, "--keep", "1"]);
  const archived = run([script("weplaning-find.cjs"), root, "NEEDLE_IN_LEDGER"]).stdout;
  assert(archived.includes("NEEDLE_IN_LEDGER"), "find missed archived history");
  const viaRead = run([script("weplaning-read.cjs"), root, "--find", "NEEDLE_IN_LEDGER"]).stdout;
  assert(viaRead.includes("NEEDLE_IN_LEDGER"), "read --find missed archived history");
}

function testInitForceOnlyFillsGaps() {
  const root = tempRoot("initforce");
  init(root);
  writeCmd(root, ["--changed", "CHANGE WORTH KEEPING"]);
  run([script("init-memory.cjs"), root, "--project", "P", "--goal", "g", "--agent", "CI"], { expectFail: true });
  run([script("init-memory.cjs"), root, "--project", "P", "--goal", "g", "--agent", "CI", "--force"]);
  assert(read(root, "CHANGES.md").includes("CHANGE WORTH KEEPING"), "--force destroyed the change ledger");
  fs.rmSync(path.join(root, ".agent-memory", "CURRENT.md"));
  run([script("init-memory.cjs"), root, "--project", "P", "--goal", "g", "--agent", "CI", "--force"]);
  assert(read(root, "CHANGES.md").includes("CHANGE WORTH KEEPING"), "gap fill lost the ledger");
  run([script("check-memory.cjs"), root]);
  const destroyed = run([
    script("init-memory.cjs"), root, "--project", "P", "--goal", "g", "--agent", "CI", "--reinit",
  ]);
  assert(destroyed.stderr.includes("discards"), "--reinit did not warn about what it destroys");
  assert(!read(root, "CHANGES.md").includes("CHANGE WORTH KEEPING"), "--reinit should start from scratch");
  run([script("init-memory.cjs"), root, "--project", "P", "--goal", "g", "--force", "--reinit"], { expectFail: true });
}

function testSyncPackageRefusesSameDirectory() {
  const pkg = tempRoot("syncpkg");
  fs.writeFileSync(path.join(pkg, "SKILL.md"), "# skill\n", "utf8");
  const refused = run([
    path.join(skillRoot, "tools", "sync-skill-package.cjs"), "--source", pkg, "--target", pkg,
  ], { expectFail: true });
  assert(
    (refused.stderr + refused.stdout).includes("same directory"),
    "sync-skill-package copied a directory onto itself",
  );
}

function testCheckDirtyMtimeFallback() {
  const root = tempRoot("dirty");
  init(root);
  const clean = JSON.parse(run([script("check-dirty.cjs"), root, "--json"]).stdout.trim());
  assert(clean.ok === true, "check-dirty json not ok");
  assert(clean.mode === "mtime", `expected the mtime fallback for a non-git project, got ${clean.mode}`);
  fs.writeFileSync(path.join(root, "notes.txt"), "edited after the last memory update\n", "utf8");
  const dirty = JSON.parse(run([script("check-dirty.cjs"), root, "--json"]).stdout.trim());
  assert(dirty.dirty.includes("notes.txt"), "mtime fallback missed a changed file");
  assert(!dirty.dirty.some((item) => item.startsWith(".agent-memory")), "memory paths must be excluded");
  run([script("check-dirty.cjs"), root, "--strict"], { expectFail: true });
}

function testCloseWrapper() {
  const root = tempRoot("closewrap");
  init(root);
  writeCmd(root, ["--changed", "seed", "--state", "Fact A;;Fact B"]);
  run([
    script("weplaning-close.cjs"), root,
    "--changed", "later work", "--agent", "CI",
  ]);
  const after = read(root, "CURRENT.md");
  assert(after.includes("Fact A"), "close wrapper clobbered curated state");
  run([
    script("weplaning-close.cjs"), root,
    "--changed", "shipped", "--state", "Shipped", "--next-step", "Rest", "--agent", "CI",
  ]);
  assert(read(root, "CURRENT.md").includes("Shipped"), "close --state did not patch");
}

function testAuditMixedBlockers() {
  const root = tempRoot("audit");
  init(root);
  writeCmd(root, ["--blockers", "VPN down;;none"]);
  const audited = run([script("check-memory.cjs"), root, "--audit"]);
  assert(audited.status === 0 || audited.status === undefined, "audit should not fail without --strict");
  run([script("check-memory.cjs"), root, "--audit", "--strict"], { expectFail: true });
}

for (const test of [
  testInitShape,
  testWritePatchesAndLedger,
  testWriteDoesNotClobberState,
  testTrivialNoteNoop,
  testDurableNote,
  testLegacy23CheckPasses,
  testLegacyWePlaningIgnored,
  testWriteUpgradesSchemaKeepsState,
  testMissingCurrentFails,
  testConflictMarkersFail,
  testCheckDetectsSyncConflict,
  testRepairMissingChanges,
  testRepairRefusesPrefer,
  testJsonOutput,
  testReadHandoffAndJson,
  testReadTruncatesLedger,
  testProjectConfigAndDecisions,
  testArchiveChanges,
  testBackupCap,
  testBackupsNeverNest,
  testLockReleasedAfterWrite,
  testFindSearchesArchivedHistory,
  testInitForceOnlyFillsGaps,
  testSyncPackageRefusesSameDirectory,
  testCheckDirtyMtimeFallback,
  testCloseWrapper,
  testAuditMixedBlockers,
]) {
  test();
  console.log(`[ok] ${test.name}`);
}

console.log("WePlaning smoke passed.");
