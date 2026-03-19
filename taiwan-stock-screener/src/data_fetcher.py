"""
Data Fetcher for Taiwan Stock Market
台股資料抓取模組 - 支援 TWSE、TPEX 及 FinMind API
"""

import logging
import time
import json
import os
from datetime import datetime, timedelta
from typing import Optional

import requests
import pandas as pd

from config import DATA_SOURCES, OUTPUT

logger = logging.getLogger(__name__)

CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", OUTPUT["results_dir"], "cache")
os.makedirs(CACHE_DIR, exist_ok=True)


class TaiwanStockDataFetcher:
    """台股資料抓取器 - 整合多個免費資料來源"""

    def __init__(self, finmind_token: str = ""):
        self.finmind_token = finmind_token or DATA_SOURCES.get("finmind_token", "")
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (compatible; TaiwanStockScreener/1.0)"
        })

    # ----------------------------------------------------------
    # 上市股票清單 (TWSE Listed Companies)
    # ----------------------------------------------------------
    def get_twse_listed_stocks(self) -> pd.DataFrame:
        """取得台灣證交所上市公司清單"""
        cache_file = os.path.join(CACHE_DIR, "twse_listed.json")
        if self._is_cache_valid(cache_file):
            return pd.read_json(cache_file)

        url = f"{DATA_SOURCES['twse_api_url']}/exchangeReport/STOCK_DAY_ALL"
        try:
            # 使用 TWSE 上市公司代碼清單
            url = "https://openapi.twse.com.tw/v1/opendata/t187ap03_L"
            resp = self.session.get(url, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            df = pd.DataFrame(data)
            df.to_json(cache_file, force_ascii=False)
            logger.info(f"取得上市公司清單: {len(df)} 筆")
            return df
        except Exception as e:
            logger.error(f"取得上市清單失敗: {e}")
            return pd.DataFrame()

    def get_tpex_listed_stocks(self) -> pd.DataFrame:
        """取得櫃買中心上櫃公司清單"""
        cache_file = os.path.join(CACHE_DIR, "tpex_listed.json")
        if self._is_cache_valid(cache_file):
            return pd.read_json(cache_file)

        url = "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_quotes"
        try:
            resp = self.session.get(url, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            df = pd.DataFrame(data)
            df.to_json(cache_file, force_ascii=False)
            logger.info(f"取得上櫃公司清單: {len(df)} 筆")
            return df
        except Exception as e:
            logger.error(f"取得上櫃清單失敗: {e}")
            return pd.DataFrame()

    # ----------------------------------------------------------
    # 財務資料 via FinMind API
    # ----------------------------------------------------------
    def _finmind_request(self, dataset: str, stock_id: str,
                         start_date: str, end_date: str = "") -> Optional[pd.DataFrame]:
        """呼叫 FinMind API 取得財務資料"""
        if not end_date:
            end_date = datetime.today().strftime("%Y-%m-%d")

        params = {
            "dataset": dataset,
            "data_id": stock_id,
            "start_date": start_date,
            "end_date": end_date,
        }
        if self.finmind_token:
            params["token"] = self.finmind_token

        try:
            resp = self.session.get(
                DATA_SOURCES["finmind_api_url"],
                params=params,
                timeout=30
            )
            resp.raise_for_status()
            result = resp.json()
            if result.get("status") == 200:
                return pd.DataFrame(result["data"])
            else:
                logger.warning(f"FinMind {dataset} {stock_id}: {result.get('msg')}")
                return None
        except Exception as e:
            logger.error(f"FinMind API 錯誤 {dataset} {stock_id}: {e}")
            return None

    def get_financial_statements(self, stock_id: str, years: int = 5) -> dict:
        """
        取得財務報表資料
        回傳: { 'income': df, 'balance': df, 'cashflow': df }
        """
        start_date = (datetime.today() - timedelta(days=365 * years)).strftime("%Y-%m-%d")
        cache_key = f"financial_{stock_id}_{years}y"
        cache_file = os.path.join(CACHE_DIR, f"{cache_key}.json")

        if self._is_cache_valid(cache_file, hours=24):
            with open(cache_file) as f:
                cached = json.load(f)
            return {k: pd.DataFrame(v) for k, v in cached.items()}

        time.sleep(0.3)  # 避免 API rate limit

        result = {}

        # 綜合損益表
        income_df = self._finmind_request(
            "TaiwanStockFinancialStatements", stock_id, start_date
        )
        result["income"] = income_df if income_df is not None else pd.DataFrame()

        # 資產負債表
        balance_df = self._finmind_request(
            "TaiwanStockBalanceSheet", stock_id, start_date
        )
        result["balance"] = balance_df if balance_df is not None else pd.DataFrame()

        # 現金流量表
        cashflow_df = self._finmind_request(
            "TaiwanStockCashFlowsStatement", stock_id, start_date
        )
        result["cashflow"] = cashflow_df if cashflow_df is not None else pd.DataFrame()

        # 快取
        cache_data = {k: v.to_dict("records") for k, v in result.items()}
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, ensure_ascii=False, default=str)

        return result

    def get_stock_price(self, stock_id: str) -> Optional[pd.DataFrame]:
        """取得股價資料 (近90天)"""
        start_date = (datetime.today() - timedelta(days=90)).strftime("%Y-%m-%d")
        return self._finmind_request("TaiwanStockPrice", stock_id, start_date)

    def get_dividend_history(self, stock_id: str, years: int = 5) -> Optional[pd.DataFrame]:
        """取得股利歷史"""
        start_date = (datetime.today() - timedelta(days=365 * years)).strftime("%Y-%m-%d")
        return self._finmind_request("TaiwanStockDividend", stock_id, start_date)

    def get_monthly_revenue(self, stock_id: str, years: int = 2) -> Optional[pd.DataFrame]:
        """取得月營收資料"""
        start_date = (datetime.today() - timedelta(days=365 * years)).strftime("%Y-%m-%d")
        return self._finmind_request("TaiwanStockMonthRevenue", stock_id, start_date)

    def get_realtime_price(self, stock_id: str) -> dict:
        """取得即時股價 (透過 TWSE API)"""
        url = f"https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch=tse_{stock_id}.tw"
        try:
            resp = self.session.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            if data.get("msgArray"):
                item = data["msgArray"][0]
                return {
                    "stock_id": stock_id,
                    "name": item.get("n", ""),
                    "price": float(item.get("z", 0) or 0),
                    "open": float(item.get("o", 0) or 0),
                    "high": float(item.get("h", 0) or 0),
                    "low": float(item.get("l", 0) or 0),
                    "volume": int(item.get("v", 0) or 0),
                    "timestamp": item.get("t", ""),
                }
        except Exception as e:
            logger.error(f"即時股價取得失敗 {stock_id}: {e}")
        return {}

    def get_pe_pb_ratios(self, stock_id: str) -> dict:
        """取得本益比及股價淨值比"""
        start_date = (datetime.today() - timedelta(days=30)).strftime("%Y-%m-%d")
        df = self._finmind_request("TaiwanStockPER", stock_id, start_date)
        if df is not None and not df.empty:
            latest = df.iloc[-1]
            return {
                "pe_ratio": float(latest.get("PER", 0) or 0),
                "pb_ratio": float(latest.get("PBR", 0) or 0),
                "dividend_yield": float(latest.get("DividendYield", 0) or 0),
            }
        return {"pe_ratio": 0, "pb_ratio": 0, "dividend_yield": 0}

    def get_all_stock_ids(self) -> list[str]:
        """取得所有上市櫃股票代碼"""
        all_ids = []

        # 上市 (TWSE)
        twse_df = self.get_twse_listed_stocks()
        if not twse_df.empty:
            id_col = next((c for c in ["公司代號", "stock_id", "Code"] if c in twse_df.columns), None)
            if id_col:
                ids = twse_df[id_col].astype(str).tolist()
                # 只取4-5碼的一般股票，排除ETF等
                all_ids += [i for i in ids if i.isdigit() and 4 <= len(i) <= 5]

        # 上櫃 (TPEX) - 簡化處理
        tpex_df = self.get_tpex_listed_stocks()
        if not tpex_df.empty:
            id_col = next((c for c in ["SecuritiesCompanyCode", "stock_id", "Code"] if c in tpex_df.columns), None)
            if id_col:
                ids = tpex_df[id_col].astype(str).tolist()
                all_ids += [i for i in ids if i.isdigit() and 4 <= len(i) <= 5]

        return list(set(all_ids))

    # ----------------------------------------------------------
    # 快取工具
    # ----------------------------------------------------------
    def _is_cache_valid(self, cache_file: str, hours: int = 24) -> bool:
        """檢查快取是否有效"""
        if not os.path.exists(cache_file):
            return False
        mtime = os.path.getmtime(cache_file)
        age = time.time() - mtime
        return age < hours * 3600
