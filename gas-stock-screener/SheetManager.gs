/**
 * SheetManager.gs — Google Sheets 儀表板管理
 * 初始化工作表、寫入篩選結果、更新日誌
 */

// ============================================================
// 工作表初始化
// ============================================================

/**
 * 初始化所有必要工作表（第一次使用時執行）
 * 可在 GAS 編輯器中直接執行此函式
 */
function initializeSheets() {
  var cfg = getConfig();
  var ss = SpreadsheetApp.getActiveSpreadsheet();

  setupResultsSheet(ss, cfg.sheets.results);
  setupWatchlistSheet(ss, cfg.sheets.watchlist);
  setupLogSheet(ss, cfg.sheets.log);

  SpreadsheetApp.getUi().alert('✅ 工作表初始化完成！\n\n請至「自選清單」填入想監控的股票代號。');
}

function setupResultsSheet(ss, sheetName) {
  var sheet = ss.getSheetByName(sheetName) || ss.insertSheet(sheetName);
  sheet.clearContents();

  var headers = [
    '排名', '股票代號', '公司名稱', '總分', '通過指標',
    '現價', 'ROE(%)', 'EPS成長(%)', '負債比(%)',
    '本益比', '股價淨值比', '自由現金流(千)', '殖利率(%)',
    '毛利率(%)', '營收成長(%)', '未通過原因', '更新時間'
  ];

  sheet.appendRow(headers);

  // 格式設定
  var headerRange = sheet.getRange(1, 1, 1, headers.length);
  headerRange
    .setBackground('#1a73e8')
    .setFontColor('#ffffff')
    .setFontWeight('bold')
    .setHorizontalAlignment('center');

  sheet.setFrozenRows(1);
  sheet.setColumnWidth(1, 50);
  sheet.setColumnWidth(2, 80);
  sheet.setColumnWidth(3, 120);
  sheet.setColumnWidth(4, 60);
  sheet.setColumnWidth(5, 80);
  sheet.setColumnWidths(6, 11, 90);
  sheet.setColumnWidth(16, 250);
  sheet.setColumnWidth(17, 140);

  Logger.log('初始化: ' + sheetName);
}

function setupWatchlistSheet(ss, sheetName) {
  var sheet = ss.getSheetByName(sheetName);
  if (sheet) return; // 已存在則不覆蓋

  sheet = ss.insertSheet(sheetName);
  sheet.appendRow(['股票代號', '公司名稱（選填）', '備註']);

  var headerRange = sheet.getRange(1, 1, 1, 3);
  headerRange
    .setBackground('#34a853')
    .setFontColor('#ffffff')
    .setFontWeight('bold');

  sheet.setFrozenRows(1);
  sheet.setColumnWidth(1, 100);
  sheet.setColumnWidth(2, 150);
  sheet.setColumnWidth(3, 200);

  // 填入預設自選清單
  var defaultData = DEFAULT_WATCHLIST.map(function(id) { return [id, '', '']; });
  if (defaultData.length > 0) {
    sheet.getRange(2, 1, defaultData.length, 3).setValues(defaultData);
  }

  Logger.log('初始化: ' + sheetName);
}

function setupLogSheet(ss, sheetName) {
  var sheet = ss.getSheetByName(sheetName) || ss.insertSheet(sheetName);
  if (sheet.getLastRow() === 0) {
    sheet.appendRow(['時間', '類型', '訊息']);
    sheet.getRange(1, 1, 1, 3)
      .setBackground('#fbbc04')
      .setFontWeight('bold');
    sheet.setFrozenRows(1);
    sheet.setColumnWidth(1, 160);
    sheet.setColumnWidth(2, 80);
    sheet.setColumnWidth(3, 500);
  }
}

// ============================================================
// 寫入篩選結果
// ============================================================

/**
 * 將篩選結果寫入「篩選結果」工作表
 * @param {Object[]} ranked - 排序後的 StockScore 陣列
 * @param {string} runTime
 */
