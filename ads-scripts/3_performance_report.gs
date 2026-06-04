/**
 * Google Ads Script: Daily Performance Report to Google Sheets
 * Writes keyword and placement performance data to a Google Sheet
 * This data is then read by n8n for monitoring and alerts
 *
 * Output: Updates Google Sheet "Daily_Performance" with:
 * - Keyword stats (CTR, CPA, CPC, conversions)
 * - Campaign performance
 * - Issues flagged for review
 */

function main() {
  const customerId = AdsApp.currentAccount().getCustomerId();
  const sheetId = PropertiesService.getUserProperties().getProperty('performance_sheet_id');

  if (!sheetId) {
    Logger.log('❌ ERROR: performance_sheet_id not set in Script Properties');
    Logger.log('   Add it via: Script Properties (gear icon) → Set performance_sheet_id');
    return;
  }

  const reportDate = new Date();
  reportDate.setDate(reportDate.getDate() - 1); // Yesterday

  Logger.log('📊 Writing performance report for ' + formatDate(reportDate));

  // Get keyword performance
  const keywords = AdsApp.keywords()
    .forDateRange(reportDate, reportDate)
    .get();

  const rows = [];
  let count = 0;

  while (keywords.hasNext()) {
    const keyword = keywords.next();
    const stats = keyword.getStatsForDateRange(reportDate, reportDate);

    if (stats.getImpressions() === 0) continue; // Skip zero-impression keywords

    const impressions = stats.getImpressions();
    const clicks = stats.getClicks();
    const conversions = stats.getConversions();
    const cost = stats.getCost();

    const ctr = impressions > 0 ? ((clicks / impressions) * 100).toFixed(2) : 0;
    const cpc = clicks > 0 ? (cost / clicks).toFixed(2) : 0;
    const cpa = conversions > 0 ? (cost / conversions).toFixed(2) : 'N/A';

    rows.push([
      formatDate(reportDate),
      keyword.getText(),
      keyword.getAdGroup().getName(),
      keyword.getAdGroup().getCampaign().getName(),
      impressions,
      clicks,
      ctr,
      cpc,
      conversions,
      cost.toFixed(2),
      cpa
    ]);

    count++;
  }

  if (rows.length === 0) {
    Logger.log('⚠️  No keyword data found for ' + formatDate(reportDate));
    return;
  }

  // Write to Google Sheet
  try {
    const ss = SpreadsheetApp.openById(sheetId);
    let sheet = ss.getSheetByName('Daily_Performance');

    if (!sheet) {
      sheet = ss.insertSheet('Daily_Performance');
      const headers = [
        'Date', 'Keyword', 'Ad Group', 'Campaign',
        'Impressions', 'Clicks', 'CTR %', 'CPC UAH',
        'Conversions', 'Cost UAH', 'CPA UAH'
      ];
      sheet.appendRow(headers);
    }

    // Append data rows
    rows.forEach(row => sheet.appendRow(row));

    Logger.log('✅ Wrote ' + count + ' keywords to sheet');
    Logger.log('   Sheet: ' + sheetId);

    // Keep only last 30 days of data
    cleanOldData(sheet, 30);

  } catch (e) {
    Logger.log('❌ Error writing to sheet: ' + e.message);
  }

  // Also log campaign summary
  logCampaignSummary(reportDate);
}

function logCampaignSummary(reportDate) {
  const campaigns = AdsApp.campaigns()
    .forDateRange(reportDate, reportDate)
    .get();

  Logger.log('📈 Campaign Summary for ' + formatDate(reportDate) + ':');

  while (campaigns.hasNext()) {
    const campaign = campaigns.next();
    const stats = campaign.getStatsForDateRange(reportDate, reportDate);

    if (stats.getImpressions() === 0) continue;

    const impressions = stats.getImpressions();
    const clicks = stats.getClicks();
    const conversions = stats.getConversions();
    const cost = stats.getCost();
    const ctr = ((clicks / impressions) * 100).toFixed(2);

    Logger.log(
      '  ' + campaign.getName() +
      ' | Impressions: ' + impressions +
      ' | Clicks: ' + clicks +
      ' | CTR: ' + ctr + '%' +
      ' | Conversions: ' + conversions +
      ' | Cost: ' + cost.toFixed(2) + ' UAH'
    );
  }
}

function cleanOldData(sheet, daysToKeep) {
  try {
    const data = sheet.getDataRange().getValues();
    if (data.length <= 1) return; // Only headers

    const cutoffDate = new Date();
    cutoffDate.setDate(cutoffDate.getDate() - daysToKeep);

    let rowsToDelete = 0;
    for (let i = data.length - 1; i > 0; i--) {
      const rowDate = new Date(data[i][0]);
      if (rowDate < cutoffDate) {
        sheet.deleteRow(i);
        rowsToDelete++;
      }
    }

    if (rowsToDelete > 0) {
      Logger.log('🧹 Cleaned ' + rowsToDelete + ' old rows (>' + daysToKeep + ' days)');
    }
  } catch (e) {
    Logger.log('⚠️  Could not clean old data: ' + e.message);
  }
}

function formatDate(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return year + '-' + month + '-' + day;
}

// Run the script
main();
