# AG_LEXICON 剪辑词典 v0.2（草案，待审定）

genius-footage 给模型的统一词表（本文件随技能发布，脚本运行时原样读入提示词）。模型在结构化字段里**只能用本表的词**（填中文名）；表外想说的写进自由备注（第十二节）。
疑似切点复核和逐镜头描述共用这一份；改词典即生效，不用改代码。

“剪辑上”一列是给模型的参考惯例，最终由模型看画面判断；标 ⚠ 的一律“待确认”，交给人判（2026-11-03 用户同意）。
术语按好莱坞通行说法（StudioBinder、wolfcrow 等制作指南）与国内视听语言教材对齐，来源见文末。

---

## 一、画面类型

| 中文名 | English | 定义 |
|---|---|---|
| 实拍 | live action | 摄影机实际拍摄 |
| CG | CG | 三维渲染或数字合成 |
| AI 生成 | AI-generated | AI 视频或图像模型生成 |
| 动态图形 | motion graphics | 以图形、文字、图标为主体的二维动画 |
| 定格动画 | stop motion | 逐帧拍摄实物摆拍后连续播放 |
| 混合 | mixed | 以上两种或更多在同一画面 |

## 二、素材用途

| 中文名 | English | 定义 |
|---|---|---|
| A-roll | A-roll | 主线素材：采访、口播、讲述，承载台词与叙事，通常带同期声 |
| B-roll | B-roll | 辅助素材：空镜、细节、产品、环境、动作，覆盖 A-roll 或做转场 |
| 无法判断 | unknown | 单看画面分不出 |

## 三、速度与拍摄手段

| 中文名 | English | 定义 | 剪辑上 / 对测量的影响 |
|---|---|---|---|
| 正常速度 | real time | 按实际速度播放 | — |
| 升格（慢动作） | slow motion / overcrank | 高帧率拍、正常帧率放，动作变慢 | 同一镜头；相邻帧变化小 |
| 极慢动作 | extreme slow motion | 1000 fps 以上拍摄 | 同一镜头 |
| 降格（快动作） | fast motion / undercrank | 低帧率拍或加速播放 | 同一镜头 |
| 变速 | speed ramp | 同一镜头内快慢变化 | 同一镜头 |
| 延时摄影 | time-lapse | 间隔拍帧，压缩时间 | 同一镜头；相邻帧跳动大，**易被误测成切点** |
| 移动延时 | hyperlapse | 机位移动中的延时 | 同一镜头；同上 |
| 抽帧 | frame skipping / step frame | 删去部分帧，动作卡顿 | 同一镜头；单帧跳动大，**易被误测成切点** |
| 补帧 | frame interpolation | 算法插出中间帧，可能变形、拖影 | 同一镜头；拖影处像叠化 |
| 慢门拖影 | slow shutter | 低快门速度造成强烈运动模糊 | 同一镜头 |
| 子弹时间 | bullet time | 机位环绕而动作近乎静止，多机拍摄 | 同一镜头 |
| 倒放 | reverse | 时间倒着播放 | 同一镜头 |
| 定格 | freeze frame | 画面停在一帧 | 同一镜头；重复帧 |
| 抠像合成 | chroma key / composite | 绿幕、蓝幕抠像后合成 | 同一镜头 |
| 分屏 | split screen | 一个画面分成几块并排 | ⚠ 待确认 |

## 四、叠加元素（不改变镜头本身）

| 中文名 | English | 定义 | 剪辑上 |
|---|---|---|---|
| 花字 | styled caption | 带样式、动效的强调文字 | 同一镜头 |
| 字幕 | subtitle | 台词或说明的常规字幕 | 同一镜头 |
| 角标 / 贴片 | bug / sticker | 固定位置的 logo、标签、贴纸 | 同一镜头 |
| 水印 | watermark | 素材来源或平台水印 | 同一镜头 |
| 遮罩 | mask / vignette / iris | 圆形遮罩、暗角、望远镜等形状遮挡 | 同一镜头 |

## 五、镜头边界（转场）

