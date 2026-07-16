#!/usr/bin/env node

const fs = require("fs");
const path = require("path");
const { spawnSync } = require("child_process");
const {
  emitResult,
  extractField,
  parseArgs,
  parseCurrentMd,
  parseSessionMd,
  readMemory,
  readSession,
  readThreads,
  renderCurrentMd,
  renderSessionMd,
  required,
  toList,
  usage,
  withMemoryLock,
  writeFile,
  writeMemory,
  writeSession,
} = require("./weplaning-utils.cjs");

const help = `
Usage:
  node safe-edit.cjs <project-root> --lite --session <id> --changed <text>
  node safe-edit.cjs <project-root> --update --session <id> [field options]
  node safe-edit.cjs <project-root> --close --session <id> --changed <text> --file <path> --verification <text> [options]

Modes:
  --lite              Append a Work Notes line with pre/post checks.
  --update            Update in-progress session fields (not mainline merge).
  --close             Append change, merge session, then run the consistency gate.

Common options:
  --session <id>        Required session id.
  --dry-run             Print steps without executing.
  --json                Print machine-readable JSON result on stdout.

--lite options:
  --changed <text>      Required. Appended to Work Notes.

--update options (at least one required):
  --result <text>       Replace session Result.
  --next-step <text>    Replace Exact Next Step (;; separated ok).
  --file <path>         Replace or append Files Touched (use --replace-files to replace).
  --replace-files       With --file: replace Files Touched instead of append.
  --decision <text>     Append Decisions bullets (;; separated).
  --note / --changed    Append Work Notes bullets.

--close options:
  --changed <text>      Required. Change description (+ session Result).
  --file <path>         Required. Repeatable or ";;" separated.
  --verification <text> Required. Repeatable or ";;" separated.
  --note <text>         Notes for append-change / session Work Notes.
  --no-sync             Do not auto-update CURRENT.md prose.
  --goal / --state / --next-step / --blockers / --understanding
`;

const args = parseArgs(process.argv.slice(2));
usage(!args.help, "", help);

const root = path.resolve(args._[0] || process.cwd());
const sessionId = required(args, "session", help);

const modeCount = [args.lite, args.update, args.close].filter(Boolean).length;
usage(modeCount === 1, "Choose exactly one mode: --lite, --update, or --close", help);
const mode = args.close ? "close" : args.update ? "update" : "lite";

const hasSyncFlags = Boolean(
  args.goal || args.state || args["next-step"] || args.blockers || args.understanding,
);

if (mode === "close") {
  required(args, "changed", help);
  if (!(args.file || args.files)) usage(false, "Missing required argument: --file", help);
  if (!args.verification) usage(false, "Missing required argument: --verification", help);
  if (args["no-sync"] && hasSyncFlags) {
    usage(false, "Conflicting flags: --no-sync cannot be combined with CURRENT.md sync flags", help);
  }
} else if (mode === "lite") {
  required(args, "changed", help);
  if (args.goal || args.state || args.blockers || args.understanding) {
    usage(false, "CURRENT.md sync flags require --close", help);
  }
  if (args["next-step"]) {
    usage(false, "--next-step requires --update or --close", help);
  }
  usage(!args["no-sync"], "--no-sync requires --close", help);
} else {
  // update
  const hasUpdateField = Boolean(
    args.result ||
      args["next-step"] ||
      args.file ||
      args.files ||
      args.decision ||
      args.note ||
      args.changed,
  );
  usage(hasUpdateField, " --update requires at least one of: --result --next-step --file --decision --note/--changed", help);
  if (args.goal || args.state || args.blockers || args.understanding) {
    usage(false, "CURRENT.md sync flags require --close", help);
  }
  usage(!args["no-sync"], "--no-sync requires --close", help);
}

function listFiles(dir) {
  if (!fs.existsSync(dir)) return [];
  const result = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) result.push(...listFiles(fullPath));
    else result.push(fullPath);
  }
  return result;
}

function createSnapshot() {
  const memoryDir = path.join(root, ".agent-memory");
  const contentByRelativePath = new Map();
  for (const filePath of listFiles(memoryDir)) {
    contentByRelativePath.set(path.relative(memoryDir, filePath), fs.readFileSync(filePath));
  }
  return { memoryDir, contentByRelativePath };
}

