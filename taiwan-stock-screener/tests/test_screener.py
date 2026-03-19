"""
Unit Tests for Buffett Screener
台股篩選器單元測試
"""

import sys
import os
import unittest

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from screener import BuffettScreener, StockScore


class TestBuffettScreener(unittest.TestCase):

    def setUp(self):
        self.screener = BuffettScreener()

    def _make_financial_data(self, roe=18.0, eps=5.0, debt_ratio=0.3) -> dict:
        """建立測試用財務資料"""
        # 模擬 FinMind 財報格式
        income_rows = []
        for year_offset in range(5):
            year = 2019 + year_offset
            for q in [1, 2, 3, 4]:
                income_rows.append({"date": f"{year}-{q*3:02d}-01", "type": "ROE", "value": roe + year_offset * 0.5})
                income_rows.append({"date": f"{year}-{q*3:02d}-01", "type": "EPS", "value": eps + year_offset * 0.2})
                income_rows.append({"date": f"{year}-{q*3:02d}-01", "type": "Revenue", "value": 1000000 + year_offset * 50000})
                income_rows.append({"date": f"{year}-{q*3:02d}-01", "type": "GrossProfit", "value": 300000 + year_offset * 15000})

        balance_rows = [
            {"date": "2024-12-01", "type": "TotalAssets", "value": 1000000},
            {"date": "2024-12-01", "type": "TotalLiabilities", "value": 1000000 * debt_ratio},
        ]

        cashflow_rows = [
            {"date": "2024-12-01", "type": "CashFlowsFromOperatingActivities", "value": 200000},
            {"date": "2024-12-01", "type": "AcquisitionOfPropertyPlantAndEquipment", "value": 50000},
        ]

        return {
            "income": pd.DataFrame(income_rows),
            "balance": pd.DataFrame(balance_rows),
            "cashflow": pd.DataFrame(cashflow_rows),
        }

    def test_high_quality_stock_passes(self):
        """優質股票應通過大部分篩選"""
        financial = self._make_financial_data(roe=20.0, eps=8.0, debt_ratio=0.25)
        price_data = {"pe_ratio": 15.0, "pb_ratio": 2.0, "dividend_yield": 4.0, "price": 100.0}

        score = self.screener.screen("2330", "台積電", financial, price_data)

        self.assertGreater(score.total_score, 60)
        self.assertGreater(score.roe_avg, 0)
        self.assertEqual(score.stock_id, "2330")

    def test_high_debt_stock_penalized(self):
        """高負債股票應得到低分"""
        financial = self._make_financial_data(roe=8.0, eps=1.0, debt_ratio=0.85)
        price_data = {"pe_ratio": 35.0, "pb_ratio": 5.0, "dividend_yield": 0.0, "price": 50.0}

        score = self.screener.screen("9999", "高負債公司", financial, price_data)

        self.assertLess(score.total_score, 60)
        self.assertIn("負債比率", " ".join(score.reason))

    def test_pe_score_calculation(self):
        """本益比評分邏輯驗證"""
        self.assertEqual(self.screener._calc_pe_score(8), 100.0)
        self.assertEqual(self.screener._calc_pe_score(15), 85.0)
        self.assertEqual(self.screener._calc_pe_score(18), 70.0)
        self.assertEqual(self.screener._calc_pe_score(0), 0.0)

    def test_pb_score_calculation(self):
        """股價淨值比評分邏輯驗證"""
        self.assertEqual(self.screener._calc_pb_score(0.8), 100.0)
        self.assertEqual(self.screener._calc_pb_score(1.3), 85.0)
        self.assertEqual(self.screener._calc_pb_score(1.8), 70.0)
        self.assertEqual(self.screener._calc_pb_score(0.0), 0.0)

    def test_rank_stocks(self):
        """排名功能驗證"""
        scores = [
            StockScore(stock_id="A", total_score=75.0),
            StockScore(stock_id="B", total_score=55.0),
            StockScore(stock_id="C", total_score=85.0),
            StockScore(stock_id="D", total_score=65.0),
        ]
        ranked = self.screener.rank_stocks(scores, min_score=60.0)

        self.assertEqual(len(ranked), 3)  # B 被排除
        self.assertEqual(ranked[0].stock_id, "C")  # 最高分排第一
        self.assertEqual(ranked[1].stock_id, "A")
        self.assertEqual(ranked[2].stock_id, "D")

    def test_total_score_weights_sum_to_one(self):
        """確認權重加總為 1"""
        from config import SCORING_WEIGHTS
        total = sum(SCORING_WEIGHTS.values())
        self.assertAlmostEqual(total, 1.0, places=5)

    def test_dividend_score(self):
        """股利評分驗證"""
        self.assertEqual(self.screener._calc_dividend_score(0.0), 0.0)
        self.assertEqual(self.screener._calc_dividend_score(1.0), 30.0)
        self.assertEqual(self.screener._calc_dividend_score(3.0), 50.0)
        self.assertEqual(self.screener._calc_dividend_score(5.0), 75.0)
        self.assertEqual(self.screener._calc_dividend_score(9.0), 100.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
