"""処方計算ロジックのユニットテスト -- 6ケース"""

import sys
from pathlib import Path

import pytest

# VT-005パッケージをインポート可能にする
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from vet_dose_calc_gui.prescription_calc import (
    PrescriptionResult,
    calculate_cost,
    calculate_prescription,
)


class TestCalculatePrescription:
    """calculate_prescription() のテスト"""

    def test_normal_bid_7days(self):
        """正常: 1錠 x BID x 7日 = 14錠"""
        result = calculate_prescription(
            dose_per_time=1.0,
            times_per_day=2,
            days=7,
        )
        assert result.total_units == 14.0
        assert result.daily_units == 2.0
        assert result.dose_per_time == 1.0
        assert result.times_per_day == 2
        assert result.days == 7

    def test_normal_half_tid_14days(self):
        """正常: 0.5錠 x TID x 14日 = 21錠"""
        result = calculate_prescription(
            dose_per_time=0.5,
            times_per_day=3,
            days=14,
        )
        assert result.total_units == 21.0
        assert result.daily_units == 1.5

    def test_error_zero_days(self):
        """エラー: 投与日数0は不正"""
        with pytest.raises(ValueError, match="投与日数は1-365の範囲"):
            calculate_prescription(
                dose_per_time=1.0,
                times_per_day=2,
                days=0,
            )

    def test_error_negative_dose(self):
        """エラー: 負の投与量は不正"""
        with pytest.raises(ValueError, match="正の値"):
            calculate_prescription(
                dose_per_time=-1.0,
                times_per_day=2,
                days=7,
            )


class TestCalculateCost:
    """calculate_cost() のテスト"""

    def test_tablet_cost(self):
        """正常: 14錠 x 50円 = 700円"""
        cost = calculate_cost(14.0, 50.0)
        assert cost == 700.0

    def test_no_unit_price(self):
        """正常: 単価未登録 → None"""
        cost = calculate_cost(14.0, None)
        assert cost is None

    def test_liquid_cost(self):
        """正常: 3.5ml x 30円 = 105円"""
        cost = calculate_cost(3.5, 30.0)
        assert cost == 105.0
