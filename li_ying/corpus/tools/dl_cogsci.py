# -*- coding: utf-8 -*-
"""Download CogSci 2016-2018 conference papers C1-C4 from escholarship."""
import csv, os, re, time
import requests

BASE = r"D:\Software\DSH\LiYing"
PDF = f"{BASE}\\pdfs"
os.makedirs(PDF, exist_ok=True)
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
rows = {r["id"]: r for r in csv.DictReader(open(f"{BASE}/papers_list.csv", encoding="utf-8-sig"))}

ITEMS = {"C1": "67k8k2jr", "C2": "14n2d5tz", "C3": "2tc6m2s4", "C4": "0bm5z6hn"}

def fname(row):
    t = re.sub(r"[^\w]", "_", f"{row['year']}_LiYing_{row['jr']}_{row['short']}_{row['cn']}")
    return re.sub(r"_+", "_", t) + ".pdf"

def is_pdf(b):
    return b[:4] == b"%PDF"

for cid, item in ITEMS.items():
    row = rows[cid]
    path = f"{PDF}\\{fname(row)}"
    if os.path.exists(path) and is_pdf(open(path, "rb").read(100)):
        print(f"{cid} SKIP", flush=True)
        continue
    urls = [
        f"https://escholarship.org/content/{item}/{item}.pdf",
        f"https://escholarship.org/content/qt{item}/qt{item}.pdf",
    ]
    # also try to scrape item page for the real content id
    try:
        r = requests.get(f"https://escholarship.org/uc/item/{item}", headers=H, timeout=30)
        m = re.findall(r'content/([a-z0-9]+)/[a-z0-9]+\.pdf', r.text)
        for c in dict.fromkeys(m):
            urls.insert(0, f"https://escholarship.org/content/{c}/{c}.pdf")
    except Exception as e:
        print(f"{cid} page scrape {e.__class__.__name__}", flush=True)
    ok = False
    for u in urls:
        try:
            r = requests.get(u, headers=H, timeout=120, allow_redirects=True)
            if r.status_code == 200 and is_pdf(r.content):
                open(path, "wb").write(r.content)
                print(f"{cid} OK {os.path.getsize(path)//1024}KB {u.split('/')[-1]}", flush=True)
                ok = True
                break
        except Exception as e:
            print(f"{cid} {u[-40:]} {e.__class__.__name__}", flush=True)
    if not ok:
        print(f"{cid} FAIL", flush=True)
    time.sleep(1)
