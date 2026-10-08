# -*- coding: utf-8 -*-
"""OSF/PsyArXiv preprint download P1-P10 via osf.io/{guid}/download with retries."""
import csv, os, re, time
import requests

BASE = r"D:\Software\DSH\LiYing"
PDF = f"{BASE}\\pdfs"
os.makedirs(PDF, exist_ok=True)
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
rows = {r["id"]: r for r in csv.DictReader(open(f"{BASE}/papers_list.csv", encoding="utf-8-sig"))}

def fname(row, year):
    t = re.sub(r"[^\w]", "_", f"{year}_LiYing_{row['jr']}_{row['short']}_{row['cn']}")
    return re.sub(r"_+", "_", t) + ".pdf"

def is_pdf(b):
    return b[:4] == b"%PDF"

def try_guid(guid):
    for attempt in range(4):
        try:
            r = requests.get(f"https://osf.io/{guid}/download", headers=H, timeout=240, allow_redirects=True)
            if r.status_code == 200 and is_pdf(r.content):
                return r.content
            if r.status_code in (410, 404):
                return None  # file gone for this guid, try next guid
        except Exception:
            pass
        time.sleep(5)
    return False  # exhausted retries (transient errors)

# guids to try per id, in order
GUIDS = {
    "P1": ["8vqhm"], "P2": ["r6tvh"], "P3": ["9dfep"], "P4": ["zxhde"],
    "P5": ["x7ft3"], "P6": ["8gvr2"], "P7": ["frvta"], "P8": ["tgeqm"],
    "P9": ["m2k67_v1", "m2k67"], "P10": ["yzufb_v1", "yzufb"],
}

for rid, guids in GUIDS.items():
    row = rows[rid]
    year = int(row["year"])
    path = f"{PDF}\\{fname(row, year)}"
    if os.path.exists(path) and is_pdf(open(path, "rb").read(100)):
        print(f"{rid:4s} SKIP already downloaded", flush=True)
        continue
    done = False
    for g in guids:
        res = try_guid(g)
        if res is None:
            print(f"{rid:4s} {g}: no file, trying next", flush=True)
            continue
        if res is False:
            print(f"{rid:4s} {g}: retries exhausted", flush=True)
            continue
        open(path, "wb").write(res)
        print(f"{rid:4s} OK {os.path.getsize(path)//1024}KB {g}", flush=True)
        done = True
        break
    if not done:
        print(f"{rid:4s} FAIL", flush=True)
    time.sleep(2)
