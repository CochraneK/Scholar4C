# -*- coding: utf-8 -*-
"""Rename AbleSci DOI-named PDFs to standard convention + verify all PDFs.
Standard name: {YYYY}_LiYing_{jr}_{short}_{cn}.pdf (year/jr/short/cn from papers_list.csv)
"""
import csv, os, re, shutil, sys

BASE = r"D:\Software\DSH\LiYing"
PDF = os.path.join(BASE, "pdfs")
os.makedirs(os.path.join(BASE, "reports"), exist_ok=True)

rows = list(csv.DictReader(open(os.path.join(BASE, "papers_list.csv"), encoding="utf-8-sig")))
by_doi = {r["doi"].strip().lower(): r for r in rows if r.get("doi") and r["doi"].strip()}

def std_name(row):
    t = f"{row['year']}_LiYing_{row['jr']}_{row['short']}_{row['cn']}"
    return re.sub(r"_+", "_", re.sub(r"[^\w]", "_", t)) + ".pdf"

def is_pdf(path):
    try:
        with open(path, "rb") as f:
            return f.read(5) == b"%PDF-"
    except OSError:
        return False

renamed, already, bad = [], [], []
seen = set()
for row in rows:
    doi = (row.get("doi") or "").strip()
    if not doi:
        continue
    doi_fn = doi.replace("/", "_") + ".pdf"
    p = os.path.join(PDF, doi_fn)
    if os.path.exists(p):
        seen.add(doi_fn)
        if not is_pdf(p):
            bad.append(doi_fn)
            continue
        target = os.path.join(PDF, std_name(row))
        if os.path.abspath(target) == os.path.abspath(p):
            already.append(doi_fn)
            continue
        if os.path.exists(target):
            print(f"CONFLICT keep existing: {target} | remove {doi_fn}")
            os.remove(p)
            continue
        shutil.move(p, target)
        renamed.append((doi_fn, os.path.basename(target)))
for fn in sorted(os.listdir(PDF)):
    if fn.lower().endswith(".pdf") and fn not in seen:
        already.append(fn) if is_pdf(os.path.join(PDF, fn)) else bad.append(fn)

print(f"\nrenamed={len(renamed)} standard_ok={len(already)} invalid_pdf={len(bad)}")
for a, b in renamed:
    print(f"  {a}  ->  {b}")
for b in bad:
    print(f"  BAD: {b}")

# coverage report: which manifest entries have a file
have = set(os.listdir(PDF))
lines = ["| id | year | type | short | 状态 | 文件 |",
         "|---|---|---|---|---|---|"]
for r in rows:
    if (r.get("oa_status") or "").strip() == "EXCLUDE" or r.get("notes", "").startswith("EXCLUDE"):
        continue
    n = std_name(r)
    ok = n in have
    lines.append(f"| {r['id']} | {r['year']} | {r['type']} | {r['short']} | {'OK' if ok else 'MISSING'} | {n if ok else '-'} |")
open(os.path.join(BASE, "reports", "coverage.md"), "w", encoding="utf-8").write(
    "# LiYing 论文 PDF 覆盖核对\n\n生成: 2026-09-29 | 标准命名: {YYYY}_LiYing_{jr}_{short}_{cn}.pdf\n\n"
    + "\n".join(lines) + "\n")
excl = lambda r: (r.get("oa_status") or "").strip() == "EXCLUDE" or r.get("notes", "").startswith("EXCLUDE")
missing = [r["id"] for r in rows if not excl(r) and std_name(r) not in have]
print("\nmissing ids:", missing if missing else "none")
print("coverage report -> reports/coverage.md")
