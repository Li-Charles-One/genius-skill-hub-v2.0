#!/usr/bin/env node

const path = require("path");
const {
  emitResult,
  parseArgs,
  parseSessionMd,
  readSession,
  readThreads,
  renderSessionMd,
  required,
  runCheck,
  usage,
  utcNow,
  withMemoryLock,
  writeSession,
  writeThreads,
} = require("./weplaning-utils.cjs");

const help = `
Usage:
  node session-status.cjs <project-root> --session <id> --pause|--resume|--abandon [options]

Transitions (refuses merged mainline sessions):
  --pause      active -> paused
  --resume     paused -> active
  --abandon    active|paused|closed -> abandoned

Options:
  --reason <text>   Appended to Work Notes
  --json            Machine-readable JSON on stdout
  --no-check        Internal use only
`;

const args = parseArgs(process.argv.slice(2));
usage(!args.help, "", help);

const actionCount = [args.pause, args.resume, args.abandon].filter(Boolean).length;
usage(actionCount === 1, "Choose exactly one of: --pause, --resume, --abandon", help);

const root = path.resolve(args._[0] || process.cwd());
const sessionId = required(args, "session", help);
const action = args.pause ? "pause" : args.resume ? "resume" : "abandon";
const now = args.time || utcNow();
const reason = args.reason ? String(args.reason) : "";

const transitions = {
  pause: { from: ["active"], to: "paused" },
  resume: { from: ["paused"], to: "active" },
  abandon: { from: ["active", "paused", "closed"], to: "abandoned" },
};

let nextStatus = null;

withMemoryLock(root, () => {
  const sessionText = readSession(root, sessionId);
  const session = parseSessionMd(sessionText);
  if (session.status === "merged") {
    console.error(`Refusing to ${action} merged session ${sessionId}.`);
    process.exit(1);
  }

  const rule = transitions[action];
  if (!rule.from.includes(session.status)) {
    console.error(
      `Cannot ${action} session ${sessionId} from status '${session.status}'. Allowed from: ${rule.from.join(", ")}.`,
    );
    process.exit(1);
  }

  nextStatus = rule.to;
  session.status = nextStatus;
  if (nextStatus === "abandoned" || nextStatus === "paused") {
    if (!session.closed || session.closed === "unknown" || session.closed === "(open)") {
      // paused stays open-ish; only set closed for abandon
      if (nextStatus === "abandoned") session.closed = now;
    }
  }
  if (nextStatus === "active") {
    session.closed = "unknown";
  }
  if (reason) {
    const note = `${action}: ${reason}`;
    const base = String(session.workNotes || "").replace(/\s*$/, "");
    session.workNotes = base ? `${base}\n- ${note}` : `- ${note}`;
  }
  writeSession(root, sessionId, renderSessionMd(session));

  const threads = readThreads(root);
  const row = threads.rows.find((item) => item.id === sessionId);
  if (!row) {
    console.error(`Session is not listed in THREADS.md: ${sessionId}`);
    process.exit(1);
  }
  row.status = nextStatus;
  writeThreads(root, threads, now);
});

if (!args["no-check"] && process.env.WEPLANING_INTERNAL_NO_CHECK !== "1") {
  runCheck(root, __dirname);
}

emitResult(args, `${sessionId} -> ${nextStatus}`, {
  sessionId,
  action,
  status: nextStatus,
});
