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

function testCloseWritesSessionResult() {
  const root = tempRoot("closeresult");
  init(root);
  const session = run([
    script("new-session.cjs"), root,
    "--role", "editor", "--summary", "Result work", "--goal", "Write session result",
    "--agent", "CI", "--adapter", "Smoke", "--os", "linux",
    "--started", "2026-06-06T00:08:00Z", "--short-id", "res",
  ]).stdout.trim().split(/\r?\n/).at(-1);
  run([
    script("safe-edit.cjs"), root, "--close", "--session", session,
    "--changed", "Implemented close session result write",
    "--file", "scripts/safe-edit.cjs",
    "--verification", "smoke",
    "--next-step", "Run audit",
  ]);
  const sessionText = read(root, path.join("sessions", `${session}.md`));
  assert(sessionText.includes("## Result\nImplemented close session result write"), "session Result not written");
  assert(sessionText.includes("- scripts/safe-edit.cjs"), "session Files Touched not written");
  assert(sessionText.includes("## Exact Next Step\nRun audit"), "session Exact Next Step not written");
  const current = read(root, "CURRENT.md");
  assert(current.includes("Last change:") && current.includes("Implemented close session result write"), "Based On Last change still placeholder");
  assert(current.includes("- Implemented close session result write"), "auto Current State sync missing");
  run([script("check-memory.cjs"), root, "--audit"]);
}

function testRepairRefusesMismatchWithoutPrefer() {
  const root = tempRoot("repairprefer");
  const rootSession = init(root);
  const current = read(root, "CURRENT.md").replace(/^Mainline session:\s*.+$/m, "Mainline session: bogus");
  write(root, "CURRENT.md", current);
  const refused = run([script("repair-memory.cjs"), root], { expectFail: true });
  assert(
    (refused.stderr + refused.stdout).includes("Refuse automatic repair"),
    "repair should refuse mainline mismatch without --prefer",
  );
  run([script("repair-memory.cjs"), root, "--prefer", "threads"]);
  const fixedCurrent = read(root, "CURRENT.md");
  assert(fixedCurrent.includes(`Mainline session: ${rootSession}`), "prefer threads did not restore CURRENT mainline");
  run([script("check-memory.cjs"), root]);
}

function testJsonOutput() {
  const root = tempRoot("jsonout");
  const initOut = run([
    script("init-memory.cjs"), root,
    "--project", "JSON", "--goal", "json output",
    "--agent", "CI", "--adapter", "Smoke", "--os", "linux",
    "--started", "2026-06-06T00:09:00Z", "--json",
  ]).stdout.trim();
  const initPayload = JSON.parse(initOut);
  assert(initPayload.ok === true && initPayload.sessionId, "init --json missing sessionId");
  const sessionOut = run([
    script("new-session.cjs"), root,
    "--role", "editor", "--summary", "JSON session", "--goal", "json",
    "--agent", "CI", "--adapter", "Smoke", "--os", "linux",
    "--started", "2026-06-06T00:10:00Z", "--short-id", "jsn", "--json",
  ]).stdout.trim();
  const sessionPayload = JSON.parse(sessionOut);
  assert(sessionPayload.ok === true && sessionPayload.sessionId, "new-session --json missing sessionId");
  const closeOut = run([
    script("safe-edit.cjs"), root, "--close", "--session", sessionPayload.sessionId,
    "--changed", "json close", "--file", "x", "--verification", "smoke", "--json",
  ]).stdout.trim();
  const closePayload = JSON.parse(closeOut);
  assert(closePayload.ok === true && closePayload.mode === "close", "safe-edit --json missing mode");
}

