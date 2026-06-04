/**
 * Kristallik — Auto Exclusions
 *
 * Правила:
 *   1. Місце розміщення: 100+ кліків, 0 конверсій → виключити (рівень акаунту)
 *   2. Товар:            100+ кліків, 0 конверсій → виключити (лог + спроба через API)
 *   3. Пошуковий запит: 100+ кліків, 0 конверсій → мінус-слово (рівень кампанії)
 *
 * ─────────────────────────────────────────────
 *  DRY_RUN = true  → тільки лог, нічого не міняє  ← починай звідси
 *  DRY_RUN = false → реально вносить зміни
 * ─────────────────────────────────────────────
 *
 * Розклад: щотижня (наприклад, понеділок 7:00)
 */

// ═══════════════════════════════════
//  НАЛАШТУВАННЯ
// ═══════════════════════════════════

var DRY_RUN      = true;   // ← змінити на false щоб вносити зміни
var LOOKBACK     = 90;     // днів для аналізу
var MIN_CLICKS   = 100;    // поріг кліків для всіх трьох правил
var CONV_MIN     = 0.5;    // менше цього конверсій → дія

var SPREADSHEET_URL = 'https://docs.google.com/spreadsheets/d/1Nrqy7MH-CPIcMTuf6YccYDmb8uJiMck8RgxDxzYnpJc/edit?usp=sharing';
var EMAIL           = 'kristallikcomua@gmail.com';
var DEVELOPER_TOKEN = 'IwswL5ObX-90K5sM9Ntw5A';  // з google-ads-config

// ═══════════════════════════════════
//  MAIN
// ═══════════════════════════════════

function main() {
  Logger.log((DRY_RUN ? '[DRY RUN]' : '[LIVE]') + ' Старт. Аналіз: ' + LOOKBACK + ' днів, поріг: ' + MIN_CLICKS + ' кліків.');

  var ss    = SpreadsheetApp.openByUrl(SPREADSHEET_URL);
  var dates = dateRange(LOOKBACK);
  var log   = { placements: [], products: [], keywords: [] };

  runPlacements(dates, log);
  runProducts(dates, log);
  runKeywords(dates, log);

  writeSheet(log, ss);

  var total = log.placements.length + log.products.length + log.keywords.length;
  Logger.log('Готово. Майданчики: ' + log.placements.length + ' | Товари: ' + log.products.length + ' | Запити: ' + log.keywords.length);
  if (total > 0) sendEmail(log);
}

// ═══════════════════════════════════
//  1. МІСЦЯ РОЗМІЩЕННЯ
// ═══════════════════════════════════

function runPlacements(dates, log) {
  Logger.log('\n── Місця розміщення ──');

  var q =
    'SELECT ' +
      'detail_placement_view.placement, ' +
      'detail_placement_view.display_name, ' +
      'detail_placement_view.placement_type, ' +
      'campaign.name, campaign.status, ' +
      'metrics.clicks, metrics.cost_micros, metrics.conversions ' +
    'FROM detail_placement_view ' +
    'WHERE ' +
      'metrics.clicks >= ' + MIN_CLICKS + ' ' +
      'AND metrics.conversions < ' + CONV_MIN + ' ' +
      "AND segments.date BETWEEN '" + dates.start + "' AND '" + dates.end + "' " +
      'AND campaign.status = ENABLED ' +
    'ORDER BY metrics.clicks DESC';

  var rows = safeSearch(q);
  if (!rows) return;

  var seen = {};
  while (rows.hasNext()) {
    var r    = rows.next();
    var url  = r.detailPlacementView.placement;
    var name = r.detailPlacementView.displayName;
    var type = r.detailPlacementView.placementType;
    var camp = r.campaign.name;
    var clk  = r.metrics.clicks;
    var cost = uah(r.metrics.costMicros);
    var conv = r.metrics.conversions;

    if (seen[url]) continue;
    seen[url] = true;

    var ok = true;
    if (!DRY_RUN) {
      try {
        AdsApp.newAccountExcludedPlacementBuilder().withUrl(url).build();
      } catch(e) {
        Logger.log('Помилка: ' + url + ' | ' + e);
        ok = false;
      }
    }

    var action = DRY_RUN ? 'Would ban' : (ok ? 'Banned' : 'ERROR');
    Logger.log(action + ' | ' + url + ' | ' + clk + ' кліків | ' + cost + ' грн | ' + camp);
    log.placements.push([today(), action, camp, url, name, type, clk, cost, conv]);
  }
}

// ═══════════════════════════════════
//  2. ТОВАРИ
// ═══════════════════════════════════

