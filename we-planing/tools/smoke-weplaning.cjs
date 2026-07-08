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
    "Validate WePlaning v2.3",
    "--agent",
    "CI",
    "--adapter",
    "Smoke",
    "--os",
    "linux",
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

function testLifecycle() {
  const root = tempRoot("lifecycle");
  const rootSession = init(root);
  assert(rootSession, "init did not print root session id");
  run([script("check-memory.cjs"), root]);
  assert(!fs.existsSync(path.join(root, ".agent-memory", "WePlaning.md")), "init should not create WePlaning.md");

  const beforeChanges = read(root, "CHANGES.md");
  const work = run([
    script("new-session.cjs"),
    root,
    "--role",
    "editor",
    "--summary",
    "Smoke work",
    "--goal",
    "Exercise v2.3 scripts",
    "--agent",
    "CI",
    "--adapter",
    "Smoke",
    "--os",
    "linux",
    "--started",
    "2026-06-06T00:01:00Z",
    "--short-id",
    "work",
  ]).stdout.trim().split(/\r?\n/).at(-1);

  const threadsAfterNew = read(root, "THREADS.md");
  assert(threadsAfterNew.includes(`| ${work} |`), "THREADS.md missing new session row");
  assert(threadsAfterNew.includes("| active |"), "THREADS.md missing active status");

  run([
    script("append-change.cjs"),
    root,
    "--session",
    work,
    "--changed",
    "Smoke change",
    "--file",
    ".agent-memory/CHANGES.md",
    "--verification",
    "append-change passed",
    "--time",
    "2026-06-06T00:02:00Z",
  ]);
  const afterChanges = read(root, "CHANGES.md");
  assert(afterChanges.length > beforeChanges.length, "CHANGES.md did not grow");
  assert(afterChanges.includes(beforeChanges.trim().split(/\r?\n/)[0]), "CHANGES.md did not retain old content");

  run([script("merge-session.cjs"), root, "--session", work, "--time", "2026-06-06T00:03:00Z"]);
  const currentMainline = read(root, "CURRENT.md").match(/^Mainline session:\s*(.+)$/m)?.[1];
  const threadsMainline = read(root, "THREADS.md").match(/^Mainline session:\s*(.+)$/m)?.[1];
  assert(currentMainline === threadsMainline, "CURRENT.md and THREADS.md mainline differ after merge");
  assert(currentMainline === work, "Merged session is not mainline");
  run([script("check-memory.cjs"), root]);
}

function testMismatchFails() {
  const root = tempRoot("mismatch");
  init(root);
  const current = read(root, "CURRENT.md").replace(/^Mainline session:\s*.+$/m, "Mainline session: bogus");
  write(root, "CURRENT.md", current);
  run([script("check-memory.cjs"), root], { expectFail: true });
}

function testLegacyWePlaningIgnored() {
  const root = tempRoot("legacy");
  init(root);
  fs.writeFileSync(path.join(root, ".agent-memory", "WePlaning.md"), "legacy stale content\n", "utf8");
  run([script("check-memory.cjs"), root]);
}

function testSafeEditRollbackKeepsNewFiles() {
  const root = tempRoot("rollback");
  const tempSkill = path.join(root, "skill");
  fs.cpSync(skillRoot, tempSkill, { recursive: true });
  const tempScripts = path.join(tempSkill, "scripts");
  const tempSafeEdit = path.join(tempScripts, "safe-edit.cjs");
  init(root);
  const session = run([
    script("new-session.cjs"),
    root,
    "--role",
    "editor",
    "--summary",
    "Rollback work",
    "--goal",
    "Trigger rollback",
    "--agent",
    "CI",
    "--adapter",
    "Smoke",
    "--os",
    "linux",
    "--started",
    "2026-06-06T00:04:00Z",
    "--short-id",
    "fail",
  ]).stdout.trim().split(/\r?\n/).at(-1);

  const failingAppend = `#!/usr/bin/env node
const fs = require("fs");
const path = require("path");
fs.writeFileSync(path.join(${JSON.stringify(root)}, ".agent-memory", "sessions", "external.md"), "external\\n", "utf8");
console.error("forced append failure");
process.exit(1);
`;
  fs.writeFileSync(path.join(tempScripts, "append-change.cjs"), failingAppend, "utf8");

  const result = run([
    tempSafeEdit,
    root,
    "--close",
    "--session",
    session,
    "--changed",
    "Rollback change",
    "--file",
    ".agent-memory/CHANGES.md",
    "--verification",
    "rollback marker",
    "--note",
    "expect rollback",
  ], { expectFail: true });
  assert(result.stderr.includes("Left new files untouched after rollback"), "rollback did not warn about new files");
  assert(fs.existsSync(path.join(root, ".agent-memory", "sessions", "external.md")), "rollback deleted a new file");
}

