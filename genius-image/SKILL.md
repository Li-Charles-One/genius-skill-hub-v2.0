---
name: genius-image
description: Use when the user explicitly asks to use Genius Image, GRSai, gpt-image-2, nano-banana, banana consistency, or the third-party GRSai image API for image generation, reference-image generation, batch image generation, or visual assets. Do not use for ordinary image generation unless the user requests this provider.
---

# Genius Image - GRSai gpt-image-2 生图

## 触发

用户明确要求使用 Genius Image、GRSai、`gpt-image-2`、`nano-banana`、`banana` 一致性，或指定走第三方 GRSai 生图接口时使用本技能。

普通「生图」「生成一张」「图片生成」「AI 绘图」请求优先使用 Codex 当前环境提供的原生图片生成能力，除非用户点名本技能或 GRSai。

## 默认比例

**除非用户明确指定比例，否则一律使用 `16:9`。**

## 模型选择

| 场景 | 模型 | 参数 |
|------|------|------|
| 默认 | `gpt-image-2` | `aspectRatio`（默认 `"16:9"`，也可传 1K 像素值） |
| 一致性 | `nano-banana-2` | `aspectRatio` + `imageSize` |
| 普通 2K/4K | `nano-banana-2` | `aspectRatio` + `imageSize` |
| 艺术性高清 2K/4K | `gpt-image-2-vip` | `aspectRatio`（像素值） |
| 特别要求高质量/专业/增强一致性 2K/4K | `nano-banana-pro` | `aspectRatio` + `imageSize` |

选择规则：

- 用户只说「2K」或「4K」时，使用 `nano-banana-2` + 对应 `imageSize`。
- 用户明确说「特别高清」「高质量」「专业级」「增强一致性」「pro」或类似要求时，才使用 `nano-banana-pro`。
- 用户强调艺术性、质感、审美风格并要求 2K/4K 时，优先使用 `gpt-image-2-vip`。
- 用户强调角色/产品/主体一致性时，优先使用 `nano-banana-2`；如果同时特别要求高质量或 pro，再升级到 `nano-banana-pro`。

## 配置

- **API Key**: 存放在 `GRSAI_API_KEY` 环境变量。若本机会话未加载，可从 `$HOME/.codex/.env` 读取
- **Base URL**: `GRSAI_BASE_URL`，默认 `https://grsaiapi.com`（全球节点）。国内节点 `https://grsai.dakka.com.cn`，遇到 `excessive system load` 时可切换。

## 执行边界

- 这是第三方 GRSai API；只有用户点名本技能、GRSai、相关模型或明确要走该接口时才使用。
- 上传参考图前，简短提醒用户参考图会发送到第三方服务；用户已经明确要求用参考图生成时无需反复确认。
- 高分辨率、pro 模型和批量生成可能消耗更多额度；用户明确要求这些能力时继续执行，并在状态更新里轻描淡写说明。
- 不要把 API key 写入日志、文件、最终回复或 Markdown 图片链接。

## 分辨率

### 速查（常用比例像素值）

完整分辨率表 → `references/resolutions.md`

```
          gpt-image-2   vip-1K      vip-2K      vip-4K
16:9      1672x941      1280x720    2048x1152   3840x2160
1:1       1024x1024     1024x1024   2048x2048   2880x2880
9:16      941x1672      720x1280    1152x2048   2160x3840
4:3       1443x1090     1152x864    2304x1728   3264x2448
3:4       1090x1443     864x1152    1728x2304   2448x3264
3:2       1536x1024     1536x1024   2048x1360   3504x2336
2:3       1024x1536     1024x1536   1360x2048   2336x3504
```

### gpt-image-2

传比例字符串（`"16:9"`、`"1:1"` 等）或 1K 像素值。用户说「16:9」「方形」→ 直接传 `"16:9"` 或 `"1:1"`，不自己算像素。比例被误判或服务不稳定时优先改用像素值重试。

### gpt-image-2-vip

只传像素值（如 `"1280x720"`、`"2048x1152"`、`"3840x2160"`），不支持比例字符串。

自定义像素值约束：
- 最大边 ≤3840px
- 两边皆 16 的倍数
- 长边:短边 ≤3:1
- 总像素 655,360~8,294,400

完整 1K/2K/4K 像素表见 `references/resolutions.md`。

### nano-banana-2 / nano-banana-pro（传比例 + imageSize）

```
aspectRatio: 1:1 / 16:9 / 9:16 / 4:3 / 3:4 / 3:2 / 2:3 / 5:4 / 4:5 / 21:9 / auto
nano-banana-2 额外: 1:4 / 4:1 / 1:8 / 8:1
imageSize: 1K / 2K / 4K
```