function restoreSnapshot(snapshot) {
  if (args["dry-run"]) return;
  const newFiles = [];
  for (const filePath of listFiles(snapshot.memoryDir)) {
    const relativePath = path.relative(snapshot.memoryDir, filePath);
    if (!snapshot.contentByRelativePath.has(relativePath)) newFiles.push(relativePath);
  }
  for (const [relativePath, content] of snapshot.contentByRelativePath.entries()) {
    writeFile(path.join(snapshot.memoryDir, relativePath), content.toString("utf8"));
  }
  if (newFiles.length) {
    console.error("Left new files untouched after rollback:");
    for (const file of newFiles) console.error(`- .agent-memory/${file.replace(/\\/g, "/")}`);
  }
}

function values(value) {
  return Array.isArray(value) ? value : [value];
}

function runStep(label, command, argv) {
  if (args["dry-run"]) {
    console.error(`[DRY-RUN] ${label}: ${command} ${argv.join(" ")}`);
    return { ok: true };
  }
  console.error(`\n> ${label}`);
  const result = spawnSync(process.execPath, [command, ...argv], {
    cwd: root,
    env: { ...process.env, WEPLANING_INTERNAL_NO_CHECK: "1" },
    encoding: "utf8",
    timeout: 30_000,
  });
  if (result.stdout) process.stderr.write(result.stdout);
  if (result.stderr) process.stderr.write(result.stderr);
  const ok = result.status === 0;
  console.error(`${ok ? "OK" : "FAILED"} ${label}`);
  return { ok, status: result.status };
}

function ensureFreshMainline() {
  const threads = readThreads(root);
  const currentMainline = extractField(readMemory(root, "CURRENT.md"), "Mainline session");
  if (currentMainline !== threads.mainline) {
    throw new Error(`Mainline mismatch before write: CURRENT.md=${currentMainline}, THREADS.md=${threads.mainline}`);
  }
  if (mode === "update") return;
  const sessionText = readSession(root, sessionId);
  const parent = extractField(sessionText, "Parent session");
  if (parent && parent !== threads.mainline && sessionId !== threads.mainline) {
    throw new Error(
      `Stale write blocked: parent=${parent}, current mainline=${threads.mainline}\n` +
      `  Fix: close the active predecessor first, or edit "Parent session:" in\n` +
      `  .agent-memory/sessions/${sessionId}.md to ${threads.mainline}, then rerun.`,
    );
  }
}

function bulletList(value, fallback) {
  const items = toList(value);
  return items.length ? items.map((item) => `- ${item}`).join("\n") : fallback;
}

function numberedList(value, fallback) {
  const items = toList(value);
  return items.length ? items.map((item, index) => `${index + 1}. ${item}`).join("\n") : fallback;
}

function appendBullets(existing, items) {
  const extra = items.map((item) => `- ${item}`).join("\n");
  const base = String(existing || "").replace(/\s*$/, "");
  return base ? `${base}\n${extra}` : extra;
}

const shouldSyncCurrent = mode === "close" && (hasSyncFlags || !args["no-sync"]);

function prepareCloseSession() {
  const session = parseSessionMd(readSession(root, sessionId));
  session.result = String(args.changed);
  const files = toList(args.file || args.files);
  session.filesTouched = files.length
    ? files.map((file) => `- ${file}`).join("\n")
    : session.filesTouched;
  if (args["next-step"]) {
    session.exactNextStep = toList(args["next-step"]).join("\n");
  } else if (/^(unknown|Session opened\.?)$/i.test(String(session.exactNextStep || "").trim())) {
    session.exactNextStep = "See CURRENT.md Accepted Next Steps.";
  }
  const notes = toList(args.note);
  if (notes.length) {
    session.workNotes = appendBullets(session.workNotes, notes);
  }
  writeSession(root, sessionId, renderSessionMd(session));
}

function updateSessionFields() {
  const session = parseSessionMd(readSession(root, sessionId));
  if (session.status === "merged") {
    throw new Error(`Refusing --update on merged session ${sessionId}. Open a new session instead.`);
  }
  if (args.result) session.result = String(args.result);
  if (args["next-step"]) session.exactNextStep = toList(args["next-step"]).join("\n");
  const files = toList(args.file || args.files);
  if (files.length) {
    if (args["replace-files"]) {
      session.filesTouched = files.map((file) => `- ${file}`).join("\n");
    } else {
      session.filesTouched = appendBullets(session.filesTouched, files);
    }
  }
  const decisions = toList(args.decision);
  if (decisions.length) session.decisions = appendBullets(session.decisions, decisions);
  const notes = [...toList(args.note), ...toList(args.changed)];
  if (notes.length) session.workNotes = appendBullets(session.workNotes, notes);
  writeSession(root, sessionId, renderSessionMd(session));
}

