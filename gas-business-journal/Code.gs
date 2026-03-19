/**
 * 業務日誌 — Google Apps Script 後端
 *
 * 使用方式：
 * 1. 在 Google Apps Script 專案中建立此檔案 (Code.gs)
 * 2. 建立 Index.html 檔案
 * 3. 部署為 Web App（執行身份：自己，存取權限：自己）
 */

var SHEET_NAME = '業務日誌';
var HEADERS = ['id', 'date', 'category', 'title', 'description', 'status', 'createdAt', 'updatedAt'];

/**
 * Web App 進入點 — 回傳前端 HTML 頁面
 */
function doGet() {
  return HtmlService.createHtmlOutputFromFile('Index')
    .setTitle('業務日誌')
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL)
    .addMetaTag('viewport', 'width=device-width, initial-scale=1');
}

/**
 * 取得或建立工作表
 */
function getOrCreateSheet() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName(SHEET_NAME);
  if (!sheet) {
    sheet = ss.insertSheet(SHEET_NAME);
    sheet.appendRow(HEADERS);
    sheet.getRange(1, 1, 1, HEADERS.length).setFontWeight('bold');
    sheet.setFrozenRows(1);
    // 設定欄寬
    sheet.setColumnWidth(1, 180); // id
    sheet.setColumnWidth(2, 110); // date
    sheet.setColumnWidth(3, 100); // category
    sheet.setColumnWidth(4, 200); // title
    sheet.setColumnWidth(5, 300); // description
    sheet.setColumnWidth(6, 80);  // status
    sheet.setColumnWidth(7, 180); // createdAt
    sheet.setColumnWidth(8, 180); // updatedAt
  }
  return sheet;
}

/**
 * 產生唯一 ID
 */
function generateId() {
  return Utilities.getUuid();
}

/**
 * 新增一筆日誌
 * @param {Object} data - { date, category, title, description, status }
 * @return {Object} 新增的完整記錄
 */
function addEntry(data) {
  var sheet = getOrCreateSheet();
  var now = new Date().toISOString();
  var id = generateId();

  var row = [
    id,
    data.date,
    data.category,
    data.title,
    data.description || '',
    data.status || '未開始',
    now,
    now
  ];

  sheet.appendRow(row);

  return {
    id: id,
    date: data.date,
    category: data.category,
    title: data.title,
    description: data.description || '',
    status: data.status || '未開始',
    createdAt: now,
    updatedAt: now
  };
}

/**
 * 取得日誌列表
 * @param {string} date - 篩選日期 (yyyy-MM-dd)，空字串則回傳全部
 * @return {Array} 日誌記錄陣列
 */
function getEntries(date) {
  var sheet = getOrCreateSheet();
  var lastRow = sheet.getLastRow();

  if (lastRow <= 1) {
    return [];
  }

  var data = sheet.getRange(2, 1, lastRow - 1, HEADERS.length).getValues();
  var entries = [];

  for (var i = 0; i < data.length; i++) {
    var row = data[i];
    if (row[0] === '' || row[0] === null) continue;

    var entry = {
      id: row[0],
      date: row[1],
      category: row[2],
      title: row[3],
      description: row[4],
      status: row[5],
      createdAt: row[6],
      updatedAt: row[7]
    };

    if (date && date !== '') {
      if (entry.date === date) {
        entries.push(entry);
      }
    } else {
      entries.push(entry);
    }
  }

  // 依建立時間倒序排列
  entries.sort(function(a, b) {
    return new Date(b.createdAt) - new Date(a.createdAt);
  });

  return entries;
}

/**
 * 更新一筆日誌
 * @param {Object} data - { id, date, category, title, description, status }
 * @return {Object} 更新後的記錄
 */
function updateEntry(data) {
  var sheet = getOrCreateSheet();
  var lastRow = sheet.getLastRow();

  if (lastRow <= 1) {
    throw new Error('找不到該筆記錄');
  }

  var allData = sheet.getRange(2, 1, lastRow - 1, HEADERS.length).getValues();

  for (var i = 0; i < allData.length; i++) {
    if (allData[i][0] === data.id) {
      var rowIndex = i + 2; // 加上表頭列
      var now = new Date().toISOString();

      sheet.getRange(rowIndex, 2).setValue(data.date);
      sheet.getRange(rowIndex, 3).setValue(data.category);
      sheet.getRange(rowIndex, 4).setValue(data.title);
      sheet.getRange(rowIndex, 5).setValue(data.description || '');
      sheet.getRange(rowIndex, 6).setValue(data.status);
      sheet.getRange(rowIndex, 8).setValue(now);

      return {
        id: data.id,
        date: data.date,
        category: data.category,
        title: data.title,
        description: data.description || '',
        status: data.status,
        createdAt: allData[i][6],
        updatedAt: now
      };
    }
  }

  throw new Error('找不到 ID 為 ' + data.id + ' 的記錄');
}

/**
 * 刪除一筆日誌
 * @param {string} id - 要刪除的記錄 ID
 * @return {boolean} 是否成功
 */
function deleteEntry(id) {
  var sheet = getOrCreateSheet();
  var lastRow = sheet.getLastRow();

  if (lastRow <= 1) {
    throw new Error('找不到該筆記錄');
  }

  var allData = sheet.getRange(2, 1, lastRow - 1, HEADERS.length).getValues();

  for (var i = 0; i < allData.length; i++) {
    if (allData[i][0] === id) {
      sheet.deleteRow(i + 2);
      return true;
    }
  }

  throw new Error('找不到 ID 為 ' + id + ' 的記錄');
}

/**
 * 快速更新狀態
 * @param {string} id - 記錄 ID
 * @param {string} status - 新狀態
 * @return {Object} 更新後的記錄
 */
function updateStatus(id, status) {
  var sheet = getOrCreateSheet();
  var lastRow = sheet.getLastRow();

  if (lastRow <= 1) {
    throw new Error('找不到該筆記錄');
  }

  var allData = sheet.getRange(2, 1, lastRow - 1, HEADERS.length).getValues();

  for (var i = 0; i < allData.length; i++) {
    if (allData[i][0] === id) {
      var rowIndex = i + 2;
      var now = new Date().toISOString();

      sheet.getRange(rowIndex, 6).setValue(status);
      sheet.getRange(rowIndex, 8).setValue(now);

      return {
        id: allData[i][0],
        date: allData[i][1],
        category: allData[i][2],
        title: allData[i][3],
        description: allData[i][4],
        status: status,
        createdAt: allData[i][6],
        updatedAt: now
      };
    }
  }

  throw new Error('找不到 ID 為 ' + id + ' 的記錄');
}
