# -*- coding: utf-8 -*-
"""OA-layer download: Europe PMC -> Crossref OA links -> publisher direct.
Downloads journals J1-J13 (excl. J14) + ResearchSquare P11.
Output: D:\\Software\\DSH\\LiYing\\pdfs\\
"""
import csv, json, os, re, time
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

def save(row, year, content, src):
    if not is_pdf(content):
        return f"NOT_PDF({src}, {len(content)}b)"
    p = f"{PDF}\\{fname(row, year)}"
    open(p, "wb").write(content)
    return f"OK {os.path.getsize(p)//1024}KB {src}"

def try_epmc(doi):
    r = requests.get("https://www.ebi.ac.uk/europepmc/webservices/rest/search",
                     params={"query": f"DOI:{doi}", "format": "json"}, headers=H, timeout=30)
    res = r.json()["resultList"]["result"]
    if not res:
        return None
    d = res[0]
    pmcid = d.get("pmcid")  # e.g. PMC7890123 (keep full prefix)
    if not pmcid:
        return None
    u = f"https://europepmc.org/backend/ptpmcrender.fcgi?accid={pmcid}&blobtype=pdf"
    r2 = requests.get(u, headers=H, timeout=60)
    if r2.status_code == 200 and is_pdf(r2.content):
        return r2.content
    return None

def try_crossref(row_id):
    links = meta.get(row_id, {}).get("links_all", []) or meta.get(row_id, {}).get("oa_pdf_links", [])
    for u in links:
        cands = [u]
        if "frontiersin.org" in u and u.endswith("/full"):
            cands.append(u[:-4] + "pdf")
        for c in cands:
            try:
                r = requests.get(c, headers=H, timeout=90, allow_redirects=True)
                if r.status_code == 200 and is_pdf(r.content):
                    return r.content
            except Exception:
                pass
    return None

def try_direct(row_id):
    doi = rows[row_id]["doi"]
    candidates = {
        "10.3390": f"https://www.mdpi.com/{doi.split('.')[1].replace('bdcc','2411-51X')}/{doi}",
        "10.3389": f"https://www.frontiersin.org/journals/psychology/articles/{doi.split('.')[-1]}/pdf",
    }
    for prefix, u in candidates.items():
        if doi.startswith(prefix):
            try:
                r = requests.get(u, headers=H, timeout=60)
                if r.status_code == 200 and is_pdf(r.content):
                    return r.content
            except Exception:
                pass
    return None

def try_rs(row_id):
    # ResearchSquare: follow DOI redirect, look for pdf link
    try:
        r = requests.get("https://doi.org/" + rows[row_id]["doi"], headers=H, timeout=60, allow_redirects=True)
        m = re.search(rb'href="([^"]*?\.pdf[^"]*)"', r.content)
        if m:
            u = m.group(1).decode()
            if u.startswith("/"):
                u = "https://www.researchsquare.com" + u
            r2 = requests.get(u, headers=H, timeout=120)
            if is_pdf(r2.content):
                return r2.content
    except Exception:
        pass
    return None

def download(row_id):
    row = rows[row_id]
    year = int(row["year"])
    if os.path.exists(f"{PDF}\\{fname(row, year)}") and is_pdf(open(f"{PDF}\\{fname(row, year)}", "rb").read(100)):
        return "SKIP already downloaded"
    if row["type"] == "journal":
        for fn, name in [(try_epmc, "EPMC"), (lambda d: try_crossref(row_id), "Crossref"), (lambda d: try_direct(row_id), "Direct")]:
            try:
                c = fn(row["doi"]) if fn is try_epmc else fn(row["doi"])
            except Exception:
                c = None
            if c:
                return save(row, year, c, name)
    else:  # P11 researchsquare
        try:
            c = try_rs(row_id)
        except Exception:
            c = None
        if c:
            return save(row, year, c, "RS")
    return "FAIL"

ids = [r for r in rows if rows[r]["oa_status"] in ("OA", "unknown") and rows[r]["type"] in ("journal", "preprint") and rows[r]["id"] != "J14"]
ids = [r for r in ids if not r.startswith("P") or r == "P11"]  # journals + P11 only
for i, rid in enumerate(ids):
    res = download(rid)
    print(f"{rid:4s} {res}", flush=True)
    time.sleep(2)
