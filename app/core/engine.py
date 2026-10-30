"""原始计算程序适配层。

设计原则
--------
1. **不修改 ``CagePython`` 里的任何文件**：通过 ``chdir`` + ``state`` 属性注入
   的方式驱动原始代码。
2. **复刻主程序流程**，而不是直接调用 ``cage_motion_simulator.main()``：
   这样才能在每个阶段之间插入进度回调。
3. ``state`` 是全局单例，所以**同一时间只能跑一个仿真**（执行器已保证）。

原始程序依赖当前工作目录（``open('wave2.dat')``、``np.loadtxt('WAMIT_5S.1')``），
所以每次运行前会 ``chdir`` 到 WAMIT 文件所在目录，结束后恢复。
"""

from __future__ import annotations

import contextlib
import importlib
import os
import sys
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import numpy as np

from app.core.config import Project


# --------------------------------------------------------------------------- #
#  结果
# --------------------------------------------------------------------------- #
@dataclass
class RunResult:
    """一次仿真的结果。"""

    case_name: str = ""
    output_dir: Path = Path(".")
    # TSR 数据
    time: np.ndarray = field(default_factory=lambda: np.array([]))
    motion: np.ndarray = field(default_factory=lambda: np.array([]))
    mooring: np.ndarray = field(default_factory=lambda: np.array([]))
    wave: np.ndarray = field(default_factory=lambda: np.array([]))
    # 统计（来自 result / result_xiboli / momax）
    stats_motion: np.ndarray = field(default_factory=lambda: np.array([]))
    stats_mooring: np.ndarray = field(default_factory=lambda: np.array([]))
    momax: np.ndarray = field(default_factory=lambda: np.array([]))
    # 文件
    mat_path: Path | None = None
    npz_path: Path | None = None
    txt_path: Path | None = None
    figures: list[Path] = field(default_factory=list)


# --------------------------------------------------------------------------- #
#  异常
# --------------------------------------------------------------------------- #
class EngineError(RuntimeError):
    """计算失败，携带原始 traceback 便于排查。"""

    def __init__(self, message: str, detail: str = ""):
        super().__init__(message)
        self.detail = detail


