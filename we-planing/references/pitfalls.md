# WePlaning Pitfalls

**1. Don't init memory before the smoke test passes.**
A broken init cascade is harder to recover from than a smoke-test failure caught up front.

**2. Don't run closeout for "just a quick note".**
Use `weplaning-note.cjs`. Closeout appends `CHANGES.md` and merges the session; using it for transient state pollutes the mainline ledger. Oral "完成了" is a note, not closeout.

**3. Junction pitfalls (dangling links, live-mirror git, copies that write through).**
The installed skill path is often a junction to a hub repo, so "isolated copies" made with `fs.cpSync` without `dereference: true` are still the hub. See `hermes-install.md`.

**4. Cross-platform paths in scripts.**
Scripts use forward slashes; on Windows they work via Node's path normalization. Don't edit them to use `\\` — they'll break on Linux/macOS.

**5. When offering destructive choices, every stated consequence must be true.**
Verify against the actual environment — junction semantics, process locks, schema invariants. If you cannot verify, say so instead of writing a confident wrong description.

**6. `safe-edit.cjs --close` requires the session's `Parent session:` to equal `THREADS.md` mainline.**
Otherwise it fails with "Stale write blocked". Close the active predecessor first, or repoint `Parent session:` at the true mainline. Lock cleanup on failure is automatic; if a lock lingers after a crash, remove `<project>/.agent-memory/.weplaning.lock`.

**7. Prefer explicit `CURRENT.md` sync flags on closeout.**
Without `--no-sync`, close auto-sets Current State from `--changed`. `weplaning-close.cjs` defaults to `--no-sync`. Closes that would discard 2 or more curated bullets are refused unless you pass `--state`, `--no-sync`, or `--replace-state`. The guard only protects Current State — still pass `--next-step` / `--blockers` / `--goal` when those sections should change.

**8. `repair-memory.cjs` will not guess on mainline mismatch.**
If CURRENT and THREADS disagree, it exits until you pass `--prefer current` or `--prefer threads`. Do not use repair as a silent authority rewrite.

**9. Running memory inside a file-sync folder (Syncthing, Dropbox, iCloud).**
Two devices writing `.agent-memory` concurrently produce sync conflict copies; the lock is process-local. `check-memory.cjs` hard-fails on `*.sync-conflict-*`. Merge anything worth keeping, then delete the copies. Exclude `.backups/` and `.weplaning.lock` from sync rules.

**10. `init-memory --reinit` is a total wipe, `--force` is not.**
`--force` only creates missing files and adopts the surviving mainline. `--reinit` rebuilds `CURRENT.md`, `THREADS.md`, `CHANGES.md`, and `DECISIONS.md` from scratch and prints how many session rows and change blocks it is discarding. Never use `--reinit` to "fix" a failing check — run `check-memory` and `repair-memory` first.
