# 星轨频谱 · Stellar Spectrum

一个 Windows 实时「系统声音」银河可视化软件：捕获电脑正在播放的音乐，把频谱变成一座真正的 3D 螺旋星系。镜头会自动巡航，星系持续自转；96 根光谱光柱立在星系外缘，每个节拍都会让核心像超新星一样向外爆发。

**按住鼠标左键拖动，可以绕星系观察侧面、俯视等角度；滚轮缩放，双击重置视角。按 `P` 切换四种视觉预设。**

![3D 螺旋星系](screenshots/preview.png)

[▶ 动态预览 GIF](screenshots/demo.gif)

> 不需要麦克风对着音响。程序通过 Windows WASAPI Loopback 直接读取当前扬声器 / 耳机正在播放的声音，全部在本地处理，不录音、不上传。

---

## 1. 直接开始

### 方式 A：双击 EXE（推荐）

1. 双击本目录的 `StellarSpectrum.exe`（也可以双击 `启动.bat`，它会优先启动 EXE）。
2. 用任意播放器播放音乐、视频或游戏声音。
3. 按住鼠标左键拖动观察星系，滚轮缩放，按 `F11` 全屏。

### 方式 B：从源码启动

要求 Windows 10/11、Python 3.10+。

```bat
python -m pip install -r requirements.txt
python main.py
```

只想看效果、不播放音乐也可以：

```bat
python main.py --demo
```

`--demo` 使用内置合成音乐，不会采集系统声音。

---

## 2. 它如何“听到”电脑里的音乐

Windows 的扬声器 / 耳机在 WASAPI 中同时提供一个 **Loopback** 录音端点，它录到的就是该设备正在播放的混音。程序启动时自动选择系统默认扬声器：

- 你播放的音乐、网页视频、游戏、会议声音，都会进入频谱；
- 不经过麦克风，不受环境噪声影响；
- 蓝牙耳机、USB 声卡、HDMI 显示器音频通常也可以；
- 如果默认设备选错，按 `D` 在列表里换一个「系统声音」即可；
- 想用麦克风做环境声可视化，按 `D` 选择「麦克风」条目。

程序只做实时 FFT 和画面渲染，不保存音频。

---

## 3. 画面里有什么

- **真正的 3D 螺旋星系**：约 3400 个粒子构成中央棒、两条旋臂、核球、外围尘埃和细碎的轨道弧线；
- **自动巡航镜头**：星系持续自转，镜头缓慢环绕；拖动鼠标可以随时接管视角；
- **96 根光谱光柱**：围绕星系外缘立起，每根绑定一个对数频段，随音乐高低起伏；
- **节拍爆发**：每一下鼓点从核心射出光射线、3D 冲击波环和飞散粒子；
- **深空背景**：程序化星云 + 750 颗闪烁星尘；
- **四种配色**：星云蓝、极光绿、赛博粉、日冕橙。

![核心爆发](screenshots/explosion.png)

侧面观察时能明显看出它是三维星系，而不是平面贴图：

![侧面视角](screenshots/galaxy-side.png)

| 设备选择 | 快捷键说明 | 极光绿主题 |
|---|---|---|
| ![设备选择](screenshots/device-menu.png) | ![快捷键](screenshots/shortcuts.png) | ![极光绿](screenshots/theme-aurora.png) |

### 四种视觉预设（按 `P` 循环）

| 3D 星系 | 星际轨道 | 极光波形 | 经典频谱 |
|---|---|---|---|
| ![3D 星系](screenshots/preview.png) | ![星际轨道](screenshots/preset-orbit.png) | ![极光波形](screenshots/preset-wave.png) | ![经典频谱](screenshots/preset-spectrum.png) |
| 螺旋粒子 + 96 根光谱光柱，可拖动观察三维结构 | 中央恒星 + 径向频谱 + 六条星际轨道 | 层叠的极光波形带 + 漂浮光斑 | 经典镜像频谱柱 + 波形线 |

---

## 4. 快捷键

| 按键 / 操作 | 功能 |
|---|---|
| **按住鼠标左键拖动** | 绕星系旋转视角 |
| **鼠标滚轮** | 拉近 / 拉远 |
| **双击画面** | 重置视角 |
| `V` | 重置视角 |
| `F11` | 全屏 / 退出全屏 |
| `D` | 选择声音来源（系统声音 / 麦克风） |
| `1` `2` `3` `4` | 星云蓝 / 极光绿 / 赛博粉 / 日冕橙 |
| `T` | 循环切换主题 |
| `P` | 循环切换视觉预设（3D 星系 / 星际轨道 / 极光波形 / 经典频谱） |
| `S` | 保存当前画面到 `screenshots/` |
| `H` | 显示 / 隐藏 HUD 文字 |
| `[` `]` | 降低 / 提高频谱灵敏度 |
| `Space` | 暂停画面（音频仍继续分析） |
| `?` 或 `F1` | 打开操作说明 |
| `Esc` | 关闭弹窗；在主界面退出程序 |

设备选择窗口中：`↑` `↓` 选择，`Enter` 确认，`R` 重新扫描，鼠标点击也可以。

---

## 5. 关于“频谱灵敏度”

