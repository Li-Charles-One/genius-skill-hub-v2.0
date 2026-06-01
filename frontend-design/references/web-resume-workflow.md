# Web Resume / Portfolio Building Workflow

## Pre-flight (BEFORE writing any code)

1. **Confirm direction with user** — style, color, language, target audience. Never assume.
2. **Show 2-3 concept directions** (text description or reference images) and get approval.
3. **Confirm language** — default Chinese unless explicitly requested English.
4. **Confirm content source** — where are their works/portfolio? Can you access it?

## AI Image Generation (Dreamina)

- CLI: `dreamina text2image --prompt="..." --ratio=4:3 --resolution_type=2k`
- Check credits first: `dreamina user_credit`
- Maestro (高级会员) text2image is FREE (credit_count: 0), no credits consumed
- Async workflow: submit → poll every 15-25s → download result
- Model: `high_aes_general_v50` (Seedream v5)

## Self-contained File Delivery (Feishu)

Feishu file upload via lark-cli:
```bash
cd /path/to/project && lark-cli im +messages-send \
  --user-id <open_id> \
  --file ./filename.html
```
- MUST use relative path (cd first)
- Embed images as base64 for single-file delivery
- Send with explanatory markdown message after file

## Anti-patterns (learned the hard way)

- ❌ Writing English when user wants Chinese
- ❌ Assuming Hollywood/dramatic style when user wants minimal/Apple
- ❌ Jumping to implementation without confirming direction
- ❌ Excessive screenshots/vision analysis (token waste)
- ❌ Trying to scrape JS SPAs with curl (use API or Playwright)
