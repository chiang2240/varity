/**
 * Screener.gs — 巴菲特價值投資篩選核心邏輯
 *
 * 7 大指標：
 *   1. ROE > 15%（3年均）         權重 25%
 *   2. EPS 連續3年正成長           權重 20%
 *   3. 負債比率 < 50%              權重 15%
 *   4. 本益比 P/E < 20             權重 15%
 *   5. 股價淨值比 P/B < 3          權重 10%
 *   6. 自由現金流 FCF > 0          權重 10%
 *   7. 股利殖利率 > 0%             權重 5%
 */

// ============================================================
// 主篩選函式
// ============================================================

/**
 * 對單一股票執行巴菲特篩選
 * @param {string} stockId
 * @param {string} name
 * @param {Object} financial - { income[], balance[], cashflow[] }
 * @param {Object} priceData - { pe, pb, dividendYield, price }
 * @param {Object} cfg - getConfig() 結果
 * @return {Object} StockScore 物件
 */
function screenStock(stockId, name, financial, priceData, cfg) {
  var c = cfg.criteria;
  var w = cfg.weights;

  var result = {
    stockId:       stockId,
    name:          name,
    totalScore:    0,
    passedCount:   0,
    totalCriteria: 7,

    roeAvg:        0, roeScore:    0,
    epsGrowth:     0, epsScore:    0,
    debtRatio:     0, debtScore:   0,
    pe:            priceData.pe,  peScore:  0,
    pb:            priceData.pb,  pbScore:  0,
    fcf:           0, fcfScore:    0,
    dividendYield: priceData.dividendYield, divScore: 0,

    price:         priceData.price,
    grossMargin:   0,
    revenueGrowth: 0,
    reasons:       [],
  };

  // 1. ROE
  var roeResult = calcRoe(financial.income, financial.balance, c.ROE_YEARS);
  result.roeAvg   = roeResult.avg;
  result.roeScore = roeResult.score;
  if (result.roeAvg >= c.ROE_MIN) {
    result.passedCount++;
  } else {
    result.reasons.push('ROE ' + result.roeAvg.toFixed(1) + '% < ' + c.ROE_MIN + '%');
  }

  // 2. EPS 成長
  var epsResult = calcEpsGrowth(financial.income, c.EPS_GROWTH_YEARS);
  result.epsGrowth = epsResult.growthRate;
  result.epsScore  = epsResult.score;
  if (result.epsGrowth > 0) {
    result.passedCount++;
  } else {
    result.reasons.push('EPS成長率 ' + result.epsGrowth.toFixed(1) + '% ≤ 0');
  }

  // 3. 負債比率
  var debtResult = calcDebtRatio(financial.balance);
  result.debtRatio = debtResult.ratio;
  result.debtScore = debtResult.score;
  if (result.debtRatio > 0 && result.debtRatio <= c.DEBT_RATIO_MAX) {
    result.passedCount++;
  } else if (result.debtRatio > c.DEBT_RATIO_MAX) {
    result.reasons.push('負債比率 ' + result.debtRatio.toFixed(1) + '% > ' + c.DEBT_RATIO_MAX + '%');
  }

  // 4. 本益比
  result.peScore = calcPeScore(result.pe);
  if (result.pe > 0 && result.pe <= c.PE_MAX) {
    result.passedCount++;
  } else if (result.pe <= 0) {
    result.reasons.push('本益比資料不足');
  } else {
    result.reasons.push('本益比 ' + result.pe.toFixed(1) + ' > ' + c.PE_MAX);
  }

  // 5. 股價淨值比
  result.pbScore = calcPbScore(result.pb);
  if (result.pb > 0 && result.pb <= c.PB_MAX) {
    result.passedCount++;
  } else if (result.pb <= 0) {
    result.reasons.push('P/B 資料不足');
  } else {
    result.reasons.push('P/B ' + result.pb.toFixed(2) + ' > ' + c.PB_MAX);
  }

  // 6. 自由現金流
  var fcfResult = calcFcf(financial.cashflow);
  result.fcf      = fcfResult.fcf;
  result.fcfScore = fcfResult.score;
  if (result.fcf > 0) {
    result.passedCount++;
  } else {
    result.reasons.push('FCF ' + Math.round(result.fcf) + ' ≤ 0');
  }

  // 7. 股利
  result.divScore = calcDividendScore(result.dividendYield);
  if (result.dividendYield > 0) {
    result.passedCount++;
  } else {
    result.reasons.push('無股利資料');
  }

  // 額外指標
  result.grossMargin   = calcGrossMargin(financial.income);
  result.revenueGrowth = calcRevenueGrowth(financial.income);

  // 加權總分
  result.totalScore = (
    result.roeScore   * w.roe +
    result.epsScore   * w.eps +
    result.debtScore  * w.debt +
    result.peScore    * w.pe +
    result.pbScore    * w.pb +
    result.fcfScore   * w.fcf +
    result.divScore   * w.dividend
  );
  result.totalScore = Math.round(result.totalScore * 10) / 10;

  return result;
}

