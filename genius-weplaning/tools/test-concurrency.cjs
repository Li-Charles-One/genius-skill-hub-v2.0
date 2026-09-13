#!/usr/bin/env node

const fs = require("fs");
const os = require("os");
const path = require("path");
const { spawn, spawnSync } = require("child_process");

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
  return new Promise((resolve, reject) => {
    const child = spawn(process.execPath, args, { cwd: scriptDir, stdio: ["ignore", "pipe", "pipe"] });
    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (chunk) => { stdout += chunk; });
    child.stderr.on("data", (chunk) => { stderr += chunk; });
    child.on("error", reject);
    child.on("close", (status) => resolve({ status, stdout, stderr }));
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

async function concurrentWriteTest() {
  const root = initProject("weplaning-write");
  const workers = [];
  for (let index = 0; index < 6; index += 1) {
    workers.push(spawnNode([
      path.join(scriptDir, "weplaning-write.cjs"),
      root,
      "--agent", "CI",
      "--changed", `Concurrent write ${index}`,
      "--file", `file-${index}.txt`,
      "--verification", `verification-${index}`,
      "--time", "2026-09-13T00:00:00Z",
      "--json",
    ]));
  }

  const results = await Promise.all(workers);
  for (const worker of results) {
    assert(worker.status === 0, `write worker failed\n${worker.stdout || ""}${worker.stderr || ""}`);
  }
  assert(new Set(results.map((worker) => JSON.parse(worker.stdout).changeId)).size === 6, "same-time concurrent writes reused change IDs");
  const changes = fs.readFileSync(path.join(root, ".agent-memory", "CHANGES.md"), "utf8");
  for (let index = 0; index < 6; index += 1) {
    assert(changes.includes(`Concurrent write ${index}`), `missing CHANGES entry ${index}`);
  }
  run([path.join(scriptDir, "check-memory.cjs"), root]);
  fs.rmSync(root, { recursive: true, force: true });
}

concurrentWriteTest().then(() => console.log("write concurrency passed (6 simultaneous workers, unique IDs)"))
  .catch((error) => { console.error(error); process.exitCode = 1; });
