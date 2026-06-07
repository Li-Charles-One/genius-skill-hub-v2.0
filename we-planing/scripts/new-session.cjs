#!/usr/bin/env node

const fs = require("fs");
const path = require("path");
const {
  allowNoCheck,
  generateSessionId,
  parseArgs,
  readThreads,
  renderSessionMd,
  required,
  runCheck,
  sessionPath,
  toList,
  usage,
  utcNow,
  withMemoryLock,
  writeSession,
  writeThreads,
} = require("./weplaning-utils.cjs");

const help = `
Usage:
  node new-session.cjs <project-root> --role <role> --summary <text> --goal <text> [options]

Options:
  --agent <name>       Agent name. Default: Codex
  --adapter <name>     Adapter name. Default: unknown
  --os <name>          OS name. Default: process platform
  --parent <id>        Parent session. Default: current THREADS.md mainline
  --id <id>            Explicit session id
  --short-id <id>      Short suffix when generating an id
  --context <text>     Context-read item. Repeat or separate with ";;"
  --note <text>        Work-note item. Repeat or separate with ";;"
  --no-check           Internal use only; external callers must run consistency checks
`;

const args = parseArgs(process.argv.slice(2));
usage(!args.help, "", help);
allowNoCheck(args, "new-session.cjs");

const root = path.resolve(args._[0] || process.cwd());
const role = required(args, "role", help);
const summary = required(args, "summary", help);
const goal = required(args, "goal", help);
const agent = args.agent || "Codex";
const adapter = args.adapter || "unknown";
const os = args.os || process.platform;
const started = args.started || utcNow();
const sessionId =
  args.id ||
  generateSessionId({
    iso: started,
    agent,
    os,
    role,
    shortId: args["short-id"],
  });

const target = sessionPath(root, sessionId);
const context = toList(args.context);
const notes = toList(args.note);
const contextLines = context.length
  ? context.map((item) => `- ${item}`).join("\n")
  : "- unknown";
const noteLines = notes.length
  ? notes.map((item) => `- ${item}`).join("\n")
  : "- Session opened by script.";

withMemoryLock(root, () => {
  let threads = readThreads(root);
  const parent = args.parent || threads.mainline;

  if (fs.existsSync(target)) {
    console.error(`Session already exists: ${target}`);
    process.exit(1);
  }
  if (threads.rows.some((row) => row.id === sessionId)) {
    console.error(`Session already listed in THREADS.md: ${sessionId}`);
    process.exit(1);
  }

  const before = { threads, sessionExists: fs.existsSync(target) };

  try {
    writeSession(
      root,
      sessionId,
      renderSessionMd({
        sessionId,
        agent,
        adapter,
        os,
        role,
        parentSession: parent,
        status: "active",
        started,
        closed: "unknown",
        goal,
        contextRead: contextLines,
        workNotes: noteLines,
        filesTouched: `- .agent-memory/sessions/${sessionId}.md
- .agent-memory/THREADS.md`,
        decisions: "- none yet",
        result: "Session opened.",
        exactNextStep: "unknown",
      }),
    );

    threads.rows.push({
      id: sessionId,
      parent,
      agent,
      os,
      role,
      status: "active",
      summary,
    });
    writeThreads(root, threads, started);
  } catch (err) {
    writeThreads(root, before.threads, started);
    if (!before.sessionExists && fs.existsSync(target)) fs.rmSync(target, { force: true });
    console.error(`Could not create session: ${err.message}`);
    process.exit(1);
  }
});

if (!args["no-check"]) runCheck(root, __dirname);
console.log(sessionId);