function syncCurrentMd() {
  const state = parseCurrentMd(readMemory(root, "CURRENT.md"));
  if (args.goal) state.activeGoal = String(args.goal);
  if (args.understanding) state.currentUnderstanding = String(args.understanding);
  if (args.state) state.currentState = bulletList(args.state, state.currentState);
  else if (!args["no-sync"]) state.currentState = bulletList(args.changed, state.currentState);
  if (args["next-step"]) state.acceptedNextSteps = numberedList(args["next-step"], state.acceptedNextSteps);
  if (args.blockers) state.openBlockers = bulletList(args.blockers, state.openBlockers);
  writeMemory(root, "CURRENT.md", renderCurrentMd(state));
}

function appendToSection(text, heading, line) {
  const marker = `## ${heading}\n`;
  const start = text.indexOf(marker);
  if (start === -1) throw new Error(`Missing section: ${heading}`);
  const bodyStart = start + marker.length;
  const rest = text.slice(bodyStart);
  const nextIndex = rest.search(/\n## /);
  const body = nextIndex === -1 ? rest : rest.slice(0, nextIndex);
  const tail = nextIndex === -1 ? "" : rest.slice(nextIndex);
  return `${text.slice(0, bodyStart)}${body.replace(/\s*$/, "")}\n- ${line}\n${tail}`;
}

function updateLiteSession() {
  const sessionText = readSession(root, sessionId);
  writeSession(root, sessionId, appendToSection(sessionText, "Work Notes", args.changed));
}

const scriptDir = __dirname;
let snapshot = null;

function abort(message) {
  console.error(message);
  if (snapshot) restoreSnapshot(snapshot);
  const check = spawnSync(process.execPath, [path.join(scriptDir, "check-memory.cjs"), root], {
    cwd: root,
    encoding: "utf8",
  });
  if (check.stdout) process.stderr.write(check.stdout);
  if (check.stderr) process.stderr.write(check.stderr);
  process.exit(1);
}

withMemoryLock(root, () => {
  snapshot = createSnapshot();

  try {
    ensureFreshMainline();
  } catch (error) {
    abort(error.message);
  }

  const preCheckResult = runStep("check-memory (pre)", path.join(scriptDir, "check-memory.cjs"), [root]);
  if (!preCheckResult.ok) abort("Pipeline aborted: pre-check failed.");

  if (mode === "lite") {
    try {
      if (!args["dry-run"]) updateLiteSession();
      else console.error(`[DRY-RUN] append session Work Notes: ${args.changed}`);
    } catch (error) {
      abort(`Pipeline aborted: lite session update failed: ${error.message}`);
    }
  } else if (mode === "update") {
    try {
      if (!args["dry-run"]) updateSessionFields();
      else console.error("[DRY-RUN] update session fields");
      console.error("OK update session fields");
    } catch (error) {
      abort(`Pipeline aborted: session update failed: ${error.message}`);
    }
  } else {
    try {
      if (!args["dry-run"]) prepareCloseSession();
      else console.error(`[DRY-RUN] write session Result/Files/Next from close args`);
      console.error("OK prepare session close fields");
    } catch (error) {
      abort(`Pipeline aborted: session close-field update failed: ${error.message}`);
    }

    const appendArgv = [root, "--session", sessionId, "--changed", args.changed, "--no-check"];
    for (const file of values(args.file || args.files)) appendArgv.push("--file", file);
    for (const item of values(args.verification)) appendArgv.push("--verification", item);
    if (args.note) for (const note of values(args.note)) appendArgv.push("--note", note);

    const appendResult = runStep("append-change", path.join(scriptDir, "append-change.cjs"), appendArgv);
    if (!appendResult.ok) abort("Pipeline aborted: append-change failed.");

    const mergeResult = runStep("merge-session", path.join(scriptDir, "merge-session.cjs"), [
      root,
      "--session", sessionId,
      "--no-check",
    ]);
    if (!mergeResult.ok) abort("Pipeline aborted: merge-session failed.");

    if (shouldSyncCurrent) {
      try {
        if (!args["dry-run"]) syncCurrentMd();
        else console.error("[DRY-RUN] sync CURRENT.md prose sections");
        console.error("OK sync CURRENT.md");
      } catch (error) {
        abort(`Pipeline aborted: CURRENT.md sync failed: ${error.message}`);
      }
    }
  }

  const postCheckResult = runStep("check-memory (post)", path.join(scriptDir, "check-memory.cjs"), [root]);
  if (!postCheckResult.ok) abort("Pipeline aborted: post-check failed. Snapshot was restored.");
});

emitResult(args, `safe-edit ${mode} pipeline completed successfully.`, {
  mode,
  sessionId,
  message: `safe-edit ${mode} pipeline completed successfully.`,
});
