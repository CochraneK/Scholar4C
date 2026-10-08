# -*- coding: utf-8 -*-
"""Sci-Hub pass for non-OA journals: J3, J5, J8 (and J12 if still missing)."""
import csv, json, os, re, time, random
import requests

BASE = r"D:\Software\DSH\LiYing"
PDF = f"{BASE}\\pdfs"
os.makedirs(PDF, exist_ok=True)
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
meta = json.load(open(f"{BASE}/papers_meta.json", encoding="utf-8"))
rows = {r["id"]: r for r in csv.DictReader(open(f"{BASE}/papers_list.csv", encoding="utf-8-sig"))}

def fname(row, year):
    t = re.sub(r"[^\w]", "_", f"{year}_LiYing_{row['jr']}_{row['short']}_{row['cn']}")
    return re.sub(r"_+", "_", t) + ".pdf"

def is_pdf(b):
    return b[:4] == b"%PDF"

targets = [r for r in ["J2", "J3", "J4", "J5", "J8", "J10", "J12", "J13"]
           if r in rows and rows[r]["type"] == "journal"]
for rid in targets:
    row = rows[rid]
    year = int(row["year"])
    path = f"{PDF}\\{fname(row, year)}"
    if os.path.exists(path) and is_pdf(open(path, "rb").read(100)):
        print(f"{rid:4s} SKIP already downloaded", flush=True)
        continue
    ok = False
    for attempt in range(2):
        try:
            r = requests.get(f"https://sci.bban.top/pdf/{row['doi']}", headers=H, timeout=90)
            if r.status_code == 200 and is_pdf(r.content):
                open(path, "wb").write(r.content)
                print(f"{rid:4s} OK {os.path.getsize(path)//1024}KB sci.bban.top", flush=True)
                ok = True
                break
            else:
                print(f"{rid:4s} attempt{attempt+1} http {r.status_code}", flush=True)
        except Exception as e:
            print(f"{rid:4s} attempt{attempt+1} {e.__class__.__name__}", flush=True)
        time.sleep(random.uniform(4, 7))
    if not ok:
        print(f"{rid:4s} FAIL", flush=True)
    time.sleep(random.uniform(4, 7))