// ============================================================
// 指標計算
// ============================================================

function calcRoe(income, balance, years) {
  var roes = extractValues(income, 'ROE');
  if (roes.length === 0) return { avg: 0, score: 0 };

  var recent = roes.slice(-years);
  var avg = recent.reduce(function(s, v) { return s + v; }, 0) / recent.length;
  var score = Math.min(100, Math.max(0, (avg / 30) * 100));
  return { avg: avg, score: score };
}

function calcEpsGrowth(income, years) {
  var eps = extractValues(income, 'EPS');
  if (eps.length < 2) return { growthRate: 0, score: 0 };

  var recent = eps.slice(-Math.min(years + 1, eps.length));
  var growths = [];
  for (var i = 1; i < recent.length; i++) {
    if (recent[i - 1] > 0) {
      growths.push((recent[i] - recent[i - 1]) / recent[i - 1] * 100);
    }
  }
  if (growths.length === 0) return { growthRate: 0, score: 0 };

  var avg = growths.reduce(function(s, v) { return s + v; }, 0) / growths.length;
  var score = Math.min(100, Math.max(0, 50 + avg * 1.67));
  return { growthRate: avg, score: score };
}

function calcDebtRatio(balance) {
  var assets = extractValues(balance, 'TotalAssets');
  var liab   = extractValues(balance, 'TotalLiabilities');
  if (assets.length === 0 || liab.length === 0) return { ratio: 0, score: 0 };

  var lastA = assets[assets.length - 1];
  var lastL = liab[liab.length - 1];
  if (lastA <= 0) return { ratio: 0, score: 0 };

  var ratio = (lastL / lastA) * 100;
  var score = Math.max(0, 100 - (ratio - 20) * 2);
  return { ratio: ratio, score: score };
}

function calcPeScore(pe) {
  if (pe <= 0)  return 0;
  if (pe <= 10) return 100;
  if (pe <= 15) return 85;
  if (pe <= 20) return 70;
  if (pe <= 25) return 55;
  return Math.max(10, 55 - (pe - 25) * 2);
}

function calcPbScore(pb) {
  if (pb <= 0)   return 0;
  if (pb <= 1.0) return 100;
  if (pb <= 1.5) return 85;
  if (pb <= 2.0) return 70;
  if (pb <= 3.0) return 50;
  return Math.max(10, 50 - (pb - 3) * 15);
}

function calcFcf(cashflow) {
  var opCf  = extractValues(cashflow, 'CashFlowsFromOperatingActivities');
  var capex = extractValues(cashflow, 'AcquisitionOfPropertyPlantAndEquipment');
  if (opCf.length === 0) return { fcf: 0, score: 0 };

  var op  = opCf[opCf.length - 1];
  var cap = capex.length > 0 ? Math.abs(capex[capex.length - 1]) : 0;
  var fcf = op - cap;
  return { fcf: fcf, score: fcf > 0 ? 100 : 0 };
}

function calcDividendScore(yield_) {
  if (yield_ <= 0) return 0;
  if (yield_ >= 8) return 100;
  if (yield_ >= 6) return 90;
  if (yield_ >= 4) return 75;
  if (yield_ >= 2) return 50;
  return 30;
}

function calcGrossMargin(income) {
  var rev   = extractValues(income, 'Revenue');
  var gross = extractValues(income, 'GrossProfit');
  if (rev.length === 0 || gross.length === 0) return 0;
  var r = rev[rev.length - 1];
  var g = gross[gross.length - 1];
  return r > 0 ? (g / r) * 100 : 0;
}

function calcRevenueGrowth(income) {
  var rev = extractValues(income, 'Revenue');
  if (rev.length < 2) return 0;
  var curr = rev[rev.length - 1];
  var prev = rev[rev.length - 2];
  return prev > 0 ? ((curr - prev) / prev) * 100 : 0;
}

// ============================================================
// 排序
// ============================================================

/**
 * 篩選並排序股票，回傳通過門檻的結果
 * @param {Object[]} scores
 * @param {number} minScore
 * @return {Object[]}
 */
function rankStocks(scores, minScore) {
  return scores
    .filter(function(s) { return s.totalScore >= minScore; })
    .sort(function(a, b) { return b.totalScore - a.totalScore; });
}
