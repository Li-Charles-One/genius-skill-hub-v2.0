# Visual Companion Guide

Browser companion for showing mockups, diagrams, and options during a Full-tier brief.

## When to Use

Decide per question, not per session: **would the user understand this better by seeing it than reading it?**

- **Browser** — the content itself is visual: UI mockups and layouts, architecture or flow diagrams, side-by-side visual comparisons, look-and-feel polish.
- **Terminal** — the answer is words: requirements and scope, conceptual A/B/C choices, trade-off lists, API or data-model decisions, clarifying questions.

A question *about* a UI topic is not automatically visual. "What kind of wizard do you want?" is conceptual. "Which of these wizard layouts feels right?" is visual.

## How It Works

The server watches `screen_dir` and serves the newest HTML file. The user clicks options in the browser; clicks are appended to `state_dir/events`, which you read on your next turn.

Write **content fragments** by default: the server wraps them in the frame template (header, theme CSS, selection indicator, click handling). A file starting with `<!DOCTYPE` or `<html` is served as-is with only the helper script injected; use that only when you need full control of the page.

## Starting a Session

```bash
scripts/start-server.sh --project-dir /path/to/project
# {"type":"server-started","port":52341,"url":"http://localhost:52341",
#  "screen_dir":"/path/to/project/.superpowers/brainstorm/12345-1706000000/content",
#  "state_dir":"/path/to/project/.superpowers/brainstorm/12345-1706000000/state"}
```

Save `screen_dir` and `state_dir`, and tell the user to open the URL. The same JSON is written to `<state_dir>/server-info`; read it there if stdout was not captured.

With `--project-dir`, mockups persist in `<project>/.superpowers/brainstorm/` (remind the user to gitignore `.superpowers/`). Without it, files go to `/tmp` and are deleted on stop.

The server must stay alive across turns. The script backgrounds itself, except where background processes get reaped:

| Environment | What to do |
|---|---|
| macOS / Linux | Run the command as shown |
| Windows Git Bash, Codex (`CODEX_CI`) | Auto-switches to foreground, which blocks: launch the call with your runtime's background-execution option, then read `server-info` next turn |
| Other runtimes that reap detached processes | Add `--foreground` and launch with the runtime's background-execution option |
| Remote or containerized (URL unreachable) | Add `--host 0.0.0.0 --url-host localhost`; `--url-host` sets the hostname printed in the URL |

**Windows PowerShell (no bash):** the launchers are bash-only, so start `server.cjs` directly, in the background:

```powershell
$session = "C:\path\to\project\.superpowers\brainstorm\$PID-$([int][double]::Parse((Get-Date -UFormat %s)))"
New-Item -ItemType Directory -Force -Path "$session\content","$session\state" | Out-Null
$env:BRAINSTORM_DIR = $session
$env:BRAINSTORM_HOST = '127.0.0.1'
$env:BRAINSTORM_URL_HOST = 'localhost'
node 'C:\path\to\skills\genius-brief-thinking\scripts\server.cjs'
```

The first stdout line is the same `server-started` JSON, and `state\server-info` / `state\events` behave the same. Stop it with Ctrl+C or `Stop-Process -Id <pid>` (`Get-NetTCPConnection -LocalPort <port>` finds the listener).

## The Loop

1. **Check the server, then write a new HTML file** to `screen_dir`.
   - If `<state_dir>/server-info` is missing or `<state_dir>/server-stopped` exists, the server has exited (it stops after 30 minutes idle): restart it first.
   - Semantic filenames (`platform.html`, `layout.html`); a revision is `layout-v2.html`. Never reuse a filename: the server serves the newest file by modification time.
   - Use the file-write tool, not `cat` or a heredoc.
2. **Tell the user what to expect and end your turn.** Repeat the URL every time, summarize what is on screen in one line, and ask them to reply in the terminal (clicking an option is optional).
3. **Next turn:** read `<state_dir>/events` if it exists and merge it with the terminal reply. The terminal message is the primary feedback.
4. **Iterate or advance.** Feedback that changes the current screen gets a new file. Move on only when the current step is settled.
5. **Clear the screen when returning to the terminal.** Push a waiting file so the user is not looking at a resolved choice:

   ```html
   <div style="display:flex;align-items:center;justify-content:center;min-height:60vh">
     <p class="subtitle">Continuing in terminal...</p>
   </div>
   ```

## Content Fragments

No `<html>`, CSS, or `<script>` needed. A complete screen:

```html
<h2>Which layout works better?</h2>
<p class="subtitle">Consider readability and visual hierarchy</p>

<div class="options">
  <div class="option" data-choice="a" onclick="toggleSelect(this)">
    <div class="letter">A</div>
    <div class="content">
      <h3>Single Column</h3>
      <p>Clean, focused reading experience</p>
    </div>
  </div>
  <div class="option" data-choice="b" onclick="toggleSelect(this)">
    <div class="letter">B</div>
    <div class="content">
      <h3>Two Column</h3>
      <p>Sidebar navigation with main content</p>
    </div>
  </div>
</div>
```

Add `data-multiselect` to the `.options` or `.cards` container to allow several selections.

Other building blocks from the frame template:

```html
<!-- Cards: visual designs -->
<div class="cards">
  <div class="card" data-choice="design1" onclick="toggleSelect(this)">
    <div class="card-image"><!-- mockup content --></div>
    <div class="card-body"><h3>Name</h3><p>Description</p></div>
  </div>
</div>

<!-- Mockup container; wrap two in <div class="split"> for side-by-side -->
<div class="mockup">
  <div class="mockup-header">Preview: Dashboard Layout</div>
  <div class="mockup-body"><!-- your mockup HTML --></div>
</div>

<!-- Pros / cons -->
<div class="pros-cons">
  <div class="pros"><h4>Pros</h4><ul><li>Benefit</li></ul></div>
  <div class="cons"><h4>Cons</h4><ul><li>Drawback</li></ul></div>
</div>

<!-- Wireframe blocks -->
<div class="mock-nav">Logo | Home | About | Contact</div>
<div style="display: flex;">
  <div class="mock-sidebar">Navigation</div>
  <div class="mock-content">Main content area</div>
</div>
<button class="mock-button">Action Button</button>
<input class="mock-input" placeholder="Input field">
<div class="placeholder">Placeholder area</div>
```

Text helpers: `h2` page title, `h3` section heading, `.subtitle`, `.section` (block with bottom margin), `.label` (small uppercase).

## Browser Events

`<state_dir>/events` holds one JSON object per line and is cleared when you push a new screen:

```jsonl
{"type":"click","choice":"a","text":"Option A - Simple Layout","timestamp":1706000101}
{"type":"click","choice":"b","text":"Option B - Hybrid","timestamp":1706000115}
```

The last event is usually the final pick; earlier clicks show hesitation worth asking about. No file means the user did not interact with the browser.

## Design Tips

- Scale fidelity to the question: wireframes for layout, polish only for polish questions.
- State the question on every page ("Which layout feels more professional?", not "Pick one").
- 2–4 options per screen.
- Use real content when it matters; placeholder content hides design problems.

## Cleaning Up

```bash
scripts/stop-server.sh <session_dir>
```

`<session_dir>` is the parent of `screen_dir`. Project sessions keep their mockups; only `/tmp` sessions are deleted.

CSS reference: `scripts/frame-template.html`. Client script: `scripts/helper.js`.
