# -*- coding: utf-8 -*-
"""P9 (m2k67) retry: probe psyarxiv.com page for PDF link + retry OSF guids."""
import re, time
import requests

H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
OUT = r"D:\Software\DSH\LiYing\pdfs\2023_LiYing_PsyArXiv_AnxietyTextAnalysisPreprint_认知网络与文本分析识别焦虑预印本.pdf"

def is_pdf(b):
    return b[:4] == b"%PDF"

def try_url(url, label):
    for attempt in range(3):
        try:
            r = requests.get(url, headers=H, timeout=180, allow_redirects=True)
            if r.status_code == 200 and is_pdf(r.content):
                with open(OUT, "wb") as f:
                    f.write(r.content)
                print(f"OK {label} {len(r.content)//1024}KB -> {OUT}")
                return True
            print(f"{label}: HTTP {r.status_code}, {len(r.content)} bytes, ct={r.headers.get('content-type','')[:40]}")
            if r.status_code in (404, 410):
                return False
        except Exception as e:
            print(f"{label}: {type(e).__name__}: {str(e)[:100]}")
        time.sleep(6)
    return False

# 1) probe psyarxiv page for direct pdf links
try:
    r = requests.get("https://psyarxiv.com/m2k67/", headers=H, timeout=60)
    print("psyarxiv page:", r.status_code)
    if r.status_code == 200:
        links = re.findall(r'href="([^"]*(?:pdf|download)[^"]*)"', r.text, re.I)
        print("candidate links:", links[:10])
        for l in links[:5]:
            if try_url(l, "page:" + l[:60]):
                raise SystemExit(0)
except SystemExit:
    raise
except Exception as e:
    print("psyarxiv probe failed:", type(e).__name__, str(e)[:100])

# 2) retry OSF guids
for g in ["m2k67_v1", "m2k67"]:
    if try_url(f"https://osf.io/{g}/download", f"osf:{g}"):
        raise SystemExit(0)

print("P9 still unavailable (content covered by J15 journal version)")
