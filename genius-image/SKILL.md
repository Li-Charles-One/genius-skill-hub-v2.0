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
- **Base URL**: `GRSAI_BASE_URL`，默认 `https://grsaiapi.com`

## 执行边界

- 这是第三方 GRSai API；只有用户点名本技能、GRSai、相关模型或明确要走该接口时才使用。
- 上传参考图前，简短提醒用户参考图会发送到第三方服务；用户已经明确要求用参考图生成时无需反复确认。
- 高分辨率、pro 模型和批量生成可能消耗更多额度；用户明确要求这些能力时继续执行，并在状态更新里轻描淡写说明。
- 不要把 API key 写入日志、文件、最终回复或 Markdown 图片链接。

## 分辨率

### gpt-image-2（传比例字符串或 1K 像素）

```
auto
1:1 → 1024x1024      16:9 → 1672x941      9:16 → 941x1672
4:3 → 1443x1090      3:4 → 1090x1443      3:2 → 1536x1024
2:3 → 1024x1536      5:4 → 1408x1120      4:5 → 1120x1408
21:9 → 1920x832      9:21 → 832x1920      2:1 → 1792x896
1:2 → 896x1792
```

用户说「16:9」「方形」→ 直接传 `"16:9"` 或 `"1:1"` 到 `aspectRatio`，不自己算像素。
也可以按文档示例传 1K 像素值，例如 `"1024x1024"`；当比例请求被误判或服务不稳定时，优先改用像素值重试。

### gpt-image-2-vip（艺术性高清，只传像素值，支持 1K/2K/4K）

`gpt-image-2-vip` 不支持比例字符串。必须给 `aspectRatio` 传像素值，例如 `"1280x720"`、`"2048x1152"`、`"3840x2160"`。

自定义像素值约束：

- 最大边长小于或等于 3840px
- 两条边都是 16 的倍数
- 长边与短边之比不超过 3:1
- 总像素数在 655,360 到 8,294,400 之间

**1K：**
```
1:1 → 1024x1024      16:9 → 1280x720       9:16 → 720x1280
4:3 → 1152x864       3:4 → 864x1152       3:2 → 1536x1024
2:3 → 1024x1536      5:4 → 1120x896       4:5 → 896x1120
21:9 → 1456x624      9:21 → 624x1456
```

**2K（默认）：**
```
1:1 → 2048x2048      16:9 → 2048x1152      9:16 → 1152x2048
4:3 → 2304x1728      3:4 → 1728x2304      3:2 → 2048x1360
2:3 → 1360x2048      5:4 → 2240x1792      4:5 → 1792x2240
21:9 → 2912x1248     9:21 → 1248x2912     2:1 → 3072x1536
1:2 → 1536x3072      1:3 → 688x2048       3:1 → 2048x688
```

**4K（用户说「4K」时用）：**
```
1:1 → 2880x2880      16:9 → 3840x2160      9:16 → 2160x3840
4:3 → 3264x2448      3:4 → 2448x3264      3:2 → 3504x2336
2:3 → 2336x3504      5:4 → 3200x2560      4:5 → 2560x3200
21:9 → 3840x1648     9:21 → 1648x3840     2:1 → 3840x1920
1:2 → 1920x3840      1:3 → 1280x3840      3:1 → 3840x1280
```

### nano-banana-2 / nano-banana-pro（传比例 + imageSize）

```
aspectRatio: 1:1 / 16:9 / 9:16 / 4:3 / 3:4 / 3:2 / 2:3 / 5:4 / 4:5 / 21:9 / auto
nano-banana-2 额外: 1:4 / 4:1 / 1:8 / 8:1
imageSize: 1K / 2K / 4K
```

默认 `imageSize: "1K"`。用户说「2K」「4K」时用 `nano-banana-2` + 对应 `imageSize`；只有特别要求高质量、专业、增强一致性或 pro 时才用 `nano-banana-pro`。

## 流程

> 执行请求前先确认 `GRSAI_API_KEY` 已在当前进程环境中。Windows PowerShell 优先用 `python`/`Invoke-RestMethod`，Unix shell 可用 `python3`/`curl`。

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

### 批量或长任务：发起异步任务

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

返回 `{"id": "<task_id>", "status": "running"}`，提取 `TASK_ID`。

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

## 并发

**GRSai 支持并发请求。** 实测 5 并发全部在 11s 内返回，不会互相阻塞。需要批量生图时并行发起多个 curl 请求即可。

## 输出规范

- 拿到 url 后先下载成本地文件，再展示给用户
- 如果当前任务有明确项目根目录，就下载到项目根目录下的 `.codex/generated-images/`
- 如果是 projectless Codex 桌面会话，就下载到当前工作区的 `outputs/genius-image/`
- 如果不在项目中也没有工作区，就下载到当前系统临时目录下的 `codex/genius-image/`，例如 Windows 的 `$env:TEMP\codex\genius-image\` 或 Unix 的 `~/.codex/tmp/genius-image/`
- 展示时优先使用本地绝对路径的 Markdown 图片链接
- 同时保留原始 URL 作为备用链接
- 第一步发起后说一句「生成中，预计 1 分钟左右」
- 失败时一句话说明原因 + 建议