function writeResults(ranked, runTime) {
  var cfg = getConfig();
  var ss  = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName(cfg.sheets.results);

  if (!sheet) {
    setupResultsSheet(ss, cfg.sheets.results);
    sheet = ss.getSheetByName(cfg.sheets.results);
  }

  // 清除舊資料（保留表頭）
  if (sheet.getLastRow() > 1) {
    sheet.getRange(2, 1, sheet.getLastRow() - 1, sheet.getLastColumn()).clearContent();
  }

  if (ranked.length === 0) {
    writeLog('INFO', '本次篩選無符合條件標的');
    return;
  }

  var rows = ranked.slice(0, cfg.maxResults).map(function(s, idx) {
    return [
      idx + 1,
      s.stockId,
      s.name,
      s.totalScore,
      s.passedCount + '/' + s.totalCriteria,
      s.price,
      roundTo(s.roeAvg, 1),
      roundTo(s.epsGrowth, 1),
      roundTo(s.debtRatio, 1),
      roundTo(s.pe, 1),
      roundTo(s.pb, 2),
      Math.round(s.fcf / 1000),
      roundTo(s.dividendYield, 2),
      roundTo(s.grossMargin, 1),
      roundTo(s.revenueGrowth, 1),
      s.reasons.join('; '),
      runTime,
    ];
  });

  sheet.getRange(2, 1, rows.length, rows[0].length).setValues(rows);

  // 條件格式：總分著色
  applyScoreColors(sheet, ranked.length);

  writeLog('INFO', '結果已更新: ' + ranked.length + ' 檔通過篩選');
}

/**
 * 依總分對結果列套用背景色
 */
function applyScoreColors(sheet, rowCount) {
  if (rowCount === 0) return;
  var dataRange = sheet.getRange(2, 4, rowCount, 1); // 總分欄
  var values = dataRange.getValues();

  values.forEach(function(row, i) {
    var score = row[0];
    var color;
    if (score >= 80)      color = '#c8e6c9'; // 深綠
    else if (score >= 70) color = '#dcedc8'; // 中綠
    else if (score >= 60) color = '#fff9c4'; // 黃
    else                  color = '#ffffff';
    sheet.getRange(i + 2, 1, 1, 16).setBackground(color);
  });
}

// ============================================================
// 執行日誌
// ============================================================

function writeLog(type, message) {
  var cfg = getConfig();
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName(cfg.sheets.log);
  if (!sheet) return;

  var time = Utilities.formatDate(new Date(), 'Asia/Taipei', 'yyyy-MM-dd HH:mm:ss');
  sheet.appendRow([time, type, message]);

  // 保留最近 200 筆日誌
  var lastRow = sheet.getLastRow();
  if (lastRow > 201) {
    sheet.deleteRows(2, lastRow - 201);
  }
}

// ============================================================
// 進度狀態（批次處理用）
// ============================================================

/**
 * 儲存批次處理進度至 PropertiesService
 * @param {number} currentIndex - 目前處理到第幾個
 * @param {Object[]} partialResults - 已處理結果
 */
function saveBatchProgress(currentIndex, partialResults) {
  var props = PropertiesService.getScriptProperties();
  props.setProperty('BATCH_INDEX', String(currentIndex));
  props.setProperty('BATCH_RESULTS', JSON.stringify(partialResults));
  props.setProperty('BATCH_UPDATED', new Date().toISOString());
}

/**
 * 讀取批次處理進度
 * @return {{ index: number, results: Object[] }}
 */
function loadBatchProgress() {
  var props = PropertiesService.getScriptProperties();
  return {
    index:   parseInt(props.getProperty('BATCH_INDEX') || '0'),
    results: JSON.parse(props.getProperty('BATCH_RESULTS') || '[]'),
  };
}

/** 清除批次進度 */
function clearBatchProgress() {
  var props = PropertiesService.getScriptProperties();
  props.deleteProperty('BATCH_INDEX');
  props.deleteProperty('BATCH_RESULTS');
  props.deleteProperty('BATCH_UPDATED');
}

// ============================================================
// 工具
// ============================================================

function roundTo(val, decimals) {
  var factor = Math.pow(10, decimals);
  return Math.round(val * factor) / factor;
}
