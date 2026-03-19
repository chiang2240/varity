"""
Taiwan Stock Screener Bot - Main Entry Point
台股巴菲特價值篩選機器人 - 主程式

使用方式:
  python main.py                    # 立即執行一次篩選
  python main.py --schedule         # 啟動排程模式 (週一三五 18:00)
  python main.py --stocks 2330 2317 # 指定股票代號篩選
  python main.py --top 10           # 只顯示前10名
  python main.py --min-score 70     # 設定最低門檻分數
"""

import argparse
import csv
import json
import logging
import os
import sys
import time
from datetime import datetime

import schedule

from config import OUTPUT, SCHEDULE, BUFFETT_CRITERIA
from data_fetcher import TaiwanStockDataFetcher
from notifier import Notifier
from screener import BuffettScreener, StockScore

# ============================================================
# Logging 設定
# ============================================================
LOG_DIR = os.path.join(os.path.dirname(__file__), "..", OUTPUT["log_dir"])
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[
        logging.FileHandler(
            os.path.join(LOG_DIR, f"screener_{datetime.now().strftime('%Y%m%d')}.log"),
            encoding="utf-8"
        ),
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger("main")


# ============================================================
# 主篩選流程
# ============================================================
class StockScreenerBot:
    """台股巴菲特篩選機器人"""

    def __init__(self, finmind_token: str = ""):
        self.fetcher = TaiwanStockDataFetcher(finmind_token=finmind_token)
        self.screener = BuffettScreener()
        self.notifier = Notifier()

    def run(self, stock_ids: list[str] = None,
            top_n: int = None, min_score: float = None) -> list[StockScore]:
        """
        執行篩選
        :param stock_ids: 指定股票代碼清單，None 表示全市場掃描
        :param top_n: 只回傳前 N 名
        :param min_score: 最低分數門檻
        """
        top_n = top_n or OUTPUT["max_results"]
        min_score = min_score if min_score is not None else OUTPUT["min_score"]
        run_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        logger.info("=" * 60)
        logger.info(f"台股巴菲特篩選開始 - {run_time}")
        logger.info("=" * 60)

        # 取得股票清單
        if not stock_ids:
            logger.info("取得上市櫃股票清單...")
            stock_ids = self.fetcher.get_all_stock_ids()
            logger.info(f"共 {len(stock_ids)} 檔股票待篩選")

        scores = []
        total = len(stock_ids)

        for idx, sid in enumerate(stock_ids, 1):
            try:
                logger.info(f"[{idx}/{total}] 處理 {sid}...")
                score = self._process_stock(sid)
                if score:
                    scores.append(score)
                    if score.is_qualified(min_score):
                        logger.info(
                            f"  ✅ {sid} {score.name} 通過 - 總分: {score.total_score:.1f}"
                        )
            except Exception as e:
                logger.warning(f"  ❌ {sid} 處理失敗: {e}")

            # 每50檔休息一下，避免 API rate limit
            if idx % 50 == 0:
                logger.info(f"進度: {idx}/{total}, 休息3秒...")
                time.sleep(3)

        # 排名
        ranked = self.screener.rank_stocks(scores, min_score=min_score)
        if top_n:
            ranked = ranked[:top_n]

        logger.info(f"\n篩選完成！共 {len(ranked)} 檔通過 (總分 ≥ {min_score})")

        # 輸出結果
        self._save_results(ranked, run_time)
        self._print_summary(ranked)
        self.notifier.send_screening_report(ranked, run_time)

        return ranked

    def _process_stock(self, stock_id: str) -> StockScore | None:
        """處理單一股票"""
        try:
            # 取得財務資料
            financial_data = self.fetcher.get_financial_statements(stock_id, years=5)

            # 取得股價及估值資料
            pe_pb = self.fetcher.get_pe_pb_ratios(stock_id)
            price_info = self.fetcher.get_realtime_price(stock_id)

            price_data = {
                "pe_ratio": pe_pb.get("pe_ratio", 0),
                "pb_ratio": pe_pb.get("pb_ratio", 0),
                "dividend_yield": pe_pb.get("dividend_yield", 0),
                "price": price_info.get("price", 0),
            }
            name = price_info.get("name", stock_id)

            # 執行篩選
            score = self.screener.screen(
                stock_id=stock_id,
                name=name,
                financial_data=financial_data,
                price_data=price_data,
            )
            return score

        except Exception as e:
            logger.debug(f"_process_stock {stock_id} 錯誤: {e}")
            return None

    def _save_results(self, scores: list[StockScore], run_time: str):
        """儲存篩選結果"""
        results_dir = os.path.join(os.path.dirname(__file__), "..", OUTPUT["results_dir"])
        os.makedirs(results_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")

        if OUTPUT["export_json"]:
            json_path = os.path.join(results_dir, f"screening_{timestamp}.json")
            data = {
                "run_time": run_time,
                "criteria": BUFFETT_CRITERIA,
                "results": [self._score_to_dict(s) for s in scores],
            }
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"結果儲存: {json_path}")

        if OUTPUT["export_csv"]:
            csv_path = os.path.join(results_dir, f"screening_{timestamp}.csv")
            if scores:
                fieldnames = list(self._score_to_dict(scores[0]).keys())
                with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    for s in scores:
                        writer.writerow(self._score_to_dict(s))
            logger.info(f"CSV儲存: {csv_path}")

    def _print_summary(self, scores: list[StockScore]):
        """印出篩選摘要"""
        if not scores:
            print("\n本次篩選無符合條件標的。")
            return

        print(f"\n{'='*60}")
        print(f"台股巴菲特篩選結果 - 共 {len(scores)} 檔通過")
        print(f"{'='*60}")
        print(f"{'排名':>4} {'代號':>6} {'名稱':^8} {'總分':>6} {'ROE':>6} "
              f"{'P/E':>6} {'P/B':>5} {'殖利率':>6} {'現價':>8}")
        print(f"{'─'*60}")
        for rank, s in enumerate(scores, 1):
            print(
                f"{rank:>4} {s.stock_id:>6} {s.name:^8} {s.total_score:>6.1f} "
                f"{s.roe_avg:>6.1f}% {s.pe_ratio:>6.1f} {s.pb_ratio:>5.2f} "
                f"{s.dividend_yield:>5.1f}% {s.current_price:>8.2f}"
            )
        print(f"{'─'*60}")
        print("⚠️  本報告僅供參考，不構成投資建議。")

    @staticmethod
    def _score_to_dict(s: StockScore) -> dict:
        return {
            "stock_id": s.stock_id,
            "name": s.name,
            "total_score": s.total_score,
            "passed_criteria": s.passed_criteria,
            "current_price": s.current_price,
            "roe_avg": s.roe_avg,
            "eps_growth_rate": s.eps_growth_rate,
            "debt_ratio": s.debt_ratio,
            "pe_ratio": s.pe_ratio,
            "pb_ratio": s.pb_ratio,
            "fcf": s.fcf,
            "dividend_yield": s.dividend_yield,
            "gross_margin": s.gross_margin,
            "revenue_growth": s.revenue_growth,
            "reason": "; ".join(s.reason),
        }


# ============================================================
# 排程模式
# ============================================================
def run_scheduled(bot: StockScreenerBot, top_n: int, min_score: float):
    """排程執行入口"""
    logger.info("啟動排程模式...")

    def job():
        logger.info("排程任務觸發")
        bot.run(top_n=top_n, min_score=min_score)

    run_time = SCHEDULE["run_time"]
    for day in SCHEDULE["run_days"]:
        getattr(schedule.every(), day.lower()).at(run_time).do(job)
        logger.info(f"設定排程: 每週{day} {run_time}")

    print(f"\n排程已啟動，下次執行: {schedule.next_run()}")
    print("按 Ctrl+C 停止...")

    while True:
        schedule.run_pending()
        time.sleep(60)


# ============================================================
# CLI 入口
# ============================================================
def main():
    parser = argparse.ArgumentParser(
        description="台股巴菲特價值篩選機器人",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例:
  python main.py                           # 全市場篩選
  python main.py --stocks 2330 2317 2454   # 指定股票
  python main.py --top 10 --min-score 70   # 前10名，最低70分
  python main.py --schedule                # 排程模式
  python main.py --token YOUR_TOKEN        # 指定 FinMind Token
        """
    )
    parser.add_argument("--stocks", nargs="+", metavar="CODE",
                        help="指定股票代號 (可多個)")
    parser.add_argument("--top", type=int, default=OUTPUT["max_results"],
                        help=f"顯示前N名 (預設: {OUTPUT['max_results']})")
    parser.add_argument("--min-score", type=float, default=OUTPUT["min_score"],
                        help=f"最低門檻分數 0-100 (預設: {OUTPUT['min_score']})")
    parser.add_argument("--schedule", action="store_true",
                        help="啟動排程模式")
    parser.add_argument("--token", default="",
                        help="FinMind API Token")
    parser.add_argument("--line-token", default="",
                        help="LINE Notify Token")

    args = parser.parse_args()

    # 注入 token
    from config import NOTIFICATION
    if args.line_token:
        NOTIFICATION["line_notify_token"] = args.line_token

    bot = StockScreenerBot(finmind_token=args.token)

    if args.schedule:
        run_scheduled(bot, top_n=args.top, min_score=args.min_score)
    else:
        bot.run(
            stock_ids=args.stocks,
            top_n=args.top,
            min_score=args.min_score,
        )


if __name__ == "__main__":
    main()