function runProducts(dates, log) {
  Logger.log('\n── Товари ──');

  var q =
    'SELECT ' +
      'segments.product_item_id, ' +
      'segments.product_title, ' +
      'campaign.id, campaign.name, campaign.status, ' +
      'metrics.clicks, metrics.cost_micros, metrics.conversions, metrics.impressions ' +
    'FROM shopping_performance_view ' +
    'WHERE ' +
      'metrics.clicks >= ' + MIN_CLICKS + ' ' +
      'AND metrics.conversions < ' + CONV_MIN + ' ' +
      "AND segments.date BETWEEN '" + dates.start + "' AND '" + dates.end + "' " +
      'AND campaign.status = ENABLED ' +
    'ORDER BY metrics.clicks DESC';

  var rows = safeSearch(q);
  if (!rows) return;

  var seen = {};
  while (rows.hasNext()) {
    var r      = rows.next();
    var itemId = r.segments.productItemId;
    var title  = r.segments.productTitle;
    var campId = r.campaign.id;
    var camp   = r.campaign.name;
    var clk    = r.metrics.clicks;
    var cost   = uah(r.metrics.costMicros);
    var conv   = r.metrics.conversions;
    var impr   = r.metrics.impressions;

    if (seen[itemId]) continue;
    seen[itemId] = true;

    var action = DRY_RUN ? 'Would ban' : 'Needs manual ban';

    // Для P-Max — виключення товарів через Scripts не підтримується напряму.
    // Записуємо в таблицю. В Google Ads: P-Max → Список товарів → виключити по item_id.
    // Альтернатива: вимкнути товар у фіді (наприклад, поставити availability=out_of_stock).

    if (!DRY_RUN) {
      // Спроба для звичайних Shopping кампаній (не P-Max)
      try {
        var campIter = AdsApp.shoppingCampaigns().withIds([campId]).get();
        if (campIter.hasNext()) {
          var shoppingCamp = campIter.next();
          // Шукаємо product group і додаємо виключення
          var pgIter = shoppingCamp.productGroups().withCondition("ProductItemId = '" + itemId + "'").get();
          if (pgIter.hasNext()) {
            pgIter.next().setExcluded(true);
            action = 'Banned';
          } else {
            action = 'Log only (P-Max)';
          }
        } else {
          action = 'Log only (P-Max)';
        }
      } catch(e) {
        action = 'Log only (P-Max)';
        Logger.log('Товар ' + itemId + ' — потрібно вручну виключити в P-Max');
      }
    }

    Logger.log(action + ' | [' + itemId + '] ' + title + ' | ' + clk + ' кліків | ' + cost + ' грн | ' + camp);
    log.products.push([today(), action, camp, itemId, title, clk, cost, conv, impr]);
  }
}

// ═══════════════════════════════════
//  3. ПОШУКОВІ ЗАПИТИ
// ═══════════════════════════════════

function runKeywords(dates, log) {
  Logger.log('\n── Пошукові запити ──');

  var q =
    'SELECT ' +
      'search_term_view.search_term, ' +
      'campaign.id, campaign.name, campaign.status, ' +
      'ad_group.name, ad_group.status, ' +
      'metrics.clicks, metrics.cost_micros, metrics.conversions, metrics.impressions ' +
    'FROM search_term_view ' +
    'WHERE ' +
      'metrics.clicks >= ' + MIN_CLICKS + ' ' +
      'AND metrics.conversions < ' + CONV_MIN + ' ' +
      "AND segments.date BETWEEN '" + dates.start + "' AND '" + dates.end + "' " +
      'AND campaign.status = ENABLED ' +
      'AND ad_group.status = ENABLED ' +
    'ORDER BY metrics.clicks DESC';

  var rows = safeSearch(q);
  if (!rows) return;

  var seen = {};
  while (rows.hasNext()) {
    var r      = rows.next();
    var term   = r.searchTermView.searchTerm;
    var campId = r.campaign.id;
    var camp   = r.campaign.name;
    var ag     = r.adGroup.name;
    var clk    = r.metrics.clicks;
    var cost   = uah(r.metrics.costMicros);
    var conv   = r.metrics.conversions;
    var impr   = r.metrics.impressions;

    var key = campId + '|' + term;
    if (seen[key]) continue;
    seen[key] = true;

    if (alreadyNegated(term, campId)) {
      Logger.log('Вже є в негативах: "' + term + '"');
      continue;
    }

    var action = DRY_RUN ? 'Would ban' : 'Banned';
    if (!DRY_RUN) {
      try {
        var iter = AdsApp.campaigns().withIds([campId]).get();
        if (iter.hasNext()) {
          iter.next().negativeKeywords().addBroadMatch(term);
        } else {
          // P-Max — пошукові запити можна заблокувати тільки через Shared Negative List
          action = 'Log only (P-Max)';
        }
      } catch(e) {
        Logger.log('Помилка: "' + term + '" | ' + e);
        action = 'ERROR';
      }
    }

    Logger.log(action + ' | "' + term + '" | ' + clk + ' кліків | ' + cost + ' грн | ' + camp);
    log.keywords.push([today(), action, camp, ag, term, clk, cost, conv, impr]);
  }
}

