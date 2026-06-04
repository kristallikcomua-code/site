#!/usr/bin/env python3
import requests, yaml, json

with open('/Users/vitalii/Documents/Projects/google/google-ads-config.yaml') as f:
    cfg = yaml.safe_load(f)

r = requests.post('https://oauth2.googleapis.com/token', data={
    'client_id': cfg['client_id'], 'client_secret': cfg['client_secret'],
    'refresh_token': cfg['refresh_token'], 'grant_type': 'refresh_token'
})
token = r.json()['access_token']
headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
acc = '6059731376'; cont = '95104925'; ws = '22'

# Get current tag 38
r = requests.get(
    f'https://tagmanager.googleapis.com/tagmanager/v2/accounts/{acc}/containers/{cont}/workspaces/{ws}/tags/38',
    headers=headers
)
tag = r.json()
fingerprint = tag['fingerprint']

new_js = """<script>
(function() {
  // Only fire on thank-you page — the single canonical purchase point
  if (!window.location.pathname.includes('/shopping/finish/')) return;

  // Deduplicate across navigations using sessionStorage
  var key = 'krist_purchase_' + window.location.search;
  if (sessionStorage.getItem(key)) return;

  var fired = false;

  function parseUAH(text) {
    // Ukrainian format: "1 845,99 grn" — space=thousands separator, comma=decimal
    var s = (text || '').replace(/\\s/g, '').replace(',', '.').replace(/[^\\d.]/g, '');
    return parseFloat(s) || 0;
  }

  function getOrderValue() {
    var selectors = ['.total-coast .value', '.total-coast', '[class*="total"] .value'];
    for (var i = 0; i < selectors.length; i++) {
      var el = document.querySelector(selectors[i]);
      if (el) {
        var val = parseUAH(el.textContent);
        if (val > 0) return val;
      }
    }
    return 0;
  }

  function firePurchase() {
    if (fired) return;
    var val = getOrderValue();
    if (val <= 0) return;
    fired = true;
    sessionStorage.setItem(key, '1');
    window.dataLayer = window.dataLayer || [];
    window.dataLayer.push({
      event: 'purchase_completed',
      orderValue: val,
      transactionId: 'ord_' + Date.now(),
      currency: 'UAH'
    });
  }

  // Retry until DOM value appears (max 3 seconds)
  var attempts = 0;
  var timer = setInterval(function() {
    firePurchase();
    if (fired || ++attempts >= 10) clearInterval(timer);
  }, 300);
})();
</script>"""

# Rebuild payload
payload = {
    'name': tag['name'],
    'type': tag['type'],
    'parameter': [],
    'firingTriggerId': tag['firingTriggerId'],
    'tagFiringOption': tag.get('tagFiringOption', 'oncePerEvent'),
    'fingerprint': fingerprint,
}
for p in tag['parameter']:
    if p['key'] == 'html':
        payload['parameter'].append({'type': 'template', 'key': 'html', 'value': new_js})
    else:
        payload['parameter'].append(p)

r = requests.put(
    f'https://tagmanager.googleapis.com/tagmanager/v2/accounts/{acc}/containers/{cont}/workspaces/{ws}/tags/38',
    headers=headers, json=payload
)
print(f'Update tag 38: {r.status_code}')
if r.status_code != 200:
    print(r.text[:400])
    exit()

# Also fix tag 39: remove trigger 37 (site's own purchase event)
# Keep only trigger 40 (our purchase_completed event) to avoid triple firing
r = requests.get(
    f'https://tagmanager.googleapis.com/tagmanager/v2/accounts/{acc}/containers/{cont}/workspaces/{ws}/tags/39',
    headers=headers
)
tag39 = r.json()

payload39 = {
    'name': tag39['name'],
    'type': tag39['type'],
    'parameter': tag39['parameter'],
    'firingTriggerId': ['40'],  # only purchase_completed, not site's purchase event
    'tagFiringOption': tag39.get('tagFiringOption', 'oncePerEvent'),
    'fingerprint': tag39['fingerprint'],
}
r = requests.put(
    f'https://tagmanager.googleapis.com/tagmanager/v2/accounts/{acc}/containers/{cont}/workspaces/{ws}/tags/39',
    headers=headers, json=payload39
)
print(f'Update tag 39 (remove trigger 37): {r.status_code}')
if r.status_code != 200:
    print(r.text[:400])
    exit()

# Publish workspace
r = requests.post(
    f'https://tagmanager.googleapis.com/tagmanager/v2/accounts/{acc}/containers/{cont}/workspaces/{ws}:create_version',
    headers=headers,
    json={'name': 'Fix: purchase value x100 bug + deduplicate events', 'notes': 'Fix Ukrainian number format parsing and remove duplicate trigger 37 from GA4 purchase tag'}
)
print(f'Create version: {r.status_code}')
if r.status_code == 200:
    ver = r.json().get('containerVersion', {})
    ver_id = ver.get('containerVersionId')
    print(f'Version ID: {ver_id}')

    # Publish
    r2 = requests.post(
        f'https://tagmanager.googleapis.com/tagmanager/v2/accounts/{acc}/containers/{cont}/versions/{ver_id}:publish',
        headers=headers
    )
    print(f'Publish: {r2.status_code}')
    if r2.status_code == 200:
        print('Published OK')
    else:
        print(r2.text[:400])
else:
    print(r.text[:400])
