# Google Ads & B2B Sales Automation Setup

Fully automated system for kristallik.com.ua using n8n, Google Ads Scripts, and SendPulse email marketing.

## 📦 Components

### Part A: n8n Workflows (JSON files)
| Workflow | Status | Trigger | Purpose |
|----------|--------|---------|---------|
| `1_ads_daily_monitor.json` | 🟢 **ACTIVE** | Daily 9:00 AM | Monitor Google Ads performance, send Telegram alerts |
| `2_b2b_email_nurture.json` | 🟢 **ACTIVE** | Daily | Automated B2B email sequences (Day 0/3/7/14/30) |
| `3_merchant_feed.json` | ⏸️ Draft | Weekly | Upload product feed to Google Merchant Center |
| `4_competitor_monitor.json` | ⏸️ Draft | Weekly | Track competitor prices, alert if cheaper |
| `5_weekly_report.json` | ⏸️ Draft | Monday 8 AM | Weekly business summary report |

### Part B: Google Ads Scripts (Google Apps Script)
| Script | File | Purpose |
|--------|------|---------|
| Negative Keywords | `ads-scripts/1_negative_keywords.gs` | Pause underperforming keywords (CTR < 0.5%, CPA > 150₴) |
| Placement Exclusions | `ads-scripts/2_placement_exclusions.gs` | Auto-exclude display placements with 0 conversions |
| Performance Report | `ads-scripts/3_performance_report.gs` | Daily report to Google Sheets for n8n monitoring |

### Part C: Cart Tracking (Monster Webby Snippet)
| File | Purpose |
|------|---------|
| `snippets/cart_webhook.js` | Insert into Monster Webby "Third-party code" for cart event tracking |

---

## 🚀 Quick Start

### 1. Verify n8n is Running
```bash
ps aux | grep n8n
# Should show: node node_modules/.bin/n8n start
```

If not running, start it:
```bash
cd /Users/vitalii/Documents/Projects/n8n
npm start
```

### 2. Access n8n Dashboard
- **URL:** https://localhost
- **Port:** 5678 (if not using HTTPS)

### 3. Verify Workflows Imported
In n8n Dashboard, go to **Workflows** section. You should see:
- ✅ B2B Email Nurture Sequence (ACTIVE)
- ✅ Google Ads Daily Monitor (ACTIVE)
- 📋 Google Merchant Center Feed Upload (draft)
- 📋 Competitor Price Monitor (draft)
- 📋 Weekly Business Report (draft)

If workflows are missing:
```bash
# Restart n8n completely
killall node
cd /Users/vitalii/Documents/Projects/n8n && npm start &
```

---

## ⚙️ Configuration Required

### Google Sheets Setup
1. Create a Google Sheet with these tabs:
   - `B2B_Contacts` - Column headers: email, name, company, status, signup_date
   - `Daily_Performance` - For Google Ads Script output
   - `GA4_Weekly` - For GA4 analytics data

2. Share the sheet with your Google service account email (if using OAuth)

3. Get the Sheet ID from URL:
   - URL: `https://docs.google.com/spreadsheets/d/1fwwBYDj37JYB_s1Yk9zhqHPTsUN6xJDXh4yEyzZSx2s/...`
   - ID: `1fwwBYDj37JYB_s1Yk9zhqHPTsUN6xJDXh4yEyzZSx2s`

### Google Ads Scripts Deployment
1. Go to **Google Ads Account**
2. **Tools & Settings** → **Scripts** (under "Account-level settings")
3. Create new script for each file:
   - Copy code from `ads-scripts/1_negative_keywords.gs`
   - Click "Schedule" and set to run **Daily at 1 AM**
   - Repeat for scripts 2 and 3

4. Before running, set Script Properties:
   - Click "⚙️ Project Settings"
   - Add property: `performance_sheet_id` = your Google Sheet ID
   - Add property: `reports_sheet_id` = your Google Sheet ID

### Monster Webby Cart Tracking
1. Go to **Monster Webby Admin Dashboard**
2. **Settings** → **Third-party code** or **Custom JavaScript**
3. Paste code from `snippets/cart_webhook.js`
4. **UPDATE** the webhook URL:
   ```javascript
   const WEBHOOK_URL = 'https://your-n8n-instance.com/webhook/cart-events';
   ```
5. Save

---

## 📧 B2B Email Sequence Details

Automated emails sent via SendPulse on these days after signup:

| Day | Subject | Content |
|-----|---------|---------|
| 0 | 🎁 Кристалік: прайс та умови оптових знижок | Price list, wholesale terms |
| 3 | ⭐ ТОП-10 бестселерів місяця | Best sellers with photos |
| 7 | 💰 Як салон заробив 15,000 грн | Success story / case study |
| 14 | 🎉 СПЕЦПРОПОЗИЦІЯ: -3% на перший заказ | First order discount |
| 30 | 🚀 Нова колекція весни! | New collection announcement |

