# -*- coding: utf-8 -*-
"""探索李赢 (Ying Li) 的 OpenAlex 作者身份与论文。

身份锚点（来自 CAS 心理所专家页 + 百度百科）：
- 华威大学博士 2019；马普人类发展所博后 2019-2022；中科院心理所副研究员 2022-
- 代表论文：The Macroscope (2019, BRM) — 一作，合著 Hills TT
用法：python explore_liying.py
"""
import json
import sys
import requests

S = requests.Session()
S.headers["User-Agent"] = "liying-papers/0.1 (mailto:kang@example.com)"
OA = "https://api.openalex.org"


def get(url, **kw):
    r = S.get(url, timeout=60, **kw)
    r.raise_for_status()
    return r.json()


def find_author_via_macroscope():
    """通过 Macroscope 论文锁定一作 OpenAlex ID。"""
    d = get(f"{OA}/works", params={"filter": 'title.search:"the macroscope: a tool for examining the historical structure of language"'})
    results = d.get("results", [])
    print(f"Macroscope 检索: {len(results)} 条")
    for w in results:
        print("  -", w.get("display_name"), "|", w.get("publication_year"), "|", w.get("doi"))
        for a in w.get("authorships", []):
            auth = a["author"]
            insts = ",".join(i["display_name"] for i in a.get("institutions", []))
            print(f"      {auth['display_name']}  id={auth['id']}  works_count={auth.get('works_count')}  aff={insts}")
            if a.get("is_corresponding") or a.get("author_position") == "first":
                print("        ^ first/corresponding")
    return results


def author_works(author_id):
    """拉取该 OpenAlex 作者的全部 works（自动翻页）。"""
    works, page = [], 0
    while True:
        d = get(f"{OA}/works", params={
            "filter": f"authorships.author.id:{author_id}",
            "per-page": 200, "page": page + 1,
            "sort": "publication_year:asc",
            "select": "id,doi,title,publication_year,authorships,primary_location,locations,open_access,cited_by_count,type",
        })
        rs = d.get("results", [])
        works.extend(rs)
        pg = d.get("meta", {}).get("pagination", {})
        if page + 1 >= pg.get("pages", 1) or not rs:
            break
        page += 1
    return works


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "find"
    if mode == "find":
        find_author_via_macroscope()
    elif mode == "works":
        aid = sys.argv[2]
        works = author_works(aid)
        print(f"\n=== {aid} 共 {len(works)} 篇 ===")
        for w in sorted(works, key=lambda x: (x.get("publication_year") or 0, x.get("display_name") or "")):
            first = w["authorships"][0]["author"]["display_name"] if w.get("authorships") else "?"
            insts = set()
            for a in w.get("authorships", []):
                for i in a.get("institutions", []):
                    insts.add(i["display_name"])
            src = (w.get("primary_location") or {}).get("source") or {}
            src = src.get("display_name", "")
            oa = w.get("open_access", {}).get("is_oa")
            print(f"{w.get('publication_year')} | {first} | {src} | {w.get('display_name')} | OA={oa} | {w.get('doi')}")
            print(f"      affs: {sorted(insts)[:4]}")
        with open(r"D:\Software\DSH\LiYing\tools\search\openalex_raw.json", "w", encoding="utf-8") as f:
            json.dump(works, f, ensure_ascii=False, indent=1)
        print("\nsaved -> tools/search/openalex_raw.json")


if __name__ == "__main__":
    main()
