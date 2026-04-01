import urllib.request, re

# Zhipu pricing
urls = [
    'https://open.bigmodel.cn/dev/howard/price',
    'https://open.bigmodel.cn/api/glm-pricing',
]
for url in urls:
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            text = r.read().decode('utf-8', errors='ignore')
        for m in re.findall(r'GLM[^<>"\n]{0,150}', text):
            s = re.sub('<[^>]+>', '', m).strip()
            if s and len(s) > 10:
                print(s[:150])
    except Exception as e:
        print('Error:', e)
