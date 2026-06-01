# Reasonix MCP Wrapper

## 概述

将 DeepSeek-Reasonix CLI 包装为 MCP 服务器，使 Hermes Agent 可以像调 Codex 和 Claude Code 一样调 Reasonix。

## 架构

```
用户 → Hermes Agent → MCP (stdio) → reasonix-mcp-hermes.py → reasonix run
                                                                ↓
                                                        DeepSeek API 直连
                                                                ↓
                                                        deepseek-v4-flash
                                                        (auto-escalate → v4-pro)
```

## 与 Claude Code MCP Wrapper 的关键区别

| 特性 | Claude Code MCP | Reasonix MCP |
|------|----------------|--------------|
| 框架 | Python FastMCP | 裸 JSON-RPC stdio（零框架依赖） |
| 实现模式 | `@mcp.tool()` 装饰器 | 手动 JSON-RPC handler，`sys.stdin.readline()` 循环 |
| subprocess 方式 | `subprocess.run()` + FastMCP asyncio | `subprocess.run()` 直接调用（无 asyncio 冲突） |
| 认证 | 当前 Charles Claude Code wrapper 配置 | `DEEPSEEK_API_KEY` + DeepSeek 直连 |
| 模型 | 当前 Charles Claude Code wrapper 配置 | deepseek-v4-flash（auto-escalate v4-pro） |

## 为什么要用裸 JSON-RPC 而非 FastMCP

在 Claude Code MCP wrapper 中 FastMCP 工作正常（`subprocess.run()` 虽然阻塞但没出问题），但在 Reasonix wrapper 中 FastMCP 的 asyncio transport 与阻塞式 `subprocess.run()` 冲突——`tools/call` 的响应被吞掉。

改用裸 JSON-RPC stdio 后问题解决：完全同步的 `sys.stdin.readline()` 循环，无需事件循环，子进程行为完全可预测。

## 服务器路径

`/home/charles/.local/bin/reasonix-mcp-hermes`

## Hermes 配置

在 `~/.hermes/config.yaml` 的 `mcp_servers` 段：

```yaml
  deepseek-reasonix:
    command: /home/charles/.local/bin/reasonix-mcp-hermes
    enabled: true
```

## MCP 工具

| 工具名 | 功能 | 参数 |
|---|---|---|
| `code` | 通用编码任务（默认 deepseek-v4-flash，复杂自动升 v4-pro） | `prompt` (必填), `workdir` (可选), `timeout` (可选), `model` (可选) |
| `plan` | 只读分析模式，不修改文件 | `task` (必填), `workdir` (可选), `timeout` (可选) |
| `patch` | 修改后输出 git diff | `task` (必填), `workdir` (可选), `timeout` (可选) |

## 接口规范

工具定义采用标准的 MCP 接口规范格式（`name`/`description`/`inputSchema`），区别于 Claude Code wrapper 的 FastMCP 装饰器风格。

## Pitfalls

- **不要假设可通过 OpenAI-only 网关中转**：如果网关没有 DeepSeek 模型，必须使用 DeepSeek 直连 API key。
- **`--no-config` 标志**：wrapper 中携带 `--no-config` 参数确保 Reasonix 只从 `~/.reasonix/config.json` 读取配置，不受环境变量干扰。
- **API key 位置**：Reasonix 的 `loadApiKey()` 优先级为：`DEEPSEEK_API_KEY` 环境变量 > `~/.reasonix/config.json` 的 `apiKey` 字段。wrapper 中未设环境变量，所以走 config 文件。
- **Base URL 优先级**：`DEEPSEEK_BASE_URL` 环境变量 > `~/.reasonix/config.json` 的 `baseUrl` 字段 > 默认 `https://api.deepseek.com`。
- **Reasonix CLI 模型**：`reasonix run` 已是非交互式，不需要 `--yolo` 标志（该标志仅对 `acp` 子命令有效）。
