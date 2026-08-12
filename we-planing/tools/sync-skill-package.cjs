#!/usr/bin/env node

const fs = require("fs");
const path = require("path");
const crypto = require("crypto");
const { parseArgs, required, toList, usage } = require("../scripts/weplaning-utils.cjs");

const help = `
Usage:
  node sync-skill-package.cjs --source <skill-dir> --target <skill-dir> [options]

Options:
  --dry-run     Print planned file copies without writing
  --keep <path> Allow extra target file or directory. Repeat or separate with ";;"
`;

const args = parseArgs(process.argv.slice(2));
usage(!args.help, "", help);

const source = path.resolve(required(args, "source", help));
const target = path.resolve(required(args, "target", help));
const dryRun = Boolean(args["dry-run"]);
const keep = toList(args.keep).map((item) => item.replace(/\\/g, "/").replace(/^\/+|\/+$/g, ""));

function listFiles(root) {
  const output = [];
  const links = [];
  function walk(dir) {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      const full = path.join(dir, entry.name);
      if (entry.name === ".git") continue;
      // isDirectory()/isFile() are both false for a link, so an unreported link
      // would silently vanish from the copy and from the verification pass.
      if (entry.isSymbolicLink()) links.push(full);
      else if (entry.isDirectory()) walk(full);
      else if (entry.isFile()) output.push(full);
    }
  }
  walk(root);
  if (links.length) {
    console.error(`Refusing to sync: ${links.length} symlink(s) inside ${root}`);
    for (const link of links) console.error(`- ${link}`);
    process.exit(1);
  }
  return output;
}

function relative(root, filePath) {
  return path.relative(root, filePath).replace(/\\/g, "/");
}

function hash(filePath) {
  return crypto.createHash("sha256").update(fs.readFileSync(filePath)).digest("hex");
}

if (!fs.existsSync(path.join(source, "SKILL.md"))) {
  console.error(`Source is not a skill directory: ${source}`);
  process.exit(1);
}
if (!fs.existsSync(target)) {
  fs.mkdirSync(target, { recursive: true });
}
// Skills are commonly installed as a junction back to the hub, in which case
// source and target are the same files and every copy would overwrite its own input.
if (fs.realpathSync(source) === fs.realpathSync(target)) {
  console.error(
    `Refusing to sync: source and target resolve to the same directory.\n` +
    `  source ${source}\n  target ${target}\n  both -> ${fs.realpathSync(source)}\n` +
    `  The target is probably a junction/symlink to the source; it is already in sync.`,
  );
  process.exit(1);
}

const sourceFiles = listFiles(source);
for (const file of sourceFiles) {
  const rel = relative(source, file);
  const dest = path.join(target, rel);
  if (dryRun) {
    console.log(`COPY ${rel}`);
  } else {
    fs.mkdirSync(path.dirname(dest), { recursive: true });
    fs.copyFileSync(file, dest);
  }
}

const targetFiles = listFiles(target);
const sourceRel = new Set(sourceFiles.map((file) => relative(source, file)));
function isKept(rel) {
  return keep.some((entry) => rel === entry || rel.startsWith(`${entry}/`));
}
let ok = true;
for (const file of targetFiles) {
  const rel = relative(target, file);
  if (!sourceRel.has(rel) && !isKept(rel)) {
    console.error(`Extra target file: ${rel}`);
    ok = false;
  }
}
for (const file of sourceFiles) {
  const rel = relative(source, file);
  const dest = path.join(target, rel);
  if (!fs.existsSync(dest)) {
    console.error(`Missing target file: ${rel}`);
    ok = false;
  } else if (hash(file) !== hash(dest)) {
    console.error(`Hash mismatch: ${rel}`);
    ok = false;
  }
}

if (!ok) process.exit(1);
console.log(`Synced ${sourceFiles.length} files.`);
