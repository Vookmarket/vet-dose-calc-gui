"""処方計算ロジック -- 投与日数・回数から総量と費用を算出

GUI非依存のpure Pythonモジュール。
VT-004のdosage_calcとは独立した処方計算専用ロジック。
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class PrescriptionResult:
    """処方計算の結果"""
    dose_per_time: float    # 1回投与量（錠/ml等）
    times_per_day: int      # 1日投与回数
    days: int               # 投与日数
    total_units: float      # 総投与量（錠/ml等）
    daily_units: float      # 1日あたり投与量


def calculate_prescription(
    dose_per_time: float,
    times_per_day: int,
    days: int,
) -> PrescriptionResult:
    """処方の総量を計算する。

    Args:
        dose_per_time: 1回あたりの投与量（錠数/ml数）
        times_per_day: 1日あたりの投与回数（1-6）
        days: 投与日数（1-365）

    Returns:
        PrescriptionResult

    Raises:
        ValueError: バリデーション違反
    """
    if dose_per_time <= 0:
        raise ValueError(
            f"1回投与量は正の値でなければなりません: {dose_per_time}"
        )
    if times_per_day < 1 or times_per_day > 6:
        raise ValueError(
            f"投与回数/日は1-6の範囲で指定してください: {times_per_day}"
        )
    if days < 1 or days > 365:
        raise ValueError(
            f"投与日数は1-365の範囲で指定してください: {days}"
        )

    daily_units = round(dose_per_time * times_per_day, 3)
    total_units = round(daily_units * days, 3)

    return PrescriptionResult(
        dose_per_time=dose_per_time,
        times_per_day=times_per_day,
        days=days,
        total_units=total_units,
        daily_units=daily_units,
    )


def calculate_cost(
    total_units: float,
    unit_price: Optional[float],
) -> Optional[float]:
    """処方費用を計算する。

    Args:
        total_units: 総投与量（錠/ml等）
        unit_price: 単価（円/錠 or 円/ml）。Noneなら費用計算しない。

    Returns:
        費用（円）。unit_priceがNoneの場合はNoneを返す。
    """
    if unit_price is None:
        return None
    if unit_price < 0:
        raise ValueError(f"単価は0以上でなければなりません: {unit_price}")
    return round(total_units * unit_price, 1)
