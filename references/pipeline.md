# 技术管线

整条片子是**纯代码算出来的**：没有素材、没有录屏、没有 AI 生图。给定 `t` 就能算出唯一一帧，所以改一个数重渲即可，不存在"这次跑出来不一样"。

```
film.html  ──(puppeteer-core + 无头 Edge)──▶  N 张 jpg  ──(ffmpeg libx264)──▶  mp4
             每帧调用 window.renderAt(t)                    + 音轨
```

## 环境

| 依赖 | 说明 |
|---|---|
| node | ≥ 18，在 PATH 里即可（或用 `NODE=<path>` 指定） |
| puppeteer-core | 装在 skill 根目录的 `node_modules`，或 `PUPPETEER_CORE=<path>` 指定 |
| 浏览器 | 自动探测 Edge / Chrome；找不到就用 `BROWSER=<path>` 指定 |
| ffmpeg / ffprobe | PATH 里 |
| Python | 3.11+；`scripts/bgm.py` 需要 numpy + scipy |

装依赖（只需要一次）：

```bash
npm i puppeteer-core            # 在 skill 根目录执行，装出 node_modules/
pip install numpy scipy         # 只用 bgm.py 才需要
```

## 三条命令

```bash
# 抽单帧（改版式时的快速循环，2 秒出图）
node templates/batch.js film.html h "1.2,5.5,11.9,14.9" out/qa

# 出一条完整的
python scripts/build.py --html film.html --audio music.wav --name MyFilm --dur 15.1

# 版式测量（不要肉眼估）
python scripts/probe.py out/qa/h_1.20.png 60 760 dark 0.72
```

`build.py --res h` 只出横版，`--res v` 只出竖版。默认两版都出。

## 性能

| 操作 | 耗时（本机，1920×1080 / 906 帧） |
|---|---|
| 逐帧截图 | ~62 s（单进程串行，~14.6 帧/秒） |
| x264 CRF16 slow 编码 | ~35 s |
| 两版合计 | ~3.5 分钟 |

不要开两个浏览器实例并行跑两版——内存会打架，反而更慢。老老实实串行。

## 九个坑

### 1 旧帧残留

`render.js` 从 `f_0000` 开始覆盖写。如果这次帧数比以前少（比如把 15.2s 改成 15.1s），旧的多余帧还在，ffmpeg 会按最长的编。**必须**在 ffmpeg 上加 `-frames:v N` 精确截断，或在渲染前清空 `frames_x/`。

### 2 中文路径

模板用 `path.resolve(html)` + `replace(/\\/g,'/')` 拼 `file:///`，puppeteer 自己会做 URL 编码，中文目录可以直接跑。但**不要在命令行里手写 `file:///`**，非 ASCII 会挂。

### 3 字体宽度

`Arial Black` 比参考片的数字字体宽约 18%。直接设字号会顶出去，必须 `fitText()` 横向压缩到固定宽度（横版 326px）。同理，中文标题按 2 字 196px / 3 字 158px 给宽度，长标题走 `fitText`。

`ctx.letterSpacing` 只有较新的 Chromium 支持，代码里用 `'letterSpacing' in ctx` 判断过；不支持时字距会归零，英文小标会挤在一起——这时改用逐字符绘制。

### 4 文字压在飞入的卡片上

总览页卡片是从下方飞入的，会穿过标题所在的高度。标题淡入的起点必须晚于最后一张卡归位：`ca=clamp((u-.44)*4)`。

### 5 演示坐标

所有 `dNN()` 用的是**舞台坐标**（横版 883..1792 × 126..906），竖版靠一次 `ctx.scale` 映射。写屏幕绝对坐标（比如 `x=1500`）在竖版会跑到画外。

### 6 音频和视频不等长

`build.py` 用的是 `-af apad` + `-t <dur>`，不用 `-shortest`。原因：`apad` 会把音轨变成无限长，`-shortest` 在这种组合下判断不准——实测 1 秒的测试片会导出 1.7 秒（画面 1.0s、音轨 1.7s），容器时长取最大值。用 `-t` 显式封顶 + `-frames:v N` 双保险，音视频都精确落在目标时长上。

### 7 音轨版权

从参考片里提出来的音轨只能内部用。要对外投放，跑 `python scripts/bgm.py out/bgm.wav` 合成一版自有 150 BPM，或换已授权曲库。**这条别省**，商业素材被投诉的成本远高于换一首曲子。

### 8 报错定位

页面里任何 `dNN()` 抛错，puppeteer 会打 `PAGEERROR: xxx is not defined`，但后续帧仍然是空白/上一帧。看到 `PAGEERROR` 就先修，别看画面"好像还行"。

### 9 颗粒层

`overlay()` 里 `globalCompositeOperation` 在浅色卡用 `multiply`、深色卡用 `screen`。如果整片发灰，检查噪点图是否被缩放（必须 1:1 平铺，缩放后对比度会塌）。

## 音画同步自检

抽成片的音轨，做 RMS 通量找瞬态，和 `CUTS` 逐个比对：

```python
# 输出每个切点与最近鼓点的偏差（毫秒）
# ±45ms 内算过（1.5 帧），超过 80ms 就要重排 CUTS
```

本机实测参考片：14 个切点中 10 个 ≤45ms，其中 6.7s / 8.3s 两处是"切在重音前 80ms"——这是原片的剪辑处理，属正常。

## 交付规格

- 视频：H.264 High / yuv420p / 60fps / CRF 16 / `+faststart`
- 音频：AAC 192k / 48kHz / 立体声
- 时长：15.1s（906 帧）；9:16 与 16:9 同源同内容
- 附：`cover_wide.jpg` / `cover_vertical.jpg`（落版前 0.2s 的帧，适合当封面）、`contact_sheet.jpg`（6×5 联系表，快速通检）
