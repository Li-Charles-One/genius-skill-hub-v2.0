#!/usr/bin/env node

const fs = require("fs");
const os = require("os");
const path = require("path");
const { spawnSync } = require("child_process");

const scriptDir = path.resolve(__dirname, "..", "scripts");

function run(args) {
  const result = spawnSync(process.execPath, args, {
    cwd: scriptDir,
    encoding: "utf8",
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

function initProject(name) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), `${name}-`));
  run([
    path.join(scriptDir, "init-memory.cjs"),
    root,
    "--project", name,
    "--goal", "Concurrency smoke test",
    "--agent", "Codex",
  ]);
  return root;
}

function concurrentWriteTest() {
  const root = initProject("weplaning-write");
  const workers = [];
  for (let index = 0; index < 5; index += 1) {
    workers.push(spawnNode([
      path.join(scriptDir, "weplaning-write.cjs"),
      root,
      "--agent", "CI",
      "--changed", `Concurrent write ${index}`,
      "--file", `file-${index}.txt`,
      "--verification", `verification-${index}`,
    ]));
  }

  for (const worker of workers) {
    assert(worker.status === 0, `write worker failed\n${worker.stdout || ""}${worker.stderr || ""}`);
  }
  const changes = fs.readFileSync(path.join(root, ".agent-memory", "CHANGES.md"), "utf8");
  for (let index = 0; index < 5; index += 1) {
    assert(changes.includes(`Concurrent write ${index}`), `missing CHANGES entry ${index}`);
  }
  run([path.join(scriptDir, "check-memory.cjs"), root]);
  fs.rmSync(root, { recursive: true, force: true });
}

concurrentWriteTest();
console.log("write concurrency passed");
