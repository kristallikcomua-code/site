/**
 * Google Ads Script: Display Network Placement Exclusions
 * Automatically excludes underperforming placements
 *
 * Rules:
 * - 0 conversions after 50+ clicks → exclude placement
 * - Cost > 500 UAH with 0 conversions → exclude placement
 * - CTR < 0.1% after 200+ impressions → exclude placement
 */

function main() {
  const customerId = AdsApp.currentAccount().getCustomerId();
  const reportDate = new Date();
  reportDate.setDate(reportDate.getDate() - 7); // Last 7 days for statistical significance

  Logger.log('🎯 Analyzing placements for exclusion - ' + customerId);

  // Get all display campaigns
  const campaigns = AdsApp.campaigns()
    .withCondition('AdvertisingChannelType = DISPLAY')
    .get();

  let excluded = 0;
  let reviewed = 0;
  const issues = [];

  while (campaigns.hasNext()) {
    const campaign = campaigns.next();

    // Get display network report
    const report = AdsApp.report(
      'SELECT Placement, PlacementCategory, Clicks, Conversions, Cost, Impressions, Ctr ' +
      'FROM PLACEMENT_PERFORMANCE_REPORT ' +
      'WHERE CampaignStatus = ENABLED ' +
      'AND AdGroupStatus = ENABLED ' +
      'AND PlacementStatus = ENABLED'
    );

    const rows = report.rows();

    while (rows.hasNext()) {
      const row = rows.next();

      const placement = row['Placement'];
      const clicks = parseInt(row['Clicks']) || 0;
      const conversions = parseInt(row['Conversions']) || 0;
      const cost = parseFloat(row['Cost']) || 0;
      const impressions = parseInt(row['Impressions']) || 0;
      const ctr = parseFloat(row['Ctr'].replace('%', '')) || 0;

      let shouldExclude = false;
      let reason = '';

      // Rule 1: Zero conversions after enough clicks
      if (clicks >= 50 && conversions === 0) {
        shouldExclude = true;
        reason = 'Zero conversions after ' + clicks + ' clicks';
      }

      // Rule 2: High cost with no conversions
      else if (cost > 500 && conversions === 0) {
        shouldExclude = true;
        reason = 'Cost ' + cost.toFixed(2) + ' UAH with 0 conversions';
      }

      // Rule 3: Very low CTR
      else if (impressions >= 200 && ctr < 0.1) {
        shouldExclude = true;
        reason = 'Very low CTR: ' + ctr.toFixed(3) + '%';
      }

      if (shouldExclude) {
        excludePlacement(campaign, placement);
        excluded++;
        issues.push({
          placement: placement,
          campaign: campaign.getName(),
          clicks: clicks,
          conversions: conversions,
          cost: cost.toFixed(2),
          reason: reason
        });
      } else if (conversions === 0 && clicks > 20) {
        // Mark for review if no conversions but not enough to auto-exclude
        reviewed++;
      }
    }
  }

  // Summary
  Logger.log('✅ Placement Exclusion Summary:');
  Logger.log('Excluded: ' + excluded);
  Logger.log('Reviewed: ' + reviewed);
  Logger.log('Total Issues: ' + issues.length);

  if (issues.length > 0) {
    Logger.log('Details:');
    issues.slice(0, 10).forEach(issue => {
      Logger.log(
        '  - ' + issue.placement + ' (' + issue.campaign + '): ' + issue.reason
      );
    });
  }
}

function excludePlacement(campaign, placement) {
  try {
    // Add as excluded placement to the campaign
    campaign.createExcludedPlacement(placement);
    Logger.log('  ✅ Excluded: ' + placement);
  } catch (e) {
    Logger.log('  ⚠️  Could not exclude ' + placement + ': ' + e.message);
  }
}

// Run the script
main();
