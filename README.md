# 网箱时域运动模拟器 · 图形界面

系泊浮式网箱**时域运动响应**与**系泊力**分析的桌面工具。

本目录是一个 Tkinter 图形界面，驱动 `CagePython/` 目录下的原始计算程序，
把「改源码 → 敲命令行 → 去文件夹里翻结果」的流程换成「填表 → 点运行 → 看结果」。

---

## 功能概览

| 能力 | 说明 |
|---|---|
| 三种波浪工况 | 规则波 / 不规则波（JONSWAP）/ 外部波面文件 |
| 6 自由度运动 | 纵荡、横荡、垂荡、横摇、纵摇、艏摇 |
| 4 根缆系泊力 | 悬链线静力模型，含局部放大预览 |
| 实时进度 | 6 个计算阶段 + 时间推进进度条 + 日志 |
| 结果查看 | 统计摘要 + 图片缩略图（可滚动、可点击放大） |
| 工程管理 | 参数存成 JSON，可保存/加载/复用 |

---

## 快速开始

### 环境要求

- Python 3.10+（已在 3.12.7 验证）
- Tkinter（macOS / Windows 的官方 Python 自带；Linux 需 `sudo apt install python3-tk`）

### 安装依赖

```bash
cd UI
python -m venv .venv

# 方式一：uv（推荐，快）
uv pip install --python .venv/bin/python numpy scipy matplotlib pillow

# 方式二：pip
.venv/bin/python -m pip install numpy scipy matplotlib pillow
```

### 运行

```bash
cd UI
.venv/bin/python main.py
```

首次启动会读 `../CagePython` 作为默认程序目录。若目录不对，在「输入」页点「浏览…」重新指一下，
选择会自动存进 `settings.json`。

---

## 界面说明

程序按 **输入 → 运行 → 结果** 三步走，左侧导航和顶部步骤条都可以跳转。

### ① 输入

三张卡片：

- **水动力系数**
  - `程序目录`：指向 `CagePython/`，原始计算代码所在位置
  - `WAMIT 目录`：`.1/.3/.9/.GDF/.hst/.mmx` 六个文件所在目录
  - 点「检查文件」逐项显示 `● 已找到 / ● 缺失` 和文件大小
  - 水深、流体密度、6 个自由度开关（取消勾选 = 该自由度固定）

- **波浪工况**（三选一，切换时只显示对应参数）
  - 规则波：波高 H、周期 T、是否加渐入渐出段
  - JONSWAP：有义波高 Hs、谱峰周期 Tp、谱峰因子 γ、模拟时长、随机种子
  - 外部波面文件：选好后自动解析，显示「N 步 × dt = 时长」和浪向数

- **系泊系统**（默认收起，勾选后展开）
  - 缆绳属性：湿重、轴向刚度、水深+干舷、未拉伸原长、预张力范围
  - 6 个导缆孔坐标和水平角表格
  - 「计算悬链线曲线」：画单根缆的*水平位移–水平力*曲线，
    带悬垂段局部放大插图，并标出初始预张力工作点和张紧点

底部可「保存工程 / 加载工程」，工程是 JSON，含全部参数。

### ② 运行

- 6 个阶段清单，状态图标随进度从 `○` 变 `◐` 再变 `●`
- 进度条 + `t = 380.0 s / 1000 s` + 已用时
- 深色日志窗口，按 `info / ok / warn / error` 分级着色
- 按钮：开始 / 暂停 / 停止 / 打开输出目录

计算跑在**后台线程**，界面不会卡死；点「停止」能真正中断。

### ③ 结果

- 左侧列出 `output/` 下所有已完成工况
- 右侧统计摘要：时长、初始系泊力、6 自由度 H1/3·H1/10·Hmax、4 根缆张力极值
- 结果图片网格：缩略图 + 中文标题，**点击放大**（`Esc` 或双击关闭）
- 整个右侧可上下滚动

---

## 目录结构

```
UI/
├─ main.py                 入口（含 matplotlib 缓存目录设置）
├─ CageSim.spec            PyInstaller 打包配置
├─ app/
│  ├─ __init__.py          版本号、标题
│  ├─ main.py              主窗口：侧边导航 + 步骤条 + 页面容器 + 状态栏
│  ├─ paths.py             路径解析（源码 / 打包后）
│  ├─ theme.py             配色、字号、ttk 样式
│  ├─ core/
│  │  ├─ config.py         数据模型：Project / Hydro / Wave / Mooring
│  │  ├─ engine.py         ★ 原始程序适配层（不修改 CagePython 任何文件）
│  │  └─ simulator.py      后台线程执行器 + 事件队列
│  ├─ pages/
│  │  ├─ input_page.py     ① 输入
│  │  ├─ run_page.py       ② 运行
│  │  └─ result_page.py    ③ 结果
│  └─ widgets/
│     └─ __init__.py       Card / Field / StatBadge / ScrollFrame / LogView / Stepper
├─ assets/                 图标（可选，放 app.ico 会自动启用）
├─ output/                 运行结果（自动创建，已被 gitignore）
├─ logs/                   运行日志（自动创建）
└─ settings.json           用户设置，记住程序目录（自动生成）
```

---

## 依赖的外部程序

界面本身**不含计算逻辑**，实际计算在 `CagePython/` 里完成。运行时需要这个目录下：

**16 个 Python 文件**

```
state.py                 plot_style.py            matlab_compat.py
read_input.py            read_wamit1_file.py      read_wamit234_file.py
read_wamit9_file.py      rk44.py                  dfdt_eqmot.py
xiboli.py                xibo_dangenlan.py        motion_simu_parameters.py
fftfiltering_hz.py       hit_spek3.py             wavestatistic.py
jonswap_h.py
```

