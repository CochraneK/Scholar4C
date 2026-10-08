# -*- coding: utf-8 -*-
"""李赢论文科学计量分析: 读 papers_list.csv + papers_meta.json
-> 统计(年度/期刊/署名层级/合著网络/阶段/OA) + OpenAlex 引文
-> 写 analysis/analysis_data.json (及 analysis/openalex_citations.json 缓存)
"""
import csv, json, os, time, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.join(ROOT, "analysis")
os.makedirs(BASE, exist_ok=True)

# ---------- load ----------
rows = []
with open(os.path.join(ROOT, "papers_list.csv"), encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        rows.append(r)
meta = json.load(open(os.path.join(ROOT, "papers_meta.json"), encoding="utf-8"))
meta_by_id = {v.get("id"): v for v in meta.values()} if isinstance(meta, dict) else {}
if not meta_by_id:  # maybe list
    meta_by_id = {v.get("id"): v for v in meta}

valid = [r for r in rows if not r.get("notes", "").startswith("已排除")
         and r.get("type") != "EXCLUDE"]
excluded = [r for r in rows if r not in valid]

# ---------- basic ----------
years = sorted(int(r["year"]) for r in valid)
by_year = {}
for r in valid:
    by_year[r["year"]] = by_year.get(r["year"], 0) + 1
cum, c = [], 0
for y in range(min(years), max(years) + 1):
    c += by_year.get(str(y), 0)
    cum.append({"year": int(y), "count": c})

journals = {}
for r in valid:
    if r["type"] in ("journal", "conference"):
        journals[r["jr"]] = journals.get(r["jr"], 0) + 1

types = {}
for r in valid:
    types[r["type"]] = types.get(r["type"], 0) + 1

oa = sum(1 for r in valid if r["oa_status"] == "OA")

# ---------- phases ----------
def phase(r):
    y = int(r["year"])
    if y <= 2019: return "博士(华威 2016-2019)"
    if y <= 2022: return "博后(MPICH 2020-2022)"
    return "心理所(2023-2026)"
phases = {}
for r in valid:
    phases[phase(r)] = phases.get(phase(r), 0) + 1

# ---------- authorship ----------
def is_li(x):
    f, g = x.get("family", "").lower(), x.get("given", "").lower()
    return (f == "li" and g.startswith("ying")) or (f == "ying" and g.split()[0] == "li")

def disp(x):
    f, g = x.get("family", "").strip(), x.get("given", "").strip()
    return (f"{g} {f}".strip() if g else f)

CANON = {
    "Thomas T. Hills": "Thomas Hills", "Tomas Trenholm Hills": "Thomas Hills",
    "Trevor J. Swanson": "Trevor Swanson", "Andreia S. Teixeira": "Andreia Sofia Teixeira",
    "Chenran Shen‐Zhang": "Chenran Shen-Zhang", "Chenran Shen-Zhang": "Chenran Shen-Zhang",
    "Chenran Shengzhang": "Chenran Shen-Zhang",
}
def canon(n):
    n = n.replace("University of Warwick", "").strip()
    return CANON.get(n, n)

MANUAL = {  # meta 缺失的条目, 作者列表来自 CSV notes / 同文 preprint
    "C1": ["Annasya Masitah", "Ying Li", "Thomas T. Hills"],
    "C2": ["Annasya Masitah", "Ying Li", "Thomas T. Hills"],
    "C3": ["Ying Li", "Thomas T. Hills"],
    "C4": ["Ying Li", "Thomas T. Hills"],
    "J16": ["Ying Li", "Wenjia Joyce Zhao", "Shenghua Luan", "Ziyong Lin",
            "Jun Fang", "Chenran Shen-Zhang", "Mingyi Chen", "Thomas Hills"],
    "T1": ["Ying Li"],
}

def full_author_list(r):
    m = meta_by_id.get(r["id"])
    if m and m.get("authors"):
        return [disp(x) for x in m["authors"]]
    return MANUAL.get(r["id"])

auth = {}
for r in valid:
    names = full_author_list(r)
    if not names:
        continue
    pos = None
    for i, x in enumerate(meta_by_id.get(r["id"], {}).get("authors", []) if (meta_by_id.get(r["id"]) or {}).get("authors") else []):
        if is_li(x):
            pos = i; break
    if pos is None:  # manual entries: find by display name
        for i, n in enumerate(names):
            if n.strip().lower() in ("ying li", "li ying"):
                pos = i; break
    if pos is None:
        continue
    co = [canon(n) for n in names if not (n.strip().lower() in ("ying li", "li ying"))]
    role = "first" if pos == 0 else ("last" if pos == len(names) - 1 else "middle")
    if role == "middle" and pos == len(names) - 2 and len(names) <= 3:
        role = "second"
    auth[r["id"]] = {"role": role, "position": pos + 1, "n_authors": len(names),
                     "coauthors": co}
role_cnt = {}
for v in auth.values():
    role_cnt[v["role"]] = role_cnt.get(v["role"], 0) + 1
auth_by_year = {}
for r in valid:
    v = auth.get(r["id"])
    if not v: continue
    k = r["year"]
    d = auth_by_year.setdefault(k, {"first":0,"last":0,"middle":0,"second":0})
    d[v["role"]] += 1

# ---------- coauthor network (与 Li Ying 共同发表篇数) ----------
cofreq = {}
for r in valid:
    names = full_author_list(r)
    if not names: continue
    for n in {canon(n) for n in names if n.strip().lower() not in ("ying li", "li ying")}:
        cofreq[n] = cofreq.get(n, 0) + 1
top_co = sorted(cofreq.items(), key=lambda kv: -kv[1])
top_li_pairs = top_co[:12]

# ---------- openalex citations ----------
cache_f = os.path.join(BASE, "openalex_citations.json")
cache = {}
if os.path.exists(cache_f):
    cache = json.load(open(cache_f, encoding="utf-8"))
fetch = []
for r in valid:
    doi = (r.get("doi") or "").strip()
    if doi and doi not in cache:
        fetch.append((r["id"], doi))
for i, (pid, doi) in enumerate(fetch):
    url = "https://api.openalex.org/works/doi:" + urllib.request.quote(doi, safe="")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "LiYing-metrics/1.0 (personal research)"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            w = json.load(resp)
        cache[doi] = {"cited_by_count": w.get("cited_by_count"),
                      "display_name": w.get("display_name")}
    except Exception as e:
        cache[doi] = {"cited_by_count": None, "error": str(e)[:80]}
    time.sleep(0.4)
json.dump(cache, open(cache_f, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

cit = {}
for r in valid:
    doi = (r.get("doi") or "").strip()
    if doi and doi in cache:
        cit[r["id"]] = cache[doi].get("cited_by_count")
cited = [v for v in cit.values() if isinstance(v, int)]
h = 0
for c_ in sorted(cited, reverse=True):
    if c_ >= h + 1: h += 1

# ---------- output ----------
out = {
    "generated": time.strftime("%Y-%m-%d %H:%M"),
    "total_valid": len(valid),
    "excluded": [r["id"] for r in excluded],
    "year_range": f"{min(years)}-{max(years)}",
    "types": types,
    "oa_count": oa,
    "oa_pct": round(100.0 * oa / len(valid), 1),
    "num_journals": len(journals),
    "year_distribution": [{"year": int(y), "count": n} for y, n in sorted(by_year.items())],
    "cumulative": cum,
    "top_journals": sorted([{"journal": k, "count": v} for k, v in journals.items()], key=lambda x: -x["count"]),
    "phases": phases,
    "authorship": {
        "analyzed": len(auth),
        "role_counts": role_cnt,
        "by_paper": {k: v for k, v in sorted(auth.items())},
        "by_year": {k: auth_by_year[k] for k in sorted(auth_by_year)},
    },
    "coauthors": {
        "top": [{"name": n, "count": c} for n, c in top_co[:15]],
        "li_top_pairs": [{"pair": k, "count": v} for k, v in top_li_pairs],
        "n_unique_coauthors": len(cofreq),
    },
    "citations": {"fetched": sum(1 for v in cit.values() if isinstance(v, int)),
                  "total_cited": sum(cited), "h_index": h,
                  "by_paper": {k: v for k, v in sorted(cit.items())}},
}
json.dump(out, open(os.path.join(BASE, "analysis_data.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("total_valid", len(valid), "| years", out["year_range"],
      "| journals", len(journals), "| oa", out["oa_pct"],
      "| auth_analyzed", len(auth), "| roles", role_cnt,
      "| h", h, "| cited_total", sum(cited))
print("meta_missing:", [r["id"] for r in valid if r["id"] not in meta_by_id])
