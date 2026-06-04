/**
 * Google Ads Script: Negative Keyword Management
 * Automatically pauses or excludes underperforming keywords
 *
 * Rules:
 * - CTR < 0.5% after 200+ impressions → pause keyword
 * - CPA > 150 UAH without conversions after 50 clicks → exclude keyword
 * - Cost per click > 5 UAH with CTR < 1.5% → review keyword
 */

function main() {
  const customerId = AdsApp.currentAccount().getCustomerId();
  const reportDate = new Date();
  reportDate.setDate(reportDate.getDate() - 1); // Yesterday for full day data

  Logger.log('🔍 Analyzing keywords for ' + customerId);

  const keywords = AdsApp.keywords()
    .forDateRange(reportDate, reportDate)
    .withCondition('Status = ENABLED')
    .get();

  let paused = 0;
  let excluded = 0;
  const issues = [];

  while (keywords.hasNext()) {
    const keyword = keywords.next();
    const stats = keyword.getStatsForDateRange(reportDate, reportDate);

    const impressions = stats.getImpressions();
    const clicks = stats.getClicks();
    const conversions = stats.getConversions();
    const cost = stats.getCost();

    const ctr = impressions > 0 ? (clicks / impressions * 100) : 0;
    const cpa = conversions > 0 ? (cost / conversions) : null;
    const cpc = clicks > 0 ? (cost / clicks) : 0;

    const keywordText = keyword.getText();
    const adGroup = keyword.getAdGroup().getName();

    // Rule 1: Low CTR after enough impressions
    if (impressions >= 200 && ctr < 0.5) {
      keyword.pause();
      paused++;
      issues.push({
        keyword: keywordText,
        reason: 'Low CTR: ' + ctr.toFixed(2) + '%',
        action: 'PAUSED'
      });
    }

    // Rule 2: High CPA without conversions
    else if (clicks >= 50 && conversions === 0 && cpa === null) {
      const keywordOperation = keyword.isNegative() ? 'Already negative' : 'Excluding';
      if (!keyword.isNegative()) {
        const campaign = keyword.getAdGroup().getCampaign();
        campaign.createNegativeKeyword(keywordText);
        excluded++;
      }
      issues.push({
        keyword: keywordText,
        reason: 'Zero conversions after ' + clicks + ' clicks',
        action: 'EXCLUDED'
      });
    }

    // Rule 3: High CPC with low CTR (potential quality issue)
    else if (cpc > 5 && ctr < 1.5) {
      issues.push({
        keyword: keywordText,
        reason: 'High CPC (' + cpc.toFixed(2) + ' UAH) + Low CTR',
        action: 'REVIEW'
      });
    }
  }

  // Log results
  const timestamp = reportDate.toLocaleDateString('uk-UA');
  const summary = {
    date: timestamp,
    total_keywords_analyzed: keywords.totalNumEntities(),
    paused: paused,
    excluded: excluded,
    issues_found: issues.length,
    details: issues.slice(0, 10) // First 10 for logging
  };

  Logger.log('✅ Summary:');
  Logger.log('Paused: ' + paused);
  Logger.log('Excluded: ' + excluded);
  Logger.log('Issues: ' + issues.length);

  // Optional: Save to Sheet
  // saveResultsToSheet(summary);
}

function saveResultsToSheet(summary) {
  const spreadsheetId = PropertiesService.getUserProperties().getProperty('reports_sheet_id');
  if (!spreadsheetId) {
    Logger.log('⚠️  reports_sheet_id not set in Script Properties');
    return;
  }

  const ss = SpreadsheetApp.openById(spreadsheetId);
  const sheet = ss.getSheetByName('Keyword_Audit') || ss.insertSheet('Keyword_Audit');

  const headers = ['Date', 'Paused', 'Excluded', 'Issues Found', 'Details'];
  if (sheet.getLastRow() === 0) {
    sheet.appendRow(headers);
  }

  sheet.appendRow([
    summary.date,
    summary.paused,
    summary.excluded,
    summary.issues_found,
    JSON.stringify(summary.details).substring(0, 500)
  ]);
}

// Run the script
main();
