/**
 * Notifier.gs — 通知發送模組
 * 支援 LINE Notify、Gmail
 */

// ============================================================
// 發送篩選報告
// ============================================================

/**
 * 發送篩選結果報告
 * @param {Object[]} ranked - 排序後的篩選結果
 * @param {string} runTime
 */
function sendReport(ranked, runTime) {
  var cfg = getConfig();
  var message = formatReport(ranked, runTime);

  if (cfg.lineToken) {
    sendLineNotify(message, cfg.lineToken);
  }

  if (cfg.emailEnabled) {
    sendEmail(
      '台股巴菲特篩選報告 ' + runTime,
      message,
      cfg.emailRecipient
    );
  }

  // 若都沒設定，寫入日誌提醒
  if (!cfg.lineToken && !cfg.emailEnabled) {
    writeLog('INFO', '通知未設定（LINE Token / Email 皆未填）');
    Logger.log(message);
  }
}

// ============================================================
// 格式化報告
// ============================================================

function formatReport(ranked, runTime) {
  var lines = [
    '📊 台股巴菲特篩選報告',
    '🗓 ' + runTime,
    '─'.repeat(38),
  ];

  if (ranked.length === 0) {
    lines.push('本次篩選無符合條件標的。');
  } else {
    lines.push('✅ 篩選通過: ' + ranked.length + ' 檔\n');

    ranked.forEach(function(s, idx) {
      var star = s.totalScore >= 80 ? '🌟' : s.totalScore >= 70 ? '✅' : '📌';
      lines.push(
        star + ' #' + (idx + 1) + ' [' + s.stockId + '] ' + s.name + '\n' +
        '   總分: ' + s.totalScore.toFixed(1) + '/100  通過: ' + s.passedCount + '/7\n' +
        '   ROE:' + s.roeAvg.toFixed(1) + '%  P/E:' + s.pe.toFixed(1) +
        '  P/B:' + s.pb.toFixed(2) + '  殖利率:' + s.dividendYield.toFixed(1) + '%\n' +
        '   現價:' + s.price.toFixed(2) + '  負債比:' + s.debtRatio.toFixed(0) + '%'
      );
    });
  }

  lines.push('\n─'.repeat(38));
  lines.push('⚠️  本報告僅供參考，不構成投資建議。');

  return lines.join('\n');
}

// ============================================================
// LINE Notify
// ============================================================

/**
 * 發送 LINE Notify（自動分段，每段 < 1000 字元）
 * @param {string} message
 * @param {string} token
 */
function sendLineNotify(message, token) {
  var chunks = splitMessage(message, 900);
  var url = 'https://notify-api.line.me/api/notify';

  chunks.forEach(function(chunk) {
    try {
      var resp = UrlFetchApp.fetch(url, {
        method: 'post',
        headers: { 'Authorization': 'Bearer ' + token },
        payload: { message: chunk },
        muteHttpExceptions: true,
      });

      var code = resp.getResponseCode();
      if (code === 200) {
        writeLog('INFO', 'LINE Notify 發送成功');
      } else {
        writeLog('ERROR', 'LINE Notify 失敗 HTTP ' + code + ': ' + resp.getContentText());
      }
    } catch (e) {
      writeLog('ERROR', 'LINE Notify 例外: ' + e.message);
    }
  });
}

// ============================================================
// Gmail
// ============================================================

/**
 * 發送 Gmail 通知
 * @param {string} subject
 * @param {string} body
 * @param {string} recipient
 */
function sendEmail(subject, body, recipient) {
  try {
    var htmlBody = textToHtml(body);
    GmailApp.sendEmail(recipient, subject, body, {
      htmlBody: htmlBody,
      name: '台股篩選機器人',
    });
    writeLog('INFO', 'Email 發送成功至 ' + recipient);
  } catch (e) {
    writeLog('ERROR', 'Email 發送失敗: ' + e.message);
  }
}

// ============================================================
// 工具
// ============================================================

function splitMessage(message, maxLen) {
  if (message.length <= maxLen) return [message];
  var chunks = [];
  while (message.length > 0) {
    if (message.length <= maxLen) { chunks.push(message); break; }
    var splitAt = message.lastIndexOf('\n', maxLen);
    if (splitAt <= 0) splitAt = maxLen;
    chunks.push(message.substring(0, splitAt));
    message = message.substring(splitAt).replace(/^\n/, '');
  }
  return chunks;
}

function textToHtml(text) {
  var escaped = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');

  var rows = escaped.split('\n').map(function(line) {
    if (line.indexOf('📊') !== -1 || line.indexOf('✅ #') !== -1 || line.indexOf('🌟') !== -1) {
      return '<p style="margin:4px 0"><b>' + line + '</b></p>';
    }
    if (line.indexOf('─') !== -1) return '<hr style="margin:8px 0">';
    return '<p style="margin:2px 0; font-size:13px">' + line + '</p>';
  });

  return '<div style="font-family:monospace; max-width:600px">' + rows.join('') + '</div>';
}
