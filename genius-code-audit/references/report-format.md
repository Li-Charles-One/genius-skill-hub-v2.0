# Report Format

Generate a self-contained HTML report using `assets/audit-report-template.html`.

## Filename

Save reports to the workspace root when possible:

```text
Code-Audit-YYYY-MM-DD-<project>.html
```

If the user explicitly asks for "Linus" branding, this filename is also acceptable:

```text
Linus-Audit-YYYY-MM-DD-<project>.html
```

## Required Template Variables

The final report must replace every placeholder:

| Placeholder | Meaning |
|:--|:--|
| `{{PROJECT_NAME}}` | Project or repository name. |
| `{{AUDIT_DATE}}` | Date in YYYY-MM-DD. |
| `{{AUDIT_SCOPE}}` | Example: `Diff: origin/main..HEAD` or `Full: src, app, scripts`. |
| `{{AUDIT_MODE}}` | `diff` or `full`. |
| `{{TOTAL_ISSUES}}` | Sum of all findings. |
| `{{FATAL_COUNT}}` | Count of `.issue.fatal`. |
| `{{SEVERE_COUNT}}` | Count of `.issue.severe`. |
| `{{FIX_COUNT}}` | Count of `.issue.fix`. |
| `{{SUGGEST_COUNT}}` | Count of `.issue.suggest`. |
| `{{ARCH_COUNT}}` | Count of `.issue.arch`. |
| `{{FATAL_PCT}}` | Percentage of total. |
| `{{SEVERE_PCT}}` | Percentage of total. |
| `{{FIX_PCT}}` | Percentage of total. |
| `{{SUGGEST_PCT}}` | Percentage of total. |
| `{{ARCH_PCT}}` | Percentage of total. |
| `{{FILE_DISTRIBUTION_ROWS}}` | `<tr><td class="file-col">path</td><td>N</td></tr>` rows. |
| `{{FATAL_ISSUES}}` | HTML issue blocks for fatal findings. |
| `{{SEVERE_ISSUES}}` | HTML issue blocks for severe findings. |
| `{{FIX_ISSUES}}` | HTML issue blocks for fix findings. |
| `{{SUGGEST_ISSUES}}` | HTML issue blocks for suggestions. |
| `{{ARCHITECTURE_SECTION}}` | Full architecture section or an empty string. |
| `{{ARCH_SUMMARY_ROW}}` | Summary row for architecture items or an empty string. |
| `{{SUMMARY_VERDICT}}` | Two or three paragraphs summarizing the audit result. |
| `{{CLOSING_QUOTE}}` | A concise closing line. |

## Issue Block

Use this structure for every finding:

```html
<div class="issue fix">
  <div class="issue-header">
    <span class="severity severity-fix">FIX</span>
    <span class="issue-title">Short title</span>
    <span class="file">path/to/file.ts:42</span>
  </div>
  <div class="issue-body">
    <div class="code-block"><pre>short code excerpt with the problem marked</pre></div>
    <p><strong>Problem:</strong> What actually breaks.</p>
    <p><strong>Fix:</strong> Concrete repair steps.</p>
  </div>
</div>
```

For architecture items, use `class="issue arch"` and `severity-arch`.

## Validation

After writing the report, run:

```powershell
node <skill-dir>/scripts/validate-audit-report.cjs <report.html>
```

The validator checks:

- no unreplaced `{{PLACEHOLDER}}` tokens remain;
- all required summary count placeholders were replaced;
- `.issue` counts match the summary numbers;
- issue class names are one of `fatal`, `severe`, `fix`, `suggest`, or `arch`.

If validation fails, fix the report before presenting it as complete.