| 中文名 | English | 定义 | 剪辑上 |
|---|---|---|---|
| 硬切 | cut | 一帧之内换成另一个镜头 | 新镜头 |
| 跳切 | jump cut | 同一主体、机位相近，时间或位置跳跃 | 新镜头 |
| 匹配剪辑 | match cut | 形状、构图或主题相似的两个镜头相接 | 新镜头 |
| 动作匹配 | match on action | 同一动作在两个机位间接续 | 新镜头 |
| 对比硬切 | smash cut | 从强烈突然切到反差画面（如惊醒） | 新镜头 |
| 叠化 | dissolve | 前后两个镜头交叠渐变 | 新镜头（切点取叠化起点） |
| 划像 | wipe | 新画面以几何边界推入 | 新镜头 |
| 遮挡转场 | hidden wipe | 借前景物体或人遮满画面完成转换 | 新镜头 |
| 甩切 | whip cut | 借甩镜的运动模糊接到另一个镜头 | 新镜头 |
| 变形转场 | morph | 一个画面形变成另一个画面 | 新镜头 |
| 黑场 / 渐隐渐显 | fade | 经黑场或纯色过渡 | 新镜头（黑场之后算起） |
| 闪白 / 闪黑 | flash frame | 一到几帧纯白或纯黑，前后同一画面 | 同一镜头 |

## 六、镜头内变化（通常不切）

| 中文名 | English | 定义 | 剪辑上 |
|---|---|---|---|
| 特效出现 | effect | 同一构图里出现激光、火花、光效、烟、粒子等 | 同一镜头 |
| 调色 / 滤镜变化 | grade change | 色调、滤镜、曝光突然改变，构图不变 | 同一镜头 |
| 光线变化 | lighting change | 灯光、闪光、阴影变化 | 同一镜头 |
| 转焦 | rack focus | 焦点从一个主体转到另一个 | 同一镜头 |
| 跑焦 | focus loss | 焦点失准，画面变虚 | 同一镜头（标记里记“跑焦”） |
| 主体运动 | subject movement | 人或物在画面内运动 | 同一镜头 |
| 遮挡穿过 | occlusion | 手、物体、人从镜头前经过（未遮满） | 同一镜头 |
| CG 内容替换 | CG swap | 构图不变，渲染内容或物体状态一下子换了 | ⚠ 待确认 |
| AI 画面突变 | AI discontinuity | AI 画面里物体、颜色、细节突然不连续 | ⚠ 待确认 |
| 拼贴 / 画中画 | collage / PiP | 画面里逐块出现其他画面 | ⚠ 待确认 |

## 七、运镜

| 中文名 | English | 定义 |
|---|---|---|
| 固定 | static | 机位、焦距不动 |
| 推 | dolly in / push in | 机位向主体靠近 |
| 拉 | dolly out / pull out | 机位远离主体 |
| 横摇 | pan | 机位不动，镜头水平转动 |
| 俯仰摇 | tilt | 机位不动，镜头上下转动 |
| 横移 | truck / crab | 机位平行于主体侧向移动 |
| 跟 | tracking / follow | 机位跟着运动主体走 |
| 升降 | crane / pedestal / jib | 机位上升或下降 |
| 环绕 | arc / orbit | 机位绕主体转 |
| 变焦 | zoom | 机位不动，焦距变化 |
| 急推变焦 | crash zoom / snap zoom | 极快的变焦推近或拉远 |
| 滑动变焦 | dolly zoom / Vertigo shot | 推拉与变焦反向同时进行，透视扭曲（希区柯克变焦） |
| 甩镜 | whip pan / swish pan | 极快的横摇或俯仰，带强烈运动模糊 |
| 手持 | handheld | 手持或肩扛，带不规则晃动 |
| 稳定器 | gimbal / Steadicam | 运动中画面平稳，无轨道感 |
| 航拍 | aerial / drone / FPV | 无人机或高空平台拍摄，FPV 为穿越机高速飞行 |
| 无法判断 | unknown | 帧不够或画面看不出 |

## 八、景别（以成年人身体为基准）

| 中文名 | English | 取景 |
|---|---|---|
| 大远景 | extreme wide shot (EWS) | 人物极小或无法辨认，环境为主 |
| 远景 | long shot / wide shot (LS/WS) | 人物全身且上下留有大量环境 |
| 全景 | full shot (FS) | 人物全身基本撑满画框 |
| 中全景 | medium wide shot (MWS) | 膝盖以上；七分身 / 牛仔镜头（cowboy，大腿中部以上）归此 |
| 中景 | medium shot (MS) | 腰部以上 |
| 近景 | medium close-up (MCU) | 胸部以上；即“中近景” |
| 特写 | close-up (CU) | 肩部以上或面部撑满；物体局部 |
| 大特写 | extreme close-up (ECU) | 眼、嘴等单一局部或极小细节 |

各教材的分界线略有出入（中景有“膝上”和“腰上”两说），本表统一按上面的分界（2026-11-03 用户审定）。

## 九、角度与构图

**角度**

