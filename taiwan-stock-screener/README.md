# 台股巴菲特價值篩選機器人

自動依照巴菲特價值投資法，從台灣上市櫃公司中篩選被低估的優質標的。

## 篩選指標 (7大巴菲特標準)

| 指標 | 條件 | 權重 |
|------|------|------|
| ROE 股東權益報酬率 | > 15%（連續3年） | 25% |
| EPS 每股盈餘成長 | 連續3年正成長 | 20% |
| 負債比率 | < 50% | 15% |
| 本益比 P/E | < 20 | 15% |
| 股價淨值比 P/B | < 3.0 | 10% |
| 自由現金流 FCF | > 0 | 10% |
| 股利殖利率 | > 0%（近3年有配息） | 5% |

總分 100 分，建議門檻 ≥ 60 分。

## 快速開始

### 1. 安裝套件

```bash
cd taiwan-stock-screener
pip install -r requirements.txt
```

### 2. 設定 API Token（可選但建議）

**FinMind API**（財務資料來源，免費版每日500次）：
1. 至 [finmindtrade.com](https://finmindtrade.com/) 免費註冊
2. 取得 API Token
3. 填入 `src/config.py` 的 `finmind_token`，或使用 `--token` 參數

**LINE Notify**（通知用，可選）：
1. 至 [notify-bot.line.me](https://notify-bot.line.me/) 申請 Token
2. 填入 `src/config.py` 的 `line_notify_token`，或使用 `--line-token` 參數

### 3. 執行篩選

```bash
cd src

# 全市場篩選（約需 2-4 小時）
python main.py

# 指定股票代號
python main.py --stocks 2330 2317 2454 2382

# 設定門檻 & 顯示前10名
python main.py --top 10 --min-score 70

# 使用 FinMind Token
python main.py --token YOUR_FINMIND_TOKEN

# 啟動排程模式（每週一三五 18:00 自動執行）
python main.py --schedule

# 組合使用
python main.py --token YOUR_TOKEN --line-token YOUR_LINE_TOKEN --schedule
```

## 專案結構

```
taiwan-stock-screener/
├── src/
│   ├── config.py          # 篩選條件 & 系統設定
│   ├── data_fetcher.py    # 台股資料抓取（TWSE / FinMind）
│   ├── screener.py        # 巴菲特篩選核心邏輯
│   ├── notifier.py        # 通知模組（LINE / Email / Telegram）
│   └── main.py            # 主程式入口
├── data/
│   ├── cache/             # API 快取（自動建立）
│   └── screening_*.json   # 篩選結果
├── logs/                  # 執行日誌
├── tests/                 # 單元測試
└── requirements.txt
```

## 資料來源

| 來源 | 用途 | 限制 |
|------|------|------|
| [TWSE OpenAPI](https://openapi.twse.com.tw/) | 上市公司清單、股價 | 免費無限制 |
| [TPEX OpenAPI](https://www.tpex.org.tw/openapi/) | 上櫃公司清單 | 免費無限制 |
| [FinMind](https://finmindtrade.com/) | 財務報表、本益比、現金流 | 免費 500次/日，付費無限 |

## 篩選結果輸出

- `data/screening_YYYYMMDD_HHMM.csv` — 可用 Excel 開啟
- `data/screening_YYYYMMDD_HHMM.json` — 完整資料（含篩選條件）
- LINE / Email / Telegram 即時通知

## 自訂篩選條件

編輯 `src/config.py`：

```python
BUFFETT_CRITERIA = {
    "roe_min": 15.0,        # ROE 最低要求
    "pe_ratio_max": 20.0,   # 本益比上限
    "pb_ratio_max": 3.0,    # 股價淨值比上限
    "debt_ratio_max": 50.0, # 負債比率上限
    # ... 更多設定
}
```

## 注意事項

- 本工具僅供學習與研究用途，**不構成任何投資建議**
- 財務資料來自第三方 API，可能有延遲或誤差
- 建議搭配產業分析、個股研究後再做投資決策
- 台股交易有風險，請謹慎評估

## 授權

MIT License
