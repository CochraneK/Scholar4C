# -*- coding: utf-8 -*-
"""Resolve Crossref metadata for each DOI in papers_list.csv -> papers_meta.json"""
import csv, json, time, requests

BASE = r"D:\Software\DSH\LiYing"
H = {"User-Agent": "liying-paper-collection/1.0 (research use)"}
rows = list(csv.DictReader(open(f"{BASE}/papers_list.csv", encoding="utf-8-sig")))

out = {}
for r in rows:
    doi = r["doi"].strip()
    r["year"] = int(r["year"])
    if not doi:
        out[r["id"]] = {"id": r["id"], "status": "no_doi", "doi": ""}
        continue
    try:
        resp = requests.get(f"https://api.crossref.org/works/{doi}", headers=H, timeout=30)
        if resp.status_code != 200:
            out[r["id"]] = {"id": r["id"], "status": f"crossref_{resp.status_code}", "doi": doi}
            time.sleep(1)
            continue
        m = resp.json()["message"]
        year = (m.get("issued", {}).get("date-parts", [[0]])[0] or [0])[0]
        title = (m.get("title") or ["?"])[0]
        jr = (m.get("container-title") or ["?"])[0]
        authors = [{"family": a.get("family", ""), "given": a.get("given", "")}
                   for a in m.get("author", [])]
        oa = [l.get("URL", "") for l in m.get("link", []) if l.get("content-type", "").startswith("application/pdf")]
        out[r["id"]] = {"id": r["id"], "status": "ok", "doi": doi,
                        "year": year, "title": title, "journal": jr,
                        "authors": authors, "oa_pdf_links": oa,
                        "ref": m.get("is-referenced-by-count", 0)}
    except Exception as e:
        out[r["id"]] = {"id": r["id"], "status": f"error:{e.__class__.__name__}", "doi": doi}
    time.sleep(1)

json.dump(out, open(f"{BASE}/papers_meta.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

# compact report
for k in sorted(out, key=lambda x: (out[x]["id"][0], int(out[x]["id"][1:]))):
    o = out[k]
    if o["status"] == "ok":
        a0 = o["authors"][0] if o["authors"] else {}
        print(f"{k:4s} {o['year']} {a0.get('family','?'):14s} | {o['title'][:70]} | {o['journal'][:30]} | OA:{len(o['oa_pdf_links'])}")
    else:
        print(f"{k:4s} -- {o['status']} {o.get('doi','')}")
