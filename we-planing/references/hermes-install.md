# Installing WePlaning into Hermes (shipping from a hub repo)

If WePlaning lives in a separate repo (e.g. `genius-skill-hub-v2.0/`) and you want to make it available to Hermes:

1. **Smoke-test first** — run `node <hub>/we-planing/tools/smoke-weplaning.cjs` from the hub path. If it doesn't print all `[ok]` lines and exit 0, don't install.
2. **Pick the right category** in `hermes/skills/`. There's no `project-management` category by default in some Hermes installs — `mkdir -p` it if missing. `software-development` is a wrong fit (WePlaning is about project memory, not code).
3. **Link, don't copy** — use a Windows directory junction (`mklink /J`, no admin needed) so changes in the hub flow to Hermes automatically:
   ```bash
   cmd //c "mklink /J C:\Users\<user>\AppData\Local\hermes\skills\project-management\we-planing <hub>\we-planing"
   ```
   `mklink /D` (symbolic link) requires admin or Developer Mode — junction is the right tool for standard users.
4. **Set the agent name** — scripts default the agent name to `$WEPLANING_AGENT` (or `Agent` if unset). Either export `WEPLANING_AGENT=<persona>` once in the environment, or pass `--agent <persona>` on `init-memory.cjs` and every `new-session.cjs` call.

## Junction pitfalls

**Junction target disappears → broken link.**
If the hub repo is moved or deleted, the junction in `hermes/skills/` becomes a dangling empty directory. Hermes won't auto-clean it. If you delete the hub, `rmdir` the junction on the Hermes side too.

**"Copying" the skill can silently write through the link.**
Tooling that duplicates the skill directory to experiment on it — most commonly a script that reverts a fix in a "throwaway copy" to check that a test really catches the bug — must dereference the link first. `fs.cpSync(src, dest, { recursive: true })` in Node defaults to `dereference: false`, so copying a junction/symlink produces **another link to the same files**, and every patch lands in the hub. Resolve the target first (`fs.realpathSync`) or pass `dereference: true`, then assert `fs.lstatSync(copy).isSymbolicLink() === false` before patching. Hash the real files before and after such a run and verify they are unchanged; the failure is otherwise invisible until a later test breaks.

**Junction is a live mirror — git operations on the hub affect Hermes instantly.**
A Windows directory junction (`mklink /J`) is a filesystem-level mirror, not a snapshot. Any operation that rewrites files inside the hub repo's working tree — `git checkout -- <file>`, `git stash`, `git reset --hard`, `git restore`, even `git pull` with conflicts — propagates to `hermes/skills/<category>/<skill>` **immediately**, with no reload and no warning. To archive hub working-tree edits without losing them from the live install, **commit** them (local or remote) — not stash.
