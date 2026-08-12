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

function newSession(root, shortId, summary, started) {
  return run([
    script("new-session.cjs"), root,
    "--role", "editor", "--summary", summary, "--goal", summary,
    "--agent", "CI", "--adapter", "Smoke", "--os", "linux",
    "--started", started, "--short-id", shortId,
  ]).stdout.trim().split(/\r?\n/).at(-1);
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

function testRepairRebuildsLostSessionFiles() {
  const root = tempRoot("lostsessions");
  init(root);
  const merged = newSession(root, "lost1", "Closed work worth keeping", "2026-06-06T04:00:00Z");
  run([
    script("safe-edit.cjs"), root, "--close", "--session", merged,
    "--changed", "First close", "--file", "x", "--verification", "smoke",
  ]);
  const note = newSession(root, "lost2", "Quick note that should survive", "2026-06-06T04:01:00Z");
  run([script("safe-edit.cjs"), root, "--lite", "--session", note, "--changed", "note body"]);

  fs.rmSync(path.join(root, ".agent-memory", "sessions", `${merged}.md`));
  fs.rmSync(path.join(root, ".agent-memory", "sessions", `${note}.md`));
  run([script("check-memory.cjs"), root], { expectFail: true });

  const dry = run([script("repair-memory.cjs"), root, "--dry-run"]).stdout;
  assert(dry.includes(merged) && dry.includes(note), "dry run should list both lost sessions");
  assert(!fs.existsSync(path.join(root, ".agent-memory", "sessions", `${note}.md`)), "dry run must not write");

  run([script("repair-memory.cjs"), root]);
  run([script("check-memory.cjs"), root]);
  const rebuiltNote = read(root, path.join("sessions", `${note}.md`));
  assert(rebuiltNote.includes("Quick note that should survive"), "row summary not carried into rebuilt session");
  assert(rebuiltNote.includes("Reconstructed by repair-memory.cjs"), "rebuilt session missing provenance");
  assert(/Status: active/.test(rebuiltNote), "rebuilt session should keep its THREADS status");
  const rebuiltMainline = read(root, path.join("sessions", `${merged}.md`));
  assert(/Status: merged/.test(rebuiltMainline), "rebuilt mainline must be merged");
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

  assert(after.includes(`Archived: archive/${archives[0]}`), "CHANGES.md lost the archive breadcrumb");
  run([script("check-memory.cjs"), root]);
  const briefing = run([script("weplaning-read.cjs"), root]).stdout;
  assert(briefing.includes(`archive/${archives[0]}`), "read briefing hides archived history");
  const payload = JSON.parse(run([script("weplaning-read.cjs"), root, "--json"]).stdout.trim());
  assert(payload.archives.length === 1, "read --json missing archive info");
  assert(payload.archives[0].kind === "changes" && payload.archives[0].count > 0, "archive entry lost its block count");

  // A CHANGES.md without its schema header must not be silently rewritten.
  const broken = tempRoot("archivebroken");
  init(broken);
  write(broken, "CHANGES.md", "## only block\n- Session: x\n");
  const refused = run([script("archive-changes.cjs"), broken, "--keep", "1"], { expectFail: true });
  assert(
    (refused.stderr + refused.stdout).includes("no recognizable schema header"),
    "archive-changes rewrote a header-less CHANGES.md",
  );
}

function testBackupsNeverNest() {
  const root = tempRoot("nestbackups");
  const tempSkill = path.join(root, "skill");
  fs.cpSync(skillRoot, tempSkill, { recursive: true });
  const tempScripts = path.join(tempSkill, "scripts");
  init(root);

  // Build up a few backup generations first, so rollback has .bak files to walk over.
  for (let index = 0; index < 3; index += 1) {
    const session = newSession(root, `n${index}`, `Nest ${index}`, `2026-06-06T02:0${index}:00Z`);
    run([
      script("safe-edit.cjs"), root, "--close", "--session", session,
      "--changed", `nest change ${index}`, "--file", "f", "--verification", "smoke",
    ]);
  }
  assert(fs.existsSync(path.join(root, ".agent-memory", ".backups")), "expected first-level backups");

  const doomed = newSession(root, "boom", "Rollback nest", "2026-06-06T02:05:00Z");
  fs.writeFileSync(
    path.join(tempScripts, "append-change.cjs"),
    "#!/usr/bin/env node\nconsole.error('forced append failure');\nprocess.exit(1);\n",
    "utf8",
  );
  run([
    path.join(tempScripts, "safe-edit.cjs"), root, "--close", "--session", doomed,
    "--changed", "rollback nest", "--file", "x", "--verification", "smoke",
  ], { expectFail: true });

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
  assert(offenders.length === 0, `rollback nested backups: ${offenders.slice(0, 3).join(", ")}`);
  run([script("check-memory.cjs"), root]);
}

function testCheckDetectsSyncConflict() {
  const root = tempRoot("syncconflict");
  init(root);
  run([script("check-memory.cjs"), root]);

  const conflict = path.join(root, ".agent-memory", "THREADS.sync-conflict-20260806-141658-DVXBQ4P.md");
  fs.writeFileSync(conflict, "# Threads\n", "utf8");
  const failed = run([script("check-memory.cjs"), root], { expectFail: true });
  assert((failed.stderr + failed.stdout).includes("Sync conflict copies found"), "conflict copy not reported");
  fs.rmSync(conflict);

  // Stale conflict copies parked under .backups are churn, not live divergence.
  const backupDir = path.join(root, ".agent-memory", ".backups");
  fs.mkdirSync(backupDir, { recursive: true });
  fs.writeFileSync(path.join(backupDir, "THREADS.sync-conflict-20260806-141658-DVXBQ4P.md.bak"), "x\n", "utf8");
  run([script("check-memory.cjs"), root]);

  fs.writeFileSync(
    path.join(root, ".agent-memory", "sessions", "s.sync-conflict-20260803-213115-DVXBQ4P.md"),
    "x\n",
    "utf8",
  );
  run([script("check-memory.cjs"), root], { expectFail: true });
}

function testCloseRefusesToClobberCuratedState() {
  const root = tempRoot("clobber");
  init(root);
  const first = newSession(root, "cur", "Curate state", "2026-06-06T03:00:00Z");
  run([
    script("safe-edit.cjs"), root, "--close", "--session", first,
    "--changed", "Recorded host map", "--file", "x", "--verification", "smoke",
    "--state", "Host A live;;Host B live;;Host C retired",
  ]);

  const second = newSession(root, "wipe", "Would wipe state", "2026-06-06T03:01:00Z");
  const refused = run([
    script("safe-edit.cjs"), root, "--close", "--session", second,
    "--changed", "small tweak", "--file", "x", "--verification", "smoke",
  ], { expectFail: true });
  const output = refused.stderr + refused.stdout;
  assert(output.includes("Refusing to overwrite curated"), "clobber guard did not fire");
  assert(output.includes("--replace-state"), "clobber guard missing escape hatch");
  const preserved = read(root, "CURRENT.md");
  assert(preserved.includes("- Host A live"), "curated state was modified despite refusal");
  assert(!read(root, "CHANGES.md").includes("small tweak"), "refused close still appended a change");
  run([script("check-memory.cjs"), root]);

  // --no-sync closes without touching prose.
  run([
    script("safe-edit.cjs"), root, "--close", "--session", second,
    "--changed", "small tweak", "--file", "x", "--verification", "smoke", "--no-sync",
  ]);
  assert(read(root, "CURRENT.md").includes("- Host A live"), "--no-sync should leave state intact");

  // Explicit override still allows the overwrite.
  const third = newSession(root, "ovr", "Override state", "2026-06-06T03:02:00Z");
  run([
    script("safe-edit.cjs"), root, "--close", "--session", third,
    "--changed", "replaced state", "--file", "x", "--verification", "smoke", "--replace-state",
  ]);
  const replaced = read(root, "CURRENT.md");
  assert(replaced.includes("- replaced state"), "--replace-state did not overwrite");
  assert(!replaced.includes("- Host A live"), "--replace-state should have dropped old state");
  run([script("check-memory.cjs"), root]);
}

function testThreadsSurvivesHandEditedPipe() {
  const root = tempRoot("pipedrow");
  init(root);
  const session = newSession(root, "pipe", "before pipe", "2026-06-06T05:00:00Z");
  const threadsPath = path.join(root, ".agent-memory", "THREADS.md");
  const edited = fs
    .readFileSync(threadsPath, "utf8")
    .replace("| before pipe |", "| kept head | dropped tail |");
  fs.writeFileSync(threadsPath, edited, "utf8");

  run([script("session-status.cjs"), root, "--session", session, "--pause"]);
  const after = read(root, "THREADS.md");
  assert(after.includes("kept head"), "summary head lost");
  assert(after.includes("dropped tail"), "text after an unescaped pipe was dropped");
  run([script("check-memory.cjs"), root]);
}

function testThreadsWriteRejectsUnparseableRow() {
  const utils = require(path.join(scripts, "weplaning-utils.cjs"));
  const root = tempRoot("threadsguard");
  init(root);
  const good = read(root, "THREADS.md");
  utils.writeMemory(root, "THREADS.md", good);

  // An empty Session ID cell renders back as "unknown", so the row identity would change.
  const broken = good.replace(/\n\| \S+ \| root \|/, "\n|  | root |");
  assert(broken !== good, "failed to build a broken THREADS row");
  let threw = null;
  try {
    utils.writeMemory(root, "THREADS.md", broken);
  } catch (error) {
    threw = error.message;
  }
  assert(threw && /round-trip/.test(threw), `expected round-trip rejection, got ${threw}`);
  assert(read(root, "THREADS.md") === good, "rejected write must leave THREADS.md untouched");
}

function testDecisionsUseSafeWritePath() {
  const root = tempRoot("decisionwrite");
  init(root);
  for (const text of ["First decision", "Second decision"]) {
    run([
      script("append-decision.cjs"), root,
      "--decision", text, "--rationale", "smoke", "--session", "n/a", "--agent", "CI",
    ]);
  }
  const decisions = read(root, "DECISIONS.md");
  assert(decisions.includes("First decision") && decisions.includes("Second decision"), "decisions not appended");
  const backups = fs
    .readdirSync(path.join(root, ".agent-memory", ".backups"))
    .filter((name) => name.startsWith("DECISIONS.md."));
  assert(backups.length > 0, "append-decision bypassed the backing-up write path");
  run([script("check-memory.cjs"), root]);
  run([script("append-decision.cjs"), root, "--decision", "x", "--no-check"], { expectFail: true });
}

function testStatusRespectsNoCheckPolicy() {
  const root = tempRoot("statuspolicy");
  init(root);
  const session = newSession(root, "pol", "policy", "2026-06-06T05:01:00Z");
  const refused = run([
    script("session-status.cjs"), root, "--session", session, "--pause", "--no-check",
  ], { expectFail: true });
  assert((refused.stderr + refused.stdout).includes("internal-only"), "session-status allowed external --no-check");
}

function testSyncPackageRefusesSameDirectory() {
  const root = tempRoot("syncpkg");
  const pkg = path.join(root, "skill");
  fs.mkdirSync(pkg, { recursive: true });
  fs.writeFileSync(path.join(pkg, "SKILL.md"), "# skill\n", "utf8");
  const refused = run([
    path.join(skillRoot, "tools", "sync-skill-package.cjs"), "--source", pkg, "--target", pkg,
  ], { expectFail: true });
  assert(
    (refused.stderr + refused.stdout).includes("same directory"),
    "sync-skill-package copied a directory onto itself",
  );
}

function testInitForceOnlyFillsGaps() {
  const root = tempRoot("initforce");
  init(root);
  const session = newSession(root, "keep", "SESSION WORTH KEEPING", "2026-06-06T06:00:00Z");
  run([
    script("safe-edit.cjs"), root, "--close", "--session", session,
    "--changed", "CHANGE WORTH KEEPING", "--file", "x", "--verification", "smoke",
  ]);

  run([script("init-memory.cjs"), root, "--project", "P", "--goal", "g", "--agent", "CI"], { expectFail: true });

  run([script("init-memory.cjs"), root, "--project", "P", "--goal", "g", "--agent", "CI", "--force"]);
  assert(read(root, "THREADS.md").includes("SESSION WORTH KEEPING"), "--force destroyed the session tree");
  assert(read(root, "CHANGES.md").includes("CHANGE WORTH KEEPING"), "--force destroyed the change ledger");

  // A missing file is recreated, and it must adopt the surviving mainline.
  fs.rmSync(path.join(root, ".agent-memory", "CURRENT.md"));
  run([script("init-memory.cjs"), root, "--project", "P", "--goal", "g", "--agent", "CI", "--force"]);
  assert(read(root, "THREADS.md").includes("SESSION WORTH KEEPING"), "gap fill lost the session tree");
  run([script("check-memory.cjs"), root]);

  const destroyed = run([
    script("init-memory.cjs"), root, "--project", "P", "--goal", "g", "--agent", "CI", "--reinit",
  ]);
  assert(destroyed.stderr.includes("discards"), "--reinit did not warn about what it destroys");
  assert(!read(root, "CHANGES.md").includes("CHANGE WORTH KEEPING"), "--reinit should start from scratch");
  run([script("init-memory.cjs"), root, "--project", "P", "--goal", "g", "--force", "--reinit"], { expectFail: true });
}

function testArchiveThreadsKeepsGateGreen() {
  const root = tempRoot("archthreads");
  init(root);
  const ids = [];
  for (let index = 0; index < 5; index += 1) {
    const session = newSession(root, `at${index}`, `Archivable ${index}`, `2026-06-06T07:0${index}:00Z`);
    ids.push(session);
    run([
      script("safe-edit.cjs"), root, "--close", "--session", session,
      "--changed", `arch change ${index}`, "--file", "f", "--verification", "smoke",
    ]);
  }
  const plan = run([script("archive-threads.cjs"), root, "--keep", "2", "--dry-run", "--json"]).stdout.trim();
  assert(JSON.parse(plan).archived > 0, "dry run found nothing to archive");
  const sessionCount = () =>
    fs.readdirSync(path.join(root, ".agent-memory", "sessions")).filter((name) => name.endsWith(".md")).length;
  assert(sessionCount() === 6, `dry run moved files (${sessionCount()} left)`);

  const result = JSON.parse(run([script("archive-threads.cjs"), root, "--keep", "2", "--json"]).stdout.trim());
  assert(result.archived === 4, `expected 4 archived rows, got ${result.archived}`);
  assert(result.movedSessions === 4, "session files were not moved");

  const threads = read(root, "THREADS.md");
  assert(threads.includes("Archived rows:"), "THREADS.md lost the archive breadcrumb");
  assert(threads.includes(ids.at(-1)), "mainline row must never be archived");
  assert(!threads.includes(ids[0]), "old row was not archived");
  const archived = fs.readdirSync(path.join(root, ".agent-memory", "archive"));
  assert(archived.some((name) => name.startsWith("THREADS-")), "archive file missing");
  assert(fs.existsSync(path.join(root, ".agent-memory", "archive", "sessions", `${ids[0]}.md`)), "session not archived");

  // Surviving rows still name archived parents; the gate must resolve them.
  run([script("check-memory.cjs"), root, "--audit"]);
  const briefing = run([script("weplaning-read.cjs"), root]).stdout;
  assert(briefing.includes("session rows"), "read briefing hides archived rows");
}

function testFindSearchesArchivedHistory() {
  const root = tempRoot("find");
  init(root);
  const session = newSession(root, "fnd", "Findable session", "2026-06-06T08:00:00Z");
  run([
    script("safe-edit.cjs"), root, "--close", "--session", session,
    "--changed", "NEEDLE_IN_LEDGER value", "--file", "x", "--verification", "smoke",
  ]);
  const hit = run([script("weplaning-find.cjs"), root, "NEEDLE_IN_LEDGER"]).stdout;
  assert(hit.includes("CHANGES.md"), "find missed the live ledger");

  // Push the needle into the older half so archiving actually moves it out.
  const later = newSession(root, "fnd2", "Later session", "2026-06-06T08:01:00Z");
  run([
    script("safe-edit.cjs"), root, "--close", "--session", later,
    "--changed", "later unrelated change", "--file", "y", "--verification", "smoke",
  ]);
  run([script("archive-changes.cjs"), root, "--keep", "1"]);

  const live = JSON.parse(
    run([script("weplaning-find.cjs"), root, "NEEDLE_IN_LEDGER", "--scope", "changes", "--json"]).stdout.trim(),
  );
  assert(live.count === 0, "needle should have left the live ledger");

  const archivedHit = JSON.parse(
    run([script("weplaning-find.cjs"), root, "NEEDLE_IN_LEDGER", "--scope", "archive", "--json"]).stdout.trim(),
  );
  assert(archivedHit.count > 0, "find cannot reach archived history");
  assert(archivedHit.matches.every((m) => m.scope === "archive"), "--scope did not restrict the search");
  const missing = run([script("weplaning-find.cjs"), root, "definitely-not-present"]).stdout;
  assert(missing.includes("No match"), "missing query should report cleanly");
}

function testReadBriefAndAbandonedFold() {
  const root = tempRoot("readbrief");
  init(root);
  const session = newSession(root, "aban", "Abandoned work", "2026-06-06T09:00:00Z");
  run([script("session-status.cjs"), root, "--session", session, "--abandon", "--reason", "obsolete"]);

  const full = run([script("weplaning-read.cjs"), root]).stdout;
  assert(full.includes("abandoned session(s) hidden"), "abandoned rows should be folded by default");
  assert(!full.includes("Abandoned work"), "abandoned summary leaked into the default briefing");
  assert(!full.includes("🚧 Blockers"), "'- none' blockers must not render as a blocker section");

  const all = run([script("weplaning-read.cjs"), root, "--all"]).stdout;
  assert(all.includes("Abandoned work"), "--all should list abandoned sessions");

  const brief = run([script("weplaning-read.cjs"), root, "--brief"]).stdout;
  assert(brief.includes("Accepted Next Steps"), "brief lost the next steps");
  assert(!brief.includes("Recent Changes"), "brief should skip change blocks");
  assert(brief.length < full.length, "brief output is not shorter");
}

function testStatusValidatesBeforeWriting() {
  const root = tempRoot("statusorder");
  init(root);
  const session = newSession(root, "ord", "Order check", "2026-06-06T10:00:00Z");
  const threadsPath = path.join(root, ".agent-memory", "THREADS.md");
  const withoutRow = fs
    .readFileSync(threadsPath, "utf8")
    .split("\n")
    .filter((line) => !line.startsWith(`| ${session} |`))
    .join("\n");
  fs.writeFileSync(threadsPath, withoutRow, "utf8");

  const before = read(root, path.join("sessions", `${session}.md`));
  run([script("session-status.cjs"), root, "--session", session, "--pause"], { expectFail: true });
  assert(
    read(root, path.join("sessions", `${session}.md`)) === before,
    "session file was written before the THREADS row was validated",
  );
}

function testCheckDirtyMtimeFallback() {
  const root = tempRoot("dirty");
  init(root);
  // A temp project has no git, so the mtime fallback is the only thing that can
  // produce a handoff reminder here. Assert it directly rather than conditionally.
  const clean = JSON.parse(run([script("check-dirty.cjs"), root, "--json"]).stdout.trim());
  assert(clean.ok === true, "check-dirty json not ok");
  assert(clean.mode === "mtime", `expected the mtime fallback for a non-git project, got ${clean.mode}`);

  fs.writeFileSync(path.join(root, "notes.txt"), "edited after the last memory update\n", "utf8");
  const dirty = JSON.parse(run([script("check-dirty.cjs"), root, "--json"]).stdout.trim());
  assert(dirty.dirty.includes("notes.txt"), "mtime fallback missed a changed file");
  assert(!dirty.dirty.some((item) => item.startsWith(".agent-memory")), "memory paths must be excluded");
  run([script("check-dirty.cjs"), root, "--strict"], { expectFail: true });
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
  testRepairRebuildsLostSessionFiles,
  testJsonOutput,
  testUpdateSessionFields,
  testReadHandoffAndJson,
  testCheckConflictAndOrphanAudit,
  testProjectConfigAndDecisions,
  testSessionStatusLifecycle,
  testArchiveChanges,
  testBackupsNeverNest,
  testCheckDetectsSyncConflict,
  testCloseRefusesToClobberCuratedState,
  testThreadsSurvivesHandEditedPipe,
  testThreadsWriteRejectsUnparseableRow,
  testDecisionsUseSafeWritePath,
  testStatusRespectsNoCheckPolicy,
  testSyncPackageRefusesSameDirectory,
  testInitForceOnlyFillsGaps,
  testArchiveThreadsKeepsGateGreen,
  testFindSearchesArchivedHistory,
  testReadBriefAndAbandonedFold,
  testStatusValidatesBeforeWriting,
  testCheckDirtyMtimeFallback,
]) {
  test();
  console.log(`[ok] ${test.name}`);
}

console.log("WePlaning smoke passed.");
