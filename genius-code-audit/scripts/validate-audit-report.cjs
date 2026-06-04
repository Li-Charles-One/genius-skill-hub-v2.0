#!/usr/bin/env node

const fs = require("fs");
const path = require("path");

const reportPath = process.argv[2];
if (!reportPath) {
  console.error("Usage: node scripts/validate-audit-report.cjs <report.html>");
  process.exit(1);
}

const fullPath = path.resolve(reportPath);
if (!fs.existsSync(fullPath)) {
  console.error(`Report not found: ${fullPath}`);
  process.exit(1);
}

const html = fs.readFileSync(fullPath, "utf8");
const errors = [];

function fail(message) {
  errors.push(message);
}

const placeholders = [...html.matchAll(/\{\{[A-Z0-9_]+\}\}/g)].map((match) => match[0]);
if (placeholders.length) {
  fail(`Unreplaced placeholders: ${[...new Set(placeholders)].join(", ")}`);
}

function countIssueClass(name) {
  const pattern = new RegExp(`class=["'][^"']*\\bissue\\s+${name}\\b[^"']*["']`, "g");
  return (html.match(pattern) || []).length;
}

function readSummaryCount(label) {
  const patterns = [
    new RegExp(`<div class=["']stat ${label}["']>[\\s\\S]*?<div class=["']num["']>(\\d+)</div>`, "i"),
    new RegExp(`<td>${label[0].toUpperCase()}${label.slice(1)}</td>\\s*<td>(\\d+)</td>`, "i"),
  ];
  for (const pattern of patterns) {
    const match = html.match(pattern);
    if (match) return Number(match[1]);
  }
  return null;
}

for (const name of ["fatal", "severe", "fix", "suggest", "arch"]) {
  const expected = readSummaryCount(name);
  if (expected === null) {
    fail(`Missing summary count for ${name}`);
    continue;
  }
  const actual = countIssueClass(name);
  if (actual !== expected) {
    fail(`${name} count mismatch: summary=${expected}, issue blocks=${actual}`);
  }
}

const totalMatch = html.match(/<strong>Total Issues<\/strong><br>(\d+)/i) || html.match(/<td>Total<\/td>\s*<td>(\d+)<\/td>/i);
if (!totalMatch) {
  fail("Missing total issue count");
} else {
  const total = Number(totalMatch[1]);
  const actualTotal = ["fatal", "severe", "fix", "suggest", "arch"]
    .map(countIssueClass)
    .reduce((sum, value) => sum + value, 0);
  if (actualTotal !== total) {
    fail(`total count mismatch: summary=${total}, issue blocks=${actualTotal}`);
  }
}

const invalidIssueClasses = [...html.matchAll(/class=["'][^"']*\bissue\s+([a-z-]+)\b[^"']*["']/g)]
  .map((match) => match[1])
  .filter((name) => !["fatal", "severe", "fix", "suggest", "arch"].includes(name));
if (invalidIssueClasses.length) {
  fail(`Invalid issue classes: ${[...new Set(invalidIssueClasses)].join(", ")}`);
}

if (errors.length) {
  console.error("Audit report validation failed:");
  for (const error of errors) console.error(`- ${error}`);
  process.exit(1);
}

console.log("Audit report validation passed.");