默认 `imageSize: "1K"`。用户说「2K」「4K」时用 `nano-banana-2` + 对应 `imageSize`；只有特别要求高质量、专业、增强一致性或 pro 时才用 `nano-banana-pro`。

## 流程

> **OS 实测**: Windows (Python / PowerShell) ✅ · macOS/Linux (Python) 未实测，预期可移植
>
> 首选 `scripts/generate.py`（跨平台，一行命令）。curl / PowerShell 示例作为参考备用。

### 首选：Python 脚本

```bash
# 单张
python scripts/generate.py "提示词"

# 批量（并发）
python scripts/generate.py "提示词1" "提示词2" "提示词3" --concurrency 3
python scripts/generate.py --batch prompts.txt --model gpt-image-2-vip --concurrency 5

# 异步轮询（长耗时单张）
python scripts/generate.py "提示词" --async

# 参考图
python scripts/generate.py "提示词" --ref image.png
python scripts/generate.py "提示词" --ref https://example.com/ref.png

# JSON 输出
python scripts/generate.py "提示词" --json
```

详细选项: `python scripts/generate.py --help`。

执行前确认 `GRSAI_API_KEY` 已在环境变量或 `~/.codex/.env` 中。

### 备选：curl / PowerShell 直连

PowerShell 如需加载 `$HOME/.codex/.env`：

```powershell
$envPath = Join-Path $HOME ".codex\.env"
if (Test-Path $envPath) {
  Get-Content $envPath | ForEach-Object {
    if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
      [Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim().Trim('"').Trim("'"), "Process")
    }
  }
}
$base = if ($env:GRSAI_BASE_URL) { $env:GRSAI_BASE_URL } else { "https://grsaiapi.com" }
```

Unix shell 如需加载：

```bash
set -a
[ -f "$HOME/.codex/.env" ] && . "$HOME/.codex/.env"
set +a
base="${GRSAI_BASE_URL:-https://grsaiapi.com}"
```

### 单张图片优先：同步 JSON 请求

对单张图片，优先使用 `replyType: "json"`，这是 GRSai 文档示例格式，成功时直接返回 `status: "succeeded"` 和 `results[0].url`。

```bash
curl -s -X POST "$base/v1/api/generate" \
  -H "Authorization: Bearer $GRSAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "<gpt-image-2 / gpt-image-2-vip / nano-banana-2 / nano-banana-pro>",
    "prompt": "<用户提示词>",
    "images": [],
    "aspectRatio": "<比例或像素值>",
    "imageSize": "<仅 nano 需要: 1K / 2K / 4K>",
    "replyType": "json"
  }'
```

> **注意**: `gpt-image-2` 可传比例或 1K 像素值；`gpt-image-2-vip` 必须传像素值；gpt 模型忽略 `imageSize`。

PowerShell 同步请求：

```powershell
$body = @{
  model = "gpt-image-2"
  prompt = "<用户提示词>"
  images = @()
  aspectRatio = "16:9"
  replyType = "json"
} | ConvertTo-Json

Invoke-RestMethod -Uri "$base/v1/api/generate" `
  -Headers @{ Authorization = "Bearer $env:GRSAI_API_KEY" } `
  -Method Post -ContentType "application/json" -Body $body
```

### 单张长耗时任务：发起异步

```bash
curl -s -X POST "$base/v1/api/generate" \
  -H "Authorization: Bearer $GRSAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "<gpt-image-2 / gpt-image-2-vip / nano-banana-2 / nano-banana-pro>",
    "prompt": "<用户提示词>",
    "aspectRatio": "<比例或像素值>",
    "imageSize": "<仅 nano 需要: 1K / 2K / 4K>",
    "replyType": "async"
  }'
```

> **注意**: nano-banana 模型不需要传 `imageSize` 时省略该字段即可；gpt 模型忽略该字段。

返回 `{"id": "<task_id>", "status": "running"}`，提取 `TASK_ID`。响应中的 `progress` 字段（0-100）可用于展示进度。

### 第二步：轮询结果

```bash
for i in $(seq 1 60); do
  resp=$(curl -s "$base/v1/api/result?id=$TASK_ID" \
    -H "Authorization: Bearer $GRSAI_API_KEY")
  status=$(echo "$resp" | jq -r '.status')
  if [ "$status" = "succeeded" ]; then
    echo "$resp" | jq -r '.results[0].url'
    break
  elif [ "$status" = "failed" ] || [ "$status" = "violation" ]; then
    echo "ERROR: $status — $(echo "$resp" | jq -r '.error')"
    exit 1
  fi
  sleep 5
done
# 超时未完成
echo "轮询超时（5 分钟），任务 $TASK_ID 可能仍在处理中，稍后可查询：$base/v1/api/result?id=$TASK_ID"
```