# --------------------------------------------------------------------------- #
#  适配器
# --------------------------------------------------------------------------- #
class CageEngine:
    """把 UI 的 ``Project`` 翻译成原始程序的 ``state`` 并驱动计算。"""

    def __init__(self, project: Project, program_dir: Path,
                 output_dir: Path,
                 log: Callable[[str, str], None] | None = None,
                 progress: Callable[[float, str], None] | None = None):
        self.project = project
        self.program_dir = Path(program_dir).resolve()
        self.output_dir = Path(output_dir).resolve()
        self._log_fn = log or (lambda msg, level="info": None)
        self._progress = progress or (lambda frac, text: None)

        self._modules: dict[str, object] = {}
        self._original_cwd: str | None = None

    # ===================================================================== #
    #  公共入口
    # ===================================================================== #
    def run(self) -> RunResult:
        """执行完整流程，返回结果。"""
        self._check_program_dir()
        self._import_modules()

        self._original_cwd = os.getcwd()
        work_dir = self._work_dir()
        os.chdir(work_dir)
        try:
            return self._run_in_dir()
        finally:
            os.chdir(self._original_cwd)

    # ===================================================================== #
    #  准备
    # ===================================================================== #
    def _check_program_dir(self) -> None:
        if not self.program_dir.is_dir():
            raise EngineError(f"程序目录不存在：{self.program_dir}")
        required = ["state.py", "read_input.py", "rk44.py",
                    "dfdt_eqmot.py", "xiboli.py", "xibo_dangenlan.py",
                    "motion_simu_parameters.py", "fftfiltering_hz.py",
                    "hit_spek3.py", "wavestatistic.py", "plot_style.py",
                    "matlab_compat.py"]
        missing = [f for f in required if not (self.program_dir / f).exists()]
        if missing:
            raise EngineError(
                f"程序目录缺少文件：{', '.join(missing)}\n"
                f"请确认「程序目录」指向 CagePython 文件夹。")

    def _import_modules(self) -> None:
        """把程序目录加入 sys.path 并导入原始模块。"""
        path = str(self.program_dir)
        if path not in sys.path:
            sys.path.insert(0, path)
        # 清理可能残留的旧模块，避免切换目录后用到缓存
        for name in list(sys.modules):
            if sys.modules[name] is not None and \
                    getattr(sys.modules[name], "__file__", "") and \
                    str(self.program_dir) in str(sys.modules[name].__file__):
                del sys.modules[name]

        for name in ("state", "plot_style", "matlab_compat", "read_input",
                     "rk44", "dfdt_eqmot", "xiboli", "xibo_dangenlan",
                     "motion_simu_parameters", "fftfiltering_hz",
                     "hit_spek3", "wavestatistic", "jonswap_h",
                     "read_wamit1_file", "read_wamit234_file",
                     "read_wamit9_file"):
            self._modules[name] = importlib.import_module(name)

    def _work_dir(self) -> Path:
        """原始程序按相对路径读 WAMIT 文件，所以工作目录 = WAMIT 目录。"""
        folder = self.project.hydro.folder
        if folder and Path(folder).is_dir():
            return Path(folder).resolve()
        return self.program_dir

    # ===================================================================== #
    #  主流程
    # ===================================================================== #
    def _run_in_dir(self) -> RunResult:
        state = self._modules["state"]
        msp = self._modules["motion_simu_parameters"]
        read_input = self._modules["read_input"]
        xibo = self._modules["xibo_dangenlan"]
        rk44 = self._modules["rk44"]
        dfdt = self._modules["dfdt_eqmot"]
        fftf = self._modules["fftfiltering_hz"]
        hitspek = self._modules["hit_spek3"]
        wavestat = self._modules["wavestatistic"]
        matlab_compat = self._modules["matlab_compat"]
        plot_style = self._modules["plot_style"]

        result = RunResult(case_name=self.project.wave.case_name(),
                           output_dir=self.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 字体必须在任何出图之前设好：read_input() 里就会画 fig1/fig1001/fig4/K66
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        plot_style.apply()
        _ensure_cjk_font(plt)

        # ---------------- 阶段 1：参数 + 波面 ----------------
        self._stage(0, "running")
        self._log("准备参数与入射波…")
        self._apply_state_params(state)
        self._generate_wave(state, msp)
        self._log(f"波面就绪：{state.zeta0file}", "ok")
        self._stage(0, "done")

        # ---------------- 阶段 2：读取水动力 ----------------
        self._stage(1, "running")
        self._log("读取 WAMIT 水动力系数…")
        self._apply_mooring_patch(state)
        with _quiet_stdout():
            read_input.read_input()
        self._log(f"自由度 {state.nmodes}，时间步 {state.nt_sim}", "ok")
        self._stage(1, "done")

        # ---------------- 阶段 3：装配 ----------------
        self._stage(2, "running")
        self._log("装配质量阵与系泊曲线…")
        x_jie, T_H = self._catenary_curve()
        state.x_jie = x_jie
        state.T_H = T_H
        self._assemble(state)
        self._log("装配完成", "ok")
        self._stage(2, "done")

        # ---------------- 阶段 4：时间推进 ----------------
        self._stage(3, "running")
        self._log("开始时间推进…")
        x = self._time_loop(state, rk44, dfdt)
        self._log("时间推进完成", "ok")
        self._stage(3, "done")

        # ---------------- 阶段 5：后处理 ----------------
        self._stage(4, "running")
        self._log("后处理：滤波 / 谱 / 统计 / 出图…")
        self._post_process(state, x, result, fftf, hitspek, wavestat,
                           matlab_compat, plot_style)
        self._stage(4, "done")

        # ---------------- 阶段 6：保存 ----------------
        self._stage(5, "running")
        self._log("保存结果…")
        self._save(state, x, result)
        self._stage(5, "done")

        return result

    # ===================================================================== #
    #  阶段 1：参数
    # ===================================================================== #
    def _apply_state_params(self, state) -> None:
        """把 UI 配置写进 state（对应 MotionSimuParameters 的前半段）。"""
        p = self.project
        w = p.wave
        h = p.hydro

        state.numhum = w.numhum
        state.dt_sim = w.dt
        state.dt_sim_ys = w.dt
        state.scalef = 1.0
        state.rho = h.rho
        state.FRFtype = "WAMIT"
        state.FRFfname = h.prefix
        state.nHead = 1
        state.hbot = h.hbot
        state.newmds = 0
        state.imode = list(h.imode)
        state.ialtfrc = 2
        state.GDFfname = f"{h.prefix}.GDF"
        state.gdfOrder = "High"
        state.OtoG = "No"
        state.ulen = 1.0
        state.Mflag = 1
        state.Dflag = 0
        state.FixedModes = np.array([], dtype=int)
        state.FreeModes = np.array([], dtype=int)
        state.x0 = np.zeros(6)
        state.output_dir = str(self.output_dir)

        if w.mode == "regular":
            state.Wave_type = "regular"
            state.input = 0
        elif w.mode == "irregular":
            state.Wave_type = "irregular"
            state.input = 0
        else:
            state.Wave_type = "irregular"
            state.input = 1

    def _generate_wave(self, state, msp) -> None:
        """生成或读取波面，写入 state.Htol / nHtol / zeta0file。"""
        w = self.project.wave
        dt = w.dt

        if w.mode == "file":
            src = Path(w.wave_file)
            if not src.is_file():
                raise EngineError(f"波面文件不存在：{src}")
            state.zeta0file = str(src)
            header, usim, dt_iwf, nbeta, beta, xwave, Htol = \
                msp._read_wave_file(str(src))
            state.Htol = Htol
            state.nHtol = Htol[:-1]
            state.tlong = len(state.nHtol) / 10.0
            state.w1_2 = 0.0
            self._log(f"读取波面文件：{src.name}（{len(Htol)} 点）")
            return

        # 规则波 / JONSWAP：写到输出目录，避免污染程序目录
        zeta_file = self.output_dir / f"{w.case_name()}.dat"
        state.zeta0file = str(zeta_file)

        if w.mode == "regular":
            self._gen_regular(state, w, zeta_file)
        else:
            self._gen_jonswap(state, w, zeta_file)

    def _gen_regular(self, state, w, zeta_file: Path) -> None:
        """复刻 _regular_case，但波高/周期来自 UI。"""
        dt = w.dt
        state.WT = w.regular_t
        state.Input_w = 2.0 * np.pi / w.regular_t
        state.WH = w.regular_h
        state.WK = (2.0 * np.pi / w.regular_t) ** 2 / 9.81
        state.WW = 2.0 * np.pi / state.WK
        state.WD = 100.0

        w1_2, w2_2, w3_2, w4_2, w5_2 = 100.0, 300.0, 1800.0, 1900.0, 2000.0
        state.tlong = w4_2 - w1_2
        state.w1_2 = w1_2

        H1 = np.zeros(int(w1_2 / dt))
        HA = w.regular_h * np.sin(2.0 * np.pi / w.regular_t *
                                  (w1_2 + dt * np.arange(1, int((w2_2 - w1_2) / dt) + 1)))
        nHA = len(HA)
        HAA = HA * (np.arange(1, nHA + 1) / nHA) if w.ramp else HA
        H3 = w.regular_h * np.sin(2.0 * np.pi / w.regular_t *
                                  (w2_2 + dt * np.arange(1, int((w3_2 - w2_2) / dt) + 1)))
        HAend = w.regular_h * np.sin(2.0 * np.pi / w.regular_t *
                                     (w3_2 + dt * np.arange(1, int((w4_2 - w3_2) / dt) + 1)))
        nHAend = len(HAend)
        HAAend = HAend * ((nHAend - np.arange(1, nHAend + 1)) / nHAend) if w.ramp else HAend
        H5 = np.zeros(int((w5_2 - w4_2) / dt))

        with open(zeta_file, "w") as fid:
            fid.write("Full scale Hs=Xm, Tp=Xs regular, U =  0.00 heading angle   0.0\n")
            fid.write("%e\t%e\t%d\n" % (0.0, dt, 1))
            fid.write("%e\n" % 0.0)
            fid.write("%e\t%e\n" % (0.0, 0.0))
            for arr in (H1, HAA, H3, HAAend, H5):
                for v in arr:
                    fid.write("%f\n" % v)

        state.Htol = np.concatenate([H1, HAA, H3, HAAend, H5])
        self._log(f"生成规则波：H={w.regular_h} m，T={w.regular_t} s")

    def _gen_jonswap(self, state, w, zeta_file: Path) -> None:
        """复刻 _irregular_input0_case。"""
        jonswap_h = self._modules["jonswap_h"].jonswap_h
        state.Hw = w.hs
        state.Tw = w.tp
        state.tlong = w.duration

        # 固定随机种子，保证可复现
        matlab_compat = self._modules["matlab_compat"]
        matlab_compat.rng_seed(w.seed)

        irregular_wave, Wjp, Sjp = jonswap_h(w.hs, w.tp, w.dt, w.duration)
        state.w1_2 = 0.0

        with open(zeta_file, "w") as fid:
            fid.write("Full scale Hs=4m, Tp=11s regular, U =  0.00 heading angle   0.0\n")
            fid.write("%e\t%e\t%d\n" % (0.0, w.dt, 1))
            fid.write("%e\n" % 0.0)
            fid.write("%e\t%e\n" % (0.0, 0.0))
            for v in irregular_wave:
                fid.write("%f\n" % v)

        state.Htol = np.asarray(irregular_wave, dtype=float)
        self._log(f"生成 JONSWAP：Hs={w.hs} m，Tp={w.tp} s，种子={w.seed}")

    # ===================================================================== #
    #  阶段 2：系泊参数注入
    # ===================================================================== #
    def _apply_mooring_patch(self, state) -> None:
        """把 UI 里的系泊几何注入原始模块。

        ``xiboli.py`` 的导缆孔坐标是**模块级常量**，直接 setattr 即可生效；
        ``xibo_dangenlan.py`` 的缆绳参数是**函数内局部变量**，无法替换，
        所以这里用 ``_catenary_curve`` 重写一份可参数化的悬链线计算，
        在 ``_assemble`` 里替换掉原始函数。
        """
        m = self.project.mooring
        xiboli = self._modules["xiboli"]

        # 导缆孔坐标：按 A1/A2/A3/B1/B2/B3 顺序映射
        fl = {f.name: f for f in m.fairleads}
        for name, attr in [("A1", "Gas1"), ("A2", "Gas2"), ("A3", "Gas3"),
                           ("B1", "Gbs1"), ("B2", "Gbs2"), ("B3", "Gbs3")]:
            f = fl.get(name)
            if f is None:
                continue
            setattr(xiboli, attr, np.array([f.x, f.y, f.z], dtype=float))

        # 重心、锚点深度、水平原长
        xiboli.Ga = np.array(m.cg, dtype=float)
        xiboli.Z = float(m.anchor_depth)
        xiboli.L0 = float(m.horizontal_length)

        # 缆绳水平角（度 → 弧度）
        deg = np.pi / 180.0
        for name, attr in [("A1", "angleA1"), ("A2", "angleA2"), ("A3", "angleA3"),
                           ("B1", "angleB1"), ("B2", "angleB2"), ("B3", "angleB3")]:
            f = fl.get(name)
            if f is not None:
                setattr(xiboli, attr, float(f.angle) * deg)

    def _catenary_curve(self) -> tuple[np.ndarray, np.ndarray]:
        """可参数化的悬链线曲线（复刻 ``xibo_dangenlan.py``）。

        与原始实现的唯一区别：缆绳参数来自 UI 配置而非写死。
        """
        m = self.project.mooring
        T = np.arange(m.pretension_min,
                      m.pretension_max + m.pretension_step / 2,
                      m.pretension_step)
        nt = len(T)
        x_jie = np.zeros(nt)
        T_H = np.zeros(nt)

        for it in range(nt):
            T0 = T[it] * 1000.0 * 9.8067     # 预张力 N
            w = m.wet_weight                 # 湿重 N/m
            EA = m.ea                        # 轴向刚度 N
            Z = m.depth                      # 水深 + 干舷 m
            ST = m.length                    # 未拉伸原长 m

            fai_all = np.array([0.0, np.pi / 2.0])
            H = V = S = None
            with np.errstate(divide="ignore", invalid="ignore"):
                while fai_all[1] - fai_all[0] > 1e-12:
                    fai = np.array([fai_all[0],
                                    (fai_all[0] + fai_all[1]) / 2.0,
                                    fai_all[1]])
                    H = T0 * np.sin(fai)
                    V = T0 * np.cos(fai)
                    S = V[1] / w
                    L = (V[1] / w
                         + (H[1] ** 2 / (2.0 * w * EA))
                         * ((V[1] / H[1])
                            * (np.sqrt(1.0 + (V[1] / H[1]) ** 2)
                               + np.arcsinh(V[1] / H[1]))))
                    if S <= L:
                        Z_fai = ((H / w) * (np.sqrt(1.0 + (V / H) ** 2) - 1.0)
                                 + V ** 2 / (2.0 * w * EA) - Z)
                        if Z_fai[0] * Z_fai[1] <= 0:
                            fai_all = np.array([fai[0], fai[1]])
                        else:
                            fai_all = np.array([fai[1], fai[2]])
                    else:
                        break

            X = (H[1] / w) * np.arcsinh(V[1] / H[1]) + H[1] * V[1] / (w * EA)
            S0 = ST - S
            x_jie[it] = S0 * (H[1] / EA + 1.0) + X
            T_H[it] = np.sin(fai[1]) * T[it]

        return x_jie, T_H

    # ===================================================================== #
    #  阶段 3：装配
    # ===================================================================== #
    def _assemble(self, state) -> None:
        """复刻主程序里时间循环之前的装配代码。"""
        nmodes = state.nmodes
        # 同 _time_loop：read_input() 已把 dt_sim 改成无量纲值，这里用物理步长
        dt_sim = state.dt_sim_ys
        bjk = state.bjk
        Kjk = state.Kjk
        msmtrx = state.msmtrx
        ajk = state.ajk
        cjk = state.cjk

        for k in range(6):
            for j in range(6):
                bjk[j, k] = bjk[j, k] + 0.5 * dt_sim * Kjk[0, j, k]

        C_linjie = np.zeros((6, 6))
        b_fujia = np.zeros((6, 6))
        for i in range(2, 5):
            C_linjie[i, i] = 2.0 * np.sqrt((msmtrx[i, i] + ajk[i, i]) * cjk[i, i])
            b_fujia[i, i] = 0.05 * C_linjie[i, i]
            bjk[i, i] = bjk[i, i] + b_fujia[i, i]

        state.memory = np.zeros((nmodes, nmodes))
        state.minv = np.linalg.inv(state.mmsmtrx)

    # ===================================================================== #
    #  阶段 4：时间推进
    # ===================================================================== #
    def _time_loop(self, state, rk44, dfdt) -> np.ndarray:
        nmodes = state.nmodes
        nt_sim = state.nt_sim
        # 注意：read_input() 会把 state.dt_sim 改成无量纲化的 dt_iwf，
        # 所以积分步长必须用 dt_sim_ys（原始物理时间步），否则时间轴会错。
        dt_sim = state.dt_sim_ys
        Kjk = state.Kjk
        nt_irf = state.nt_irf

        x = np.zeros((2 * nmodes, nt_sim))
        x[nmodes:2 * nmodes, 0] = state.x0

        Fa1 = np.zeros(nt_sim); Fa2 = np.zeros(nt_sim); Fa3 = np.zeros(nt_sim)
        Fb1 = np.zeros(nt_sim); Fb2 = np.zeros(nt_sim); Fb3 = np.zeros(nt_sim)
        Fxiboli = np.zeros((6, nt_sim))

        report_every = max(1, nt_sim // 200)
        for it in range(2, nt_sim + 1):
            it0 = it - 1
            t0 = (it0 - 1) * dt_sim

            cstop = max(1, it - nt_irf + 1)
            for j in range(6):
                for k in range(6):
                    xk = x[k, (it - 2):(cstop - 1):-1]
                    kj = Kjk[1:(it - cstop), j, k]
                    mem = xk @ kj
                    mem = dt_sim * (mem + 0.5 * (Kjk[nt_irf - 1, j, k] * x[k, cstop - 1]))
                    state.memory[j, k] = mem

            res = rk44.rk44(x[:, it - 2], t0, dt_sim, dfdt.dfdt_eqmot)
            x[:, it - 1] = res[0]
            Fxiboli[:, it - 2] = res[2]
            Fa1[it - 2] = res[3]; Fa2[it - 2] = res[4]; Fa3[it - 2] = res[5]
            Fb1[it - 2] = res[6]; Fb2[it - 2] = res[7]; Fb3[it - 2] = res[8]

            if it % report_every == 0:
                frac = it / nt_sim
                self._progress(frac, f"t = {it * dt_sim:.1f} s / {nt_sim * dt_sim:.0f} s")

        state._Fa1, state._Fa2, state._Fa3 = Fa1, Fa2, Fa3
        state._Fb1, state._Fb2, state._Fb3 = Fb1, Fb2, Fb3
        state._Fxiboli = Fxiboli
        return x

    # ===================================================================== #
    #  阶段 5：后处理
    # ===================================================================== #
    def _post_process(self, state, x, result, fftf, hitspek, wavestat,
                      matlab_compat, plot_style) -> None:
        import matplotlib.pyplot as plt

        nmodes = state.nmodes
        nt_sim = state.nt_sim
        dt_sim_ys = state.dt_sim_ys
        rho = state.rho
        grav = state.grav
        numhum = state.numhum

        # 字体已在 _run_in_dir 开头设好（read_input 出图更早）

        t_sim = np.arange(1, nt_sim + 1) * dt_sim_ys
        fmin = 0.3 / (2.0 * np.pi)
        fmax = 3.0 / (2.0 * np.pi)
        dt1, dt2 = 500, nt_sim

        wave = x[:, dt1 - 1:dt2].T
        Fa1, Fa3 = state._Fa1, state._Fa3
        Fb1, Fb3 = state._Fb1, state._Fb3
        scaleF = rho * grav
        xiboli_f = np.column_stack([
            state._Fa1[dt1 - 1:dt2], state._Fa2[dt1 - 1:dt2],
            state._Fa3[dt1 - 1:dt2], state._Fb1[dt1 - 1:dt2],
            state._Fb2[dt1 - 1:dt2], state._Fb3[dt1 - 1:dt2],
        ]) * (rho * grav) / (1000.0 * grav)

        Real_wave, _, _ = fftf.fftfiltering_hz(fmin, fmax, dt_sim_ys, wave)
        Real_xiboli_f, _, _ = fftf.fftfiltering_hz(fmin, fmax, dt_sim_ys, xiboli_f)
        ys_wave, _, _ = fftf.fftfiltering_hz(0.00001, 100.0, dt_sim_ys, wave)
        ys_Real_xiboli_f, _, _ = fftf.fftfiltering_hz(0.00001, 100.0, dt_sim_ys, xiboli_f)

        titlem = ["纵荡", "横荡", "垂荡", "横摇", "纵摇", "艏摇"]
        motion_ylabel = ["位移 (m)"] * 3 + ["角位移 (rad)"] * 3
        motion_speclabel = ["谱密度 S(ω) (m²·s/rad)"] * 3 + ["谱密度 S(ω) (rad²·s/rad)"] * 3
        titlel = ["右舷缆 R1", "右舷缆 R2", "左舷缆 L1", "左舷缆 L2"]

        # ---- fig188：运动谱 ----
        plt.figure(188, figsize=plot_style.FIG_2x3)
        for j in range(6):
            RS, RW = hitspek.hit_spek3(Real_wave[:, 6 + j], len(Real_wave[:, 6 + j]), numhum, 10.0, 1.0)
            ysS, ysW = hitspek.hit_spek3(ys_wave[:, 6 + j], len(ys_wave[:, 6 + j]), numhum, 10.0, 1.0)
            ax = plt.subplot(2, 3, j + 1)
            plt.plot(ysW, ysS, lw=plot_style.LW_NORMAL)
            plt.plot(RW, RS, lw=plot_style.LW_NORMAL)
            plt.legend(["滤波前", "滤波后"], loc="upper right")
            plt.xlabel("圆频率 ω (rad/s)")
            plt.ylabel(motion_speclabel[j])
            plt.title(plot_style.spec_title(titlem[j], RW, RS))
            plt.xlim([0, 3])
            plot_style.plain_yaxis(ax)
            plot_style.plain_xaxis(ax)
        plt.suptitle("运动响应谱（滤波前后对比）")

        # ---- fig189：系泊力谱 ----
        mor = [1, 3, 4, 6]
        plt.figure(189, figsize=plot_style.FIG_2x2)
        for i in range(4):
            j = mor[i]
            RxiS, RxiW = hitspek.hit_spek3(Real_xiboli_f[:, j - 1], len(Real_xiboli_f[:, j - 1]), numhum, 10.0, 1.0)
            ysxiS, ysxiW = hitspek.hit_spek3(ys_Real_xiboli_f[:, j - 1], len(ys_Real_xiboli_f[:, j - 1]), numhum, 10.0, 1.0)
            ax = plt.subplot(2, 2, i + 1)
            plt.plot(ysxiW, ysxiS, lw=plot_style.LW_NORMAL)
            plt.plot(RxiW, RxiS, lw=plot_style.LW_NORMAL)
            plt.legend(["滤波前", "滤波后"], loc="upper right")
            plt.xlabel("圆频率 ω (rad/s)")
            plt.ylabel("谱密度 S(ω) (t²·s/rad)")
            plt.title(plot_style.spec_title(titlel[i], RxiW, RxiS))
            plt.xlim([0, 3])
            plot_style.plain_yaxis(ax)
            plot_style.plain_xaxis(ax)
        plt.suptitle("系泊力谱（滤波前后对比）")

        # ---- fig171：运动时程 ----
        plt.figure(171, figsize=plot_style.FIG_2x3)
        for j in range(6):
            ax = plt.subplot(2, 3, j + 1)
            plt.plot(t_sim, x[6 + j, :], lw=plot_style.LW_DENSE)
            plt.xlabel("时间 t (s)")
            plt.ylabel(motion_ylabel[j])
            plt.title(titlem[j])
            plt.xlim([0, t_sim[-1]])
            plot_style.plain_yaxis(ax)
            plot_style.stats_box(ax, x[6 + j, :])
        plt.suptitle("运动响应原始时程")

        # ---- fig173：系泊力时程 ----
        t_mor = t_sim[:-1]
        F_mor = [(Fb1 * scaleF)[:-1], (Fb3 * scaleF)[:-1],
                 (Fa1 * scaleF)[:-1], (Fa3 * scaleF)[:-1]]
        plt.figure(173, figsize=plot_style.FIG_2x2)
        for i in range(4):
            ax = plt.subplot(2, 2, i + 1)
            plt.plot(t_mor, F_mor[i], lw=plot_style.LW_DENSE)
            plt.ylabel("缆绳张力 (N)")
            plt.xlabel("时间 t (s)")
            plt.title(titlel[i])
            plt.xlim([t_mor[0], t_mor[-1]])
            plot_style.plain_yaxis(ax)
            plot_style.stats_box(ax, F_mor[i])
        plt.suptitle("系泊力原始时程（末端无效点已剔除）")

        # ---- 统计 ----
        SA = 2000
        lo = 199
        hi = (dt2 - dt1 + 1) - 200
        real_time = np.arange(1, hi - lo + 1) * dt_sim_ys

        result_stats = np.zeros((12, 3))
        for i in range(12):
            result_stats[i, :] = wavestat.wavestatistic(
                real_time, Real_wave[lo:hi, i] - matlab_compat.smooth(Real_wave[lo:hi, i], SA))

        result_xiboli = np.zeros((4, 3))
        for idx, col in enumerate([0, 2, 3, 5]):
            result_xiboli[idx, :] = wavestat.wavestatistic(
                real_time, Real_xiboli_f[lo:hi, col] - matlab_compat.smooth(Real_xiboli_f[lo:hi, col], SA))

        # ---- fig191：运动滤波对比 ----
        tseg = np.arange(lo + 1, hi + 1) * dt_sim_ys
        plt.figure(191, figsize=plot_style.FIG_2x3)
        for j in range(6):
            ax = plt.subplot(2, 3, j + 1)
            raw = wave[lo:hi, 6 + j]
            wf = Real_wave[lo:hi, 6 + j] - matlab_compat.smooth(Real_wave[lo:hi, 6 + j], SA)
            plt.plot(tseg, raw, lw=plot_style.LW_DENSE)
            plt.plot(tseg, wf, lw=plot_style.LW_DENSE)
            plt.xlabel("时间 t (s)")
            plt.ylabel(motion_ylabel[j])
            plt.legend(["原始时程", "波频分量"], loc="lower center", ncol=2)
            plt.title(titlem[j])
            plt.xlim([tseg[0], tseg[-1]])
            plot_style.plain_yaxis(ax)
            plot_style.stats_box(ax, wf, loc="upper right", title="波频分量")
        plt.suptitle("运动滤波前后时程对比")

        # ---- fig193：系泊力滤波对比 ----
        plt.figure(193, figsize=plot_style.FIG_2x2)
        for i in range(4):
            j = mor[i]
            ax = plt.subplot(2, 2, i + 1)
            raw = ys_Real_xiboli_f[lo:hi, j - 1]
            wf = Real_xiboli_f[lo:hi, j - 1] - matlab_compat.smooth(Real_xiboli_f[lo:hi, j - 1], SA)
            plt.plot(tseg, raw, lw=plot_style.LW_DENSE)
            plt.plot(tseg, wf, lw=plot_style.LW_DENSE)
            plt.legend(["原始时程", "波频分量"], loc="lower center", ncol=2)
            plt.xlabel("时间 t (s)")
            plt.ylabel("缆绳张力 (t)")
            plt.title(titlel[i])
            plt.xlim([tseg[0], tseg[-1]])
            plot_style.plain_yaxis(ax)
            plot_style.stats_box(ax, wf, loc="upper right", title="波频分量")
        plt.suptitle("系泊力滤波前后时程对比")

        # ---- fig200/203：波面 ----
        wave_fignum = 203 if self.project.wave.mode == "file" else 200
        plt.figure(wave_fignum, figsize=plot_style.FIG_1x1)
        ax = plt.gca()
        Htol = np.asarray(state.Htol, dtype=float)
        plt.plot(dt_sim_ys * np.arange(1, len(Htol) + 1), Htol, lw=plot_style.LW_DENSE)
        plt.xlabel("时间 t (s)")
        plt.ylabel("波面高程 η (m)")
        plt.title(f"入射波面时历（{self.project.wave.case_name()}）")
        plot_style.plain_yaxis(ax)

        # ---- 保存图片 ----
        fig_names = [188, 189, 171, 173, 191, 193, wave_fignum, 1001, 1, 4]
        if self.project.wave.mode == "irregular":
            fig_names.append(71)
        for fignum in fig_names:
            try:
                fig = plt.figure(fignum)
                path = self.output_dir / f"fig{fignum}.png"
                fig.savefig(path, dpi=180)
                result.figures.append(path)
            except Exception:  # noqa: BLE001
                pass

        # K66 图由 read_input 生成，这里补存
        k66 = self.output_dir / "K66-0.png"
        if k66.exists():
            result.figures.append(k66)

        plt.close("all")

        # ---- 汇总 ----
        result.time = t_sim
        xx = np.zeros((6, nt_sim))
        xx[0:3, :] = x[6:9, :]
        xx[3:6, :] = x[9:12, :] * 57.3
        result.motion = xx
        result.mooring = np.vstack([Fa1, Fa3, Fb1, Fb3]) * scaleF
        result.wave = np.asarray(state.Htol, dtype=float)[:nt_sim]
        result.stats_motion = result_stats
        result.stats_mooring = result_xiboli

        momax = np.zeros(14)
        for i in range(6):
            momax[i] = np.max(x[6 + i, :])
        momax[6] = np.max(Fb1 * scaleF); momax[7] = np.max(Fb3 * scaleF)
        momax[8] = np.max(Fa1 * scaleF); momax[9] = np.max(Fa3 * scaleF)
        momax[10] = np.min(Fb1 * scaleF); momax[11] = np.min(Fb3 * scaleF)
        momax[12] = np.min(Fa1 * scaleF); momax[13] = np.min(Fa3 * scaleF)
        result.momax = momax

    # ===================================================================== #
    #  阶段 6：保存
    # ===================================================================== #
    def _save(self, state, x, result: RunResult) -> None:
        import scipy.io as sio

        case = result.case_name
        result.mat_path = self.output_dir / f"{case}_TSR.mat"
        result.npz_path = self.output_dir / f"{case}_TSR.npz"
        result.txt_path = self.output_dir / f"{case}_统计结果.txt"

        tsr = {
            "case": str(case),
            "motion": result.motion,
            "mooring": result.mooring,
            "time": result.time,
            "wave": result.wave,
        }
        sio.savemat(result.mat_path, {"TSR": tsr})
        np.savez(result.npz_path,
                 case=np.asarray(case), motion=result.motion,
                 mooring=result.mooring, time=result.time, wave=result.wave)

        # 统计文本
        dof = ["纵荡", "横荡", "垂荡", "横摇", "纵摇", "艏摇"]
        lines = [f"工况名称        : {case}",
                 f"仿真时长        : {result.time[-1]:.1f} s",
                 f"初始系泊力      : {result.mooring[0, 0]:.2f} N / 缆",
                 "",
                 "[一] 运动响应 —— 波频分量特征值",
                 "%-6s %14s %14s %14s  %s" % ("自由度", "H13", "H110", "Hmax", "单位")]
        for j in range(6):
            h13, h110, hmax = result.stats_motion[6 + j, :]
            lines.append("%-6s %14.5g %14.5g %14.5g  %s"
                         % (dof[j], h13, h110, hmax, "m" if j < 3 else "rad"))
        lines += ["", "[二] 运动响应 —— 全时历极值",
                  "%-6s %14s %14s  %s" % ("自由度", "最大值", "最小值", "单位")]
        for j in range(6):
            lines.append("%-6s %14.5g %14.5g  %s"
                         % (dof[j], result.momax[j], np.min(result.motion[j]),
                            "m" if j < 3 else "rad"))
        result.txt_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # ===================================================================== #
    #  工具
    # ===================================================================== #
    def _stage(self, index: int, status: str) -> None:
        """阶段事件通过 progress 回调的特殊前缀传递。"""
        self._progress(-1.0, f"__stage__{index}:{status}")

    def _log(self, msg: str, level: str = "info") -> None:
        self._log_fn(msg, level)


@contextlib.contextmanager
def _quiet_stdout():
    """临时屏蔽原始程序的 print 输出。"""
    import io
    old = sys.stdout
    sys.stdout = io.StringIO()
    try:
        yield
    finally:
        sys.stdout = old


# 各平台常见中文字体（按优先级）
_CJK_FONTS = [
    "Microsoft YaHei", "SimHei", "PingFang SC", "Hiragino Sans GB",
    "Source Han Sans SC", "Noto Sans CJK SC", "WenQuanYi Micro Hei",
    "Arial Unicode MS",
]


def _ensure_cjk_font(plt) -> None:
    """确保 matplotlib 能显示中文。

    ``plot_style.apply()`` 里写死了 Windows 字体，这里检查当前系统实际
    可用的字体，把可用的中文字体排到最前面。
    """
    from matplotlib import font_manager

    available = {f.name for f in font_manager.fontManager.ttflist}
    usable = [name for name in _CJK_FONTS if name in available]
    if not usable:
        return
    current = list(plt.rcParams.get("font.sans-serif", []))
    # 可用中文字体优先，其余保持原样（去重）
    merged = usable + [f for f in current if f not in usable]
    plt.rcParams["font.sans-serif"] = merged
    plt.rcParams["axes.unicode_minus"] = False
