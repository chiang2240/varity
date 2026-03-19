/**
 * Main.gs — 主程式入口 & 觸發器設定
 *
 * 【使用說明】
 *
 * 1. 第一次使用 → 在編輯器執行 initializeSheets()
 * 2. 立即執行一次 → 執行 runScreener()
 * 3. 設定自動排程 → 執行 setupTriggers()
 * 4. 全市場批次掃描 → 執行 startBatchScreening()
 *
 * 【GAS 執行限制】
 *   免費帳號: 每次執行 6 分鐘，每日累計 90 分鐘
 *   每次 API 呼叫約 0.7 秒，BATCH_SIZE=30 約需 6×3=~2 分鐘
 */

// ============================================================
// 主篩選流程（自選清單模式，單次完成）
// ============================================================

/**
 * 對自選清單執行巴菲特篩選
 * 適合清單 < 60 檔使用（約 3-5 分鐘完成）
 */
function runScreener() {
  var cfg     = getConfig();
  var runTime = Utilities.formatDate(new Date(), 'Asia/Taipei', 'yyyy-MM-dd HH:mm:ss');

  writeLog('INFO', '=== 篩選開始 ' + runTime + ' ===');

  var stockIds = getWatchlist();
  writeLog('INFO', '待篩選: ' + stockIds.length + ' 檔');

  var scores = [];

  for (var i = 0; i < stockIds.length; i++) {
    var sid = stockIds[i];
    try {
      var score = processOneStock(sid, cfg);
      if (score) {
        scores.push(score);
        if (score.totalScore >= cfg.criteria.MIN_SCORE) {
          writeLog('INFO', '[通過] ' + sid + ' ' + score.name + ' 總分:' + score.totalScore);
        }
      }
    } catch (e) {
      writeLog('WARN', '[跳過] ' + sid + ': ' + e.message);
    }
  }

  var ranked = rankStocks(scores, cfg.criteria.MIN_SCORE);
  writeLog('INFO', '篩選完成，通過: ' + ranked.length + '/' + scores.length);

  writeResults(ranked, runTime);
  sendReport(ranked, runTime);

  writeLog('INFO', '=== 篩選結束 ===');
}

// ============================================================
// 批次模式（適合全市場掃描，跨多次觸發）
// ============================================================

/**
 * 啟動全市場批次掃描
 * 執行後每 10 分鐘自動觸發一次 runNextBatch()
 */
function startBatchScreening() {
  clearBatchProgress();
  writeLog('INFO', '=== 批次掃描啟動 ===');

  // 設定觸發器，每 10 分鐘執行一批
  ScriptApp.newTrigger('runNextBatch')
    .timeBased()
    .everyMinutes(10)
    .create();

  // 立即執行第一批
  runNextBatch();
}

/**
 * 執行下一批（由觸發器自動呼叫）
 * 全部完成後自動整合結果並刪除觸發器
 */
function runNextBatch() {
  var cfg      = getConfig();
  var progress = loadBatchProgress();
  var allIds   = getWatchlist(); // 可換成全市場清單
  var runTime  = Utilities.formatDate(new Date(), 'Asia/Taipei', 'yyyy-MM-dd HH:mm:ss');

  var start = progress.index;
  var end   = Math.min(start + cfg.batchSize, allIds.length);
  var batch = allIds.slice(start, end);

  writeLog('INFO', '批次 ' + (start + 1) + '–' + end + ' / ' + allIds.length);

  var newScores = progress.results;

  for (var i = 0; i < batch.length; i++) {
    var sid = batch[i];
    try {
      var score = processOneStock(sid, cfg);
      if (score) newScores.push(score);
    } catch (e) {
      writeLog('WARN', '[跳過] ' + sid + ': ' + e.message);
    }
  }

  if (end >= allIds.length) {
    // 全部完成
    writeLog('INFO', '全部批次完成，整合結果...');
    var ranked = rankStocks(newScores, cfg.criteria.MIN_SCORE);
    writeResults(ranked, runTime);
    sendReport(ranked, runTime);
    clearBatchProgress();
    removeBatchTriggers();
    writeLog('INFO', '=== 批次掃描結束，通過 ' + ranked.length + ' 檔 ===');
  } else {
    // 儲存進度，等待下次觸發
    saveBatchProgress(end, newScores);
    writeLog('INFO', '已處理 ' + end + '/' + allIds.length + '，等待下次觸發...');
  }
}

// ============================================================
// 單一股票處理
// ============================================================

/**
 * 取得一檔股票的所有資料並執行篩選
 * @param {string} stockId
 * @param {Object} cfg
 * @return {Object|null} StockScore
 */
function processOneStock(stockId, cfg) {
  var financial = getFinancialData(stockId, cfg.finmindToken);
  var pePb      = getPePbRatios(stockId, cfg.finmindToken);
  var priceInfo = getRealtimePrice(stockId);

  var priceData = {
    pe:            pePb.pe,
    pb:            pePb.pb,
    dividendYield: pePb.dividendYield,
    price:         priceInfo.price,
  };

  return screenStock(stockId, priceInfo.name, financial, priceData, cfg);
}

// ============================================================
// 觸發器管理
// ============================================================

/**
 * 設定自動排程觸發器（每週一、三、五 18:00 執行）
 * 在編輯器中執行此函式一次即可
 */
function setupTriggers() {
  // 先刪除舊觸發器
  removeAllTriggers();

  // 週一 18:00
  ScriptApp.newTrigger('runScreener').timeBased()
    .onWeekDay(ScriptApp.WeekDay.MONDAY).atHour(18).create();

  // 週三 18:00
  ScriptApp.newTrigger('runScreener').timeBased()
    .onWeekDay(ScriptApp.WeekDay.WEDNESDAY).atHour(18).create();

  // 週五 18:00
  ScriptApp.newTrigger('runScreener').timeBased()
    .onWeekDay(ScriptApp.WeekDay.FRIDAY).atHour(18).create();

  writeLog('INFO', '排程設定完成：每週一三五 18:00 自動執行');
  SpreadsheetApp.getUi().alert('✅ 排程設定完成！\n每週一、三、五 18:00 盤後自動執行篩選。');
}

/** 移除所有觸發器 */
function removeAllTriggers() {
  ScriptApp.getProjectTriggers().forEach(function(t) {
    ScriptApp.deleteTrigger(t);
  });
  writeLog('INFO', '已清除所有觸發器');
}

/** 只移除批次觸發器 */
function removeBatchTriggers() {
  ScriptApp.getProjectTriggers().forEach(function(t) {
    if (t.getHandlerFunction() === 'runNextBatch') {
      ScriptApp.deleteTrigger(t);
    }
  });
}

// ============================================================
// 自訂選單（開啟試算表時出現）
// ============================================================

function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('📊 股票篩選機器人')
    .addItem('🚀 立即執行篩選', 'runScreener')
    .addSeparator()
    .addItem('⏰ 設定自動排程（週一三五 18:00）', 'setupTriggers')
    .addItem('🌍 啟動全市場批次掃描', 'startBatchScreening')
    .addSeparator()
    .addItem('🔧 初始化工作表', 'initializeSheets')
    .addItem('🗑️ 清除所有觸發器', 'removeAllTriggers')
    .addToUi();
}