function alreadyNegated(term, campId) {
  try {
    var iter = AdsApp.campaigns().withIds([campId]).get();
    if (!iter.hasNext()) return false;
    var neg = iter.next().negativeKeywords().get();
    while (neg.hasNext()) {
      if (neg.next().getText().toLowerCase() === term.toLowerCase()) return true;
    }
  } catch(e) {}
  return false;
}

// ═══════════════════════════════════
//  ТАБЛИЦЯ
// ═══════════════════════════════════

function writeSheet(log, ss) {
  writeTab(ss, 'Placements',
    ['Date','Action','Campaign','URL','Display Name','Type','Clicks','Cost UAH','Conversions'],
    log.placements);

  writeTab(ss, 'Products',
    ['Date','Action','Campaign','Item ID','Title','Clicks','Cost UAH','Conversions','Impressions'],
    log.products);

  writeTab(ss, 'Keywords',
    ['Date','Action','Campaign','Ad Group','Search Term','Clicks','Cost UAH','Conversions','Impressions'],
    log.keywords);
}

function writeTab(ss, name, header, rows) {
  var sh = ss.getSheetByName(name);
  if (!sh) {
    sh = ss.insertSheet(name);
    sh.appendRow(header);
    sh.getRange(1, 1, 1, header.length).setFontWeight('bold').setBackground('#f0f0f0');
  }
  rows.forEach(function(r) { sh.appendRow(r); });
  Logger.log('Записано в "' + name + '": ' + rows.length + ' рядків');
}

// ═══════════════════════════════════
//  EMAIL
// ═══════════════════════════════════

function sendEmail(log) {
  var mode = DRY_RUN ? '[DRY RUN] ' : '';
  var total = log.placements.length + log.products.length + log.keywords.length;
  var subject = mode + '[Kristallik] Виключення: ' + total + ' позицій';

  var lines = [
    DRY_RUN ? '⚠️  DRY RUN — зміни ще НЕ внесені. Змінити DRY_RUN = false і запустити ще раз.' : '✅ Зміни внесені.',
    'Таблиця: ' + SPREADSHEET_URL,
    '',
    '── Майданчики (' + log.placements.length + ') ──',
  ];
  log.placements.slice(0, 20).forEach(function(r) {
    lines.push(r[1] + ': ' + r[3] + ' | ' + r[6] + ' кліків | ' + r[7] + ' грн');
  });

  lines.push('', '── Товари (' + log.products.length + ') ──');
  log.products.slice(0, 20).forEach(function(r) {
    lines.push(r[1] + ': [' + r[3] + '] ' + r[4] + ' | ' + r[5] + ' кліків | ' + r[6] + ' грн');
  });

  lines.push('', '── Пошукові запити (' + log.keywords.length + ') ──');
  log.keywords.slice(0, 20).forEach(function(r) {
    lines.push(r[1] + ': "' + r[4] + '" | ' + r[5] + ' кліків | ' + r[6] + ' грн');
  });

  MailApp.sendEmail(EMAIL, subject, lines.join('\n'));
}

// ═══════════════════════════════════
//  ХЕЛПЕРИ
// ═══════════════════════════════════

function safeSearch(query) {
  try {
    return AdsApp.search(query);
  } catch(e) {
    Logger.log('Помилка запиту: ' + e + '\nQuery: ' + query);
    return null;
  }
}

function dateRange(days) {
  var tz    = AdsApp.currentAccount().getTimeZone();
  var end   = new Date(Date.now() - 86400000);
  var start = new Date(Date.now() - days * 86400000);
  return {
    start: Utilities.formatDate(start, tz, 'yyyy-MM-dd'),
    end:   Utilities.formatDate(end,   tz, 'yyyy-MM-dd')
  };
}

function uah(micros) { return (micros / 1000000).toFixed(2); }

function today() {
  return Utilities.formatDate(new Date(), AdsApp.currentAccount().getTimeZone(), 'yyyy-MM-dd');
}