**6 个 WAMIT 数据文件**

```
WAMIT_5S.1      附加质量 / 阻尼
WAMIT_5S.3      一阶激振力
WAMIT_5S.9      二阶漂移力
WAMIT_5S.GDF    几何
WAMIT_5S1.hst   静水刚度
WAMIT_5S1.mmx   质量 / 外阻尼
```

> 不需要 `cage_motion_simulator.py`（那是原始主程序，界面自己复刻了流程），
> 也不需要 `tsunami_model.py` / `interp1_h.py`（备用，主链未用）。

### 界面是怎么接入的

`app/core/engine.py` 复刻原始主程序的流程，但**不修改 `CagePython` 里的任何文件**：

1. 把工程配置写进原始程序的 `state` 模块（等价于 `MotionSimuParameters` 做的事）
2. `chdir` 到 WAMIT 目录，调用 `read_input()` 读系数、算激振力
3. 悬链线曲线由适配层自己算一份（原版的缆绳参数是函数内硬编码，改不了）
4. 时间循环用原始 `rk44` + `dfdt_eqmot` + `xiboli`，每若干步回调一次进度
5. 后处理沿用原始的滤波 / 谱估计 / 统计函数，出图后存盘

因为 `state` 是全局单例，**同一时间只能跑一个仿真**（执行器已保证）。

---

## 输出结果

每次运行在 `output/<工况名>/` 下生成：

| 文件 | 内容 |
|---|---|
| `<工况>_TSR.mat` | MATLAB 可读的结构体 `TSR` |
| `<工况>_TSR.npz` | numpy 格式，字段同上 |
| `<工况>_统计结果.txt` | 人看的统计汇总 |
| `fig*.png` | 10–11 张图 |
| `K66-0.png` | 辐射迟滞函数 |

`TSR` 五个字段：`time`(s)、`wave`(m)、`motion`(6×N，m/°)、`mooring`(4×N，N)、`case`。

工况目录名规则：

| 波型 | 目录名 |
|---|---|
| 规则波 | `RegularH=<H>T=<T>` |
| JONSWAP | `IrregularHs=<Hs>Tp=<Tp>` |
| 外部文件 | 波面文件名（去扩展名） |

---

## 打包成 exe

采用**文件夹版**（onedir）：可执行文件旁边放一个 `CagePython/` 目录，
用户可自行替换 WAMIT 文件、修改计算代码，不用重新打包。

```bash
cd UI
.venv/bin/pip install pyinstaller
.venv/bin/pyinstaller CageSim.spec
```

产物在 `dist/CageSim/`。组装分发目录：

```
CageSim/
├─ CageSim.exe          ← Windows；macOS/Linux 下是无扩展名的 CageSim
├─ _internal/           ← PyInstaller 运行时，别动
├─ CagePython/          ← 从源码目录整个拷过来
│    ├─ state.py ...（16 个 .py）
│    └─ WAMIT_5S.*（6 个文件）
└─ （首次运行生成 output/、logs/、settings.json）
```

> `CagePython/` 不打包进 exe 是刻意的：这些模块名太通用（`state`、`rk44`），
> 打进包里容易和第三方包重名，排查困难。spec 里已把它们显式列入 `excludes`。

图标：把 `app.ico`（Windows）或 `app.icns`（macOS）放进 `assets/`，
spec 会自动检测并启用，不放也能打。

---

## 常见问题

**Q：启动时控制台一直显示 "Matplotlib is building the font cache"？**

说明 matplotlib 的缓存目录不可写，每次启动都在重建缓存。
`main.py` 已经把它固定到 `~/.cagesim/mpl`（家目录不可写时退到程序目录下的 `.mplcache/`）。
若你手动设了 `MPLCONFIGDIR` 环境变量，程序不会覆盖。

**Q：图上中文变成方块？**

`CagePython/plot_style.py` 里配的是 Windows 字体（Microsoft YaHei / SimHei）。
界面在出图前会调 `ensure_cjk_font()`，按 `Microsoft YaHei → PingFang SC →
Hiragino Sans GB → Source Han Sans SC …` 的顺序挑系统里能用的那个。
如果全都缺，需要自己装一个中文字体。

**Q：结果页图片是空的？**

先确认该工况目录下确实有 `fig*.png`。另外显示缩略图依赖 Pillow，
缺了会在网格里提示「缺少 Pillow」。

**Q：运行时报 "程序目录不存在" 或 "缺文件"？**

「输入」页的**程序目录**要指向 `CagePython/`（不是项目根目录、也不是 `output/`）。
点「检查文件」能逐项看到缺哪个。

**Q：切换工况后旧图还在？**

原始程序会先清掉本工况目录里的 `fig*.png` 和 `K66-0.png` 再重画，
所以同一工况重跑不会残留旧图；不同工况在各自目录，互不影响。

---

## 已知限制

- **`TSR.mooring` 末点恒为 0**：原始程序的时间循环只记录到 `nt_sim-1`，
  最后一个采样点是初始化的 0。按约定不改数据，只在绘图和统计时剔除该点
  （`fig173` / `fig193` 图题有注明）。
- **不规则波的二阶漂移力依赖随机数**：界面上暴露了随机种子（默认 5489 = MATLAB
  默认状态），同种子可复现。
- **数值一致性**：确定性部分与原始程序逐位一致（初始系泊力 `49014.28 N` 完全吻合，
  已实测 `motion` / `mooring` 最大差异为 0）。

---

## 依赖版本（验证过）

| 包 | 版本 |
|---|---|
| Python | 3.12.7 |
| tkinter | 8.6 |
| numpy | 2.5.4 |
| scipy | 1.18.1 |
| matplotlib | 3.11.2 |
| pillow | 13.0.0 |
