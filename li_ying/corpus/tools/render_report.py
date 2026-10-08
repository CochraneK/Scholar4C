# -*- coding: utf-8 -*-
"""渲染整合报告 reports/report.html（自包含：Chart.js 内联，无 CDN 依赖）

数据源（单一事实源，全部可复现）：
  - analysis/analysis_data.json   计量数据（scientometrics.py 产出）
  - papers_list.csv               32 条著录
  - reports/research_timeline.md  研究方向演变（md→HTML 内嵌）
  - reports/acknowledgement_analysis.md  致谢页人格分析（md→HTML 内嵌）
  - reports/profile.md            履历/谱系/机构（md→HTML 内嵌）
  - reports/paper_plain.md        逐篇通俗讲解（md→HTML 内嵌）
"""
import json, os, csv, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
d = json.load(open(os.path.join(ROOT, "analysis", "analysis_data.json"), encoding="utf-8"))

# ---------- 论文清单 ----------
papers = []
with open(os.path.join(ROOT, "papers_list.csv"), encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        papers.append(r)
byid = {r["id"]: r for r in papers}
excluded = set(d.get("excluded", []))

# ---------- 预印本→期刊转化与时滞（配对见 papers_list.csv notes） ----------
PAIRS = [("P1", "J2"), ("P2", "J3"), ("P3", "J4"), ("P4", "J5"), ("P5", "J7"),
         ("P8", "J10"), ("P9", "J15"), ("P10", "J16"), ("P11", "J13")]
lag = [{"pair": p + "→" + j, "name": byid[j]["cn"],
        "lag": int(byid[j]["year"]) - int(byid[p]["year"]), "jr": byid[j]["jr"]}
       for p, j in PAIRS]
lag.sort(key=lambda x: -x["lag"])
lags = [x["lag"] for x in lag]
lag_median = sorted(lags)[len(lags) // 2]

n_preprint = sum(1 for r in papers if r["type"] == "preprint")
n_preprint_oa = sum(1 for r in papers if r["type"] == "preprint" and r["oa_status"] == "OA")
n_journal = sum(1 for r in papers if r["type"] == "journal" and r["id"] not in excluded)
n_journal_oa = sum(1 for r in papers if r["type"] == "journal" and r["id"] not in excluded and r["oa_status"] == "OA")

# ---------- 研究线聚类（依据 research_timeline.md 的八条线） ----------
THEMES = {
    "语言演化": ["J7", "J10", "J11", "P5", "P8"],
    "风险与决策": ["J2", "J8", "J12", "J13", "P1", "P11", "C4"],
    "情绪与福祉": ["J3", "J4", "P2", "P3", "C1", "C2"],
    "临床(自杀遗书)": ["J9", "J15", "P6", "P7", "P9"],
    "社会态度与偏见": ["J5", "P4", "C3"],
    "平台与语料": ["J1", "J6"],
    "发展语义": ["P10", "J16"],
    "博士论文": ["T1"],
}
theme_counts = {k: len(v) for k, v in THEMES.items()}
assert sum(theme_counts.values()) == d["total_valid"], (sum(theme_counts.values()), d["total_valid"])

# ---------- 引文集中度 ----------
bp = d["citations"]["by_paper"]
top3 = sorted(((k, v) for k, v in bp.items() if isinstance(v, int)), key=lambda x: -x[1])[:3]
top3_sum = sum(v for _, v in top3)
top3_share = round(100.0 * top3_sum / max(1, d["citations"]["total_cited"]), 1)
t3txt = " + ".join(f"{k} {byid[k]['cn']}({v})" for k, v in top3)

first_n = d["authorship"]["role_counts"].get("first", 0)

# ---------- 嵌入 JSON ----------
D = {**d, "lag": lag, "themes": theme_counts}

# ---------- 迷你 md→HTML（覆盖三份 md 实际使用的语法） ----------
def inline(s):
    s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"\*([^\s*,.][^*]*)\*", r"<i>\1</i>", s)  # 不匹配 "Y.*, Zhao" 式作者星号（逗号/句点开头不视为斜体）
    def _link(m):
        if m.group(1) is not None:
            return f'<a href="{m.group(2)}" target="_blank">{m.group(1)}</a>'
        return f'<a href="{m.group(3)}" target="_blank">{m.group(3)}</a>'
    s = re.sub(r"\[([^\]]+)\]\((https?://[^\s)]+)\)|(https?://[^\s<>\"）)；,;]+)", _link, s)
    return s

def md_to_html(md):
    lines = md.splitlines()
    out, i, n = [], 0, len(lines)
    in_code = False
    while i < n:
        st = lines[i].strip()
        if st.startswith("```"):
            out.append("</code></pre>" if in_code else "<pre><code>")
            in_code = not in_code
            i += 1
            continue
        if in_code:
            out.append(inline(lines[i]))
            i += 1
            continue
        if not st:
            i += 1
            continue
        if st.startswith("|") and i + 1 < n and re.match(r"^\|[\s:|-]+\|$", lines[i + 1].strip()):
            hdr = [c.strip() for c in st.strip("|").split("|")]
            i += 2
            rows = []
            while i < n and lines[i].strip().startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            out.append("<table><thead><tr>" + "".join(f"<th>{inline(c)}</th>" for c in hdr) + "</tr></thead><tbody>")
            for r in rows:
                out.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>")
            out.append("</tbody></table>")
            continue
        if st.startswith("### "):
            out.append(f"<h4>{inline(st[4:])}</h4>"); i += 1; continue
        if st.startswith("## "):
            out.append(f"<h3>{inline(st[3:])}</h3>"); i += 1; continue
        if st.startswith("# "):
            out.append(f"<h2 class='mdt'>{inline(st[2:])}</h2>"); i += 1; continue
        if st == "---":
            out.append("<hr>"); i += 1; continue
        if st.startswith(">"):
            buf = []
            while i < n and lines[i].strip().startswith(">"):
                buf.append(inline(lines[i].strip().lstrip(">").strip()))
                i += 1
            out.append("<blockquote>" + "<br>".join(buf) + "</blockquote>")
            continue
        if re.match(r"^[-*] ", st):
            buf = []
            while i < n and re.match(r"^[-*] ", lines[i].strip()):
                buf.append(inline(re.sub(r"^[-*] ", "", lines[i].strip())))
                i += 1
            out.append("<ul>" + "".join(f"<li>{x}</li>" for x in buf) + "</ul>")
            continue
        if re.match(r"^\d+\. ", st):
            buf = []
            while i < n and re.match(r"^\d+\. ", lines[i].strip()):
                buf.append(inline(re.sub(r"^\d+\. ", "", lines[i].strip())))
                i += 1
            out.append("<ol>" + "".join(f"<li>{x}</li>" for x in buf) + "</ol>")
            continue
        buf = [st]
        i += 1
        while i < n:
            s2 = lines[i].strip()
            if (not s2 or s2.startswith(("#", "|", ">", "```", "- ", "* ")) or re.match(r"^\d+\. ", s2) or s2 == "---"):
                break
            buf.append(s2)
            i += 1
        out.append("<p>" + " ".join(inline(b) for b in buf) + "</p>")
    return "\n".join(out)

def read_md(name):
    return open(os.path.join(ROOT, "reports", name), encoding="utf-8").read()

md_timeline = md_to_html(read_md("research_timeline.md"))
md_persona = md_to_html(read_md("acknowledgement_analysis.md"))
md_profile = md_to_html(read_md("profile.md"))
md_plain_raw = read_md("paper_plain.md")  # 通俗读论文：专用 parser 卡片化渲染（见下方 parse_plain）

# ---------- 论文表格 ----------
TYPE_LABEL = {"journal": "期刊", "preprint": "预印本", "conference": "会议", "thesis": "论文"}
OA_TAG = {"OA": '<span class="tag oa">OA</span>', "nonOA": '<span class="tag noa">非OA</span>',
          "unknown": '<span class="tag unk">待核</span>', "INPRESS": '<span class="tag inp">in press</span>',
          "EXCLUDE": '<span class="tag excl">已排除</span>'}

def phase_color(y):
    y = int(y)
    return "#8b5cf6" if y <= 2019 else ("#f59e0b" if y <= 2022 else "#10b981")

TYPE_PILL = {"journal": ("期刊", "#2563eb"), "preprint": ("预印本", "#0d9488"),
             "conference": ("会议", "#f59e0b"), "thesis": ("论文", "#8b5cf6")}
TYPE_COUNTS = {t: sum(1 for r in papers if r["type"] == t) for t in TYPE_PILL}

prows = []
for r in papers:
    doi = r["doi"].strip()
    doi_cell = f'<a href="https://doi.org/{doi}" target="_blank">{doi}</a>' if doi else "—"
    rows_excl = 1 if r["id"] in excluded else 0
    tlabel, tcolor = TYPE_PILL.get(r["type"], (r["type"], "#64748b"))
    prows.append(
        f'<tr data-type="{r["type"]}" data-oa="{r["oa_status"]}" data-excl="{rows_excl}" '
        f'style="border-left:3px solid {phase_color(r["year"])}">'
        f'<td><a class="pid-link" href="#pc-{r["id"]}"><b>{r["id"]}</b></a></td><td>{r["year"]}</td><td>{r["jr"]}</td>'
        f'<td>{inline(r["cn"])}</td>'
        f'<td><span class="type-pill" style="color:{tcolor};background:{tcolor}12;border-color:{tcolor}55">{tlabel}</span></td>'
        f'<td>{OA_TAG.get(r["oa_status"], r["oa_status"])}</td>'
        f'<td class="doi">{doi_cell}</td><td class="note-cell">{inline(r["notes"])}</td></tr>')
paper_rows = "\n".join(prows)

# ---------- 通俗读论文：卡片式渲染（paper_plain.md 专用 parser） ----------
def parse_plain(md):
    groups, intro = [], []
    cur_group, cur_card = None, None
    def flush_card():
        nonlocal cur_card
        if cur_card is not None:
            cur_group["cards"].append(cur_card)
            cur_card = None
    for raw in md.splitlines():
        st = raw.strip()
        if st.startswith("## "):
            flush_card()
            cur_group = {"title": st[3:].strip(), "intro": [], "cards": []}
            groups.append(cur_group)
        elif st.startswith("### "):
            flush_card()
            m = re.match(r"(\S+)\s*·\s*(.+?)\s*·\s*(\d{4})\s*$", st[4:].strip())
            if m:
                cur_card = dict(id=m.group(1), name=m.group(2), year=m.group(3),
                                en="", venue="", authors="", tags="", angle="", same="", excl=False, body=[])
            else:
                cur_card = dict(id=st[4:].strip(), name="", year="", en="", venue="",
                                authors="", tags="", angle="", same="", excl=False, body=[])
        elif cur_card is not None:
            if st.startswith("英文题名:"): cur_card["en"] = st.split(":", 1)[1].strip()
            elif st.startswith("载体:"): cur_card["venue"] = st.split(":", 1)[1].strip()
            elif st.startswith("作者:"): cur_card["authors"] = st.split(":", 1)[1].strip()
            elif st.startswith("标签:"): cur_card["tags"] = st.split(":", 1)[1].strip()
            elif st.startswith("同源:"): cur_card["same"] = st.split(":", 1)[1].strip()
            elif st.startswith("状态:"): cur_card["excl"] = ("排除" in st) or ("删除" in st)
            elif st.startswith("面试角度:"): cur_card["angle"] = st.split(":", 1)[1].strip()
            elif st.startswith("大白话:"): cur_card["body"].append(st.split(":", 1)[1].strip())
            elif st and st != "---": cur_card["body"].append(st)
        elif st.startswith(">"):
            line = st.lstrip(">").strip()
            if line:
                (cur_group["intro"] if cur_group is not None else intro).append(line)
    flush_card()
    return intro, groups

TYPE_BADGE = {"journal": ("期刊", "#2563eb"), "preprint": ("预印本", "#0d9488"),
              "conference": ("会议", "#f59e0b"), "thesis": ("博论", "#8b5cf6")}

def plain_card(c):
    pid = c["id"]
    r = byid.get(pid, {})
    ptype = r.get("type", "journal")
    bl, bc = TYPE_BADGE.get(ptype, (ptype, "#64748b"))
    y = int(c["year"]) if c["year"].isdigit() else 2000
    phase = phase_color(y)
    cls = "pc"
    if "代表作" in c["tags"]:
        cls += " star"
    if c["excl"]:
        cls += " excl"
    tags = "".join(f'<span class="pc-tag">{inline(t.strip())}</span>'
                   for t in re.split(r"[、,]", c["tags"]) if t.strip())
    same = (f'<a class="pc-same" href="#pc-{c["same"]}">→ 期刊版 {c["same"]}，点我跳转</a>'
            if c["same"] and c["same"] in byid else "")
    head = (f'<div class="pc-head"><span class="pc-id" style="background:{bc}">{pid}</span>'
            f'<span class="pc-name">{inline(c["name"])}</span>{tags}'
            f'<span class="pc-year">{c["year"]}</span>'
            f'<span class="pc-type" style="color:{bc}">{bl}</span></div>')
    en = f'<div class="pc-en">{inline(c["en"])}</div>' if c["en"] else ""
    meta = (f'<div class="pc-meta">{inline(c["venue"])}'
            + (f' · {inline(c["authors"])}' if c["authors"] else "") + "</div>") if (c["venue"] or c["authors"]) else ""
    body = f'<div class="pc-body">{inline(" ".join(c["body"]))}</div>' if c["body"] else ""
    angle = f'<div class="pc-angle">💡 面试角度：{inline(c["angle"])}</div>' if c["angle"] else ""
    foot = f'<div class="pc-foot">{same}</div>' if same else ""
    return (f'<div class="{cls}" id="pc-{pid}" style="border-left:4px solid {phase}">'
            f'{head}{en}{meta}{body}{angle}{foot}</div>')

plain_intro, plain_groups = parse_plain(md_plain_raw)
plain_intro_html = ('<div class="plain-intro">' + " ".join(inline(x) for x in plain_intro) + "</div>") if plain_intro else ""
plain_legend = """
<div class="plain-legend">
<span class="lg"><i style="background:#8b5cf6"></i>博士期 ≤2019</span>
<span class="lg"><i style="background:#f59e0b"></i>博后期 2020–2022</span>
<span class="lg"><i style="background:#10b981"></i>心理所 2023–</span>
<span class="lg lg-note">卡片左侧色条=阶段 · 彩色徽章=类型 · 渐变紫卡片=代表作 · 半透明卡片=已排除/已删除</span>
</div>"""
plain_groups_html = "\n".join(
    f'<div class="pg" id="pg{gi}"><div class="pg-title">{inline(g["title"])}'
    f'<span class="pg-count">{len(g["cards"])} 篇</span></div>'
    + ('<div class="pg-intro">' + " ".join(inline(x) for x in g["intro"]) + "</div>" if g["intro"] else "")
    + "\n".join(plain_card(c) for c in g["cards"])
    + "</div>"
    for gi, g in enumerate(plain_groups))

# ---------- 研究时间线：可视化渲染（research_timeline.md 专用 parser） ----------
def md_sections(md):
    """按 '## ' 切分，返回 ({标题: [行]}, [标题顺序])；首个 ## 之前的行归入 preamble。"""
    secs, order, pre, cur = {}, [], [], None
    for line in md.splitlines():
        st = line.strip()
        if st.startswith("## "):
            cur = st[3:].strip(); secs[cur] = []; order.append(cur)
        elif cur is None:
            pre.append(line)
        else:
            secs[cur].append(line)
    return secs, order, pre

def first_table(lines):
    for i, l in enumerate(lines):
        st = l.strip()
        if st.startswith("|") and i + 1 < len(lines) and re.match(r"^\|[\s:|-]+\|$", lines[i + 1].strip()):
            hdr = [c.strip() for c in st.strip("|").split("|")]
            i += 2; rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            return hdr, rows
    return None, None

tl_md = read_md("research_timeline.md")
tl_secs, tl_order, tl_pre = md_sections(tl_md)
tl_core = [l.strip().lstrip(">").strip() for l in tl_pre if l.strip().startswith(">")]
tl_core_html = (f'<div class="tl-core">💡 {inline(" ".join(tl_core))}</div>') if tl_core else ""

PHASE_COLORS = ["#8b5cf6", "#f59e0b", "#10b981"]

def tl_phase_card(title, lines, idx):
    m = re.match(r"^阶段\s*(\d+)[:：]\s*(\S+)（(.+)）$", title)
    num, name, rest = (m.group(1), m.group(2), m.group(3)) if m else (str(idx + 1), title, "")
    parts = rest.split("，")
    when, metas = (parts[0] if parts else ""), parts[1:]
    c = PHASE_COLORS[idx % 3]
    chips = "".join(f'<span class="tl-chip">{inline(x)}</span>' for x in metas)
    return (f'<div class="tl-phase" style="border-top:4px solid {c}">'
            f'<div class="tl-phead" style="background:{c}12"><span class="tl-pbadge" style="background:{c}">阶段 {num}</span>'
            f'<span class="tl-pname">{inline(name)}</span><span class="tl-pwhen">{inline(when)}</span></div>'
            + (f'<div class="tl-pmeta">{chips}</div>' if chips else "")
            + f'<div class="tl-pbody md">{md_to_html("\n".join(lines))}</div></div>')

tl_phase_titles = [t for t in tl_order if t.startswith("阶段")]
tl_phases_html = "\n".join(tl_phase_card(t, tl_secs[t], i) for i, t in enumerate(tl_phase_titles))

def tl_flow_html(lines):
    banner, steps, arrows, cur = "", [], [], None
    for line in lines:
        st = line.strip()
        if not st or st.startswith("```"):
            continue
        m = re.match(r"方法论恒定[:：]\s*(.+)", st)
        if m:
            banner = m.group(1); continue
        m = re.match(r"^(\d{4})-(\d{4}\+?)\s+(.+)$", st)
        if m:
            bits = re.split(r"\s{2,}", m.group(3), maxsplit=1)
            y = int(m.group(1))
            cur = dict(when=f"{m.group(1)}–{m.group(2)}", who=bits[0],
                       what=bits[1] if len(bits) > 1 else "",
                       c=PHASE_COLORS[0 if y <= 2019 else (1 if y <= 2022 else 2)])
            steps.append(cur); continue
        if st.startswith("│"):
            if steps:
                arrows.append(st[1:].strip())
            continue
        if cur is not None:
            cur["what"] += " " + st
    out = []
    if banner:
        out.append(f'<div class="tl-banner">⚙️ 方法论恒定：{inline(banner)}</div>')
    for i, s in enumerate(steps):
        if i > 0 and arrows:
            lbl = arrows.pop(0)
            out.append(f'<div class="tl-arrow">{inline(lbl)}</div>')
        out.append(f'<div class="tl-step" style="border-left:5px solid {s["c"]};background:{s["c"]}0d">'
                   f'<div class="tl-when">{s["when"]}</div><div class="tl-who">{inline(s["who"])}</div>'
                   f'<div class="tl-what">{inline(s["what"])}</div></div>')
    return "\n".join(out)

tl_flow_html_ = tl_flow_html(tl_secs.get("方向迁移总图", []))
tl_oneliner = next((l.strip() for l in tl_secs.get("方向迁移总图", [])
                    if l.strip().startswith("**一句话**")), "")
tl_oneliner_html = f'<div class="tl-oneliner">{inline(tl_oneliner)}</div>' if tl_oneliner else ""
tl_ev_lines = tl_secs.get("证据清单（本地可查）", [])
tl_ev_html = (f'<div class="tl-ev"><div class="tl-ev-t">📎 证据清单（本地可查）</div>'
              f'<div class="md">{md_to_html("\n".join(tl_ev_lines))}</div></div>') if tl_ev_lines else ""

timeline_html = f"""
{tl_core_html}
{tl_phases_html}
<div class="tl-flow-wrap">
<div class="pg-title">🧭 方向迁移总图<span class="pg-count">方法论恒定 · 应用对象迁移</span></div>
{tl_flow_html_}
</div>
{tl_oneliner_html}
{tl_ev_html}
"""

# ---------- 人格画像：卡片化渲染（acknowledgement_analysis.md 专用 parser） ----------
pv_md = read_md("acknowledgement_analysis.md")
pv_secs, pv_order, pv_pre = md_sections(pv_md)

def pv_sec(name_prefix):
    for t in pv_order:
        if t.startswith(name_prefix):
            return t, pv_secs[t]
    return None, []

EV_COLORS = ["#2563eb", "#8b5cf6", "#0d9488", "#f59e0b", "#10b981", "#e11d48"]

def pv_title(t):
    return f'<div class="pg-title">{inline(t)}</div>'

# 一、硬证据 → 对象卡片
_, ev_lines = pv_sec("一、")
ev_hdr, ev_rows = first_table(ev_lines)
pv_ev_cards = ""
if ev_rows:
    cards = []
    for i, row in enumerate(ev_rows):
        obj, quote, fact = row[0], row[1], (row[2] if len(row) > 2 else "")
        quotes = [q.strip() for q in re.split(r"[；;]", quote) if q.strip()]
        q_html = "".join(f'<div class="pv-quote">{inline(q)}</div>' for q in quotes)
        cards.append(
            f'<div class="pv-ev" style="border-top:3px solid {EV_COLORS[i % 6]}">'
            f'<div class="pv-ev-name">{inline(obj)}</div>{q_html}'
            + (f'<div class="pv-ev-fact">📌 {inline(fact)}</div>' if fact else "")
            + "</div>")
    pv_ev_cards = '<div class="pv-ev-grid">' + "".join(cards) + "</div>"

# 二、人格推断 → 强度卡片
_, inf_lines = pv_sec("二、")
STRENGTH_COLOR = {"强推断": "#10b981", "中强推断": "#2563eb", "中等推断": "#f59e0b"}
pv_inf_cards = ""
inf_items = []
for l in inf_lines:
    st = l.strip()
    if re.match(r"^\d+\. ", st):
        inf_items.append(st)
for l in inf_items:
    m = re.match(r"^\d+\.\s*\*\*(.+?)（([^）]+)）\*\*[:：]\s*(.+)$", l)
    if m:
        name, strength, content = m.group(1), m.group(2), m.group(3)
    else:
        name, strength, content = l, "", ""
    c = STRENGTH_COLOR.get(strength, "#64748b")
    num = re.match(r"^(\d+)", l).group(1)
    pv_inf_cards += (
        f'<div class="pv-inf"><span class="pv-inf-num" style="background:{c}">{num}</span>'
        f'<div class="pv-inf-main"><div class="pv-inf-head"><b>{inline(name)}</b>'
        f'<span class="pv-pill" style="color:{c};border-color:{c}66;background:{c}12">{strength}</span></div>'
        f'<div class="pv-inf-body">{inline(content)}</div></div></div>')

# 三、cross-check → 表格 + 一致性徽章
_, cc_lines = pv_sec("三、")
cc_hdr, cc_rows = first_table(cc_lines)
pv_cc_html = ""
if cc_rows:
    trs = []
    for row in cc_rows:
        a, b, c3 = row[0], row[1], (row[2] if len(row) > 2 else "")
        cls = "hi" if c3.startswith("高") else "lo"
        trs.append(f'<tr><td>{inline(a)}</td><td>{inline(b)}</td>'
                   f'<td><span class="pv-cons {cls}">{inline(c3)}</span></td></tr>')
    pv_cc_html = ('<table class="pv-table"><thead><tr><th>推断</th><th>后续行为</th><th>一致性</th></tr></thead>'
                  "<tbody>" + "".join(trs) + "</tbody></table>")

# 四、限制 → 警示框
_, lim_lines = pv_sec("四、")
lim_items = [l.strip().lstrip("- ").strip() for l in lim_lines if l.strip().startswith("- ")]
pv_lim_html = ('<div class="pv-warn"><div class="pv-warn-t">⚠️ 解读限制</div><ul>'
               + "".join(f"<li>{inline(x)}</li>" for x in lim_items) + "</ul></div>") if lim_items else ""

# 一句话画像 → 大引用卡
_, hero_lines = pv_sec("一句话画像")
hero_txt = " ".join(l.strip() for l in hero_lines if l.strip())
pv_hero_html = (f'<div class="pv-hero">“{inline(hero_txt)}”</div>') if hero_txt else ""

persona_html = f"""
{pv_title("一、硬证据（致谢页直接引文，6 对象）")}
{pv_ev_cards}
{pv_title("二、人格推断（按强度排序）")}
{pv_inf_cards}
{pv_title("三、与后续行为 cross-check（互证，均来自本地语料）")}
{pv_cc_html}
{pv_lim_html}
{pv_title("一句话画像")}
{pv_hero_html}
"""

# ---------- 履历：卡片化渲染（profile.md 专用 parser） ----------
pf_md = read_md("profile.md")
pf_secs, pf_order, pf_pre = md_sections(pf_md)
pf_note = " ".join(l.strip().lstrip(">").strip() for l in pf_pre if l.strip().startswith(">"))

def pf_sec(num):
    for t in pf_order:
        if t.startswith(str(num) + "."):
            return t, pf_secs[t]
    return None, []

SRC_COLORS = {"官网": "#2563eb", "个人页": "#0d9488", "MPHD": "#8b5cf6",
              "ORCID": "#0ea5e9", "WRAP": "#6366f1", "其他": "#94a3b8"}

def src_badges(cell):
    toks = re.findall(r"【([^】]+)】", cell)
    rest = re.sub(r"【[^】]+】", "", cell).strip(" （）")
    badges = "".join(
        f'<span class="pf-src" style="color:{SRC_COLORS.get(t, "#94a3b8")};border-color:{SRC_COLORS.get(t, "#94a3b8")}55">{t}</span>'
        for t in toks)
    note = f'<span class="pf-src-note">{inline(rest)}</span>' if rest else ""
    return badges + note

# §1 基本信息 → KV 卡片
_, b1 = pf_sec(1)
_, b1_rows = first_table(b1)
pf_kv_html = ""
if b1_rows:
    cards = []
    for k, v, src in [(r[0], r[1], (r[2] if len(r) > 2 else "")) for r in b1_rows]:
        cards.append(
            f'<div class="pf-kv"><div class="pf-k">{inline(k)}</div>'
            f'<div class="pf-v">{inline(v)}</div>'
            + (f'<div class="pf-srcs">{src_badges(src)}</div>' if src else "") + "</div>")
    pf_kv_html = '<div class="pf-kv-grid">' + "".join(cards) + "</div>"

# §2 教育经历 → 三步卡 + 博士论文特写
_, b2 = pf_sec(2)
_, ed_rows = first_table(b2)
pf_edu_html = ""
if ed_rows:
    edu_cards = []
    for i, r in enumerate(ed_rows):
        period, inst, deg = r[0], r[1], (r[2] if len(r) > 2 else "")
        src = r[3] if len(r) > 3 else ""
        cap = "🎓" if "博士" in deg else ("📜" if "硕士" in deg else "🏫")
        edu_cards.append(
            f'<div class="pf-edu" style="border-top:3px solid {PHASE_COLORS[min(i, 2)]}">'
            f'<div class="pf-edu-cap">{cap}</div><div class="pf-edu-inst">{inline(inst)}</div>'
            f'<div class="pf-edu-deg">{inline(deg)}</div>'
            f'<div class="pf-edu-when">{period}</div>'
            + (f'<div class="pf-srcs">{src_badges(src)}</div>' if src else "") + "</div>")
    pf_edu_html = '<div class="pf-edu-grid">' + "".join(edu_cards) + "</div>"
thesis_lines = [l for l in b2
                if not l.strip().startswith("|") and not l.strip().startswith("**博士论文**")]
pf_thesis_html = (f'<div class="pf-thesis"><div class="pf-thesis-t">🎓 博士论文（T1，已下载至 pdfs/）</div>'
                  f'<div class="md">{md_to_html("\n".join(thesis_lines))}</div></div>') if any(l.strip() for l in thesis_lines) else ""

# §3 工作/研究经历 → 垂直时间轴
_, b3 = pf_sec(3)
_, wt_rows = first_table(b3)
pf_wt_html = ""
if wt_rows:
    items = []
    for r in wt_rows:
        period, pos, org = r[0], r[1], (r[2] if len(r) > 2 else "")
        note = r[3] if len(r) > 3 else ""
        c = "#f59e0b" if "2019" in period else "#10b981"
        items.append(
            f'<div class="pf-wt"><div class="pf-wt-dot" style="background:{c}"></div>'
            f'<div class="pf-wt-main"><div class="pf-wt-pos">{inline(pos)}<span class="pf-wt-org">{inline(org)}</span></div>'
            + (f'<div class="pf-wt-note">{inline(note)}</div>' if note else "") + "</div>"
            f'<div class="pf-wt-when">{period}</div></div>')
    pf_wt_html = '<div class="pf-wt-wrap">' + "".join(items) + "</div>"

# §4 导师与学术谱系 → 编号卡 + 一句话条
_, b4 = pf_sec(4)
LINE_COLORS = ["#8b5cf6", "#f59e0b", "#10b981", "#64748b"]
pf_lin_cards, pf_lin_quote = "", ""
lin_items = []
for l in b4:
    st = l.strip()
    m = re.match(r"^\d+\.\s+(.+)$", st)
    if m:
        lin_items.append([m.group(1), []])
    elif st.startswith("- ") and lin_items:
        lin_items[-1][1].append(st[2:])
    elif st.startswith(">"):
        pf_lin_quote = st.lstrip(">").strip()
for i, (name, subs) in enumerate(lin_items):
    subs_html = "".join(f"<li>{inline(s)}</li>" for s in subs)
    pf_lin_cards += (
        f'<div class="pf-lin" style="border-left:4px solid {LINE_COLORS[i % 4]}">'
        f'<span class="pf-lin-num" style="background:{LINE_COLORS[i % 4]}">{i + 1}</span>'
        f'<div class="pf-lin-main"><div class="pf-lin-name">{inline(name)}</div>'
        + (f'<ul class="pf-lin-sub">{subs_html}</ul>' if subs_html else "") + "</div></div>")
pf_lin_quote_html = (f'<div class="tl-oneliner">{inline(pf_lin_quote)}</div>') if pf_lin_quote else ""

# §5 研究方向（现） → 主题卡
_, b5 = pf_sec(5)
THEME_COLORS = ["#2563eb", "#8b5cf6", "#10b981", "#f59e0b"]
pf_dir_cards, pf_tool = "", ""
for l in b5:
    st = l.strip()
    m = re.match(r"^\d+\.\s*\*\*(.+?)\*\*[:：—]*[:：]?\s*(.*)$", st)
    if m:
        nm, desc = m.group(1), m.group(2)
        pf_dir_cards += (f'<div class="pf-dir" style="border-top:3px solid {THEME_COLORS[(len(pf_dir_cards.split("pf-dir")) - 1) % 4]}">'
                         f'<div class="pf-dir-name">{inline(nm)}</div>'
                         + (f'<div class="pf-dir-desc">{inline(desc)}</div>' if desc else "") + "</div>")
    elif st.startswith("工具资产"):
        pf_tool = st
pf_dir_html = (f'<div class="pf-dir-grid">{pf_dir_cards}</div>'
               + (f'<div class="pf-tool">🧰 {inline(pf_tool)}</div>' if pf_tool else "")) if pf_dir_cards else ""

# §6 主持项目 → 项目卡 + 合计条
_, b6 = pf_sec(6)
_, pj_rows = first_table(b6)
pf_pj_html = ""
if pj_rows:
    cards = []
    for r in pj_rows:
        name, period, amt, src = r[0], r[1], (r[2] if len(r) > 2 else ""), (r[3] if len(r) > 3 else "")
        cards.append(
            f'<div class="pf-pj"><div class="pf-pj-name">{inline(name)}</div>'
            f'<div class="pf-pj-amt">{inline(amt)}</div>'
            f'<div class="pf-pj-period">{period}</div>'
            + (f'<div class="pf-srcs">{src_badges(src)}</div>' if src else "") + "</div>")
    pf_pj_html = '<div class="pf-pj-grid">' + "".join(cards) + "</div>"
pf_pj_note = ""
for l in b6:
    st = l.strip()
    if st.startswith("合计"):
        pf_pj_note = st
pf_pj_note_html = (f'<div class="pf-pj-total">{inline(pf_pj_note)}</div>') if pf_pj_note else ""

# §7 学生与招生 → 学生卡 + 招生高亮 callout
_, b7 = pf_sec(7)
pf_student, pf_recruit = "", ""
for l in b7:
    st = l.strip()
    if not st.startswith("- "):
        continue
    body = st[2:]
    m = re.match(r"\*\*(.+?)\*\*([^:：]*)[:：]\s*(.+)$", body)
    nm, desc = (m.group(1) + m.group(2), m.group(3)) if m else ("", body)
    if "招生" in nm:
        pf_recruit = (f'<div class="pv-recruit">🎓 <b>{inline(nm)}</b><div class="pv-recruit-d">{inline(desc)}</div></div>')
    else:
        pf_student = (f'<div class="pf-student">👨‍🎓 <b>{inline(nm)}</b><div class="pf-student-d">{inline(desc)}</div></div>')
pf_b7_html = f'<div class="pf-b7-grid">{pf_student}{pf_recruit}</div>' if (pf_student or pf_recruit) else ""

# §8 代表作 / §9 同名排除 / §10 来源
_, b8 = pf_sec(8)
pf_works_html = (f'<div class="pf-works"><div class="pf-works-t">🏅 代表作（官网列 1–8，摘录可见项）</div>'
                 f'<div class="md">{md_to_html("\n".join(b8))}</div></div>') if b8 else ""
_, b9 = pf_sec(9)
excl_items = [l.strip().lstrip("- ").strip() for l in b9 if l.strip().startswith("- ")]
pf_excl_html = ('<div class="pv-warn red"><div class="pv-warn-t">🚫 同名排除（非目标人物）</div><ul>'
                + "".join(f"<li>{inline(x)}</li>" for x in excl_items) + "</ul></div>") if excl_items else ""
_, b10 = pf_sec(10)
_, b10_rows = first_table(b10)
pf_src_html = ""
if b10_rows:
    chips = []
    for r in b10_rows:
        nm, url = r[0], (r[1] if len(r) > 1 else "")
        chips.append(f'<div class="pf-src-row"><span class="pf-src-nm">{inline(nm)}</span>'
                     f'<span class="pf-src-url">{inline(url)}</span></div>')
    pf_src_html = ('<div class="pf-src-box"><div class="pf-works-t">🔗 主要来源清单</div>'
                   + "".join(chips) + "</div>")

profile_md_html = (f'<div class="pf-note">📎 源标注纪律：{inline(pf_note)}</div>' if pf_note else "")
profile_html = f"""
{profile_md_html}
<div class="pg-title">📇 基本信息<span class="pg-count">{len(b1_rows) if b1_rows else 0} 项</span></div>
{pf_kv_html}
<div class="pg-title">🎓 教育经历</div>
{pf_edu_html}
{pf_thesis_html}
<div class="pg-title">🧳 工作/研究经历</div>
{pf_wt_html}
<div class="pg-title">🌳 导师与学术谱系</div>
<div class="pf-lin-grid">{pf_lin_cards}</div>
{pf_lin_quote_html}
<div class="pg-title">🎯 研究方向（现，官网四主题）</div>
{pf_dir_html}
<div class="pg-title">💰 主持项目</div>
{pf_pj_html}
{pf_pj_note_html}
<div class="pg-title">👥 学生与招生</div>
{pf_b7_html}
{pf_works_html}
{pf_excl_html}
{pf_src_html}
"""

# ---------- CSS ----------
CSS = """
:root{--bg:#f5f7fa;--card:#fff;--text:#1a2332;--accent:#2563eb;--border:#e0e6ed;
--purple:#8b5cf6;--amber:#f59e0b;--green:#10b981;--gray:#94a3b8;--teal:#0d9488;}
*{margin:0;padding:0;box-sizing:border-box}
html{scroll-behavior:smooth}
body{font-family:-apple-system,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;
background:var(--bg);color:var(--text);line-height:1.6}
.header{background:linear-gradient(135deg,#1e3a5f,#2563eb);color:#fff;padding:48px 24px;text-align:center}
.header h1{font-size:1.9rem;font-weight:700;margin-bottom:8px}
.header p{opacity:.9}
.header .meta{margin-top:14px;display:flex;gap:12px;justify-content:center;flex-wrap:wrap}
.header .meta span{background:rgba(255,255,255,.15);padding:4px 16px;border-radius:20px;font-size:.88rem}
.nav{position:sticky;top:0;z-index:50;background:rgba(255,255,255,.93);backdrop-filter:blur(8px);
border-bottom:1px solid var(--border);display:flex;gap:4px;justify-content:center;flex-wrap:wrap;padding:8px 12px}
.nav a{color:#475569;text-decoration:none;font-size:.86rem;font-weight:600;padding:5px 13px;border-radius:16px}
.nav a:hover{background:#eef2ff;color:var(--accent)}
.container{max-width:1100px;margin:0 auto;padding:24px}
.stats-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:14px;margin-bottom:28px}
.stat-card{background:var(--card);border-radius:12px;padding:18px;text-align:center;
box-shadow:0 1px 3px rgba(0,0,0,.08);border:1px solid var(--border)}
.stat-card .num{font-size:2rem;font-weight:800;color:var(--accent)}
.stat-card .label{color:#666;font-size:.82rem;margin-top:2px}
.g .num{color:var(--green)}.a .num{color:var(--amber)}.p .num{color:var(--purple)}
.section{background:var(--card);border-radius:12px;border:1px solid var(--border);
padding:24px;margin-bottom:24px;box-shadow:0 1px 3px rgba(0,0,0,.05)}
.section h2{font-size:1.15rem;margin-bottom:14px;border-left:4px solid var(--accent);padding-left:10px}
.row{display:grid;grid-template-columns:1fr 1fr;gap:24px}
@media(max-width:800px){.row{grid-template-columns:1fr}}
.chart-box{position:relative;height:320px}
table{width:100%;border-collapse:collapse;font-size:.88rem}
th,td{padding:7px 10px;text-align:left;border-bottom:1px solid var(--border)}
th{background:#f8fafc;color:#475569;font-weight:600}
tr:hover td{background:#f8fafc}
.tag{display:inline-block;padding:1px 9px;border-radius:10px;font-size:.78rem;font-weight:600}
.tag.first{background:#dbeafe;color:#1d4ed8}.tag.second{background:#ccfbf1;color:#0f766e}
.tag.middle{background:#f1f5f9;color:#475569}.tag.last{background:#fef3c7;color:#b45309}
.tag.oa{background:#dcfce7;color:#15803d}.tag.noa{background:#fee2e2;color:#b91c1c}
.tag.unk{background:#f1f5f9;color:#64748b}.tag.inp{background:#ede9fe;color:#6d28d9}
.tag.excl{background:#f1f5f9;color:#94a3b8;text-decoration:line-through}
tr[data-excl="1"]{opacity:.5}
.filters{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:12px}
.flabel{font-size:.8rem;color:#64748b;font-weight:600;margin-left:10px}
.fbtn{border:1px solid var(--border);background:#fff;border-radius:16px;padding:4px 14px;font-size:.82rem;cursor:pointer;color:#475569}
.fbtn.on{background:var(--accent);color:#fff;border-color:var(--accent)}
.doi{word-break:break-all;font-size:.78rem}
.note-cell{color:#64748b;font-size:.78rem}
.lineage{display:flex;align-items:stretch;gap:8px;flex-wrap:wrap;margin:6px 0 18px}
.node{flex:1;min-width:170px;background:#f8fafc;border:2px solid var(--border);border-radius:10px;padding:12px}
.node .n-y{font-size:.75rem;color:#64748b;font-weight:700}
.node .n-t{font-weight:700;margin:2px 0}
.node .n-s{font-size:.78rem;color:#475569}
.arrow{align-self:center;font-size:1.2rem;color:#94a3b8}
@media(max-width:800px){.lineage{flex-direction:column}.arrow{transform:rotate(90deg)}}
.insight-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:14px}
.insight{background:linear-gradient(160deg,#f8fafc,#eef2ff);border:1px solid var(--border);border-radius:12px;padding:16px}
.insight .i-num{font-size:1.55rem;font-weight:800;color:var(--accent)}
.insight .i-title{font-weight:700;font-size:.9rem;margin:2px 0 6px}
.insight .i-body{font-size:.8rem;color:#475569}
ul.findings li{margin:8px 0 8px 20px}
.note{font-size:.82rem;color:#64748b;margin-top:10px}
.md h2.mdt{font-size:1.3rem;margin:6px 0 10px}
.md h3{font-size:1.05rem;margin:20px 0 8px;color:#1e3a5f}
.md h4{font-size:.95rem;margin:14px 0 6px}
.md table{margin:10px 0}
.md blockquote{border-left:3px solid var(--accent);background:#f8fafc;padding:10px 14px;margin:10px 0;
font-size:.88rem;color:#475569;border-radius:0 8px 8px 0}
.md ul,.md ol{margin:8px 0 8px 22px}
.md li{margin:4px 0}
.md p{margin:8px 0}
.md pre{background:#0f172a;color:#e2e8f0;padding:14px;border-radius:8px;overflow-x:auto;font-size:.8rem;line-height:1.55;margin:10px 0}
.md code{background:#f1f5f9;padding:1px 5px;border-radius:4px;font-size:.85em}
.md pre code{background:none;padding:0}
.md hr{border:none;border-top:1px solid var(--border);margin:16px 0}
.md a{color:var(--accent)}
footer{text-align:center;color:#94a3b8;font-size:.8rem;padding:20px}
/* ---- 通俗读论文卡片 ---- */
.plain-legend{display:flex;gap:14px;flex-wrap:wrap;align-items:center;margin:0 0 16px;font-size:.8rem;color:#475569}
.plain-legend .lg{display:inline-flex;align-items:center;gap:6px}
.plain-legend .lg i{width:10px;height:10px;border-radius:3px;display:inline-block}
.plain-legend .lg-note{color:#94a3b8;margin-left:auto}
.plain-intro{background:#f8fafc;border:1px solid var(--border);border-left:3px solid var(--accent);border-radius:0 10px 10px 0;padding:12px 16px;font-size:.88rem;color:#475569;margin-bottom:20px;line-height:1.7}
.pg{margin:26px 0 10px}
.pg-title{font-size:1.08rem;font-weight:800;color:#1e3a5f;border-bottom:2px solid var(--border);padding-bottom:8px;display:flex;align-items:baseline;gap:10px}
.pg-count{font-size:.78rem;font-weight:700;color:#fff;background:var(--accent);padding:2px 10px;border-radius:10px;align-self:center}
.pg-intro{font-size:.84rem;color:#64748b;background:#f8fafc;border-radius:8px;padding:10px 14px;margin:12px 0;line-height:1.7}
.pc{background:#fff;border:1px solid var(--border);border-radius:12px;padding:16px 18px;margin-bottom:14px;
box-shadow:0 1px 3px rgba(0,0,0,.05);scroll-margin-top:70px;transition:box-shadow .18s ease,transform .18s ease}
.pc:hover{box-shadow:0 6px 18px rgba(30,58,95,.12);transform:translateY(-1px)}
.pc.star{background:linear-gradient(160deg,#fff 60%,#eef2ff)}
.pc.excl{opacity:.6;background:#f8fafc}
.pc-head{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:8px}
.pc-id{font-weight:800;font-size:.82rem;padding:2px 10px;border-radius:8px;color:#fff;letter-spacing:.5px}
.pc-name{font-weight:700;font-size:1.02rem;color:#1a2332}
.pc-tag{display:inline-block;background:#eef2ff;color:#4338ca;font-size:.72rem;font-weight:600;padding:1px 9px;border-radius:10px}
.pc-year{margin-left:auto;color:#64748b;font-size:.85rem;font-weight:700}
.pc-type{font-size:.75rem;font-weight:700;border:1px solid currentColor;padding:0 8px;border-radius:10px}
.pc-en{font-size:.82rem;color:#475569;font-style:italic;margin-bottom:6px}
.pc-meta{font-size:.78rem;color:#64748b;margin-bottom:8px}
.pc-body{font-size:.92rem;line-height:1.8;color:#263243}
.pc-angle{background:#f0f9ff;border:1px dashed #93c5fd;border-radius:8px;padding:8px 12px;margin-top:10px;font-size:.82rem;color:#1e40af;line-height:1.7}
.pc-foot{margin-top:10px}
.pc-same{display:inline-block;font-size:.78rem;font-weight:600;color:var(--accent);background:#eff6ff;border:1px solid #bfdbfe;border-radius:14px;padding:3px 12px;text-decoration:none}
.pc-same:hover{background:var(--accent);color:#fff}
.pid-link{text-decoration:none;color:inherit}
.pid-link:hover b{color:var(--accent);text-decoration:underline}
/* ---- 时间线可视化 ---- */
.tl-core{background:linear-gradient(135deg,#eef2ff,#f8fafc);border:1px solid #c7d2fe;border-left:4px solid #8b5cf6;border-radius:10px;padding:14px 18px;margin:0 0 20px;font-size:.9rem;line-height:1.8;color:#1e293b}
.tl-phase{background:#fff;border:1px solid var(--border);border-radius:12px;margin-bottom:18px;overflow:hidden;box-shadow:0 1px 3px rgba(30,58,95,.06)}
.tl-phead{display:flex;align-items:center;gap:12px;padding:12px 18px;flex-wrap:wrap}
.tl-pbadge{color:#fff;font-weight:800;font-size:.8rem;padding:3px 12px;border-radius:12px}
.tl-pname{font-size:1.05rem;font-weight:800;color:#1a2332}
.tl-pwhen{margin-left:auto;font-size:.85rem;font-weight:700;color:#475569;background:#fff;border:1px solid var(--border);padding:2px 12px;border-radius:12px}
.tl-pmeta{display:flex;gap:8px;flex-wrap:wrap;padding:0 18px 10px}
.tl-chip{font-size:.75rem;font-weight:600;color:#475569;background:#f1f5f9;border:1px solid var(--border);padding:2px 10px;border-radius:10px}
.tl-pbody{padding:0 18px 16px}
.tl-flow-wrap{margin-top:26px}
.tl-banner{background:#0f172a;color:#e2e8f0;border-radius:10px;padding:12px 18px;font-size:.88rem;font-weight:600;margin-bottom:14px}
.tl-step{background:#f8fafc;border:1px solid var(--border);border-radius:10px;padding:14px 18px}
.tl-when{font-size:.78rem;font-weight:800;color:#64748b;letter-spacing:.5px}
.tl-who{font-size:1rem;font-weight:800;color:#1a2332;margin:2px 0}
.tl-what{font-size:.85rem;color:#475569;line-height:1.7}
.tl-arrow{text-align:center;color:#94a3b8;font-size:.75rem;padding:4px 0 2px}
.tl-arrow:after{content:"↓";display:block;font-size:1.05rem;color:#cbd5e1;line-height:1.2}
.tl-oneliner{background:linear-gradient(135deg,#fffbeb,#fef3c7);border:1px solid #fde68a;border-radius:10px;padding:14px 18px;margin:16px 0;font-size:.92rem;font-weight:600;color:#92400e;line-height:1.8}
.tl-ev{background:#f8fafc;border:1px dashed var(--border);border-radius:10px;padding:14px 18px;margin-top:16px}
.tl-ev-t{font-weight:800;font-size:.9rem;color:#334155;margin-bottom:8px}
.tl-ev .md li{font-size:.84rem}
/* ---- 人格画像 ---- */
.pv-ev-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:12px;margin:12px 0 22px}
.pv-ev{background:#fff;border:1px solid var(--border);border-radius:12px;padding:14px 16px;box-shadow:0 1px 3px rgba(30,58,95,.05)}
.pv-ev-name{font-weight:800;font-size:.95rem;color:#1a2332;margin-bottom:8px}
.pv-quote{font-size:.8rem;color:#475569;font-style:italic;border-left:3px solid #e2e8f0;padding:4px 10px;margin:6px 0;line-height:1.6;background:#fafbfc;border-radius:0 6px 6px 0}
.pv-ev-fact{font-size:.78rem;color:#1e40af;background:#eff6ff;border-radius:6px;padding:6px 10px;margin-top:8px;line-height:1.6}
.pv-inf{display:flex;gap:12px;background:#fff;border:1px solid var(--border);border-radius:10px;padding:12px 16px;margin-bottom:10px}
.pv-inf-num{flex:none;width:26px;height:26px;border-radius:50%;color:#fff;font-weight:800;font-size:.85rem;display:flex;align-items:center;justify-content:center;margin-top:2px}
.pv-inf-head{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.pv-inf-head b{font-size:.95rem;color:#1a2332}
.pv-pill{font-size:.72rem;font-weight:700;border:1px solid;padding:1px 10px;border-radius:10px}
.pv-inf-body{font-size:.85rem;color:#475569;line-height:1.75;margin-top:4px}
.pv-table{margin:12px 0 20px;background:#fff;border:1px solid var(--border);border-radius:10px;overflow:hidden}
.pv-table th{background:#f1f5f9;font-size:.8rem;color:#475569;padding:9px 14px;text-align:left;border-bottom:2px solid var(--border)}
.pv-table td{font-size:.85rem;color:#263243;padding:10px 14px;border-bottom:1px solid #eef2f7;line-height:1.6}
.pv-table tr:last-child td{border-bottom:none}
.pv-cons{font-size:.72rem;font-weight:800;padding:2px 10px;border-radius:10px;white-space:nowrap}
.pv-cons.hi{color:#065f46;background:#d1fae5}
.pv-cons.lo{color:#64748b;background:#f1f5f9}
.pv-warn{background:#fffbeb;border:1px solid #fde68a;border-left:4px solid #f59e0b;border-radius:10px;padding:12px 16px;margin:14px 0 20px}
.pv-warn.red{background:#fef2f2;border-color:#fecaca;border-left-color:#e11d48}
.pv-warn-t{font-weight:800;font-size:.88rem;color:#92400e;margin-bottom:6px}
.pv-warn.red .pv-warn-t{color:#9f1239}
.pv-warn li{font-size:.82rem;color:#7c2d12;line-height:1.7;margin:4px 0 4px 18px}
.pv-warn.red li{color:#881337}
.pv-hero{background:linear-gradient(135deg,#eef2ff,#fdf2f8);border:1px solid #c7d2fe;border-radius:14px;padding:22px 26px;margin:12px 0;font-size:1.02rem;font-weight:600;color:#1e293b;line-height:1.9;box-shadow:0 2px 8px rgba(99,102,241,.1)}
/* ---- 论文清单 chips/药丸 ---- */
.paper-chips{display:flex;gap:8px;flex-wrap:wrap;margin:0 0 14px}
.chip{font-size:.78rem;font-weight:700;color:#334155;background:#fff;border:1px solid var(--border);border-radius:14px;padding:3px 12px}
.chip.excl-chip{color:#b91c1c;background:#fef2f2;border-color:#fecaca}
.type-pill{display:inline-block;font-size:.72rem;font-weight:700;padding:2px 10px;border-radius:10px;border:1px solid}
.node .n-ic{font-size:1.25rem;line-height:1;margin-bottom:4px}
/* ---- 履历卡片 ---- */
.pf-note{font-size:.78rem;color:#64748b;background:#f8fafc;border:1px dashed var(--border);border-radius:8px;padding:8px 14px;margin:6px 0 14px;line-height:1.7}
.pf-kv-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:10px;margin:12px 0 22px}
.pf-kv{background:#fff;border:1px solid var(--border);border-radius:10px;padding:12px 14px;box-shadow:0 1px 2px rgba(30,58,95,.04)}
.pf-k{font-size:.72rem;font-weight:800;color:#8b5cf6;letter-spacing:.5px;margin-bottom:4px}
.pf-v{font-size:.86rem;color:#1a2332;line-height:1.6}
.pf-srcs{margin-top:6px;display:flex;gap:4px;flex-wrap:wrap;align-items:center}
.pf-src{font-size:.68rem;font-weight:700;border:1px solid;padding:0 8px;border-radius:8px;background:#fff}
.pf-src-note{font-size:.72rem;color:#94a3b8}
.pf-edu-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px;margin:12px 0}
.pf-edu{background:#fff;border:1px solid var(--border);border-radius:12px;padding:14px 16px;box-shadow:0 1px 3px rgba(30,58,95,.05)}
.pf-edu-cap{font-size:1.3rem;margin-bottom:6px}
.pf-edu-inst{font-weight:800;font-size:.95rem;color:#1a2332}
.pf-edu-deg{font-size:.8rem;color:#475569;margin:3px 0}
.pf-edu-when{font-size:.74rem;font-weight:700;color:#94a3b8}
.pf-thesis{background:linear-gradient(160deg,#fff 55%,#f5f3ff);border:1px solid #ddd6fe;border-radius:12px;padding:16px 18px;margin:12px 0 22px}
.pf-thesis-t{font-weight:800;font-size:.95rem;color:#5b21b6;margin-bottom:8px}
.pf-thesis .md li{font-size:.85rem}
.pf-thesis .md p{font-size:.85rem}
.pf-wt-wrap{position:relative;margin:12px 0 22px;padding-left:20px;border-left:3px solid var(--border)}
.pf-wt{position:relative;background:#fff;border:1px solid var(--border);border-radius:10px;padding:12px 16px;margin-bottom:10px;display:flex;gap:14px;align-items:baseline;flex-wrap:wrap}
.pf-wt-dot{position:absolute;left:-27px;top:16px;width:11px;height:11px;border-radius:50%;border:2px solid #fff;box-shadow:0 0 0 1px var(--border)}
.pf-wt-main{flex:1;min-width:200px}
.pf-wt-pos{font-weight:800;font-size:.92rem;color:#1a2332}
.pf-wt-org{font-weight:600;font-size:.82rem;color:#475569;margin-left:8px}
.pf-wt-note{font-size:.78rem;color:#64748b;margin-top:3px;line-height:1.6}
.pf-wt-when{font-size:.76rem;font-weight:700;color:#94a3b8;white-space:nowrap}
.pf-lin-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:12px;margin:12px 0}
.pf-lin{display:flex;gap:12px;background:#fff;border:1px solid var(--border);border-radius:10px;padding:14px 16px;box-shadow:0 1px 3px rgba(30,58,95,.05)}
.pf-lin-num{flex:none;width:26px;height:26px;border-radius:50%;color:#fff;font-weight:800;font-size:.85rem;display:flex;align-items:center;justify-content:center;margin-top:2px}
.pf-lin-name{font-weight:700;font-size:.92rem;color:#1a2332;margin-bottom:4px}
.pf-lin-sub{margin:6px 0 0 18px}
.pf-lin-sub li{font-size:.8rem;color:#475569;line-height:1.7;margin:3px 0}
.pf-dir-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:12px;margin:12px 0}
.pf-dir{background:#fff;border:1px solid var(--border);border-radius:12px;padding:14px 16px;box-shadow:0 1px 3px rgba(30,58,95,.05)}
.pf-dir-name{font-weight:800;font-size:.98rem;color:#1a2332}
.pf-dir-desc{font-size:.8rem;color:#475569;margin-top:5px;line-height:1.65}
.pf-tool{font-size:.82rem;font-weight:600;color:#0d9488;background:#f0fdfa;border:1px dashed #99f6e4;border-radius:8px;padding:8px 14px;margin:10px 0 18px}
.pf-pj-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:12px;margin:12px 0}
.pf-pj{background:#fff;border:1px solid var(--border);border-radius:12px;padding:14px 16px;box-shadow:0 1px 3px rgba(30,58,95,.05)}
.pf-pj-name{font-weight:700;font-size:.88rem;color:#1a2332;line-height:1.5}
.pf-pj-amt{font-size:1.25rem;font-weight:800;color:#2563eb;margin:6px 0 2px}
.pf-pj-period{font-size:.76rem;font-weight:700;color:#94a3b8}
.pf-pj-total{background:linear-gradient(135deg,#eff6ff,#f8fafc);border:1px solid #bfdbfe;border-radius:10px;padding:12px 16px;margin:0 0 22px;font-size:.86rem;color:#1e40af;font-weight:600;line-height:1.7}
.pf-b7-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:12px;margin:12px 0 22px}
.pf-student{background:#fff;border:1px solid var(--border);border-radius:12px;padding:14px 16px;box-shadow:0 1px 3px rgba(30,58,95,.05)}
.pf-student-d{font-size:.82rem;color:#475569;margin-top:6px;line-height:1.7}
.pv-recruit{background:#f0f9ff;border:1px dashed #93c5fd;border-radius:12px;padding:14px 16px;color:#1e40af}
.pv-recruit b{font-size:.92rem}
.pv-recruit-d{font-size:.82rem;color:#1e40af;margin-top:6px;line-height:1.7}
.pf-works{background:#fffbeb;border:1px solid #fde68a;border-radius:12px;padding:14px 18px;margin:12px 0}
.pf-works-t{font-weight:800;font-size:.9rem;color:#92400e;margin-bottom:8px}
.pf-works .md li{font-size:.84rem}
.pf-src-box{background:#f8fafc;border:1px solid var(--border);border-radius:12px;padding:14px 18px;margin:12px 0}
.pf-src-row{display:flex;gap:10px;align-items:baseline;padding:6px 0;border-bottom:1px dashed #eef2f7;font-size:.82rem;flex-wrap:wrap}
.pf-src-row:last-child{border-bottom:none}
.pf-src-nm{font-weight:700;color:#334155;min-width:180px}
.pf-src-url{color:var(--accent);word-break:break-all}
"""

# ---------- HTML ----------
head = f"""
<div class="header"><h1>李赢（Ying Li）研究整合报告</h1>
<p>中科院心理研究所副研究员 · 计量分析 × 研究时间线 × 论文清单 × 通俗读论文 × 人格画像 × 履历谱系</p>
<div class="meta"><span>共 {d['total_valid']} 条</span><span>{d['year_range']}</span>
<span>h-index {d['citations']['h_index']}</span><span>总被引 {d['citations']['total_cited']}</span>
<span>OA {d['oa_pct']}%</span><span>第一作者 {100.0*first_n/d['total_valid']:.0f}%</span></div></div>
<nav class="nav">
<a href="#overview">总览</a><a href="#insights">深度洞察</a><a href="#timeline">研究时间线</a>
<a href="#papers">论文清单</a><a href="#plain">通俗读论文</a><a href="#persona">人格画像</a><a href="#profile">履历与谱系</a><a href="#method">方法</a>
</nav>
<div class="container">
"""

overview = f"""
<div id="overview">
<div class="stats-grid">
<div class="stat-card"><div class="num">{d['total_valid']}</div><div class="label">论文总数(排除1条)</div></div>
<div class="stat-card"><div class="num">{d['types'].get('journal',0)}</div><div class="label">期刊论文</div></div>
<div class="stat-card a"><div class="num">{d['types'].get('preprint',0)+d['types'].get('conference',0)+d['types'].get('thesis',0)}</div><div class="label">预印本/会议/论文</div></div>
<div class="stat-card p"><div class="num">{100.0*first_n/d['total_valid']:.0f}%</div><div class="label">第一作者占比 {first_n}/{d['total_valid']}</div></div>
<div class="stat-card g"><div class="num">{d['citations']['h_index']}</div><div class="label">h-index</div></div>
<div class="stat-card g"><div class="num">{d['citations']['total_cited']}</div><div class="label">总被引 (OpenAlex)</div></div>
<div class="stat-card"><div class="num">{d['num_journals']}</div><div class="label">发表载体</div></div>
<div class="stat-card a"><div class="num">{d['oa_pct']}%</div><div class="label">开放获取率</div></div>
</div>
<div class="section"><h2>📈 年度发文与机构阶段</h2>
<div class="row"><div class="chart-box"><canvas id="chYear"></canvas></div>
<div class="chart-box"><canvas id="chPhase"></canvas></div></div>
<p class="note">柱=当年发表数（紫=博士华威 / 琥珀=博后MPICH / 绿=心理所），线=累计。博后期(2020–2022)为产出峰值。</p></div>
<div class="section"><h2>✍️ 作者署名层级</h2>
<div class="row"><div class="chart-box"><canvas id="chRole"></canvas></div>
<div class="chart-box"><canvas id="chRolePie"></canvas></div></div>
<p class="note">第一作者 {first_n} 篇（61%）、第二作者 2 篇、中间作者 10 篇、末作者 0 篇。独立研究者画像：以一作主导，尚未出现 PI 式末作者署名。注：J10/J16 实为共同一作（按排序计一作）。</p></div>
<div class="section"><h2>📚 发表载体分布（{d['num_journals']} 种）</h2>
<div class="chart-box" style="height:360px"><canvas id="chJournal"></canvas></div>
<p class="note">含 4 篇 CogSci 会议；顶配：PNAS×2、Cognition×2、American Psychologist、Psychological Review(in press)。J16 尚无 DOI，未计入引文。</p></div>
<div class="section"><h2>🤝 合作者网络（与 Li Ying 共同发表篇数）</h2>
<div class="row"><div class="chart-box" style="height:360px"><canvas id="chCo"></canvas></div>
<div><table id="coTable"><thead><tr><th>合作者</th><th>篇数</th><th>关系</th></tr></thead><tbody></tbody></table></div></div>
<p class="note">Hills（前导师，22/31=71%）与 Hertwig（博后导师，7）构成核心学术谱系；回国后滦盛华（6）为最主要国内合作者；Stella 线（Stella/Teixeira/Swanson/Watson 自杀研究团队）合计覆盖 10 篇。唯一合著者超过 60% 总量 → 高度稳定的小圈子合作模式。</p></div>
<div class="section"><h2>📊 引文表现（OpenAlex, 2026-09-29 快照）</h2>
<div class="chart-box" style="height:340px"><canvas id="chCit"></canvas></div>
<p class="note">工具/语料类论文引文占主导：J4 疫情情绪(85) &gt; J6 DASentimental(58) &gt; J2 风险简史(36) &gt; J1 Macroscope(35)。h=9 仍在爬坡期——2024 后 8 篇被引尚未充分累积。</p></div>
<div class="section"><h2>🔍 关键发现</h2><ul class="findings">
<li><b>独立研究者而非 PI</b>：一作 61%、末作者 0；署名结构随阶段演化——博士全一作(7/7 含会议)，博后混入中间作者(自杀团队大合作)，心理所回归一作主导(J10/J13/P10 一作)。</li>
<li><b>顶配期刊组合</b>：PNAS×2（语言演化、集体行动）+ Cognition×2 + AmPsych + PsychRev in press，15 篇期刊论文平均影响因子层级高（无低分灌水期刊）。</li>
<li><b>引文由工具驱动</b>：前两名被引（J4/J6）与方法工具（Macroscope 35、ERT 25）合计 203 引，占总引文 56%；理论类（J10 PNAS 9、J13 PNAS 1）引文滞后于发表时间，符合理论论文引文曲线。</li>
<li><b>合作圈高度集中</b>：Top1 合作者占 71%，Top3 占 90%（22+7+6=35 人次/31 篇）；跨机构长关系（Hills 线 2016–2026 未断）与致谢人格分析互证。</li>
<li><b>预印本→期刊转化率高</b>：11 篇预印本中 8 篇已转化期刊（P1→J2, P2→J3, P3→J4, P4→J5, P5→J7, P8→J10, P9→J15, P11→J13），P6/P7/P10 在途或长尾。</li>
</ul></div>
</div>
"""

insights = f"""
<div id="insights">
<div class="section"><h2>🎯 深度洞察</h2>
<div class="insight-grid">
<div class="insight"><div class="i-num">{lag_median} 年</div><div class="i-title">预印本→期刊中位时滞</div>
<div class="i-body">9 对已转化：旗舰 PNAS 2024（P8→J10）恰好 2 年——越重要的成果审稿越慢；最快 P2→J3 同年落地（0 年）。P6/P7 仍在 OSF 未期刊化。</div></div>
<div class="insight"><div class="i-num">{top3_share}%</div><div class="i-title">引文集中度（Top3/总引文）</div>
<div class="i-body">{t3txt} 合计 {top3_sum} 引，占全部 {d['citations']['total_cited']} 引——工具/语料类驱动引文，理论类（PNAS×2）引文曲线滞后。</div></div>
<div class="insight"><div class="i-num">{n_preprint_oa}/{n_preprint}</div><div class="i-title">预印本 OA 率</div>
<div class="i-body">11 篇预印本全部 OA（OSF/PsyArXiv/RS）；期刊 OA {n_journal_oa}/{n_journal}。开放科学策略自博士阶段一贯稳定。</div></div>
<div class="insight"><div class="i-num">1 条线</div><div class="i-title">学术谱系连续未断</div>
<div class="i-body">Hills（博士，合著 71%）→ Hertwig（博后，博士期间已是"非正式导师"）→ 滦盛华（心理所）。跨机构长关系 2016–2026 未断，与致谢页人格分析互证。</div></div>
<div class="insight"><div class="i-num">61% / 0</div><div class="i-title">一作率 / 末作者数</div>
<div class="i-body">独立研究者画像而非 PI：无资深通讯末作者署名；10 篇中间作者集中于博后自杀研究团队大合作。</div></div>
</div></div>
<div class="section"><h2>⏱ 预印本→期刊转化时滞（9 对）</h2>
<div class="chart-box" style="height:340px"><canvas id="chLag"></canvas></div>
<p class="note">中位 {lag_median} 年 / 均值 {sum(lags)/len(lags):.1f} 年。紫=≥2 年、琥珀=1 年、绿=0 年。P9 的 OSF 文件已被作者删除(410)，但期刊版 J15 正常发表。</p></div>
<div class="section"><h2>🧭 研究线聚类（据时间线文档）</h2>
<div class="row"><div class="chart-box"><canvas id="chTheme"></canvas></div>
<div><p class="note">8 条研究线覆盖全部 31 条有效著录。风险与决策(7) 与情绪与福祉(6) 是篇数主力；语言演化(5) 是影响力主线（PNAS×2）；临床线(5) 博后从 0 到 1；发展语义(2) 为 2025 新增长点。四个官方主题（官网）正是此聚类的收敛结果。</p></div></div></div>
</div>
"""

timeline_sec = f"""
<div id="timeline"><div class="section"><h2>🧭 研究方向演变时间线（2016–2026）</h2>
{timeline_html}</div></div>
"""

papers_sec = f"""
<div id="papers"><div class="section"><h2>📖 论文清单（32 条著录，J14 已排除标注）</h2>
<div class="filters">
<span class="flabel">类型</span>
<button class="fbtn on" data-group="type" data-val="all">全部</button>
<button class="fbtn" data-group="type" data-val="journal">期刊</button>
<button class="fbtn" data-group="type" data-val="preprint">预印本</button>
<button class="fbtn" data-group="type" data-val="conference">会议</button>
<button class="fbtn" data-group="type" data-val="thesis">论文</button>
<span class="flabel">OA</span>
<button class="fbtn on" data-group="oa" data-val="all">全部</button>
<button class="fbtn" data-group="oa" data-val="OA">OA</button>
<button class="fbtn" data-group="oa" data-val="nonOA">非OA</button>
<span class="flabel" style="margin-left:14px;color:#94a3b8">行左侧色条 = 阶段（紫=博士 / 琥珀=博后 / 绿=心理所）</span>
</div>
<div class="paper-chips">
<span class="chip">{len(papers)} 条著录</span>
<span class="chip" style="color:#2563eb;border-color:#2563eb55">期刊 {TYPE_COUNTS["journal"]}</span>
<span class="chip" style="color:#0d9488;border-color:#0d948855">预印本 {TYPE_COUNTS["preprint"]}</span>
<span class="chip" style="color:#f59e0b;border-color:#f59e0b55">会议 {TYPE_COUNTS["conference"]}</span>
<span class="chip" style="color:#8b5cf6;border-color:#8b5cf655">论文 {TYPE_COUNTS["thesis"]}</span>
<span class="chip excl-chip">⚠ J14 已排除（同名不同人）</span>
</div>
<table id="paperTable"><thead><tr><th>ID</th><th>年</th><th>载体</th><th>中文题</th><th>类型</th><th>OA</th><th>DOI</th><th>备注</th></tr></thead>
<tbody>
{paper_rows}
</tbody></table>
<p class="note">T1=博士论文（华威，112 页，已抽取用于时间线与致谢分析）；J16 无 DOI（in press）；C1–C4 无 DOI（CogSci 会议，escholarship）。</p>
</div></div>
"""

plain_sec = f"""
<div id="plain"><div class="section"><h2>💬 通俗读论文（31 篇，逐篇大白话）</h2>
{plain_legend}
{plain_intro_html}
{plain_groups_html}
<p class="note">每篇卡片讲清三件事：在干嘛 + 怎么干的 + 为什么值得记住。预印本与期刊版同源的，用卡片底部"→ 期刊版"链接跳转；上方论文清单的 ID 也可点进对应卡片。J14 为排除注（同名不同人），不计入 31 篇。</p>
</div></div>
"""

persona_sec = f"""
<div id="persona"><div class="section"><h2>🪞 人格画像（博士论文致谢页样本）</h2>
{persona_html}</div></div>
"""

lineage = """
<div class="lineage">
<div class="node" style="border-top:4px solid #94a3b8"><div class="n-ic">🏫</div><div class="n-y">2009–2013</div><div class="n-t">新加坡管理大学 · 学士</div><div class="n-s">SMU</div></div>
<div class="arrow">→</div>
<div class="node" style="border-top:4px solid #8b5cf6"><div class="n-ic">🎓</div><div class="n-y">2014–2019</div><div class="n-t">华威大学 · 硕士+博士</div><div class="n-s">导师 Thomas Hills · Leverhulme 资助</div></div>
<div class="arrow">→</div>
<div class="node" style="border-top:4px solid #f59e0b"><div class="n-ic">🔬</div><div class="n-y">2019–2022</div><div class="n-t">马普人类发展所 · 博后</div><div class="n-s">CAR 中心 · 正式导师 Ralph Hertwig</div></div>
<div class="arrow">→</div>
<div class="node" style="border-top:4px solid #10b981"><div class="n-ic">🏛️</div><div class="n-y">2022–今</div><div class="n-t">中科院心理所 · 副研究员</div><div class="n-s">滦盛华协作 + 马普双栖（2026 Partner Group 负责人）</div></div>
</div>
"""

profile_sec = f"""
<div id="profile"><div class="section"><h2>🗂 履历、导师与机构</h2>
{lineage}
{profile_html}</div></div>
"""

method_sec = """
<div id="method"><div class="section"><h2>⚠️ 方法学说明与限制</h2><ul class="findings">
<li>引文来自 OpenAlex 单快照（2026-09-29），未做跨库（WoS/Scopus）交叉；J16/T1/C1–C4 无 DOI 或无收录，引文按 0 处理。</li>
<li>署名层级按作者排序推断（末位=资深），未解析共同一作标记与通讯作者标记；C1–C4 作者列表取自 CSV notes。</li>
<li>J14 已排除（同名同姓，苏州城市学院 Ying Li，非目标人物）；J12 为 2025 年新文，0 引正常。</li>
<li>"合作者篇数"按共同发表计算，未区分主导贡献。</li>
<li>人格画像基于单页致谢文本（体裁化、社会期许影响），推断均已标注强度，详见该节"限制"。</li>
<li>研究线聚类为分析性归类（据时间线文档），一篇论文可能跨线（如 J2 兼属概念史与风险决策），此处按主线归一。</li>
</ul></div></div>
"""

footer = f"""
<footer>LiYing 论文收集项目 · 生成于 {d['generated']} · 数据源: papers_list.csv + papers_meta.json + OpenAlex + reports/{{profile,research_timeline,acknowledgement_analysis,paper_plain}}.md<br>
复现: tools/scientometrics.py → analysis/analysis_data.json → tools/render_report.py（自包含，无 CDN）</footer>
</div>
"""

# ---------- JS ----------
JS = """<script>__CHARTJS__</script>
<script>
const D = __DATA__;
const YEARS = D.year_distribution.map(x=>x.year), CNT = D.year_distribution.map(x=>x.count);
const CUM = D.cumulative.map(x=>x.count);
const PHASE = y => y<=2019 ? '#8b5cf6' : (y<=2022 ? '#f59e0b' : '#10b981');
new Chart(chYear,{data:{labels:YEARS,datasets:[
 {type:'bar',label:'当年发表',data:CNT,backgroundColor:YEARS.map(PHASE),borderRadius:4},
 {type:'line',label:'累计',data:CUM,yAxisID:'y1',borderColor:'#2563eb',backgroundColor:'#2563eb',tension:.3,pointRadius:3}]},
 options:{maintainAspectRatio:false,scales:{y:{beginAtZero:true,ticks:{precision:0}},y1:{position:'right',beginAtZero:true,grid:{drawOnChartArea:false},ticks:{precision:0}}}}});
new Chart(chPhase,{type:'doughnut',data:{labels:Object.keys(D.phases),
 datasets:[{data:Object.values(D.phases),backgroundColor:['#8b5cf6','#f59e0b','#10b981']}]},
 options:{maintainAspectRatio:false,plugins:{legend:{position:'bottom'},title:{display:true,text:'机构阶段(按发表年)'}}}});
const BYY = D.authorship.by_year, RKEYS=['first','second','middle'];
const RLABEL={first:'第一作者',second:'第二作者',middle:'中间作者'};
const RCOLOR={first:'#2563eb',second:'#0d9488',middle:'#cbd5e1'};
new Chart(chRole,{type:'bar',data:{labels:YEARS,datasets:RKEYS.map(k=>({label:RLABEL[k],data:YEARS.map(y=>(BYY[y]||{})[k]||0),
 backgroundColor:RCOLOR[k],stack:'s',borderRadius:3}))},
 options:{maintainAspectRatio:false,scales:{x:{stacked:true},y:{stacked:true,beginAtZero:true,ticks:{precision:0}}}}});
const RC=D.authorship.role_counts;
new Chart(chRolePie,{type:'doughnut',data:{labels:RKEYS.map(k=>RLABEL[k]),
 datasets:[{data:RKEYS.map(k=>RC[k]||0),backgroundColor:RKEYS.map(k=>RCOLOR[k])}]},
 options:{maintainAspectRatio:false,plugins:{legend:{position:'bottom'},title:{display:true,text:'署名层级总计'}}}});
new Chart(chJournal,{type:'bar',data:{labels:D.top_journals.map(x=>x.journal),
 datasets:[{label:'篇数',data:D.top_journals.map(x=>x.count),backgroundColor:'#2563eb',borderRadius:4}]},
 options:{indexAxis:'y',maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{x:{beginAtZero:true,ticks:{precision:0}}}}});
const CO=D.coauthors.top.slice(0,12);
new Chart(chCo,{type:'bar',data:{labels:CO.map(x=>x.name),
 datasets:[{label:'共同发表篇数',data:CO.map(x=>x.count),backgroundColor:CO.map((x,i)=>i===0?'#8b5cf6':(i===1?'#f59e0b':'#93c5fd')),borderRadius:4}]},
 options:{indexAxis:'y',maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{x:{beginAtZero:true,ticks:{precision:0}}}}});
const REL={'Thomas Hills':'前博士导师(2016-2026未断)','Ralph Hertwig':'博后导师(MPICH)',
'滦盛华':'心理所主要国内合作者','Massimo Stella':'自杀研究团队(意/澳)',
'Cynthia S. Q. Siew':'博士同辈(Warwick→学者)','Andreia Sofia Teixeira':'自杀研究团队',
'Trevor Swanson':'自杀研究团队','Annasya Masitah':'博士共同一作(ERT)',
'Ziyong Lin':'语言演化合作者','Fritz Breithaupt':'语言演化/集体行动',
'Chenran Shen-Zhang':'语言演化(心理所)','David Watson':'自杀研究团队'};
document.querySelector('#coTable tbody').innerHTML = CO.map(x=>
 `<tr><td>${x.name}</td><td><b>${x.count}</b></td><td>${REL[x.name]||'—'}</td></tr>`).join('');
const NAMES={J1:'Macroscope',J2:'风险简史',J3:'情绪回忆任务',J4:'疫情情绪',J5:'群体偏见',
J6:'DASentimental',J7:'语义历时变化',J8:'风险感知(AmPsych)',J9:'自杀遗书网络',
J10:'认知选择(PNAS)',J11:'人类vsChatGPT',J12:'少数意见',J13:'私人方案(PNAS)',
J15:'自杀遗书焦虑',P1:'P1',P2:'P2',P3:'P3',P4:'P4',P5:'P5',P6:'P6',P7:'P7',
P8:'P8',P9:'P9',P10:'P10',P11:'P11'};
const CIT=Object.entries(D.citations.by_paper).filter(([,v])=>v>0).sort((a,b)=>b[1]-a[1]).slice(0,10);
new Chart(chCit,{type:'bar',data:{labels:CIT.map(([id])=>id+' '+NAMES[id]),
 datasets:[{label:'被引',data:CIT.map(([,v])=>v),backgroundColor:'#10b981',borderRadius:4}]},
 options:{indexAxis:'y',maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{x:{beginAtZero:true,ticks:{precision:0}}}}});
const LAG=D.lag;
new Chart(chLag,{type:'bar',data:{labels:LAG.map(x=>x.pair+' '+x.name),
 datasets:[{label:'时滞(年)',data:LAG.map(x=>x.lag),backgroundColor:LAG.map(x=>x.lag>=2?'#8b5cf6':(x.lag===1?'#f59e0b':'#10b981')),borderRadius:4}]},
 options:{indexAxis:'y',maintainAspectRatio:false,plugins:{legend:{display:false},title:{display:true,text:'中位 2 年 · PNAS 2024 恰好 2 年'}},scales:{x:{beginAtZero:true,ticks:{precision:0},max:2.5}}}});
const TH=D.themes, TCOLORS=['#2563eb','#8b5cf6','#10b981','#f59e0b','#0d9488','#ef4444','#f472b6','#64748b'];
new Chart(chTheme,{type:'doughnut',data:{labels:Object.keys(TH),
 datasets:[{data:Object.values(TH),backgroundColor:TCOLORS}]},
 options:{maintainAspectRatio:false,plugins:{legend:{position:'bottom'},title:{display:true,text:'研究线著录数 (n=31)'}}}});
const FT={type:'all',oa:'all'};
function applyFilter(){
 document.querySelectorAll('#paperTable tbody tr').forEach(tr=>{
  const okT=FT.type==='all'||tr.dataset.type===FT.type;
  const okO=FT.oa==='all'||tr.dataset.oa===FT.oa;
  tr.style.display=(okT&&okO)?'':'none';
 });
}
document.querySelectorAll('.fbtn').forEach(b=>b.addEventListener('click',()=>{
 const g=b.dataset.group;FT[g]=b.dataset.val;
 document.querySelectorAll('.fbtn[data-group="'+g+'"]').forEach(x=>x.classList.toggle('on',x===b));
 applyFilter();
}));
</script>
</body></html>"""

JS = JS.replace("__DATA__", json.dumps(D, ensure_ascii=False))
# Chart.js vendored (npm registry tarball, Chart.js v4.4.7) to keep report.html self-contained
JS = JS.replace("__CHARTJS__", open(os.path.join(ROOT, "tools", "vendor", "chart.umd.min.js"), encoding="utf-8").read())

CSS_DOC = ('<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">'
           '<meta name="viewport" content="width=device-width, initial-scale=1.0">'
           '<title>李赢研究整合报告</title><style>'
           + CSS + '</style></head><body>'
           + head + overview + insights + timeline_sec + papers_sec + plain_sec + persona_sec + profile_sec + method_sec + footer + JS)
open(os.path.join(ROOT, "reports", "report.html"), "w", encoding="utf-8").write(CSS_DOC)
print("report.html written,", len(CSS_DOC), "bytes")
print("themes:", theme_counts)
print("lag median:", lag_median, "| top3 share:", top3_share, t3txt)
print("preprint OA:", n_preprint_oa, "/", n_preprint, "| journal OA:", n_journal_oa, "/", n_journal)