function testBackupCleanup() {
  const root = tempRoot("backups");
  init(root);
  for (let index = 0; index < 15; index += 1) {
    const session = run([
      script("new-session.cjs"),
      root,
      "--role",
      "editor",
      "--summary",
      `Backup ${index}`,
      "--goal",
      "Exercise backup cleanup",
      "--agent",
      "CI",
      "--adapter",
      "Smoke",
      "--os",
      "linux",
      "--started",
      `2026-06-06T00:${String(10 + index).padStart(2, "0")}:00Z`,
      "--short-id",
      `b${index}`,
    ]).stdout.trim().split(/\r?\n/).at(-1);
    run([script("merge-session.cjs"), root, "--session", session, "--time", `2026-06-06T01:${String(index).padStart(2, "0")}:00Z`]);
  }
  const backupDir = path.join(root, ".agent-memory", ".backups");
  const backups = fs.readdirSync(backupDir);
  const threadsBackups = backups.filter((name) => name.startsWith("THREADS.md."));
  const currentBackups = backups.filter((name) => name.startsWith("CURRENT.md."));
  assert(threadsBackups.length <= 10, "THREADS.md backups were not capped");
  assert(currentBackups.length <= 10, "CURRENT.md backups were not capped");
}

function testStaleWriteReleasesLock() {
  // Business error before the lock callback used to leak .weplaning.lock.
  const root = tempRoot("stalelock");
  init(root);
  const first = run([
    script("new-session.cjs"), root,
    "--role", "editor", "--summary", "First", "--goal", "First session",
    "--agent", "CI", "--adapter", "Smoke", "--os", "linux",
    "--started", "2026-06-06T00:05:00Z", "--short-id", "one",
  ]).stdout.trim().split(/\r?\n/).at(-1);
  run([
    script("safe-edit.cjs"), root, "--close", "--session", first,
    "--changed", "First close", "--file", ".agent-memory/CHANGES.md",
    "--verification", "smoke",
  ]);
  const second = run([
    script("new-session.cjs"), root,
    "--role", "editor", "--summary", "Second", "--goal", "Second session",
    "--agent", "CI", "--adapter", "Smoke", "--os", "linux",
    "--started", "2026-06-06T00:06:00Z", "--short-id", "two",
  ]).stdout.trim().split(/\r?\n/).at(-1);
  // Make second stale: rewind its parent to the pre-close mainline.
  const sessionPath = path.join(root, ".agent-memory", "sessions", `${second}.md`);
  const stale = fs.readFileSync(sessionPath, "utf8").replace(/^Parent session:.*$/m, "Parent session: bogus-parent");
  fs.writeFileSync(sessionPath, stale, "utf8");
  const result = run([
    script("safe-edit.cjs"), root, "--close", "--session", second,
    "--changed", "Stale close", "--file", ".agent-memory/CHANGES.md",
    "--verification", "smoke",
  ], { expectFail: true });
  assert(result.stderr.includes("Stale write blocked"), "expected stale write error");
  assert(result.stderr.includes("Fix:"), "stale write error should include fix guidance");
  assert(
    !fs.existsSync(path.join(root, ".agent-memory", ".weplaning.lock")),
    "stale write leaked .weplaning.lock",
  );
}

function testCloseSyncsCurrentMd() {
  const root = tempRoot("currentsync");
  init(root);
  const session = run([
    script("new-session.cjs"), root,
    "--role", "editor", "--summary", "Sync work", "--goal", "Sync CURRENT.md",
    "--agent", "CI", "--adapter", "Smoke", "--os", "linux",
    "--started", "2026-06-06T00:07:00Z", "--short-id", "sync",
  ]).stdout.trim().split(/\r?\n/).at(-1);
  run([
    script("safe-edit.cjs"), root, "--close", "--session", session,
    "--changed", "Synced close", "--file", ".agent-memory/CHANGES.md",
    "--verification", "smoke",
    "--state", "Feature A done;;Feature B in review",
    "--next-step", "Ship feature B;;Start feature C",
    "--blockers", "none",
  ]);
  const current = read(root, "CURRENT.md");
  assert(current.includes("- Feature A done"), "CURRENT.md missing synced state bullet");
  assert(current.includes("1. Ship feature B"), "CURRENT.md missing synced next step");
  assert(current.includes("2. Start feature C"), "CURRENT.md missing second next step");
  run([script("check-memory.cjs"), root]);
  // Sync flags without --close must be rejected.
  run([
    script("safe-edit.cjs"), root, "--lite", "--session", session,
    "--changed", "note", "--state", "should fail",
  ], { expectFail: true });
}

for (const test of [
  testLifecycle,
  testMismatchFails,
  testLegacyWePlaningIgnored,
  testSafeEditRollbackKeepsNewFiles,
  testBackupCleanup,
  testStaleWriteReleasesLock,
  testCloseSyncsCurrentMd,
]) {
  test();
  console.log(`[ok] ${test.name}`);
}

console.log("WePlaning smoke passed.");
