# -*- coding: utf-8 -*-
"""构建李赢 (Ying Li) 论文清单 v1：Crossref + Europe PMC 双源，合著者锚点消歧。

身份锚点：
- 华威大学博士 2019（导师圈：Thomas T. Hills）
- 马普人类发展所博后 2019-2022（Ralph Hertwig, Sheng-Hwa Luan）
- 中科院心理所副研究员 2022-（栾胜华组）
- 方向：语言演化 / 情绪与心理健康 / 风险感知与决策

用法：python build_list_crossref_epmc.py
输出：tools/search/candidates.json
"""
import json
import re
import time
import requests

S = requests.Session()
S.headers["User-Agent"] = "liying-papers/0.1"
OUT = r"D:\Software\DSH\LiYing\tools\search\candidates.json"

# 合著者锚点（family 名，大小写不敏感）——她的合著者网络非常独特
ANCHORS = ["hills", "hertwig", "luan", "siew", "breithaupt", "engelthaler",
           "masitah"]
# 主题词（标题命中）
TOPIC = re.compile(
    r"\b(language|linguistic|lexical|word|words|vocabulary|semantic|semantics|"
    r"emot|affect|well[- ]?being|happiness|risk|pandemic|covid|prejudice|"
    r"outgroup|ingroup|culture|cultural|cognition|decision|judgment|judgement|"
    r"recognition|recall|concepts?|psycholog|mental health|history of)\b",
    re.I)


def norm(name):
    return re.sub(r"\s+", " ", name or "").strip().lower()


def cr_author_key(a):
    return f"{norm(a.get('family'))} {norm(a.get('given'))}"


def get_json(url, params=None, tries=4):
    for i in range(tries):
        try:
            r = S.get(url, params=params, timeout=60)
            if r.status_code == 200:
                return r.json()
            if r.status_code in (403, 429):
                time.sleep(5)
                continue
            print("  status", r.status_code, url[:100])
            return None
        except Exception as e:
            print("  err", type(e).__name__, str(e)[:80])
        time.sleep(3)
    return None


def fetch_crossref():
    """Crossref: query.author=Ying Li, 2014 起，翻页直到拿完相关结果。"""
    items, page = [], 0
    while True:
        d = get_json("https://api.crossref.org/works", {
            "query.author": "Ying Li",
            "filter": "from-pub-date:2014-01-01,type:journal-article",
            "rows": 100, "offset": page * 100,
        })
        if not d:
            break
        rs = d["message"]["items"]
        items.extend(rs)
        total = int(d["message"]["total-results"])
        page += 1
        if len(items) >= total or page >= 20 or len(rs) < 100:
            break
        time.sleep(1.2)
    print(f"[Crossref] 原始 {len(items)} 条 (total={total})")
    out = []
    for w in items:
        auths = w.get("author", [])
        names = [f"{a.get('family','')} {a.get('given','')}" for a in auths]
        keys = [cr_author_key(a) for a in auths]
        if not any(k in ("li ying", "li y.") for k in keys):
            continue
        title = (w.get("title") or [""])[0]
        src = ((w.get("container-title") or [""]))[0]
        year = (w.get("issued", {}).get("date-parts") or [[None]])[0][0]
        co = " ".join(names).lower()
        anchors_hit = [a for a in ANCHORS if a in co]
        topic_hit = bool(TOPIC.search(title))
        out.append({
            "src": "crossref",
            "doi": (w.get("DOI") or "").lower(),
            "title": title, "journal": src, "year": year,
            "authors": names,
            "anchors": anchors_hit, "topic": topic_hit,
        })
    print(f"[Crossref] 含 'Ying Li' 署名: {len(out)}")
    return out


def fetch_epmc(query, label):
    d = get_json("https://www.ebi.ac.uk/europepmc/webservices/rest/search", {
        "query": query, "format": "json", "pageSize": 1000,
    })
    if not d:
        print(f"[EPMC] {label}: 无结果")
        return []
    hits = d.get("resultList", {}).get("result", [])
    print(f"[EPMC] {label}: {len(hits)} 条")
    out = []
    for h in hits:
        astr = (h.get("authorString") or "").lower()
        anchors_hit = [a for a in ANCHORS if a in astr]
        title = h.get("title", "")
        out.append({
            "src": "europepmc",
            "doi": (h.get("doi") or "").lower(),
            "pmid": h.get("pmid"), "pmcid": h.get("pmcid"),
            "title": title,
            "journal": h.get("journalTitle", ""),
            "year": h.get("pubYear"),
            "authors": astr,
            "anchors": anchors_hit,
            "topic": bool(TOPIC.search(title)),
            "isOpenAccess": h.get("isOpenAccess"),
            "inEPMC": h.get("inEPMC"),
        })
    return out


def main():
    cands = fetch_crossref()
    epmc = []
    for anchor in ["Hills", "Hertwig", "Luan", "Siew", "Breithaupt", "Engelthaler"]:
        epmc += fetch_epmc(f'AUTH:"Ying Li" AND AUTH:"{anchor}"', f"LiYing+{anchor}")
        time.sleep(1)
    # 无锚点但主题强相关的（可能漏掉的合作者组合）
    epmc += fetch_epmc(
        'AUTH:"Ying Li" AND (TITLE:"emotional recall" OR TITLE:"semantic change" '
        'OR TITLE:"history of risk" OR TITLE:"outgroup prejudice" '
        'OR TITLE:"cognitive selection" OR TITLE:"language change" '
        'OR TITLE:"risk perception" OR TITLE:"pandemic")', "LiYing+titles")

    # 合并去重（DOI 为主，无 DOI 用标题）
    merged = {}
    for c in cands + epmc:
        key = c["doi"] if c["doi"] else ("t:" + norm(c["title"]))
        if key in merged:
            m = merged[key]
            for f in ("pmid", "pmcid", "isOpenAccess", "inEPMC", "journal", "year"):
                if not m.get(f) and c.get(f):
                    m[f] = c[f]
            m["src"] = m["src"] + "+" + c["src"]
            m["anchors"] = sorted(set(m["anchors"] + c["anchors"]))
            m["topic"] = m["topic"] or c["topic"]
        else:
            c["src"] = c["src"]
            merged[key] = c

    def yr(x):
        try:
            return int(x.get("year"))
        except (TypeError, ValueError):
            return 0

    rows = sorted(merged.values(), key=lambda x: (yr(x), x.get("title") or ""))
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)
    print(f"\n=== 合并后候选 {len(rows)} 条 ===")
    for r in rows:
        flag = "A" if r["anchors"] else ("t" if r["topic"] else "?")
        print(f"[{flag}] {r['year']} | {r['title'][:80]} | {r['journal'][:30]} | anchors={r['anchors']} | {r['doi']}")
    print(f"\nsaved -> {OUT}")


if __name__ == "__main__":
    main()
