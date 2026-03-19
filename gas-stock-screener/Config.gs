/**
 * Config.gs — 台股巴菲特篩選機器人設定
 *
 * ⚠️  請在這裡填入你的 Token 與設定
 *     或使用 Script Properties（更安全）:
 *     「專案設定」→「指令碼屬性」→ 新增屬性
 */

// ============================================================
// 使用者設定（直接填入，或改用 Script Properties）
// ============================================================
var CONFIG = {

  // ── FinMind API（財務資料）─────────────────────────────
  // 免費申請: https://finmindtrade.com/
  // 免費版限制: 500 次/日，每次請求 0.6 秒間隔
  FINMIND_TOKEN: '',          // 填入後可提升上限至 600 次/日

  // ── LINE Notify（推播通知，可選）──────────────────────
  // 免費申請: https://notify-bot.line.me/
  LINE_NOTIFY_TOKEN: '',

  // ── Email 通知（使用 Gmail，可選）────────────────────
  EMAIL_ENABLED: false,
  EMAIL_RECIPIENT: '',        // 收信 Email，空白表示寄給自己

  // ── 篩選條件（巴菲特7大指標）─────────────────────────
  CRITERIA: {
    ROE_MIN:           15.0,  // 股東權益報酬率下限 (%)
    ROE_YEARS:         3,     // 連續幾年達標
    EPS_GROWTH_YEARS:  3,     // EPS 連續成長年數
    DEBT_RATIO_MAX:    50.0,  // 負債比率上限 (%)
    PE_MAX:            20.0,  // 本益比上限
    PB_MAX:            3.0,   // 股價淨值比上限
    FCF_POSITIVE:      true,  // 自由現金流必須為正
    DIVIDEND_REQUIRED: true,  // 必須有配息
    MIN_SCORE:         60.0,  // 總分門檻 (0–100)
  },

  // ── 評分權重（加總必須為 1）───────────────────────────
  WEIGHTS: {
    roe:      0.25,
    eps:      0.20,
    debt:     0.15,
    pe:       0.15,
    pb:       0.10,
    fcf:      0.10,
    dividend: 0.05,
  },

  // ── 批次處理設定（應對 GAS 6分鐘執行限制）────────────
  BATCH_SIZE:     30,   // 每次觸發最多處理幾檔股票
  API_DELAY_MS:   700,  // 每次 API 呼叫間隔 (ms)，避免超量

  // ── 輸出設定 ──────────────────────────────────────────
  MAX_RESULTS:    20,   // 結果表最多保留幾筆
  SHEET_RESULTS:  '篩選結果',
  SHEET_WATCHLIST:'自選清單',
  SHEET_LOG:      '執行日誌',
};

// ============================================================
// 讀取設定（優先使用 Script Properties，其次使用上方 CONFIG）
// ============================================================
function getConfig() {
  var props = PropertiesService.getScriptProperties();
  return {
    finmindToken:    props.getProperty('FINMIND_TOKEN')    || CONFIG.FINMIND_TOKEN,
    lineToken:       props.getProperty('LINE_NOTIFY_TOKEN')|| CONFIG.LINE_NOTIFY_TOKEN,
    emailEnabled:    CONFIG.EMAIL_ENABLED,
    emailRecipient:  CONFIG.EMAIL_RECIPIENT || Session.getActiveUser().getEmail(),
    criteria:        CONFIG.CRITERIA,
    weights:         CONFIG.WEIGHTS,
    batchSize:       CONFIG.BATCH_SIZE,
    apiDelayMs:      CONFIG.API_DELAY_MS,
    maxResults:      CONFIG.MAX_RESULTS,
    sheets:          {
      results:   CONFIG.SHEET_RESULTS,
      watchlist: CONFIG.SHEET_WATCHLIST,
      log:       CONFIG.SHEET_LOG,
    },
  };
}

// ============================================================
// 台灣50大市值股票（預設監控清單，可在「自選清單」工作表自訂）
// ============================================================
var DEFAULT_WATCHLIST = [
  // 半導體
  '2330','2303','2454','2379','2344','3711','2408','3034','2376',
  // 電子代工
  '2317','2354','2382','2357','2353',
  // 金融
  '2891','2882','2881','2886','2884','2892','2883','5880',
  // 傳產/消費
  '1301','1303','1326','2002','1101','2207','2105',
  // 電信/服務
  '2412','3045','4904',
  // 生技
  '4938','6505',
];