function testUpdateSessionFields() {
  const root = tempRoot("update");
  init(root);
  const session = run([
    script("new-session.cjs"), root,
    "--role", "editor", "--summary", "Update work", "--goal", "Mid-session update",
    "--agent", "CI", "--adapter", "Smoke", "--os", "linux",
    "--started", "2026-06-06T00:11:00Z", "--short-id", "upd",
  ]).stdout.trim().split(/\r?\n/).at(-1);
  run([
    script("safe-edit.cjs"), root, "--update", "--session", session,
    "--result", "Halfway done",
    "--next-step", "Finish and close",
    "--file", "src/a.ts",
    "--decision", "Use approach B",
    "--note", "Wrote helper",
  ]);
  const text = read(root, path.join("sessions", `${session}.md`));
  assert(text.includes("## Result\nHalfway done"), "update Result missing");
  assert(text.includes("## Exact Next Step\nFinish and close"), "update next step missing");
  assert(text.includes("- src/a.ts"), "update file missing");
  assert(text.includes("- Use approach B"), "update decision missing");
  assert(text.includes("- Wrote helper"), "update note missing");
  run([
    script("safe-edit.cjs"), root, "--close", "--session", session,
    "--changed", "Update path closed", "--file", "src/a.ts", "--verification", "smoke",
  ]);
  run([
    script("safe-edit.cjs"), root, "--update", "--session", session, "--result", "nope",
  ], { expectFail: true });
}

function testReadHandoffAndJson() {
  const root = tempRoot("read");
  init(root);
  const session = run([
    script("new-session.cjs"), root,
    "--role", "editor", "--summary", "Read work", "--goal", "Handoff",
    "--agent", "CI", "--adapter", "Smoke", "--os", "linux",
    "--started", "2026-06-06T00:12:00Z", "--short-id", "rd",
  ]).stdout.trim().split(/\r?\n/).at(-1);
  run([
    script("safe-edit.cjs"), root, "--close", "--session", session,
    "--changed", "Handoff ready", "--file", "x", "--verification", "smoke",
    "--next-step", "Ship it;;Document it",
  ]);
  const human = run([script("weplaning-read.cjs"), root, "--handoff", "--next", "2"]).stdout;
  assert(human.includes("HANDOFF"), "handoff banner missing");
  assert(human.includes("Focus Next Step #2"), "focus next step missing");
  assert(human.includes("Document it"), "next step #2 text missing");
  assert(human.includes("mainline CURRENT"), "truth hierarchy missing");
  const jsonOut = run([script("weplaning-read.cjs"), root, "--json", "--handoff"]).stdout.trim();
  const payload = JSON.parse(jsonOut);
  assert(payload.ok === true && payload.mainlineSession, "read --json missing mainline");
  assert(payload.focusNextStep && payload.focusNextStep.index === 1, "handoff focus should default to #1");
  assert(Array.isArray(payload.recentChanges), "read --json missing recentChanges");
}

function testCheckConflictAndOrphanAudit() {
  const root = tempRoot("checkx");
  init(root);
  const current = read(root, "CURRENT.md");
  write(root, "CURRENT.md", `${current}\n<<<<<<< HEAD\nconflict\n=======\nother\n>>>>>>> branch\n`);
  run([script("check-memory.cjs"), root], { expectFail: true });

  const root2 = tempRoot("orphan");
  init(root2);
  fs.writeFileSync(path.join(root2, ".agent-memory", "sessions", "orphan-session.md"), "# orphan\n", "utf8");
  const soft = run([script("check-memory.cjs"), root2, "--audit"]);
  assert(soft.status === 0, "audit warnings should exit 0 by default");
  assert((soft.stderr + soft.stdout).includes("Orphan session file"), "orphan warning missing");
  run([script("check-memory.cjs"), root2, "--audit", "--strict"], { expectFail: true });
}

function testProjectConfigAndDecisions() {
  const root = tempRoot("projcfg");
  fs.writeFileSync(path.join(root, "main.py"), "print('x')\n", "utf8");
  init(root);
  const current = read(root, "CURRENT.md");
  assert(current.includes("## Project Config"), "Project Config section missing");
  assert(current.includes("Type: code"), "auto type code missing");
  assert(fs.existsSync(path.join(root, ".agent-memory", "DECISIONS.md")), "DECISIONS.md missing");
  run([
    script("append-decision.cjs"), root,
    "--decision", "Prefer SQLite",
    "--rationale", "simple local store",
    "--session", "n/a",
    "--agent", "CI",
  ]);
  const decisions = fs.readFileSync(path.join(root, ".agent-memory", "DECISIONS.md"), "utf8");
  assert(decisions.includes("Prefer SQLite"), "decision not appended");
}

