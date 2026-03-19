/**
 * DataFetcher.gs — 台股資料抓取模組
 * 使用 UrlFetchApp 呼叫 FinMind API 與 TWSE OpenAPI
 */

// ============================================================
// FinMind API 呼叫
// ============================================================

/**
 * 呼叫 FinMind API
 * @param {string} dataset - 資料集名稱
 * @param {string} stockId - 股票代號
 * @param {string} startDate - 開始日期 'YYYY-MM-DD'
 * @param {string} token - API Token
 * @return {Array|null} 資料陣列，失敗回傳 null
 */
function finmindFetch(dataset, stockId, startDate, token) {
  var cfg = getConfig();
  var delay = cfg.apiDelayMs || 700;

  var url = 'https://api.finmindtrade.com/api/v4/data';
  var params = {
    dataset:    dataset,
    data_id:    stockId,
    start_date: startDate,
  };
  if (token) params['token'] = token;

  // 組合 query string
  var qs = Object.keys(params).map(function(k) {
    return encodeURIComponent(k) + '=' + encodeURIComponent(params[k]);
  }).join('&');

  Utilities.sleep(delay);

  try {
    var resp = UrlFetchApp.fetch(url + '?' + qs, {
      method: 'get',
      muteHttpExceptions: true,
      headers: { 'User-Agent': 'GAS-TaiwanStockScreener/1.0' },
    });

    if (resp.getResponseCode() !== 200) {
      Logger.log('[FinMind] HTTP ' + resp.getResponseCode() + ' | ' + stockId + ' | ' + dataset);
      return null;
    }

    var json = JSON.parse(resp.getContentText());
    if (json.status !== 200) {
      Logger.log('[FinMind] API Error: ' + json.msg + ' | ' + stockId);
      return null;
    }

    return json.data || [];
  } catch (e) {
    Logger.log('[FinMind] Exception: ' + e.message + ' | ' + stockId);
    return null;
  }
}

// ============================================================
// 財務資料取得函式
// ============================================================

/**
 * 取得財務報表（綜合損益表、資產負債表、現金流量）
 * @param {string} stockId
 * @param {string} token
 * @return {{ income, balance, cashflow }}
 */
function getFinancialData(stockId, token) {
  var startDate = formatDateYearsAgo(5);

  return {
    income:   finmindFetch('TaiwanStockFinancialStatements', stockId, startDate, token) || [],
    balance:  finmindFetch('TaiwanStockBalanceSheet',        stockId, startDate, token) || [],
    cashflow: finmindFetch('TaiwanStockCashFlowsStatement',  stockId, startDate, token) || [],
  };
}

/**
 * 取得本益比、股價淨值比、殖利率
 * @param {string} stockId
 * @param {string} token
 * @return {{ pe, pb, dividendYield }}
 */
function getPePbRatios(stockId, token) {
  var startDate = formatDateYearsAgo(0.1); // 近一個月
  var data = finmindFetch('TaiwanStockPER', stockId, startDate, token) || [];

  if (data.length === 0) return { pe: 0, pb: 0, dividendYield: 0 };

  var latest = data[data.length - 1];
  return {
    pe:            parseFloat(latest['PER']           || 0),
    pb:            parseFloat(latest['PBR']           || 0),
    dividendYield: parseFloat(latest['DividendYield'] || 0),
  };
}

/**
 * 取得即時股價（TWSE）
 * @param {string} stockId
 * @return {{ price, name }}
 */
function getRealtimePrice(stockId) {
  try {
    var url = 'https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch=tse_' + stockId + '.tw';
    var resp = UrlFetchApp.fetch(url, { muteHttpExceptions: true });
    var json = JSON.parse(resp.getContentText());
    if (json.msgArray && json.msgArray.length > 0) {
      var item = json.msgArray[0];
      return {
        name:  item['n'] || stockId,
        price: parseFloat(item['z'] || item['y'] || 0),
      };
    }
  } catch (e) {
    Logger.log('[Price] ' + stockId + ': ' + e.message);
  }
  return { name: stockId, price: 0 };
}

// ============================================================
// 股票清單
// ============================================================

/**
 * 從「自選清單」工作表讀取股票代號
 * 若工作表為空，回傳預設大市值清單
 * @return {string[]}
 */
function getWatchlist() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName(getConfig().sheets.watchlist);

  if (!sheet || sheet.getLastRow() <= 1) {
    return DEFAULT_WATCHLIST;
  }

  var data = sheet.getRange(2, 1, sheet.getLastRow() - 1, 1).getValues();
  var ids = [];
  data.forEach(function(row) {
    var id = String(row[0]).trim();
    if (id && /^\d{4,5}$/.test(id)) ids.push(id);
  });

  return ids.length > 0 ? ids : DEFAULT_WATCHLIST;
}

// ============================================================
// 工具
// ============================================================

/**
 * 計算 N 年前的日期字串
 * @param {number} years
 * @return {string} 'YYYY-MM-DD'
 */
function formatDateYearsAgo(years) {
  var d = new Date();
  d.setFullYear(d.getFullYear() - Math.floor(years));
  if (years < 1) {
    d.setMonth(d.getMonth() - Math.round(years * 12));
  }
  return Utilities.formatDate(d, 'Asia/Taipei', 'yyyy-MM-dd');
}

/**
 * 安全轉換數字
 * @param {*} val
 * @return {number}
 */
function toNum(val) {
  var n = parseFloat(val);
  return isNaN(n) ? 0 : n;
}

/**
 * 從陣列中篩選特定 type 欄位的資料，回傳 value 陣列（依 date 排序）
 * @param {Array} data - FinMind 財報資料
 * @param {string} type - 欄位類型
 * @return {number[]}
 */
function extractValues(data, type) {
  if (!data || data.length === 0) return [];
  var filtered = data.filter(function(r) { return r['type'] === type; });
  filtered.sort(function(a, b) { return a['date'] > b['date'] ? 1 : -1; });
  return filtered.map(function(r) { return toNum(r['value']); });
}
