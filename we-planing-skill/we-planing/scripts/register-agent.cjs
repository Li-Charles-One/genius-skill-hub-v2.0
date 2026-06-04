#!/usr/bin/env node

const path = require("path");
const {
  osToken,
  allowNoCheck,
  parseArgs,
  readMemory,
  replaceOrAppendTableRow,
  required,
  runCheck,
  toList,
  usage,
  utcNow,
  writeMemory,
} = require("./weplaning-utils.cjs");

const help = `
Usage:
  node register-agent.cjs <project-root> --session <id> --agent <name> --adapter <name> [options]

Options:
  --os <name>       OS name. Default: process platform
  --tool <name>     Repeat or separate with ";;"
  --mcp <status>    MCP status. Default: unknown
  --skill <name>    Repeat or separate with ";;"
  --notes <text>    Notes. Default: Registered by script
  --no-check        Internal use only; external callers must run consistency checks
`;

const args = parseArgs(process.argv.slice(2));
usage(!args.help, "", help);
allowNoCheck(args, "register-agent.cjs");

const root = path.resolve(args._[0] || process.cwd());
const sessionId = required(args, "session", help);
const agent = required(args, "agent", help);
const adapter = required(args, "adapter", help);
const os = osToken(args.os || process.platform);
const tools = toList(args.tool || args.tools).join(", ") || "unknown";
const mcp = args.mcp || "unknown";
const skills = toList(args.skill || args.skills).join(", ") || "unknown";
const notes = args.notes || "Registered by script";
const now = args.time || utcNow();

let toolsText = readMemory(root, "TOOLS.md");
toolsText = toolsText.replace(/^Last updated:\s*.*$/m, `Last updated: ${now}`);
toolsText = replaceOrAppendTableRow(toolsText, "## Agent Sessions", sessionId, [
  sessionId,
  agent,
  os,
  adapter,
  tools,
  mcp,
  skills,
  notes,
]);

writeMemory(root, "TOOLS.md", toolsText);
if (!args["no-check"]) runCheck(root, __dirname);
console.log(sessionId);
