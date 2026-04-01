import urllib.request, re

# Get Doubao model names and prices
url = 'https://www.volcengine.com/docs/82379/1544106'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req, timeout=10) as r:
    text = r.read().decode('utf-8', errors='ignore')

# Extract all model names and prices
lines = text.split('\n')
in_price_section = False
for line in lines:
    if 'doubao' in line.lower() or 'token' in line.lower() or '¥' in line or '元/' in line:
        cleaned = re.sub('<[^>]+>', '', line).strip()
        if cleaned and len(cleaned) > 3:
            print(cleaned[:200])