| 中文名 | English | 定义 |
|---|---|---|
| 平视 | eye level | 机位与人物视线等高 |
| 俯拍 | high angle | 机位高于主体向下拍 |
| 仰拍 | low angle | 机位低于主体向上拍 |
| 顶拍 | overhead / bird's eye | 正上方垂直向下 |
| 地面机位 | ground level | 机位贴地 |
| 荷兰角 | Dutch angle | 画面地平线倾斜 |

**画面人数与构图**

| 中文名 | English | 定义 |
|---|---|---|
| 单人镜头 | single | 画面只有一人（他人在画面边缘入画时叫“脏单”，dirty single） |
| 双人镜头 | two shot | 两人同框 |
| 三人镜头 | three shot | 三人同框 |
| 群像 | group shot / crowd shot | 四人及以上同框，以人群整体为主体 |
| 过肩 | over-the-shoulder (OTS) | 前景带一方肩背，拍另一方 |
| 主观镜头 | POV | 角色眼中所见，角色本人不入画 |
| 中心构图 | center framing | 主体在画面正中 |
| 负空间 | negative space | 主体很小，周围大量留白 |

## 十、镜头与焦点

| 中文名 | English | 定义 |
|---|---|---|
| 广角 | wide angle | 视野宽，透视夸张 |
| 鱼眼 | fisheye | 超广角，边缘强烈畸变 |
| 长焦 | telephoto | 视野窄，空间压缩 |
| 微距 | macro | 极近对焦拍小物体 |
| 浅景深 | shallow depth of field | 主体清晰，前后景虚化 |
| 深焦 | deep focus | 前景到背景都清晰 |
| 移轴 | tilt-shift | 局部清晰，呈微缩模型感 |
| 柔焦 | soft focus / diffusion | 整体柔和朦胧 |
| 分焦镜 | split diopter | 前后两个平面同时清晰，中间虚 |

## 十一、镜头关系（跨镜头）

| 中文名 | English | 定义 |
|---|---|---|
| 主镜头 | master shot | 覆盖整场戏全过程的大景，其他镜头切入其中 |
| 建立镜头 | establishing shot | 交代地点环境的开场镜头，通常大景 |
| 正反打 | shot / reverse shot | 对话双方两个机位交替，每次切换都是新镜头 |
| 插入镜头 | insert | 同一场景内的细节、物件、手部特写 |
| 切出镜头 | cutaway | 切到场景外或旁支的画面再切回 |
| 反应镜头 | reaction shot | 人物对事件的反应 |
| 空镜 | empty shot | 无人物的环境或物件画面 |
| 英雄镜头 | hero shot / money shot | 全片最有冲击力的画面；产品片里指产品主视觉 |
| 长镜头 / 一镜到底 | long take / oner | 长时间连续不切 |
| 越轴 | crossing the line | 机位跨过人物间的 180° 轴线，空间方向反转 |

## 十二、自由备注

每条结构化回答都带**自由备注**，模型可写词典以外想说的：画面的特别之处、拿不准的原因、剪辑建议等。
- 自由备注**不进结构化字段**，不参与切点、检索、统计，只原样显示在说明书里给人看。
- 结构化字段遇到词典没有的情况，选最接近的词，再在备注里说明。

---

## 不收录

- **J-cut / L-cut（声画错位）**：剪辑时声音与画面错开切，单条素材里看不出来，不放进画面词典；可下刀点仍由台词表负责。

## 待你审定

1. 镜头表要不要加列：“画面类型”（第一节）、“素材用途”（第二节）、“速度与拍摄手段”（第三节）？加列要改 AG_FOOTAGE 镜头表（现 13 列）。
2. 还有没有你们常用、表里缺的词？

## 参考来源

- [StudioBinder：Ultimate Guide to Camera Shots](https://www.studiobinder.com/blog/ultimate-guide-to-camera-shots/)（景别、构图、角度、运镜、器材、焦点）
- [wolfcrow：100 Camera Angles, Shots and Movements](https://wolfcrow.com/?p=44469)（角度、镜头、运镜、速度手段、剪辑）
- [MasterClass：Essential Film Cuts](https://www.masterclass.com/articles/essential-film-cuts)、[Vimeo：Jump cuts, L-cuts, J-cuts](https://vimeo.com/blog/post/guide-to-film-cuts)（剪辑转场）
- [CSDN：景别的认识及景别的作用](https://adg.csdn.net/69525a905b9f5f31781bac5c.html)、[Bilibili 景别专栏](https://www.bilibili.com/opus/681662982804996113)（中文景别划分）
- [Morphic：反打镜头](https://morphic.com/zh/ai-glossary/reverse-shot)（正反打、180° 轴线）
