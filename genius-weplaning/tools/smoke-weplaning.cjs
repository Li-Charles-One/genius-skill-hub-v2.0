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
    "codex",
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
  return run([script("weplaning-write.cjs"), root, "--agent", "codex", ...extra]);
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
  const result = writeCmd(root, ["完成了"]);
  assert(result.stdout.includes("nothing-to-persist"), "trivial note should no-op");
  assert(read(root, "CHANGES.md") === beforeChanges, "trivial note mutated CHANGES.md");
  assert(read(root, "CURRENT.md") === beforeCurrent, "trivial note mutated CURRENT.md");
}

function testDurableNote() {
  const root = tempRoot("note");
  init(root);
  writeCmd(root, ["us-one Hy2 recovered"]);
  assert(read(root, "CHANGES.md").includes("us-one Hy2 recovered"), "positional note did not append ledger");
  assert(!fs.existsSync(path.join(root, ".agent-memory", "THREADS.md")), "note created a session tree");
}

function testLegacyWePlaningIgnored() {
  const root = tempRoot("legacy");
  init(root);
  fs.writeFileSync(path.join(root, ".agent-memory", "WePlaning.md"), "legacy stale content\n", "utf8");
  run([script("check-memory.cjs"), root]);
}

function testOldSchemaIsRejected() {
  const root = tempRoot("old-schema");
  init(root);
  write(root, "CHANGES.md", read(root, "CHANGES.md").replace("Schema version: 3.0", "Schema version: 2.3"));
  run([script("check-memory.cjs"), root], { expectFail: true });
  run([script("weplaning-write.cjs"), root, "--agent", "codex", "--changed", "SHOULD_NOT_PERSIST"], { expectFail: true });
  assert(!read(root, "CHANGES.md").includes("SHOULD_NOT_PERSIST"), "write accepted a 2.x ledger");
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
  const briefing = run([script("weplaning-read.cjs"), root]).stdout;
  assert(briefing.includes("Validate WePlaning 3.0") && briefing.includes("Sync conflict copies found"), "read did not show the live memory with a conflict warning");
  const payload = JSON.parse(run([script("weplaning-read.cjs"), root, "--json"]).stdout);
  assert(payload.warnings.length === 1 && payload.goal.includes("Validate WePlaning 3.0"), "read json lost the conflict warning or the live memory");
  fs.rmSync(conflict);
  assert(JSON.parse(run([script("weplaning-read.cjs"), root, "--json"]).stdout).warnings.length === 0, "read warned on a clean memory");
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

function testJsonOutput() {
  const root = tempRoot("json");
  const initJson = JSON.parse(run([
    script("init-memory.cjs"), root, "--project", "Smoke", "--goal", "json", "--agent", "codex", "--json",
  ]).stdout.trim());
  assert(initJson.ok === true && initJson.schema === "3.0", "init --json missing schema");
  const written = JSON.parse(writeCmd(root, ["--changed", "json fact", "--json"]).stdout.trim());
  assert(written.persisted === true, "write --json not persisted");
  const noop = JSON.parse(run([
    script("weplaning-write.cjs"), root, "--changed", "done", "--agent", "codex", "--json",
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
  writeCmd(root, [longNote]);
  assert(read(root, "CHANGES.md").includes("UNIQUE_TAIL_SHOULD_NOT_LEAK"), "ledger lost the full note");
  assert(!read(root, "CURRENT.md").includes("UNIQUE_TAIL_SHOULD_NOT_LEAK"), "Based On copied the full ledger line");
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
  run([script("init-memory.cjs"), root, "--project", "P", "--goal", "g", "--agent", "codex"], { expectFail: true });
  run([script("init-memory.cjs"), root, "--project", "P", "--goal", "g", "--agent", "codex", "--force"]);
  assert(read(root, "CHANGES.md").includes("CHANGE WORTH KEEPING"), "--force destroyed the change ledger");
  fs.rmSync(path.join(root, ".agent-memory", "CURRENT.md"));
  run([script("init-memory.cjs"), root, "--project", "P", "--goal", "g", "--agent", "codex", "--force"]);
  assert(read(root, "CHANGES.md").includes("CHANGE WORTH KEEPING"), "gap fill lost the ledger");
  run([script("check-memory.cjs"), root]);
  const destroyed = run([
    script("init-memory.cjs"), root, "--project", "P", "--goal", "g", "--agent", "codex", "--reinit",
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

function testExactEdits() {
  const root = tempRoot("exact");
  init(root);
  writeCmd(root, ["--changed", "seed", "--state", "xtc uses jp.yaml;;Fact B", "--next-step", "Do X;;Do Y;;Do Z"]);
  const edited = JSON.parse(writeCmd(root, ["--changed", "SWITCHED_EXIT", "--replace", "jp.yaml", "--with", "us-good.yaml", "--json"]).stdout);
  assert(edited.persisted && edited.patched.includes("replace"), "replace was not persisted");
  let current = read(root, "CURRENT.md");
  assert(current.includes("- xtc uses us-good.yaml\n- Fact B"), "replace did not edit in place");
  const ledger = read(root, "CHANGES.md");
  assert(ledger.includes("SWITCHED_EXIT") && !ledger.includes("Replaced in CURRENT"), "ledger copied the CURRENT diff instead of the stated change");
  const before = memorySnapshot(root);
  for (const extra of [["--replace", "Do ", "--with", "x"], ["--replace", "NOT_THERE", "--with", "x"], ["--replace", "Fact B"], ["--drop", "Do "]]) {
    run([script("weplaning-write.cjs"), root, "--agent", "codex", "--changed", "c", ...extra], { expectFail: true });
    assert(memorySnapshot(root) === before, `ambiguous exact edit mutated memory: ${extra.join(" ")}`);
  }
  const same = JSON.parse(writeCmd(root, ["--changed", "rechecked", "--replace", "Fact B", "--with", "Fact B", "--json"]).stdout);
  assert(same.patched.length === 0, "identical replace reported a patch");
  writeCmd(root, ["--changed", "c", "--drop", "Do X", "--add-state", "Fact C"]);
  current = read(root, "CURRENT.md");
  assert(current.includes("## Accepted Next Steps\n1. Do Y\n2. Do Z\n"), "drop did not renumber next steps");
  assert(current.includes("- Fact B\n- Fact C\n"), "add-state did not append to Current State");
  writeCmd(root, ["--changed", "c", "--next-step", "1. a;;1. b;;c"]);
  assert(read(root, "CURRENT.md").includes("1. a\n2. b\n3. c\n"), "numbered next steps were not renumbered");
  run([script("check-memory.cjs"), root]);
}

function testRejectsInjectedStructure() {
  const root = tempRoot("inject");
  init(root);
  const before = memorySnapshot(root);
  for (const extra of [
    ["--changed", "line one\n## injected"], ["--changed", "two\nlines"], ["--changed", "c", "--state", "fact\n## Extra"],
    ["--changed", "c", "--understanding", "ok\n## Evil"], ["--changed", "c", "--replace", "Required memory files exist.", "--with", "x\n# Evil"], ["single\nline note"],
  ]) {
    run([script("weplaning-write.cjs"), root, "--agent", "codex", ...extra], { expectFail: true });
    assert(memorySnapshot(root) === before, `injected structure mutated memory: ${JSON.stringify(extra)}`);
  }
  writeCmd(root, ["--changed", "c", "--understanding", "- rule one\n- rule two"]);
  assert(read(root, "CURRENT.md").includes("## Current Understanding\n- rule one\n- rule two\n"), "multi-line understanding was rejected");
}

function testAuditMixedBlockers() {
  const root = tempRoot("audit");
  init(root);
  writeCmd(root, ["--changed", "c", "--blockers", "VPN down;;none"]);
  const audited = run([script("check-memory.cjs"), root, "--audit"]);
  assert(audited.status === 0 || audited.status === undefined, "audit should not fail without --strict");
  run([script("check-memory.cjs"), root, "--audit", "--strict"], { expectFail: true });
}

function testAuditOversizedCurrent() {
  const root = tempRoot("audit-size");
  init(root);
  const audit = () => run([script("check-memory.cjs"), root, "--audit"]).stderr;
  assert(!audit().includes("[audit]"), "audit warned on a fresh memory");
  assert(!writeCmd(root, ["--changed", "SMALL_FACT"]).stderr.includes("[audit]"), "write warned on a small memory");
  // 3750 CJK characters are 11250 bytes: the budget counts characters.
  const cjk = writeCmd(root, ["--changed", "c", "--add-state", Array.from({ length: 25 }, (_, i) => `事实${i} ${"字".repeat(150)}`).join(";;")]);
  assert(!cjk.stderr.includes("[audit]"), "audit charged CJK text by bytes");
  const grown = writeCmd(root, ["--changed", "c", "--add-state", `LONG_ITEM ${"x".repeat(300)}`]);
  assert(grown.stderr.includes("[audit] CURRENT.md has 1 item(s) over 300 characters"), "write did not warn when CURRENT grew a long item");
  assert(audit().includes("1 item(s) over 300 characters") && !audit().includes("over 10000"), "audit missed a long item");
  writeCmd(root, ["--changed", "c", "--add-state", Array.from({ length: 40 }, (_, i) => `FACT_${i} ${"y".repeat(200)}`).join(";;")]);
  assert(audit().includes("characters (over 10000)"), "audit missed an oversized CURRENT");
  run([script("check-memory.cjs"), root, "--audit", "--strict"], { expectFail: true });
  run([script("check-memory.cjs"), root]);
}

function memorySnapshot(root) {
  const base = path.join(root, ".agent-memory");
  const files = [];
  (function walk(dir) {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      const full = path.join(dir, entry.name);
      if (entry.isDirectory()) walk(full);
      else files.push([path.relative(base, full), fs.readFileSync(full, "utf8")]);
    }
  })(base);
  return JSON.stringify(files.sort((a, b) => a[0].localeCompare(b[0])));
}

function testWritePreservesWhitespaceAndExtraContent() {
  const root = tempRoot("preserve");
  init(root);
  writeCmd(root, ["--changed", "seed", "--state", "FACT_A;;FACT_B", "--understanding", "CHECK_PORT_FIRST"]);
  const original = read(root, "CURRENT.md")
    .replace("## Current State\n", "## Current State  \n")
    .replace("## Current Understanding\n", "##\tCurrent Understanding\t\n")
    .replace("# Current Mainline\n", "# Current Mainline\nCustom metadata: keep me\n") + "\n## Extra Notes\nCUSTOM_FACT_KEEP_ME\n";
  write(root, "CURRENT.md", original);
  run([script("check-memory.cjs"), root]);
  const before = JSON.parse(run([script("weplaning-read.cjs"), root, "--json"]).stdout);
  assert(before.currentState.includes("FACT_B"), "reader lost a whitespace-suffixed section");
  assert(before.understanding === "CHECK_PORT_FIRST", "reader lost a tab-separated section");
  writeCmd(root, ["--changed", "ledger-only"]);
  const after = read(root, "CURRENT.md");
  for (const value of ["FACT_A", "FACT_B", "CHECK_PORT_FIRST", "CUSTOM_FACT_KEEP_ME", "Custom metadata: keep me", "## Current State  "]) {
    assert(after.includes(value), `write lost ${value}`);
  }
}

function testInvalidStructureCannotBeReadOrWritten() {
  for (const kind of ["missing", "empty", "duplicate"]) {
    const root = tempRoot(`structure-${kind}`);
    init(root);
    let current = read(root, "CURRENT.md");
    if (kind === "missing") current = current.replace(/^## Current State\n[\s\S]*?(?=\n## )/m, "");
    if (kind === "empty") current = current.replace(/^## Current State\n[\s\S]*?(?=\n## )/m, "## Current State\n");
    if (kind === "duplicate") current += "\n## Current State\n- conflicting duplicate\n";
    write(root, "CURRENT.md", current);
    const before = memorySnapshot(root);
    run([script("check-memory.cjs"), root], { expectFail: true });
    run([script("weplaning-read.cjs"), root, "--json"], { expectFail: true });
    run([script("weplaning-write.cjs"), root, "--agent", "codex", "--changed", "do not write"], { expectFail: true });
    assert(memorySnapshot(root) === before, `invalid ${kind} structure was mutated`);
  }
}

function testPatchNeedsChanged() {
  const root = tempRoot("patch-needs-changed");
  init(root);
  const before = memorySnapshot(root);
  for (const extra of [["--state", "STATE_ONLY_FACT"], ["--add-state", "X"], ["--drop", "Required memory"], ["--replace", "Required", "--with", "X"], ["--state", "STATE_ONLY_FACT", "--changed", "done"]]) {
    const refused = run([script("weplaning-write.cjs"), root, "--agent", "codex", ...extra], { expectFail: true });
    assert(refused.stderr.includes("needs --changed"), `patch without a stated change was not refused: ${extra.join(" ")}`);
    assert(memorySnapshot(root) === before, `patch without a stated change mutated memory: ${extra.join(" ")}`);
  }
  const result = JSON.parse(writeCmd(root, ["--changed", "STATED_CHANGE", "--state", "STATE_ONLY_FACT", "--verification", "ACTUAL_CHECK", "--json"]).stdout);
  const ledger = read(root, "CHANGES.md");
  assert(ledger.includes(result.changeId) && ledger.includes("STATED_CHANGE") && ledger.includes("ACTUAL_CHECK"), "patch write has no traceable ledger entry");
  const decision = JSON.parse(writeCmd(root, ["--decision", "DECISION_ONLY_FACT", "--json"]).stdout);
  assert(read(root, "CHANGES.md").includes(decision.changeId), "decision-only write has no change ledger entry");
}

function testInvalidWriteArgumentsAreNoWrite() {
  const root = tempRoot("bad-args");
  init(root);
  writeCmd(root, ["--changed", "c", "--blockers", "REAL_BLOCKER"]);
  const before = memorySnapshot(root);
  const cases = [
    ...["state", "next-step", "blockers", "goal", "understanding", "changed", "decision", "verification"].map((flag) => [`--${flag}`]),
    ["--state", "  "], ["--state", ";;"], ["--state", "Fact", "--state"], ["--sttae", "typo"],
  ];
  for (const extra of cases) {
    run([script("weplaning-write.cjs"), root, "--agent", "codex", ...extra, "--json"], { expectFail: true });
    assert(memorySnapshot(root) === before, `invalid arguments mutated memory: ${extra.join(" ")}`);
  }
}

function testWriteValidatesBeforeAnyMutation() {
  const root = tempRoot("preflight");
  init(root);
  const conflict = "CURRENT.sync-conflict-20260913-100000-OTHER.md";
  write(root, conflict, read(root, "CURRENT.md"));
  let before = memorySnapshot(root);
  run([script("weplaning-write.cjs"), root, "--agent", "codex", "--changed", "c", "--state", "NEW_FACT"], { expectFail: true });
  assert(memorySnapshot(root) === before, "write changed memory before rejecting existing sync conflicts");
  fs.rmSync(path.join(root, ".agent-memory", conflict));
  before = memorySnapshot(root);
  run([
    script("weplaning-write.cjs"), root, "--agent", "codex", "--changed", "c", "--state", "NEW_FACT",
    "--decision", "Invalid decision\n<<<<<<< HEAD\n=======\n>>>>>>> branch",
  ], { expectFail: true });
  assert(memorySnapshot(root) === before, "invalid proposed decision was rejected after mutating CURRENT/CHANGES");
}

function testRepairAddsOnlySchema() {
  const root = tempRoot("repair-local");
  init(root);
  const original = {};
  for (const file of ["CURRENT.md", "CHANGES.md"]) {
    original[file] = read(root, file).replace(/^Schema version:[^\n]*\n/m, "") + "\n## Extra Notes\nPRESERVE_CUSTOM_CONTENT\n";
    write(root, file, original[file].replace(/\n/g, "\r\n"));
  }
  const before = memorySnapshot(root);
  run([script("repair-memory.cjs"), root, "--dry-run", "--json"]);
  assert(memorySnapshot(root) === before, "repair dry-run mutated files");
  run([script("repair-memory.cjs"), root]);
  for (const file of Object.keys(original)) {
    const expected = original[file].replace(/^(#[^\n]*\n)/, "$1Schema version: 3.0\n");
    assert(read(root, file) === expected, `repair changed more than the missing schema in ${file}`);
  }
}

function testRepairRefusesUnparseableOrUnsupportedMemory() {
  for (const kind of ["malformed", "unsupported", "sync-conflict"]) {
    const root = tempRoot(`repair-refuse-${kind}`);
    init(root);
    if (kind === "malformed") {
      write(root, "CURRENT.md", "# Current Mainline\n\n## Active Goal\nKeep me\n\n## Custom Notes\nUNPARSED_IMPORTANT_FACT\n");
      fs.rmSync(path.join(root, ".agent-memory", "CHANGES.md"));
    }
    if (kind === "unsupported") write(root, "CURRENT.md", read(root, "CURRENT.md").replace("Schema version: 3.0", "Schema version: 4.0"));
    if (kind === "sync-conflict") write(root, "CURRENT.sync-conflict-20260913-100000-OTHER.md", read(root, "CURRENT.md"));
    const before = memorySnapshot(root);
    run([script("repair-memory.cjs"), root, "--json"], { expectFail: true });
    assert(memorySnapshot(root) === before, `repair mutated ${kind} memory`);
  }
}

function testRepeatedArchivePreservesHistory() {
  const root = tempRoot("archive-repeat");
  init(root);
  writeCmd(root, ["--changed", "FIRST_ARCHIVE_FACT"]);
  writeCmd(root, ["--changed", "KEEP_AFTER_FIRST"]);
  const clock = path.join(root, "fixed-clock.cjs");
  fs.writeFileSync(clock, 'const NativeDate = Date; global.Date = class extends NativeDate { constructor(...args) { super(...(args.length ? args : ["2026-09-13T10:10:00Z"])); } };\n');
  const first = JSON.parse(run(["--require", clock, script("archive-changes.cjs"), root, "--keep", "1", "--json"]).stdout);
  writeCmd(root, ["--changed", "NEW_LIVE_FACT"]);
  const second = JSON.parse(run(["--require", clock, script("archive-changes.cjs"), root, "--keep", "1", "--json"]).stdout);
  assert(first.archivePath !== second.archivePath, "same-time archives reused a filename");
  assert(fs.readFileSync(first.archivePath, "utf8").includes("FIRST_ARCHIVE_FACT"), "first archive was overwritten");
  assert(fs.readFileSync(second.archivePath, "utf8").includes("KEEP_AFTER_FIRST"), "second archive lost its entry");
  const forcedPath = path.join(root, ".agent-memory", "archive", "CHANGES-forced-collision.md");
  fs.writeFileSync(forcedPath, "EXISTING_ARCHIVE_MUST_SURVIVE\n");
  const forceCollision = path.join(root, "force-collision.cjs");
  fs.writeFileSync(forceCollision, `require(${JSON.stringify(script("weplaning-utils.cjs"))}).uniqueStamp = () => "forced-collision";\n`);
  writeCmd(root, ["--changed", "ANOTHER_LIVE_FACT"]);
  const before = memorySnapshot(root);
  run(["--require", forceCollision, script("archive-changes.cjs"), root, "--keep", "1"], { expectFail: true });
  assert(memorySnapshot(root) === before, "exclusive archive creation overwrote history or changed the ledger");
}

function testReadIncludesContextTimeAndVerification() {
  const root = tempRoot("read-details");
  init(root);
  writeCmd(root, ["--changed", "CHECKED_FACT", "--understanding", "CHECK_PORT_FIRST", "--verification", "curl returned 200 at 2026-09-01T00:00:00Z", "--file", "config.yaml", "--time", "2026-09-01T00:00:00Z"]);
  const plain = run([script("weplaning-read.cjs"), root]).stdout;
  assert(plain.includes("CHECK_PORT_FIRST") && plain.includes("Memory last updated: 2026-09-01T00:00:00Z"), "briefing omitted accepted context or update time");
  assert(plain.includes("not a live verification"), "read output treats recorded facts as fresh checks");
  const payload = JSON.parse(run([script("weplaning-read.cjs"), root, "--json"]).stdout);
  assert(payload.lastUpdated === "2026-09-01T00:00:00Z", "JSON lost lastUpdated");
  assert(payload.recentChanges[0].verification[0].includes("curl returned 200"), "JSON lost verification");
  assert(payload.recentChanges[0].files[0] === "config.yaml", "JSON lost file reference");
  const handoff = run([script("weplaning-read.cjs"), root, "--handoff"]).stdout;
  assert(handoff.includes("Verification (recorded): curl returned 200"), "handoff omitted verification evidence");
}

function testNextStepsNoneUnknownAndInvalidNumber() {
  const root = tempRoot("next-boundary");
  init(root);
  writeCmd(root, ["--changed", "c", "--next-step", "TASK_A;;TASK_B"]);
  for (const n of ["0", "99", "-1", "1.9", "abc"]) {
    run([script("weplaning-read.cjs"), root, "--next", n, "--handoff", "--json"], { expectFail: true });
  }
  run([script("weplaning-read.cjs"), root, "--next", "--json"], { expectFail: true });
  const focused = JSON.parse(run([script("weplaning-read.cjs"), root, "--next", "2", "--json"]).stdout);
  assert(focused.focusNextStep.text === "TASK_B", "valid explicit task selection changed");
  for (const value of ["none", "无待执行事项", "unknown"]) {
    writeCmd(root, ["--changed", "c", "--next-step", value, "--blockers", "unknown"]);
    const payload = JSON.parse(run([script("weplaning-read.cjs"), root, "--handoff", "--json"]).stdout);
    assert(payload.focusNextStep === null, `handoff focused ${value} as a task`);
    assert(payload.nextStepsStatus === (value === "unknown" ? "unknown" : "none"), "lost none/unknown distinction");
    const plain = run([script("weplaning-read.cjs"), root, "--handoff"]).stdout;
    assert(plain.includes("Blockers:") && plain.includes("unknown"), "unknown blockers were hidden");
    run([script("weplaning-read.cjs"), root, "--next", "1", "--json"], { expectFail: true });
  }
}

function testBriefShortensLongItems() {
  const root = tempRoot("brief");
  init(root);
  writeCmd(root, ["--changed", "c", "--state", `SHORT_FACT stays whole;;HOST_LABEL：${"细节".repeat(60)} BRIEF_TAIL_SHOULD_NOT_SHOW`]);
  const brief = run([script("weplaning-read.cjs"), root, "--brief"]).stdout;
  assert(brief.includes("SHORT_FACT stays whole"), "--brief cut a short item");
  assert(brief.includes("- HOST_LABEL…") && !brief.includes("BRIEF_TAIL_SHOULD_NOT_SHOW"), "--brief did not cut a long item to its label");
  assert(brief.includes("1 long item(s) shortened"), "--brief hid that items were shortened");
  const full = run([script("weplaning-read.cjs"), root]).stdout;
  assert(full.includes("BRIEF_TAIL_SHOULD_NOT_SHOW") && !full.includes("shortened"), "default read lost item detail");
}

function testLedgerOmitsEmptyFields() {
  const root = tempRoot("ledger-fields");
  init(root);
  const lastBlock = () => read(root, "CHANGES.md").split(/\n(?=## )/).at(-1);
  writeCmd(root, ["--changed", "PLAIN_FACT"]);
  assert(lastBlock().includes("PLAIN_FACT"), "ledger lost the change");
  for (const label of ["Change ID:", "Files touched:", "Verification:", "Notes:", "- none"]) {
    assert(!lastBlock().includes(label), `ledger wrote an empty or duplicate field: ${label}`);
  }
  writeCmd(root, ["--changed", "NOTED_FACT", "--file", "a.yaml", "--verification", "checked", "--note", "extra"]);
  assert(/- Files touched:\n  - a\.yaml\n- Verification:\n  - checked\n- Notes:\n  - extra\n$/.test(lastBlock()), "ledger dropped a provided field");
}

function testSupersedeDecision() {
  const root = tempRoot("supersede");
  init(root);
  writeCmd(root, ["--decision", "OLD_CHOICE use port 1", "--rationale", "first guess"]);
  const before = memorySnapshot(root);
  run([script("weplaning-write.cjs"), root, "--agent", "codex", "--decision", "x", "--supersedes", "NO_SUCH_DECISION"], { expectFail: true });
  run([script("weplaning-write.cjs"), root, "--agent", "codex", "--changed", "x", "--supersedes", "OLD_CHOICE"], { expectFail: true });
  assert(memorySnapshot(root) === before, "a failed --supersedes changed memory");
  writeCmd(root, ["--decision", "NEW_CHOICE use port 2", "--supersedes", "OLD_CHOICE"]);
  const blocks = read(root, "DECISIONS.md").split(/\n(?=## )/);
  const oldBlock = blocks.find((block) => block.includes("OLD_CHOICE"));
  const newBlock = blocks.find((block) => block.includes("NEW_CHOICE"));
  assert(/^- Superseded by: \S+ decision$/m.test(oldBlock) && oldBlock.includes("first guess"), "old decision was not marked or lost content");
  assert(/^- Supersedes: \S+ decision$/m.test(newBlock) && !newBlock.includes("Superseded by"), "new decision does not point at the old one");
  assert(read(root, "CHANGES.md").includes("Superseded decision: OLD_CHOICE use port 1"), "ledger missed the superseded decision");
  run([script("weplaning-write.cjs"), root, "--agent", "codex", "--decision", "y", "--supersedes", "OLD_CHOICE"], { expectFail: true });
  fs.mkdirSync(path.join(root, ".agent-memory", "archive"), { recursive: true });
  write(root, path.join("archive", "DECISIONS-old.md"), "# Archived Decisions\nSchema version: 3.0\nBlocks: 2\n");
  const full = run([script("weplaning-read.cjs"), root, "--full"]).stdout;
  const shownDecisions = full.split("⚖ Decisions")[1].split("\n\n")[0];
  assert(shownDecisions.includes("NEW_CHOICE use port 2") && !shownDecisions.includes("OLD_CHOICE"), "--full did not show only active decisions");
  assert(full.includes("1 superseded hidden") && full.includes("archive/DECISIONS-old.md  (2 decision blocks)"), "--full missed the superseded count or the decision archive");
  assert(!run([script("weplaning-read.cjs"), root]).stdout.includes("⚖ Decisions"), "default read printed the decisions section");
  const payload = JSON.parse(run([script("weplaning-read.cjs"), root, "--json"]).stdout);
  assert(payload.supersededDecisions === 1 && payload.decisions.some((item) => item.decision.includes("NEW_CHOICE")), "JSON lost decisions");
}

function testHandoffSkipsUserOwnedSteps() {
  const root = tempRoot("user-steps");
  init(root);
  writeCmd(root, ["--changed", "c", "--next-step", "【待用户处理】USER_TASK;;AGENT_TASK"]);
  const mixed = JSON.parse(run([script("weplaning-read.cjs"), root, "--handoff", "--json"]).stdout);
  assert(mixed.focusNextStep.index === 2 && mixed.focusNextStep.text === "AGENT_TASK" && mixed.nextStepsStatus === "ready", "handoff focused a user-owned step");
  writeCmd(root, ["--changed", "c", "--next-step", "【待用户处理】USER_TASK;;[user] OTHER_USER_TASK"]);
  const waiting = JSON.parse(run([script("weplaning-read.cjs"), root, "--handoff", "--json"]).stdout);
  assert(waiting.focusNextStep === null && waiting.nextStepsStatus === "waiting-user", "handoff invented a task when every step waits on the user");
  assert(run([script("weplaning-read.cjs"), root, "--handoff"]).stdout.includes("Every next step waits on the user"), "handoff hid that every step waits on the user");
  const chosen = JSON.parse(run([script("weplaning-read.cjs"), root, "--next", "1", "--json"]).stdout);
  assert(chosen.focusNextStep.text.includes("USER_TASK"), "explicit --next could not select a user-owned step");
}

function testAgentTagIsLowercaseWithDevice() {
  const root = tempRoot("agent-tag");
  init(root);
  run([script("weplaning-write.cjs"), root, "--agent", "Grok", "--changed", "TAGGED_FACT", "--decision", "TAGGED_DECISION"]);
  for (const file of ["CHANGES.md", "DECISIONS.md"]) {
    assert(/^- Agent: grok@[^\s@]+$/m.test(read(root, file)), `${file} agent is not lowercase name@device`);
  }
  assert(/^- Agent: codex@[^\s@]+$/m.test(read(root, "CHANGES.md")), "init agent is not lowercase name@device");
}

function testAgentMustBeKnownRuntime() {
  const root = tempRoot("agent-known");
  init(root);
  const before = memorySnapshot(root);
  for (const agent of [[], ["--agent", "jp-beta-ops"], ["--agent", "Charles"], ["--agent", "huajin-mac"]]) {
    run([script("weplaning-write.cjs"), root, ...agent, "--changed", "SHOULD_NOT_PERSIST"], { expectFail: true });
    assert(memorySnapshot(root) === before, `write accepted a missing or unknown agent: ${agent.join(" ")}`);
    const fresh = tempRoot("agent-init");
    run([script("init-memory.cjs"), fresh, ...agent, "--project", "P", "--goal", "g"], { expectFail: true });
    assert(!fs.existsSync(path.join(fresh, ".agent-memory")), `init accepted a missing or unknown agent: ${agent.join(" ")}`);
  }
}

function testSearchPrioritizesCurrentTruth() {
  const root = tempRoot("search-priority");
  init(root);
  writeCmd(root, ["--changed", "c", "--state", "NEEDLE_CURRENT_TRUTH"]);
  write(root, "CHANGES.md", "# Changes\nSchema version: 3.0\n\n" + Array.from({ length: 45 }, (_, i) => `## historical ${i}\n- Changed:\n  - NEEDLE_OLD_${i}\n`).join("\n"));
  const result = JSON.parse(run([script("weplaning-find.cjs"), root, "NEEDLE", "--json"]).stdout);
  assert(result.truncated && result.matches[0].scope === "current", "old history crowded current truth out of search results");
}

function testDirtyGitErrorIsNotClean() {
  const root = tempRoot("git-error");
  init(root);
  fs.mkdirSync(path.join(root, ".git"));
  const result = run([script("check-dirty.cjs"), root, "--json", "--strict"], { expectFail: true });
  const payload = JSON.parse(result.stdout);
  assert(payload.ok === false && payload.mode === "git-error", "git failure reported success");
  assert(!payload.message.includes("Workspace clean"), "git failure reported a clean workspace");
}

for (const test of [
  testInitShape,
  testWritePatchesAndLedger,
  testWriteDoesNotClobberState,
  testTrivialNoteNoop,
  testDurableNote,
  testLegacyWePlaningIgnored,
  testOldSchemaIsRejected,
  testMissingCurrentFails,
  testConflictMarkersFail,
  testCheckDetectsSyncConflict,
  testRepairMissingChanges,
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
  testExactEdits,
  testRejectsInjectedStructure,
  testAuditMixedBlockers,
  testAuditOversizedCurrent,
  testWritePreservesWhitespaceAndExtraContent,
  testInvalidStructureCannotBeReadOrWritten,
  testPatchNeedsChanged,
  testInvalidWriteArgumentsAreNoWrite,
  testWriteValidatesBeforeAnyMutation,
  testRepairAddsOnlySchema,
  testRepairRefusesUnparseableOrUnsupportedMemory,
  testRepeatedArchivePreservesHistory,
  testReadIncludesContextTimeAndVerification,
  testNextStepsNoneUnknownAndInvalidNumber,
  testBriefShortensLongItems,
  testLedgerOmitsEmptyFields,
  testSupersedeDecision,
  testHandoffSkipsUserOwnedSteps,
  testAgentTagIsLowercaseWithDevice,
  testAgentMustBeKnownRuntime,
  testSearchPrioritizesCurrentTruth,
  testDirtyGitErrorIsNotClean,
]) {
  test();
  console.log(`[ok] ${test.name}`);
}

console.log("WePlaning smoke passed.");
