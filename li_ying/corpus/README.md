# 李赢（Ying Li）论文 PDF 收集

> **本目录 = 语料层快照（可复现资产）**：下载脚本 `tools/`、数据 `analysis/`、清单 `papers_meta.json`、非学术原文 `blog/`+`wechat/`。
> **md 单一事实源在 `li_ying/` 顶层**（`reports/*.md` 已迁至上层，不在本目录内）；`report.html` 亦在 `li_ying/` 顶层。
> **PDF 不入 git**（约定）：`pdfs/` 本地保留，凭 `papers_list.csv` 的 DOI 可重下。
> **复现 report.html**：需还原本地布局（`LiYing/{reports,analysis,tools/vendor,papers_list.csv,README.md}`），运行 `tools/render_report.py`（其 `ROOT` 取脚本的上一级目录）。

**作者**：李赢，中国科学院心理研究所社会与工程心理学研究室副研究员（2019–2022 马普人类发展研究所 CAR 博后；2026 起兼马普伙伴组负责人）
**ORCID**：0000-0003-0678-9535
**建库日期**：2026-09-29
**履历/导师/机构调研**：见 [reports/profile.md](reports/profile.md)
**科学计量分析**：见 [reports/report.html](reports/report.html)（8 区块：总览/深度洞察/时间线/论文清单/通俗读论文/人格画像/履历谱系/方法，Chart.js 交互版；数据 analysis/analysis_data.json）
**方向演变时间线 / 致谢人格分析 / 通俗读论文**：[reports/research_timeline.md](reports/research_timeline.md) · [reports/acknowledgement_analysis.md](reports/acknowledgement_analysis.md) · [reports/paper_plain.md](reports/paper_plain.md)（31 篇逐篇大白话讲解，已内嵌 report.html）
**非学术写作（公众号"识心观象" / 个人网站 Blog，共 6 篇）**：[wechat/](wechat/)（微信原文 1 篇）· [blog/](blog/)（Blog 5 篇，html 原文 + md）· 分析见 Scholar4C `li_ying/public_writing_analysis.md`

## 覆盖范围

32 条记录 = 16 期刊（J1–J16）+ 11 预印本（P1–P11）+ 4 会议（CogSci 2016–2018）+ 1 博士论文（T1）。
**到手 PDF：29 个**（全部通过 magic 校验，标准命名 {YYYY}_LiYing_{jr}_{short}_{cn}.pdf）。

- 期刊 16：J1–J13、J15 已下载（14 篇）；J14 排除（同名）；J16 为 Psychological Review in-press 期刊版（= P10 同文，暂无 DOI/正文，待正式发表后补）
- 预印本 11：P1–P11（P9 的 OSF 文件已被作者删除，内容已由 J15 期刊版覆盖）
- 会议 4：CogSci 2016/2017×2/2018（escholarship 全文）
- 博士论文 1：T1 华威大学 2019《From words to mind》（WRAP 152056，15 MB）

### 排除项

| id | 论文 | 原因 |
|---|---|---|
| J14 | PRBM 2023, 10.2147/prbm.s434765 | 末作者 Ying Li 属苏州城市学院（yingli.szcityu@gmail.com），非目标作者 |

### 已知缺口

- P9（PsyArXiv m2k67，2023）：OSF 文件 410 Gone，作者删除，无法恢复；BDCC 2025 期刊版（J15）已含相同内容
- J16（Psych Rev in press）：无 DOI、无正文，待正式在线发表后补 PDF
- 中文期刊（CNKI）未覆盖（与参考项目 zhou_fuchun_papers 口径一致）

## 目录结构

```
LiYing/
├── papers_list.csv        # 32 条清单（id/year/doi/type/oa_status/jr/short/cn/notes）
├── papers_meta.json       # Crossref 元数据（title/authors/links_all）
├── still_missing_dois.txt # 科研通待下 DOI（poll 自动更新）
├── pdfs/                  # 29 个 PDF，命名 {YYYY}_LiYing_{jr}_{short}_{cn}.pdf
├── wechat/                # 公众号"识心观象"文章（1 篇：2019-03-07《让天性归天性 道德归道德》微信全文）
├── blog/                  # 个人网站 Blog 非学术写作（5 篇：html 原文 + md；nature 篇=2019 微信文 2026 修订版）
├── tools/                 # 下载器 + 科研通批处理 + 校验
│   ├── fetch_meta.py      #   Crossref 元数据解析
│   ├── dl_oa.py           #   OA 层（EPMC/Crossref links_all/直连）
│   ├── dl_preprints_osf.py#   OSF/PsyArXiv 预印本
│   ├── dl_cogsci.py       #   escholarship CogSci 会议论文
│   ├── dl_scihub.py       #   Sci-Hub（bban.top 已死，保留存档）
│   ├── dl_p9_retry.py     #   P9 多渠道重试
│   ├── ablesci_batch.py   #   科研通 check/post/poll（自 zhou_fuchun_papers 复制，load_titles 已适配本项目 CSV 列）
│   ├── ablesci_cookie.txt #   科研通 cookie
│   ├── ablesci-cli/       #   科研通 CLI（含 csrf meta 回退补丁）
│   ├── rename_verify.py   #   DOI 命名→标准命名 + PDF magic 校验 + 覆盖报告
│   ├── debug_epmc.py      #   EPMC 调试
│   ├── scientometrics.py  #   科学计量统计 + OpenAlex 引文（引文缓存 analysis/openalex_citations.json）
│   └── render_report.py   #   从 analysis/analysis_data.json 渲染 reports/report.html
├── analysis/
│   └── analysis_data.json # 计量数据（年度/署名/合作/引文）
└── reports/
    ├── coverage.md        # 逐条覆盖核对（rename_verify.py 生成）
    ├── profile.md         # 履历/导师/机构调研（含来源标注）
    ├── report.html        # 8 区块自包含交互报告（Chart.js 内联，0 外部依赖）
    ├── research_timeline.md        # 博后/博士方向演变时间线
    ├── acknowledgement_analysis.md # 致谢人格分析（证据/推断/限制分离）
    └── paper_plain.md      # 31 篇逐篇通俗讲解（md 单一事实源，内嵌 report.html）
```

## 下载优先级（执行记录）

1. **OA 层**（EPMC render / Crossref links_all / MDPI / Frontiers / OSF / escholarship）→ 到手 20 篇
2. **Sci-Hub**（sci.bban.top）→ 8 篇全部 404，镜像 2026-09 已死
3. **科研通 AbleSci** → 8 篇期刊（J2/J3/J4/J5/J8/J10/J12/J13），≤10 篇免请示；post 积分 10/篇（APA 最低 30）
4. **博士论文**（T1）→ WRAP 直连下载 15 MB

## 复现/续跑

```bash
PY="C:/Users/SCZ_2207/.workbuddy/binaries/python/versions/3.13.12/python.exe"
$PY tools/ablesci_batch.py check                # 登录+积分
echo <DOI> >> still_missing_dois.txt
$PY tools/ablesci_batch.py post --point 10 --interval 8 [--accept-warning]
$PY tools/ablesci_batch.py poll --interval 30 --timeout 7200   # 后台
$PY tools/rename_verify.py                      # 重命名+校验+coverage.md
```