function testSessionStatusLifecycle() {
  const root = tempRoot("status");
  init(root);
  const session = run([
    script("new-session.cjs"), root,
    "--role", "editor", "--summary", "status work", "--goal", "lifecycle",
    "--agent", "CI", "--adapter", "Smoke", "--os", "linux",
    "--started", "2026-06-06T00:13:00Z", "--short-id", "st",
  ]).stdout.trim().split(/\r?\n/).at(-1);
  run([script("session-status.cjs"), root, "--session", session, "--pause", "--reason", "wait review"]);
  let text = read(root, path.join("sessions", `${session}.md`));
  assert(/Status: paused/.test(text), "pause failed");
  run([script("session-status.cjs"), root, "--session", session, "--resume"]);
  text = read(root, path.join("sessions", `${session}.md`));
  assert(/Status: active/.test(text), "resume failed");
  run([script("session-status.cjs"), root, "--session", session, "--abandon", "--reason", "obsolete"]);
  text = read(root, path.join("sessions", `${session}.md`));
  assert(/Status: abandoned/.test(text), "abandon failed");
  const threads = read(root, "THREADS.md");
  assert(threads.includes("| abandoned |"), "THREADS status not abandoned");
  run([script("session-status.cjs"), root, "--session", session, "--pause"], { expectFail: true });
}

function testArchiveChanges() {
  const root = tempRoot("archive");
  init(root);
  for (let index = 0; index < 5; index += 1) {
    const session = run([
      script("new-session.cjs"), root,
      "--role", "editor", "--summary", `A${index}`, "--goal", "archive",
      "--agent", "CI", "--adapter", "Smoke", "--os", "linux",
      "--started", `2026-06-06T01:${String(index).padStart(2, "0")}:00Z`,
      "--short-id", `a${index}`,
    ]).stdout.trim().split(/\r?\n/).at(-1);
    run([
      script("safe-edit.cjs"), root, "--close", "--session", session,
      "--changed", `change ${index}`, "--file", `f${index}`, "--verification", "smoke",
    ]);
  }
  const before = read(root, "CHANGES.md");
  const beforeBlocks = before.split(/\n## /).length - 1;
  assert(beforeBlocks >= 5, "expected multiple change blocks");
  run([script("archive-changes.cjs"), root, "--keep", "2"]);
  const after = read(root, "CHANGES.md");
  const afterBlocks = after.split(/\n## /).length - 1;
  assert(afterBlocks === 2, `expected 2 kept blocks, got ${afterBlocks}`);
  const archiveDir = path.join(root, ".agent-memory", "archive");
  assert(fs.existsSync(archiveDir), "archive dir missing");
  const archives = fs.readdirSync(archiveDir).filter((name) => name.startsWith("CHANGES-"));
  assert(archives.length === 1, "expected one archive file");
}

function testCheckDirtyNoGit() {
  const root = tempRoot("dirty");
  init(root);
  const result = run([script("check-dirty.cjs"), root, "--json"]);
  const payload = JSON.parse(result.stdout.trim());
  assert(payload.ok === true, "check-dirty json not ok");
  assert(payload.mode === "none" || payload.mode === "git", "unexpected dirty mode");
}

for (const test of [
  testLifecycle,
  testMismatchFails,
  testLegacyWePlaningIgnored,
  testSafeEditRollbackKeepsNewFiles,
  testBackupCleanup,
  testStaleWriteReleasesLock,
  testCloseSyncsCurrentMd,
  testCloseWritesSessionResult,
  testRepairRefusesMismatchWithoutPrefer,
  testJsonOutput,
  testUpdateSessionFields,
  testReadHandoffAndJson,
  testCheckConflictAndOrphanAudit,
  testProjectConfigAndDecisions,
  testSessionStatusLifecycle,
  testArchiveChanges,
  testCheckDirtyNoGit,
]) {
  test();
  console.log(`[ok] ${test.name}`);
}

console.log("WePlaning smoke passed.");