**Requirement:** Google Sheet must have these columns:
- `email` - Contact email
- `name` - Contact name
- `company` - Company name
- `status` - One of: new, contacted, replied, customer, inactive
- `signup_date` - Date contact was added (ISO format: YYYY-MM-DD)

---

## 📊 Monitoring & Alerts

### Google Ads Daily Monitor
**Triggers:** Daily at 9:00 AM UTC

Sends Telegram alerts for:
- 🔴 **Critical:** CPA > 150₴, zero conversions after 50 clicks
- ⚠️ **Warning:** CTR < 0.5% after 200 impressions, High CPC

Telegram Chat ID: `375672051`

### Competitor Price Monitor
**Triggers:** Weekly on Wednesday

Compares your base product prices with competitors:
- 🔴 **CRITICAL:** Competitors 20%+ cheaper
- ⚠️ **WARNING:** Competitors slightly cheaper

---

## 🔑 API Keys & Credentials (Already Configured)

These are already set up in n8n:

| Service | Credential | Status |
|---------|-----------|--------|
| SendPulse | API ID + Secret | ✅ Configured |
| Telegram | Bot Token | ✅ Configured |
| Google Sheets | OAuth2 | ✅ Configured |
| Google Ads API | (via Scripts) | ✅ Ready to use |

---

## 🧪 Testing

### Test B2B Email Workflow
1. Go to n8n Dashboard
2. Open **"B2B Email Nurture Sequence"** workflow
3. Click **"Test Workflow"** button
4. Check:
   - Email logs in SendPulse
   - Telegram notification in @kristallik_accessories_bot

### Test Google Ads Monitor
1. Open **"Google Ads Daily Monitor"** workflow
2. Click **"Test Workflow"**
3. Should send Telegram message with keyword analysis

### Test Google Ads Scripts (Preview Mode)
1. Go to **Google Ads Scripts**
2. Click "Preview" (don't run yet)
3. Check logs for errors
4. Once verified, schedule for daily run

---

## 📁 File Structure

```
/Users/vitalii/Documents/Projects/google/
├── 1_ads_daily_monitor.json              # Active workflow
├── 2_b2b_email_nurture.json              # Active workflow
├── 3_merchant_feed.json                  # Draft workflow
├── 4_competitor_monitor.json             # Draft workflow
├── 5_weekly_report.json                  # Draft workflow
├── ads-scripts/
│   ├── 1_negative_keywords.gs            # Google Apps Script
│   ├── 2_placement_exclusions.gs         # Google Apps Script
│   └── 3_performance_report.gs           # Google Apps Script
├── snippets/
│   └── cart_webhook.js                   # Monster Webby code
├── n8n_setup_correct.py                  # DB setup script (already run)
├── import_remaining_workflows.py          # DB import script (already run)
└── README.md                              # This file
```

---

## 🔧 Troubleshooting

### Workflows not visible in n8n UI
```bash
# 1. Check database
sqlite3 /Users/vitalii/.n8n/database.sqlite "SELECT name, active FROM workflow_entity;"

# 2. Restart n8n
killall node
cd /Users/vitalii/Documents/Projects/n8n && npm start &

# 3. Wait 30 seconds and refresh https://localhost
```

### Emails not sending
1. Verify SendPulse API keys are correct:
   ```bash
   sqlite3 /Users/vitalii/.n8n/database.sqlite \
     "SELECT name, data FROM credentials_entity WHERE name LIKE 'sendpulse%';"
   ```
2. Check SendPulse account for blocked emails
3. Verify Google Sheet "B2B_Contacts" has correct column headers

### Google Ads Scripts not running
1. Verify you added script to Google Ads account (not Google Analytics)
2. Check "Scripts" section shows "Successful runs"
3. Look at script logs for errors
4. Verify Google Sheet ID in Script Properties

---

## 📈 Performance Expectations

**Goal:** Increase orders from 50+/month to 100+/month

**From B2B Email Nurture:**
- 355 contacts × 15-20% conversion rate = 50-70 new orders/month
- Average order value: 1500+ UAH
- Expected revenue: 75,000-105,000 UAH/month

**From Google Ads optimization:**
- Remove 20-30% wasted budget (low-performing keywords)
- Save: ~3,000-5,000 UAH/month
- Improve ROAS from ~1.5x to ~2.5x

---

## 📞 Support & Next Steps

1. **Activate B2B Email:** After testing, set workflow to "Active" for real sending
2. **Setup Google Ads Scripts:** Copy to Google Ads account and schedule
3. **Monitor Performance:** Check Telegram alerts daily
4. **Weekly Reviews:** Use Weekly Report for business review
5. **Optimize:** Adjust email templates based on open/click rates

For questions or issues, check workflow logs in n8n Dashboard:
- Click workflow → "Executions" tab
- View detailed logs of each run

---

**Last updated:** 2026-03-10
**Status:** System initialized, ready for production
