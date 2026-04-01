import urllib.request, re

# 1. MiniMax pricing
print("=== MiniMax ===")
req = urllib.request.Request('https://www.minimaxi.com/pricing', headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req, timeout=10) as r:
    text = r.read().decode('utf-8', errors='ignore')
for m in re.findall(r'price[^}]{0,300}', text, re.I):
    s = m.strip()
    if s and len(s) > 10:
        print(re.sub('<[^>]+>', '', s)[:200])
        print()

print("\n=== 智谱 ===")
req2 = urllib.request.Request('https://open.bigmodel.cn/pricing', headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req2, timeout=10) as r:
    text2 = r.read().decode('utf-8', errors='ignore')
# Look for GLM prices
for m in re.findall(r'GLM[^<>"\n]{0,100}', text2, re.I):
    s = m.strip()
    if s and len(s) > 10:
        print(re.sub('<[^>]+>', '', s)[:200])