默认 `GAIN 1.00`。如果音乐本身很轻、光柱不够高，用 `]` 调到 1.2–1.5；如果爆炸段全部顶满，用 `[` 调低。设置会保存到 `config.json`。

---

## 6. 命令行参数

```bat
python main.py                          :: 默认：1600x900 窗口，捕获默认扬声器
python main.py --fullscreen             :: 全屏启动
python main.py --demo                   :: 内置音乐演示，不采集系统声音
python main.py --mic                    :: 使用第一个麦克风
python main.py --list-devices           :: 列出所有可用的系统声音 / 麦克风
python main.py --device 3               :: 使用列表中的第 3 个声音来源
python main.py --device-name 耳机        :: 按名称片段选择
python main.py --theme aurora           :: 启动主题
python main.py --preset wave            :: 启动预设：galaxy / orbit / wave / spectrum
python main.py --sensitivity 1.3        :: 启动灵敏度
python main.py --size 1280x720          :: 降低分辨率以提升帧率
python main.py --fps 60                 :: 目标帧率
python main.py --no-hud                 :: 不显示界面文字
python main.py --demo --screenshot screenshots/shot.png --frames 420
                                        :: 离屏渲染截图（不需要显示器 / 声音）
```

主题 key：`nebula`、`aurora`、`cyber`、`corona`。

---

## 7. 常见问题

### 画面有星系，但没有频谱 / 一直显示“等待系统声音”

1. 确认音乐确实从**当前选中的扬声器 / 耳机**播放，而不是另一个设备；
2. 按 `D`，选另一个「系统声音 · …」；
3. 检查 Windows 音量合成器里播放器没有被静音；
4. 蓝牙耳机刚连接时，Windows 可能仍把默认输出留在旧设备，切换一下默认输出；
5. 如果播放器使用了 ASIO / 独占模式，Loopback 可能拿不到声音，改用共享模式。

### 列表里没有声音设备

- 确认 Windows 音频服务正在运行；
- 确认 `soundcard` 已正确安装（`python -c "import soundcard"`）；
- 某些虚拟声卡 / 采集卡不提供 Loopback，可以改用麦克风模式。

### 帧率偏低

星系是约 3400 个 3D 粒子 + 96 根光柱 + 750 颗星尘 + 实时光晕。默认 1600×900 在多数电脑上约 45–55 FPS。老显卡 / 核显可以：

```bat
python main.py --size 1280x720 --fps 60
```

全屏 1920×1080 对核显压力更大，建议 1280×720 或 1440×810。

### 鼠标拖动没有反应

- 确认没有打开 `D` 设备菜单或 `?` 帮助面板（它们会拦截鼠标）；
- 按住左键拖动，不要只移动鼠标；
- 双击或按 `V` 可以重置视角。

### 滑动 / 滚轮导致退出

此问题已修复：以前滚轮会触发 `TypeError: 'float' object is not callable`，部分鼠标/触控事件会触发 `AttributeError: ... has no attribute 'clicks'`，现在都能正常处理。

如果仍然遇到其他报错，程序目录下会生成 `error.log`，里面是完整的 traceback。把最后几行发给我即可定位。

---

## 8. 自己打包 EXE

```bat
双击 build_exe.bat
```

或：

```bat
python -m pip install pyinstaller
python -m PyInstaller --noconfirm --clean --onefile --windowed ^
  --name StellarSpectrum --collect-submodules soundcard main.py
```

生成 `dist\StellarSpectrum.exe`。该 EXE 会把 `config.json` 和 `screenshots/` 放在 EXE 所在目录。

---

## 9. 项目结构

```
main.py                 程序入口、窗口 / 事件循环 / 鼠标视角 / 设备菜单
stellar/
  audio.py              WASAPI Loopback 采集、设备枚举、内置合成音乐
  analysis.py           对数频谱、AGC、峰值保持、波形、节拍检测
  galaxy.py             3D 螺旋星系、轨道相机、96 根光谱光柱、爆发粒子
  orbit.py              星际轨道预设（中央恒星、径向频谱、六条轨道）
  wave.py               极光波形预设（层叠波形带、漂浮光斑）
  spectrum.py           经典镜像频谱预设
  hud.py                HUD、设备选择面板、帮助面板
  themes.py             四套配色
启动.bat                自动找 Python、装依赖、启动
启动全屏.bat            全屏启动
build_exe.bat           打包 EXE
requirements.txt
screenshots/            截图输出目录
config.json             自动保存的主题 / 灵敏度 / 设备 / 全屏状态
```

---

## 10. 实现要点

- 48 kHz、4096 点 Hann 窗 FFT，96 个对数频段（32 Hz–16 kHz）；
- 每频段自适应峰值参考，兼顾安静段落与响度战争；
- 低频 30–160 Hz 的**正向频谱通量**做主节拍检测，比单纯“低音够响”更适合流行乐；
- 轨道相机：yaw / pitch / distance 三个自由度，鼠标拖动带惯性，自动巡航；
- 96 根 3D 光柱绑定频段，同时调制旋臂粒子亮度和核心脉冲；
- 节拍触发核心射线、3D 冲击波环、爆发粒子和镜头震动；
- 辉光精灵按颜色/亮度量化缓存；辉光层每两帧更新一次，保证帧率。

如果它让你的桌面变好看了，就把 `screenshots/` 里的图发出去吧。
