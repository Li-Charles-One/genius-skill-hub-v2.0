# WePlaning Pitfalls

**1. Don't init memory before the smoke test passes.**
A broken init cascade is harder to recover from than a smoke-test failure caught up front.

**2. Don't write for "完成了" with no fact.**
`weplaning-write.cjs` no-ops trivial oral done. If accepted state changed, pass `--state` / `--next-step`. `--changed` never overwrites Current State.

**3. Junction pitfalls (dangling links, live-mirror git, copies that write through).**
The installed skill path is often a junction to a hub repo, so "isolated copies" made with `fs.cpSync` without `dereference: true` are still the hub. See `hermes-install.md`.

**4. Cross-platform paths in scripts.**
Scripts use forward slashes; on Windows they work via Node's path normalization. Don't edit them to use `\\` — they'll break on Linux/macOS.

**5. When offering destructive choices, every stated consequence must be true.**
`--reinit` discards CURRENT/CHANGES/DECISIONS. `--force` only fills missing files. Never use `--reinit` to "fix" a failing check — run `check-memory` and `repair-memory` first.

**6. Do not create new 2.3 sessions.**
`THREADS.md` / `sessions/` are leftover. New writes go through `weplaning-write.cjs` only.

**7. Repair will not invent CURRENT.md.**
If CURRENT is missing, init (or restore from backup). Repair may recreate CHANGES.md only.

**8. Running memory inside a file-sync folder (Syncthing, Dropbox, iCloud).**
Two devices writing `.agent-memory` concurrently produce sync conflict copies; the lock is process-local. `check-memory.cjs` hard-fails on `*.sync-conflict-*`. Merge anything worth keeping, then delete the copies. Exclude `.backups/` and `.weplaning.lock` from sync rules.

**9. Do not log WePlaning skill upgrades into a business project.**
Put skill changelog in the skill folder. Project memory is for that project's accepted facts.

**10. `--prefer current|threads` is gone.**
3.0 has no mainline session pointer. If leftover THREADS disagrees with an old Mainline session field, ignore the tree.

**11. Section replacement is not item merging.**
Re-read before `--state` / `--next-step`; include still-valid facts/tasks in the replacement. Other sections and custom content are preserved. Missing/empty/duplicate required sections are rejected rather than filled with `unknown`.

**12. Recorded state is not a live check.**
Read time and Last updated do not prove a service is currently healthy. Record verification method/time/result with `--verification`; handoff surfaces that evidence. Keep `unknown` distinct from `none`.

**13. No pending task is a valid stopping point.**
Use `none` / `无待执行事项`, not maintenance slogans. Invalid `--next N` must fail instead of silently selecting #1. Conditional tasks retain their trigger conditions.

**14. Preserve data when repairing and archiving.**
Repair only inserts missing schema lines into otherwise valid content and refuses unsupported/malformed input. Archives use unique names and exclusive creation; repeated runs must retain every previous archive.
