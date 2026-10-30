"""工程配置数据模型。

一个「工程」= 一份配置 + 一个输出目录。配置可存成 JSON，
后续计算模块直接读这个对象，不再改源码里的硬编码变量。
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


# --------------------------------------------------------------------------- #
#  水动力
# --------------------------------------------------------------------------- #
@dataclass
class HydroConfig:
    """WAMIT 水动力系数。"""

    prefix: str = "WAMIT_5S"
    folder: str = ""
    hbot: float = -1.0          # 水深（m）
    rho: float = 1025.0         # 流体密度（kg/m³）
    # 6 个自由度是否自由（1=自由，0=固定）
    imode: list[int] = field(default_factory=lambda: [1, 1, 1, 1, 1, 1])

    # 需要检查的 6 个文件（相对 folder）
    REQUIRED_FILES = [
        (".1", "附加质量 / 阻尼"),
        (".3", "一阶激振力"),
        (".9", "二阶漂移力"),
        (".GDF", "几何"),
        ("1.hst", "静水刚度"),
        ("1.mmx", "质量 / 外阻尼"),
    ]

    def file_paths(self) -> list[tuple[str, str, Path]]:
        folder = Path(self.folder) if self.folder else Path(".")
        out = []
        for suffix, desc in self.REQUIRED_FILES:
            out.append((f"{self.prefix}{suffix}", desc, folder / f"{self.prefix}{suffix}"))
        return out


# --------------------------------------------------------------------------- #
#  波浪
# --------------------------------------------------------------------------- #
@dataclass
class WaveConfig:
    """波浪工况。mode: regular / irregular / file"""

    mode: str = "regular"

    # 规则波
    regular_h: float = 6.0
    regular_t: float = 10.0
    ramp: bool = True

    # JONSWAP
    hs: float = 6.0
    tp: float = 10.0
    gamma: float = 3.3
    duration: float = 2000.0
    seed: int = 5489

    # 外部波面文件
    wave_file: str = ""

    # 通用
    dt: float = 0.1
    numhum: int = 50

    def case_name(self) -> str:
        """输出目录名，与 Python 版命名规则一致。"""
        if self.mode == "regular":
            return f"RegularH={self.regular_h}T={self.regular_t}"
        if self.mode == "irregular":
            return f"IrregularHs={self.hs}Tp={self.tp}"
        stem = Path(self.wave_file).stem if self.wave_file else "wave_file"
        return stem


# --------------------------------------------------------------------------- #
#  系泊
# --------------------------------------------------------------------------- #
@dataclass
class Fairlead:
    name: str
    x: float
    y: float
    z: float
    angle: float
    enabled: bool = True


def default_fairleads() -> list[Fairlead]:
    return [
        Fairlead("A1", -40.5, -15.0, -11.5, 210.0, True),
        Fairlead("A2", 0.0, 0.0, 0.0, 270.0, False),
        Fairlead("A3", 40.5, -15.0, -11.5, 330.0, True),
        Fairlead("B1", -40.5, 15.0, -11.5, 150.0, True),
        Fairlead("B2", 0.0, 0.0, 0.0, 90.0, False),
        Fairlead("B3", 40.5, 15.0, -11.5, 30.0, True),
    ]


@dataclass
class MooringConfig:
    """系泊系统。"""

    wet_weight: float = 290.0       # 湿重 N/m
    ea: float = 1.1468e7            # 轴向刚度 N
    depth: float = 90.74            # 水深 + 干舷 m
    length: float = 160.0           # 未拉伸原长 m
    pretension_min: float = 5.0     # ton
    pretension_max: float = 50.0
    pretension_step: float = 0.05

    cg: tuple[float, float, float] = (0.0, 0.0, -5.26)
    anchor_depth: float = 90.0
    horizontal_length: float = 132.29

    fairleads: list[Fairlead] = field(default_factory=default_fairleads)


# --------------------------------------------------------------------------- #
#  工程
# --------------------------------------------------------------------------- #
@dataclass
class Project:
    name: str = "未命名工程"
    hydro: HydroConfig = field(default_factory=HydroConfig)
    wave: WaveConfig = field(default_factory=WaveConfig)
    mooring: MooringConfig = field(default_factory=MooringConfig)

    # ---- 序列化 ----
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Project":
        hydro = HydroConfig(**data.get("hydro", {}))
        wave = WaveConfig(**data.get("wave", {}))
        moor_data = dict(data.get("mooring", {}))
        fairleads = [Fairlead(**f) for f in moor_data.pop("fairleads", [])]
        mooring = MooringConfig(**moor_data)
        if fairleads:
            mooring.fairleads = fairleads
        return cls(name=data.get("name", "未命名工程"),
                   hydro=hydro, wave=wave, mooring=mooring)

    def save(self, path: Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: Path) -> "Project":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.from_dict(data)
