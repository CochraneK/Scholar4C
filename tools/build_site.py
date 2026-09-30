#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_site.py — Scholar4C 多学者档案站生成器（目录窗口版）

约定：
  <repo>/{scholar}/report.html   学者报告（必需）
  <repo>/{scholar}/card.json     学者卡片（可选，缺省时自动从 report 抽取）

输出（构建目录 site/，不入库）：
  site/index.html               首页目录窗口，自动聚合全部学者
  site/{scholar}/index.html     = report.html 拷贝

用法：
  python build_site.py            # 仅构建
  python build_site.py --deploy   # 构建 + 部署到 GitHub Pages（CochraneK/scholar-archive）
                                  # token 自动从 Novel2game → Scholar4C 的 .git/config remote 探测（试哪个 API 活）

card.json 字段（均可选，缺省走 fallback）：
  name / en / role / fields[] / oneliner / years
  stats: [["32","论文著录"], ...]
  color: "#8b5cf6"
"""
import base64, datetime, html as H, json, os, re, shutil, sys, time, urllib.request, urllib.error

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO, 'site')
GITHUB_REPO = 'CochraneK/scholar-archive'
COLORS = ['#2563eb', '#8b5cf6', '#10b981', '#f59e0b', '#0d9488']

CSS = """
:root{--bg:#f5f7fa;--card:#fff;--text:#1a2332;--accent:#2563eb;--border:#e0e6ed;--purple:#8b5cf6;--amber:#f59e0b;--green:#10b981;--gray:#94a3b8;}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;background:var(--bg);color:var(--text);line-height:1.6}
.header{background:linear-gradient(135deg,#1e3a5f,#2563eb);color:#fff;padding:48px 24px;text-align:center}
.header h1{font-size:1.9rem;font-weight:700;margin-bottom:8px}
.header p{opacity:.9}
.header .meta{margin-top:14px;display:flex;gap:12px;justify-content:center;flex-wrap:wrap}
.header .meta span{background:rgba(255,255,255,.15);padding:4px 16px;border-radius:20px;font-size:.88rem}
.container{max-width:1100px;margin:0 auto;padding:28px 24px}
.sch-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(440px,1fr));gap:20px}
.sch-card{display:block;background:var(--card);border:1px solid var(--border);border-radius:14px;
padding:22px 24px;text-decoration:none;color:var(--text);box-shadow:0 1px 3px rgba(0,0,0,.06);
transition:box-shadow .15s,transform .15s;overflow:hidden}
.sch-card:hover{box-shadow:0 6px 18px rgba(37,99,235,.16);transform:translateY(-2px)}
.sch-card::before{content:"";display:block;height:5px;background:var(--c,#2563eb);margin:-22px -24px 16px}
.sch-top{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap}
.sch-name{font-size:1.45rem;font-weight:800}
.sch-en{color:var(--gray);font-size:.95rem;font-weight:600}
.sch-role{margin-top:4px;font-size:.9rem;color:#475569;font-weight:600}
.chips{margin-top:10px;display:flex;gap:8px;flex-wrap:wrap}
.chips span{background:#eef2ff;color:#3730a3;border:1px solid #c7d2fe;font-size:.78rem;font-weight:600;padding:3px 12px;border-radius:14px}
.sch-one{margin-top:12px;font-size:.9rem;color:#263243;background:#fafbff;border-left:3px solid var(--c,#2563eb);
padding:10px 14px;border-radius:0 10px 10px 0;line-height:1.8;font-style:italic}
.sch-foot{margin-top:14px;display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap}
.sch-stats{font-size:.82rem;color:#64748b}
.sch-go{font-size:.9rem;font-weight:700;color:var(--accent)}
.sch-card:hover .sch-go{text-decoration:underline}
.note{margin-top:26px;background:var(--card);border:1px dashed var(--border);border-radius:12px;padding:14px 18px;font-size:.85rem;color:#64748b}
.footer{text-align:center;color:#94a3b8;font-size:.8rem;padding:26px}
"""


def scan_scholars():
    out = []
    for d in sorted(os.listdir(REPO)):
        p = os.path.join(REPO, d)
        if d.startswith(('.', '_')) or d in ('tools', 'site'):
            continue
        if os.path.isdir(p) and os.path.isfile(os.path.join(p, 'report.html')):
            out.append(d)
    return out


def fallback_card(scholar, i):
    t = open(os.path.join(REPO, scholar, 'report.html'), encoding='utf-8', errors='replace').read()
    m = re.search(r'<title>(.*?)</title>', t)
    name = (m.group(1) if m else scholar).replace('研究整合报告', '').strip() or scholar
    hero = re.search(r'<div class="pv-hero">(.*?)</div>', t, re.S)
    one = H.unescape(hero.group(1)).strip() if hero else ''
    if len(one) > 100:
        one = one[:100] + '…'
    papers = len(re.findall(r'class="type-pill', t))
    return {
        'name': name, 'role': '', 'fields': [], 'oneliner': one, 'years': '',
        'stats': [[str(papers), '论文著录']] if papers else [],
        'color': COLORS[i % len(COLORS)],
    }


def scholar_card(scholar, card, i):
    c = card if card is not None else fallback_card(scholar, i)
    color = c.get('color') or COLORS[i % len(COLORS)]
    fields = ''.join('<span>%s</span>' % H.escape(f) for f in c.get('fields', []))
    stats = ' · '.join('%s %s' % (v, l) for v, l in c.get('stats', []))
    en, role, years = c.get('en', ''), c.get('role', ''), c.get('years', '')
    foot = ' · '.join(x for x in [years, stats] if x)
    return (
        '<a class="sch-card" style="--c:%s" href="%s/">\n'
        '<div class="sch-top"><span class="sch-name">%s</span>%s</div>\n'
        '%s%s%s\n'
        '<div class="sch-foot"><span class="sch-stats">%s</span><span class="sch-go">进入完整报告 →</span></div>\n'
        '</a>'
    ) % (
        color, scholar,
        H.escape(c.get('name', scholar)),
        ('<span class="sch-en">%s</span>' % H.escape(en)) if en else '',
        ('<div class="sch-role">%s</div>' % H.escape(role)) if role else '',
        ('<div class="chips">%s</div>' % fields) if fields else '',
        ('<div class="sch-one">“%s”</div>' % H.escape(c.get('oneliner', ''))) if c.get('oneliner') else '',
        H.escape(foot),
    )


def build():
    scholars = scan_scholars()
    if not scholars:
        sys.exit('未找到学者（缺 {scholar}/report.html）')
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    cards = []
    for i, s in enumerate(scholars):
        os.makedirs(os.path.join(OUT, s))
        shutil.copy2(os.path.join(REPO, s, 'report.html'), os.path.join(OUT, s, 'index.html'))
        cp = os.path.join(REPO, s, 'card.json')
        card = json.load(open(cp, encoding='utf-8')) if os.path.isfile(cp) else None
        cards.append(scholar_card(s, card, i))
    today = datetime.date.today().isoformat()
    page = (
        '<!DOCTYPE html>\n<html lang="zh"><head><meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
        '<title>Scholar4C · 学者研究档案库</title>\n<style>' + CSS + '</style></head>\n<body>\n'
        '<div class="header"><h1>Scholar4C · 学者研究档案库</h1>\n'
        '<p>每位学者一份自包含研究整合报告 —— 零外部依赖，离线可开</p>\n'
        '<div class="meta"><span>%d 位学者</span><span>更新 %s</span><span>数据源 Scholar4C 档案层</span></div></div>\n'
        '<div class="container">\n<div class="sch-grid">%s</div>\n'
        '<div class="note">每位学者的报告为完全自包含单文件 HTML（图表内联）。目录页由 build_site.py 自动生成，'
        '随档案层增长：在 Scholar4C 仓库新增 {scholar}/report.html（可附 card.json 定制首页卡片），'
        '重跑 python tools/build_site.py --deploy 即可。</div>\n</div>\n'
        '<div class="footer">Scholar4C · build_site.py 自动生成 · %s</div>\n</body></html>'
    ) % (len(scholars), today, ''.join(cards), today)
    open(os.path.join(OUT, 'index.html'), 'w', encoding='utf-8').write(page)
    print('built: %d 学者 → %s' % (len(scholars), OUT))
    for s in scholars:
        print('   ', s)
    return scholars


def get_token():
    for cand in (r'D:\Software\DSH\Novel2game', REPO):
        cfg = os.path.join(cand, '.git', 'config')
        if not os.path.isfile(cfg):
            continue
        m = re.search(r'url\s*=\s*https://[^@/]+:([^@]+)@github\.com',
                      open(cfg, encoding='utf-8', errors='replace').read())
        if not m:
            continue
        tok = m.group(1)
        try:
            req = urllib.request.Request('https://api.github.com/user',
                                         headers={'Authorization': 'token ' + tok, 'User-Agent': 'wb'})
            urllib.request.urlopen(req, timeout=15)
            print('token ok ←', os.path.basename(cand))
            return tok
        except Exception:
            continue
    sys.exit('未找到有效 GitHub API 令牌（已试 Novel2game / Scholar4C remote）')


def api(tok, method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request('https://api.github.com' + path, data=data, method=method,
                                 headers={'Authorization': 'token ' + tok, 'Accept': 'application/vnd.github+json',
                                          'User-Agent': 'wb', 'Content-Type': 'application/json'})
    try:
        r = urllib.request.urlopen(req, timeout=60)
        b = r.read()
        return r.status, (json.loads(b) if b else {})
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b'{}')


def deploy():
    tok = get_token()
    for root, _, files in os.walk(OUT):
        for f in sorted(files):
            fp = os.path.join(root, f)
            rel = os.path.relpath(fp, OUT).replace(os.sep, '/')
            b64 = base64.b64encode(open(fp, 'rb').read()).decode().replace('\n', '')
            s, d = api(tok, 'GET', '/repos/%s/contents/%s' % (GITHUB_REPO, rel))
            body = {'content': b64, 'message': 'site: update %s' % rel}
            if s == 200 and d.get('sha'):
                body['sha'] = d['sha']
            s, d = api(tok, 'PUT', '/repos/%s/contents/%s' % (GITHUB_REPO, rel), body)
            ok = s in (200, 201)
            print(('PUT ok   ' if ok else 'PUT FAIL %s ' % s) + rel,
                  ('' if ok else json.dumps(d, ensure_ascii=False)[:200]))
    for i in range(10):
        time.sleep(15)
        s, d = api(tok, 'GET', '/repos/%s/pages' % GITHUB_REPO)
        st = d.get('status')
        print('pages poll %d: %s %s' % (i + 1, st, d.get('html_url')))
        if st == 'built':
            break
    print('done: https://cochranek.github.io/scholar-archive/')


if __name__ == '__main__':
    build()
    if '--deploy' in sys.argv:
        deploy()
