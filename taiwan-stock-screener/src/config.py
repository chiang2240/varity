"""
Configuration for Taiwan Stock Screener Bot
巴菲特價值投資篩選條件設定
"""

# ============================================================
# 巴菲特篩選條件 (Buffett Screening Criteria)
# ============================================================
BUFFETT_CRITERIA = {
    # 股東權益報酬率 (Return on Equity) > 15% (連續3年)
    "roe_min": 15.0,
    "roe_years": 3,

    # 每股盈餘成長 (EPS Growth) > 0% (連續3年正成長)
    "eps_growth_years": 3,

    # 負債比率 (Debt Ratio) < 50%
    "debt_ratio_max": 50.0,

    # 本益比 (P/E Ratio) < 20 (合理估值)
    "pe_ratio_max": 20.0,

    # 股價淨值比 (P/B Ratio) < 3.0
    "pb_ratio_max": 3.0,

    # 自由現金流 (Free Cash Flow) 必須為正
    "fcf_positive": True,

    # 營收成長率 (Revenue Growth) > 0% (近一年)
    "revenue_growth_min": 0.0,

    # 毛利率 (Gross Margin) > 20%
    "gross_margin_min": 20.0,

    # 市值下限 (Market Cap) 單位: 億台幣
    "market_cap_min_billion": 10,

    # 股利發放 (Dividend) - 是否要求近3年有配股配息
    "require_dividend": True,
    "dividend_years": 3,
}

# ============================================================
# 評分權重設定 (Scoring Weights)
# ============================================================
SCORING_WEIGHTS = {
    "roe":              0.25,   # ROE 權重 25%
    "eps_growth":       0.20,   # EPS成長 權重 20%
    "debt_ratio":       0.15,   # 負債比率 權重 15%
    "pe_ratio":         0.15,   # 本益比 權重 15%
    "pb_ratio":         0.10,   # 股價淨值比 權重 10%
    "fcf":              0.10,   # 自由現金流 權重 10%
    "dividend":         0.05,   # 股利 權重 5%
}

# ============================================================
# 資料來源設定 (Data Sources)
# ============================================================
DATA_SOURCES = {
    # FinMind API (免費版每日500次)
    "finmind_api_url": "https://api.finmindtrade.com/api/v4/data",
    "finmind_token": "",  # 填入 FinMind API Token (可免費申請)

    # TWSE 公開API
    "twse_api_url": "https://openapi.twse.com.tw/v1",

    # 公開資訊觀測站 MOPS
    "mops_url": "https://mops.twse.com.tw",
}

# ============================================================
# 通知設定 (Notification Settings)
# ============================================================
NOTIFICATION = {
    # LINE Notify (免費)
    "line_notify_token": "",  # 填入 LINE Notify Token

    # Email 設定
    "email_enabled": False,
    "smtp_host": "smtp.gmail.com",
    "smtp_port": 587,
    "email_sender": "",
    "email_password": "",
    "email_recipients": [],

    # Telegram Bot
    "telegram_enabled": False,
    "telegram_bot_token": "",
    "telegram_chat_id": "",
}

# ============================================================
# 排程設定 (Schedule Settings)
# ============================================================
SCHEDULE = {
    # 每週執行幾次 (建議週一、三、五盤後)
    "run_days": ["Monday", "Wednesday", "Friday"],
    "run_time": "18:00",  # 盤後 18:00 執行

    # 資料快取時間 (小時)
    "cache_hours": 24,
}

# ============================================================
# 輸出設定 (Output Settings)
# ============================================================
OUTPUT = {
    "results_dir": "data",
    "log_dir": "logs",
    "max_results": 20,       # 最多顯示前20名
    "min_score": 60.0,       # 最低分數門檻 (0-100)
    "export_csv": True,
    "export_json": True,
}
