# 用配音锁节奏

镜头的起止时间直接卡在配音句子的边界上，不靠估算。配音一换，重新生成时间点文件，整片节奏自动跟上。

## 口播文本格式

一个纯文本文件，每行一句。行首写 `+` 表示**新增口播**：还没录音、需要先显示成字幕的句子。

```text
这是一颗灯珠。
+ 十二颗依次点亮，计数同步。
最后收在全景。
```

## 生成时间点：`scripts/vo_timeline.mjs`

在项目根目录运行，输出 `src/vo.json`。

**有配音，每句一个音频文件**（推荐让配音员或 TTS 按句交付）：

```bash
node '<skill>/scripts/vo_timeline.mjs' --clips vo_clips --text vo.txt --audio public/vo.wav --out src/vo.json
```

- 音频文件按文件名的自然顺序排列（`01.wav`、`02.wav`……），和口播文本按行对应；
- 脚本用 ffprobe 量出每句的真实时长，句与句之间补静音（`--gap`，默认 0.4 秒），开头留空白（`--lead`，默认 0.5 秒），再用 ffmpeg 拼成一条 `public/vo.wav`；
- 需要本机有 ffmpeg 和 ffprobe。

**还没有配音，只有文字**：

```bash
node '<skill>/scripts/vo_timeline.mjs' --text vo.txt --out src/vo.json
```

- 按每秒 4.5 个字估时长（`--cps` 可改），只数汉字、字母和数字；
- 生成的 `vo.json` 里 `estimated` 为 `true`，交付时要告诉用户：节奏是估的，配音到了还要再对一遍。

Windows PowerShell 的写法相同，路径用反斜杠，带空格的路径用单引号。

## 只有一整条配音时

先用语音转写工具拿到每句的起止时间（环境里有 genius-omni 的话，用它的 `audio-transcribe` 模式），再按下面的格式手写 `vo.json`，把音频放进 `public/`：

```json
{
  "audio": "vo.wav",
  "estimated": false,
  "total": 7.4,
  "cues": [
    {"id": "c1", "text": "这是一颗灯珠。", "subtitle": false, "start": 0.5, "end": 1.8}
  ]
}
```

## 在代码里用

- `src/vo.ts` 的 `cue('c2')` 返回第 2 句的起止帧。镜头写成「从上一镜结束开始，至少 N 帧，并且至少持续到这句说完」：`atLeast(S1.end, 120, cue('c2').end)`。
- 总时长取「最后一个镜头的结束」和「配音总长」中较大的那个。
- `vo.json` 里有 `audio` 时，成片自动带上配音；`subtitle: true` 的句子自动显示成字幕。
- 一个镜头里的动画节点（比如某个部件在说到某个词时亮起）也可以写成 `cue('c3').start + 偏移`。

## 临时配音

正式配音还没录的时候，建议先用 TTS 合成一版临时配音放进去，审片时就能听着看节奏。macOS 可以直接用系统自带的 `say` 命令：

```bash
say -v Tingting -o vo_clips/01.aiff '这是一颗灯珠。'
```

其他系统用任意 TTS 工具，按句导出音频文件即可。临时配音只用来对节奏，交付时要说明它不是正式配音。
