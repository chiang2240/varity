"""
Buffett Value Screener for Taiwan Stocks
台股巴菲特價值篩選核心邏輯

篩選條件 (7大指標):
1. ROE (股東權益報酬率)    > 15% 連續3年
2. EPS (每股盈餘)          連續3年正成長
3. 負債比率                < 50%
4. 本益比 (P/E)            < 20
5. 股價淨值比 (P/B)        < 3.0
6. 自由現金流 (FCF)        > 0
7. 股利發放                連續3年有配息
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

from config import BUFFETT_CRITERIA, SCORING_WEIGHTS

logger = logging.getLogger(__name__)


@dataclass
class StockScore:
    """個股評分結果"""
    stock_id: str
    name: str = ""
    total_score: float = 0.0
    passed_criteria: int = 0
    total_criteria: int = 7

    # 個別指標
    roe_avg: float = 0.0
    roe_score: float = 0.0

    eps_growth_rate: float = 0.0
    eps_score: float = 0.0

    debt_ratio: float = 0.0
    debt_score: float = 0.0

    pe_ratio: float = 0.0
    pe_score: float = 0.0

    pb_ratio: float = 0.0
    pb_score: float = 0.0

    fcf: float = 0.0
    fcf_score: float = 0.0

    dividend_yield: float = 0.0
    dividend_score: float = 0.0

    # 額外資訊
    current_price: float = 0.0
    market_cap: float = 0.0
    revenue_growth: float = 0.0
    gross_margin: float = 0.0
    reason: list = field(default_factory=list)

    def is_qualified(self, min_score: float = 60.0) -> bool:
        return self.total_score >= min_score

    def summary(self) -> str:
        lines = [
            f"{'='*50}",
            f"股票代號: {self.stock_id}  {self.name}",
            f"總分: {self.total_score:.1f}/100  通過指標: {self.passed_criteria}/{self.total_criteria}",
            f"{'─'*50}",
            f"ROE (3年均)    : {self.roe_avg:>6.1f}%   得分: {self.roe_score:.0f}",
            f"EPS成長率      : {self.eps_growth_rate:>6.1f}%   得分: {self.eps_score:.0f}",
            f"負債比率       : {self.debt_ratio:>6.1f}%   得分: {self.debt_score:.0f}",
            f"本益比 (P/E)   : {self.pe_ratio:>6.1f}x   得分: {self.pe_score:.0f}",
            f"股價淨值比(P/B): {self.pb_ratio:>6.2f}x   得分: {self.pb_score:.0f}",
            f"自由現金流     : {self.fcf:>8.0f}   得分: {self.fcf_score:.0f}",
            f"股利殖利率     : {self.dividend_yield:>6.2f}%   得分: {self.dividend_score:.0f}",
            f"{'─'*50}",
            f"現價: {self.current_price:.2f}  毛利率: {self.gross_margin:.1f}%  "
            f"營收成長: {self.revenue_growth:.1f}%",
        ]
        if self.reason:
            lines.append("未通過原因: " + "; ".join(self.reason))
        return "\n".join(lines)


class BuffettScreener:
    """巴菲特價值投資篩選器"""

    def __init__(self, criteria: dict = None, weights: dict = None):
        self.criteria = criteria or BUFFETT_CRITERIA
        self.weights = weights or SCORING_WEIGHTS

    # ----------------------------------------------------------
    # 主篩選入口
    # ----------------------------------------------------------
    def screen(self, stock_id: str, name: str,
               financial_data: dict, price_data: dict) -> StockScore:
        """
        對單一股票執行巴菲特篩選
        :param financial_data: { 'income': df, 'balance': df, 'cashflow': df }
        :param price_data: { 'pe_ratio', 'pb_ratio', 'dividend_yield', 'price' }
        :return: StockScore
        """
        score = StockScore(stock_id=stock_id, name=name)
        score.current_price = price_data.get("price", 0)
        score.pe_ratio = price_data.get("pe_ratio", 0)
        score.pb_ratio = price_data.get("pb_ratio", 0)
        score.dividend_yield = price_data.get("dividend_yield", 0)

        income_df = financial_data.get("income", pd.DataFrame())
        balance_df = financial_data.get("balance", pd.DataFrame())
        cashflow_df = financial_data.get("cashflow", pd.DataFrame())

        # === 1. ROE 分析 ===
        score.roe_avg, score.roe_score = self._calc_roe_score(income_df, balance_df)
        if score.roe_avg >= self.criteria["roe_min"]:
            score.passed_criteria += 1
        else:
            score.reason.append(f"ROE {score.roe_avg:.1f}% < {self.criteria['roe_min']}%")

        # === 2. EPS 成長 ===
        score.eps_growth_rate, score.eps_score = self._calc_eps_growth_score(income_df)
        if score.eps_growth_rate > 0:
            score.passed_criteria += 1
        else:
            score.reason.append(f"EPS成長率 {score.eps_growth_rate:.1f}% ≤ 0")

        # === 3. 負債比率 ===
        score.debt_ratio, score.debt_score = self._calc_debt_score(balance_df)
        if score.debt_ratio <= self.criteria["debt_ratio_max"]:
            score.passed_criteria += 1
        else:
            score.reason.append(f"負債比率 {score.debt_ratio:.1f}% > {self.criteria['debt_ratio_max']}%")

        # === 4. 本益比 ===
        score.pe_score = self._calc_pe_score(score.pe_ratio)
        if 0 < score.pe_ratio <= self.criteria["pe_ratio_max"]:
            score.passed_criteria += 1
        elif score.pe_ratio == 0:
            score.reason.append("本益比資料不足")
        else:
            score.reason.append(f"本益比 {score.pe_ratio:.1f} > {self.criteria['pe_ratio_max']}")

        # === 5. 股價淨值比 ===
        score.pb_score = self._calc_pb_score(score.pb_ratio)
        if 0 < score.pb_ratio <= self.criteria["pb_ratio_max"]:
            score.passed_criteria += 1
        elif score.pb_ratio == 0:
            score.reason.append("股價淨值比資料不足")
        else:
            score.reason.append(f"P/B {score.pb_ratio:.2f} > {self.criteria['pb_ratio_max']}")

        # === 6. 自由現金流 ===
        score.fcf, score.fcf_score = self._calc_fcf_score(cashflow_df)
        if score.fcf > 0:
            score.passed_criteria += 1
        else:
            score.reason.append(f"自由現金流 {score.fcf:.0f} ≤ 0")

        # === 7. 股利 ===
        score.dividend_score = self._calc_dividend_score(score.dividend_yield)
        if score.dividend_yield > 0:
            score.passed_criteria += 1
        else:
            score.reason.append("近期無股利資料")

        # === 額外指標 ===
        score.gross_margin = self._calc_gross_margin(income_df)
        score.revenue_growth = self._calc_revenue_growth(income_df)

        # === 加權總分 ===
        score.total_score = self._calc_total_score(score)

        return score

    # ----------------------------------------------------------
    # 個別指標計算
    # ----------------------------------------------------------
    def _calc_roe_score(self, income_df: pd.DataFrame,
                        balance_df: pd.DataFrame) -> tuple[float, float]:
        """計算 ROE 平均值與得分"""
        try:
            roe_values = self._extract_roe(income_df, balance_df)
            if not roe_values:
                return 0.0, 0.0
            avg_roe = np.mean(roe_values[-self.criteria["roe_years"]:])
            # 評分: ROE 15%=60分, 20%=80分, 30%+=100分
            score = min(100, max(0, (avg_roe / 30) * 100))
            return float(avg_roe), float(score)
        except Exception as e:
            logger.debug(f"ROE計算錯誤: {e}")
            return 0.0, 0.0

    def _calc_eps_growth_score(self, income_df: pd.DataFrame) -> tuple[float, float]:
        """計算 EPS 成長率與得分"""
        try:
            eps_values = self._extract_eps(income_df)
            if len(eps_values) < 2:
                return 0.0, 0.0
            # 取近3年成長率平均
            growths = []
            for i in range(1, min(self.criteria["eps_growth_years"] + 1, len(eps_values))):
                if eps_values[i - 1] > 0:
                    g = (eps_values[i] - eps_values[i - 1]) / eps_values[i - 1] * 100
                    growths.append(g)
            if not growths:
                return 0.0, 0.0
            avg_growth = np.mean(growths)
            # 評分: 成長5%=50分, 15%=80分, 30%+=100分
            score = min(100, max(0, 50 + avg_growth * 1.67))
            return float(avg_growth), float(score)
        except Exception as e:
            logger.debug(f"EPS成長計算錯誤: {e}")
            return 0.0, 0.0

    def _calc_debt_score(self, balance_df: pd.DataFrame) -> tuple[float, float]:
        """計算負債比率與得分"""
        try:
            debt_ratio = self._extract_debt_ratio(balance_df)
            if debt_ratio == 0:
                return 0.0, 0.0
            # 評分: 負債比率低=高分 (30%=100, 50%=70, 70%=30)
            score = max(0, 100 - (debt_ratio - 20) * 2)
            return float(debt_ratio), float(score)
        except Exception as e:
            logger.debug(f"負債比率計算錯誤: {e}")
            return 0.0, 0.0

    def _calc_pe_score(self, pe_ratio: float) -> float:
        """計算本益比得分"""
        if pe_ratio <= 0:
            return 0.0
        # P/E 5=100, 10=85, 15=70, 20=55, 25=40, 30+=20
        if pe_ratio <= 10:
            return 100.0
        elif pe_ratio <= 15:
            return 85.0
        elif pe_ratio <= 20:
            return 70.0
        elif pe_ratio <= 25:
            return 55.0
        else:
            return max(10, 55 - (pe_ratio - 25) * 2)

    def _calc_pb_score(self, pb_ratio: float) -> float:
        """計算股價淨值比得分"""
        if pb_ratio <= 0:
            return 0.0
        # P/B 1=100, 1.5=85, 2=70, 3=50, 4+=20
        if pb_ratio <= 1.0:
            return 100.0
        elif pb_ratio <= 1.5:
            return 85.0
        elif pb_ratio <= 2.0:
            return 70.0
        elif pb_ratio <= 3.0:
            return 50.0
        else:
            return max(10, 50 - (pb_ratio - 3) * 15)

    def _calc_fcf_score(self, cashflow_df: pd.DataFrame) -> tuple[float, float]:
        """計算自由現金流得分"""
        try:
            fcf = self._extract_fcf(cashflow_df)
            if fcf is None:
                return 0.0, 0.0
            score = 100.0 if fcf > 0 else 0.0
            return float(fcf), float(score)
        except Exception as e:
            logger.debug(f"FCF計算錯誤: {e}")
            return 0.0, 0.0

    def _calc_dividend_score(self, dividend_yield: float) -> float:
        """計算股利殖利率得分"""
        if dividend_yield <= 0:
            return 0.0
        # 殖利率 2%=50, 4%=75, 6%=90, 8%+=100
        if dividend_yield >= 8:
            return 100.0
        elif dividend_yield >= 6:
            return 90.0
        elif dividend_yield >= 4:
            return 75.0
        elif dividend_yield >= 2:
            return 50.0
        else:
            return 30.0

    # ----------------------------------------------------------
    # 資料萃取輔助方法
    # ----------------------------------------------------------
    def _extract_roe(self, income_df: pd.DataFrame, balance_df: pd.DataFrame) -> list:
        """從財報萃取年度 ROE"""
        roe_values = []
        try:
            # FinMind 財務比率資料集 (TaiwanStockFinancialStatements) 包含 ROE
            if "type" in income_df.columns and "value" in income_df.columns:
                roe_df = income_df[income_df["type"] == "ROE"]
                if not roe_df.empty:
                    roe_df = roe_df.sort_values("date")
                    roe_values = roe_df["value"].astype(float).tolist()
        except Exception:
            pass
        return roe_values

    def _extract_eps(self, income_df: pd.DataFrame) -> list:
        """從財報萃取年度 EPS"""
        eps_values = []
        try:
            if "type" in income_df.columns and "value" in income_df.columns:
                eps_df = income_df[income_df["type"] == "EPS"]
                if not eps_df.empty:
                    # 取年報 (Q4 或全年)
                    eps_df = eps_df.sort_values("date")
                    eps_values = eps_df["value"].astype(float).tolist()
        except Exception:
            pass
        return eps_values

    def _extract_debt_ratio(self, balance_df: pd.DataFrame) -> float:
        """從資產負債表萃取負債比率"""
        try:
            if "type" in balance_df.columns and "value" in balance_df.columns:
                total_assets = balance_df[balance_df["type"] == "TotalAssets"]["value"]
                total_liab = balance_df[balance_df["type"] == "TotalLiabilities"]["value"]
                if not total_assets.empty and not total_liab.empty:
                    assets = float(total_assets.iloc[-1])
                    liab = float(total_liab.iloc[-1])
                    if assets > 0:
                        return (liab / assets) * 100
        except Exception:
            pass
        return 0.0

    def _extract_fcf(self, cashflow_df: pd.DataFrame) -> Optional[float]:
        """從現金流量表計算自由現金流"""
        try:
            if "type" in cashflow_df.columns and "value" in cashflow_df.columns:
                op_cf = cashflow_df[cashflow_df["type"] == "CashFlowsFromOperatingActivities"]["value"]
                capex = cashflow_df[cashflow_df["type"] == "AcquisitionOfPropertyPlantAndEquipment"]["value"]
                if not op_cf.empty:
                    op = float(op_cf.iloc[-1])
                    cap = float(capex.iloc[-1]) if not capex.empty else 0
                    return op - abs(cap)
        except Exception:
            pass
        return None

    def _calc_gross_margin(self, income_df: pd.DataFrame) -> float:
        """計算毛利率"""
        try:
            if "type" in income_df.columns and "value" in income_df.columns:
                revenue = income_df[income_df["type"] == "Revenue"]["value"]
                gross = income_df[income_df["type"] == "GrossProfit"]["value"]
                if not revenue.empty and not gross.empty:
                    r = float(revenue.iloc[-1])
                    g = float(gross.iloc[-1])
                    if r > 0:
                        return (g / r) * 100
        except Exception:
            pass
        return 0.0

    def _calc_revenue_growth(self, income_df: pd.DataFrame) -> float:
        """計算營收成長率 (YoY)"""
        try:
            if "type" in income_df.columns and "value" in income_df.columns:
                rev_df = income_df[income_df["type"] == "Revenue"].sort_values("date")
                if len(rev_df) >= 2:
                    latest = float(rev_df.iloc[-1]["value"])
                    prev = float(rev_df.iloc[-2]["value"])
                    if prev > 0:
                        return (latest - prev) / prev * 100
        except Exception:
            pass
        return 0.0

    # ----------------------------------------------------------
    # 加權總分
    # ----------------------------------------------------------
    def _calc_total_score(self, score: StockScore) -> float:
        """計算加權總分 (0-100)"""
        w = self.weights
        total = (
            score.roe_score * w.get("roe", 0.25) +
            score.eps_score * w.get("eps_growth", 0.20) +
            score.debt_score * w.get("debt_ratio", 0.15) +
            score.pe_score * w.get("pe_ratio", 0.15) +
            score.pb_score * w.get("pb_ratio", 0.10) +
            score.fcf_score * w.get("fcf", 0.10) +
            score.dividend_score * w.get("dividend", 0.05)
        )
        return round(total, 2)

    # ----------------------------------------------------------
    # 批次篩選
    # ----------------------------------------------------------
    def rank_stocks(self, scores: list[StockScore],
                    min_score: float = 60.0) -> list[StockScore]:
        """對多檔股票排名，回傳通過門檻的股票（由高至低）"""
        qualified = [s for s in scores if s.total_score >= min_score]
        return sorted(qualified, key=lambda x: x.total_score, reverse=True)