PowerShell 轮询示例：

```powershell
for ($i = 0; $i -lt 60; $i++) {
  $resp = Invoke-RestMethod -Uri "$base/v1/api/result?id=$TASK_ID" `
    -Headers @{ Authorization = "Bearer $env:GRSAI_API_KEY" }
  if ($resp.status -eq "succeeded") {
    $resp.results[0].url
    break
  }
  if ($resp.status -eq "failed" -or $resp.status -eq "violation") {
    throw "ERROR: $($resp.status) - $($resp.error)"
  }
  Start-Sleep -Seconds 5
}
# 超时未完成
if ($resp.status -ne "succeeded") {
  Write-Host "轮询超时（5 分钟），任务 $TASK_ID 可能仍在处理中，稍后可查询：$base/v1/api/result?id=$TASK_ID"
}
```

拿到 url 后先下载到本地，再用本地绝对路径的 Markdown 图片链接展示。

## 状态码

| status | error | 含义 | 处理 |
|--------|-------|------|------|
| `succeeded` | — | 生成成功 | 提取 url 展示 |
| `running` | — | 进行中 | 继续轮询 |
| `failed` | `apikey error` | key 无效或过期，两个节点都返回此错误 | 确认 key 在 .env 中正确加载（51 字符 `sk-` 前缀），如仍报错则 key 本身已失效，需去 GRSai 后台检查 |
| `failed` | `insufficient credits` | **可能不是真缺额度**，有时是服务端过载挡回来的假报错 | 告知「服务端拒绝，可能是负载过高」，建议稍后重试或换节点 |
| `failed` | `excessive system load` | 服务端过载 | 等几分钟重试，或切另一个节点（全球↔国内） |
| `failed` | 其他 | 生成失败 | 查看 error 字段，告知用户 |
| `violation` | — | 违规 | 告知用户 prompt 违规，建议修改 |
| *(空响应)* | — | async 模式 key 无效时返回 HTTP 200 + 空 body，比 sync 更难诊断 | 先用 sync 模式（不带 `replyType`）验证连通性，sync 会返回明确错误信息 |

## 参考图（可选）

如果用户提供了参考图，加到 `images` 数组（base64 或 URL）：

```json
{
  "images": ["https://example.com/ref.png"]
}
```

参考图 base64 编码命令：
- Linux/macOS: `base64 -w0 image.png`
- Windows PowerShell: `[Convert]::ToBase64String([IO.File]::ReadAllBytes("image.png"))`

## 并发（批量生图）

**GRSai 支持并发请求。** 实测 5 并发同步请求约 40-55s/张，总耗时约 60s（gpt-image-2，16:9）。批量生图用并发同步请求，比异步轮询更快更简单。

bash 并发（N 张并行）：
```bash
for prompt in "提示词1" "提示词2" "提示词3"; do
  curl -s -X POST "$base/v1/api/generate" \
    -H "Authorization: Bearer $GRSAI_API_KEY" \
    -H "Content-Type: application/json" \
    -d "{\"model\":\"gpt-image-2\",\"prompt\":\"$prompt\",\"images\":[],\"aspectRatio\":\"16:9\",\"replyType\":\"json\"}" &
done
wait
```

PowerShell 并发（Start-Job）：
```powershell
$prompts = @("提示词1", "提示词2", "提示词3")
$prompts | ForEach-Object {
  Start-Job -ScriptBlock {
    param($p, $b, $k)
    Invoke-RestMethod -Uri "$b/v1/api/generate" `
      -Headers @{ Authorization = "Bearer $k" } `
      -Method Post -ContentType "application/json" `
      -Body (@{model="gpt-image-2"; prompt=$p; images=@(); aspectRatio="16:9"; replyType="json"} | ConvertTo-Json)
  } -ArgumentList $_, $base, $env:GRSAI_API_KEY
}
Get-Job | Wait-Job | Receive-Job
Get-Job | Remove-Job
```

## 输出规范

- 拿到 url 后先下载成本地文件，再展示给用户。下载目录按优先级：
  1. 项目根目录 → `.codex/generated-images/`
  2. 工作区 → `outputs/genius-image/`
  3. 兜底 → 系统临时目录（Windows: `$env:TEMP\codex\genius-image\`，Unix: `~/.codex/tmp/genius-image/`）
- 展示时优先使用本地绝对路径的 Markdown 图片链接
- 同时保留原始 URL 作为备用链接
- 第一步发起后说一句「生成中，预计 30-60 秒」
- 失败时一句话说明原因 + 建议
