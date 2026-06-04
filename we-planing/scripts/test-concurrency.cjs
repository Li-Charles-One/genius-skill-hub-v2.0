#!/usr/bin/env node

const fs = require("fs");
const os = require("os");
const path = require("path");
const { spawnSync } = require("child_process");

const scriptDir = __dirname;

function run(args, options = {}) {
  const result = spawnSync(process.execPath, args, {
    cwd: scriptDir,
    encoding: "utf8",
    ...options,
  });
  if (result.status !== 0) {
    throw new Error(`${args.join(" ")} failed\n${result.stdout || ""}${result.stderr || ""}`);
  }
  return result.stdout.trim();
}

function spawnNode(args) {
  return spawnSync(process.execPath, args, {
    cwd: scriptDir,
    encoding: "utf8",
  });
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

function countMatches(text, pattern) {
  return (text.match(pattern) || []).length;
}

function initProject(name) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), `${name}-`));
  run([
    path.join(scriptDir, "init-memory.cjs"),
    root,
    "--project", name,
    "--goal", "Concurrency smoke test",
    "--agent", "Codex",
    "--adapter", "codex",
    "--os", "win",
  ]);
  return root;
}

function concurrentAppendTest() {
  const root = initProject("weplaning-append");
  const sessionId = run([
    path.join(scriptDir, "new-session.cjs"),
    root,
    "--role", "implementer",
    "--summary", "Append stress session",
    "--goal", "Stress CHANGES append",
    "--agent", "Codex",
    "--adapter", "codex",
    "--os", "win",
    "--context", "concurrency test",
  ]).split(/\r?\n/).pop().trim();

  const workers = [];
  for (let index = 0; index < 5; index += 1) {
    workers.push(spawnNode([
      path.join(scriptDir, "append-change.cjs"),
      root,
      "--session", sessionId,
      "--changed", `Concurrent append ${index}`,
      "--file", `file-${index}.txt`,
      "--verification", `verification-${index}`,
      "--change-id", `concurrent-append-${index}`,
    ]));
  }

  for (const worker of workers) {
    assert(worker.status === 0, `append worker failed\n${worker.stdout || ""}${worker.stderr || ""}`);
  }
  const changes = fs.readFileSync(path.join(root, ".agent-memory", "CHANGES.md"), "utf8");
  for (let index = 0; index < 5; index += 1) {
    assert(changes.includes(`## concurrent-append-${index}`), `missing CHANGES entry ${index}`);
  }
  run([path.join(scriptDir, "check-memory.cjs"), root]);
  fs.rmSync(root, { recursive: true, force: true });
}

function concurrentNewSessionTest() {
  const root = initProject("weplaning-new-session");
  const ids = Array.from({ length: 5 }, (_, index) => `concurrent-session-${index}`);
  const workers = ids.map((id, index) =>
    spawnNode([
      path.join(scriptDir, "new-session.cjs"),
      root,
      "--role", "implementer",
      "--summary", `Concurrent session ${index}`,
      "--goal", `Open concurrent session ${index}`,
      "--agent", "Codex",
      "--adapter", "codex",
      "--os", "win",
      "--id", id,
      "--context", "concurrency test",
    ]),
  );

  for (const worker of workers) {
    assert(worker.status === 0, `new-session worker failed\n${worker.stdout || ""}${worker.stderr || ""}`);
  }
  const threads = fs.readFileSync(path.join(root, ".agent-memory", "THREADS.md"), "utf8");
  for (const id of ids) {
    assert(fs.existsSync(path.join(root, ".agent-memory", "sessions", `${id}.md`)), `missing session file ${id}`);
    assert(threads.includes(`| ${id} |`), `missing THREADS row ${id}`);
  }
  run([path.join(scriptDir, "check-memory.cjs"), root]);
  fs.rmSync(root, { recursive: true, force: true });
}

function concurrentToolsTest() {
  const root = initProject("weplaning-tools");
  const ids = Array.from({ length: 5 }, (_, index) => `tools-session-${index}`);
  for (const [index, id] of ids.entries()) {
    run([
      path.join(scriptDir, "new-session.cjs"),
      root,
      "--role", "implementer",
      "--summary", `Tools session ${index}`,
      "--goal", `Register tools ${index}`,
      "--agent", "Codex",
      "--adapter", "codex",
      "--os", "win",
      "--id", id,
      "--context", "concurrency test",
    ]);
  }

  const workers = ids.map((id, index) =>
    spawnNode([
      path.join(scriptDir, "register-agent.cjs"),
      root,
      "--session", id,
      "--agent", "Codex",
      "--adapter", "codex",
      "--os", "win",
      "--tool", `tool-${index}`,
      "--mcp", "unavailable",
      "--skill", "we-planing",
      "--notes", `registered-${index}`,
    ]),
  );

  for (const worker of workers) {
    assert(worker.status === 0, `register-agent worker failed\n${worker.stdout || ""}${worker.stderr || ""}`);
  }
  const tools = fs.readFileSync(path.join(root, ".agent-memory", "TOOLS.md"), "utf8");
  for (let index = 0; index < ids.length; index += 1) {
    assert(tools.includes(`| ${ids[index]} | Codex | win | codex | tool-${index} | unavailable | we-planing | registered-${index} |`), `missing TOOLS row ${ids[index]}`);
  }
  assert(countMatches(tools, /\| tools-session-/g) === 5, "unexpected TOOLS session row count");
  run([path.join(scriptDir, "check-memory.cjs"), root]);
  fs.rmSync(root, { recursive: true, force: true });
}

concurrentAppendTest();
console.log("append concurrency passed");
concurrentNewSessionTest();
console.log("new-session concurrency passed");
concurrentToolsTest();
console.log("tools concurrency passed");
