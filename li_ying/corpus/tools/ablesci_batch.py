# -*- coding: utf-8 -*-
"""
AbleSci (科研通) batch literature-assistance driver.
Modes:
  check  — verify login, show points, checkin if possible
  post   — create assistance requests for still-missing DOIs (consumes points)
  poll   — poll all posted assists, auto-download when files appear
State file: ablesci_assists.json  (doi -> {id, title, point, status})
"""
import sys, os, json, time, shutil, argparse
from pathlib import Path
from datetime import datetime, timedelta

BASE = Path(__file__).resolve().parent.parent          # zhou_fuchun_papers/
CLI_DIR = Path(__file__).resolve().parent / "ablesci-cli"
sys.path.insert(0, str(CLI_DIR))
from ablesci_cli import AbleSciClient, AbleSciError     # noqa: E402

COOKIE_FILE = Path(__file__).resolve().parent / "ablesci_cookie.txt"
STATE_FILE = Path(__file__).resolve().parent / "ablesci_assists.json"
PDF_DIR = BASE / "pdfs"
MISSING = BASE / "still_missing_dois.txt"
META = BASE / "papers_list.csv"
PRIORITY = BASE / "request_list.md"   # order source: P1->P2->P3 as listed


def get_client():
    cookie = COOKIE_FILE.read_text(encoding="utf-8").strip()
    dummy = COOKIE_FILE.parent / "ablesci_nocookies.txt"
    return AbleSciClient(cookie=cookie, cookie_file=dummy, allow_anonymous=False)


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {}


def save_state(st):
    STATE_FILE.write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")


def load_titles():
    import csv
    titles = {}
    with open(META, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            doi = (row.get("DOI") or row.get("doi") or "").strip()
            t = (row.get("标题") or row.get("short") or row.get("cn") or "").strip()
            if doi and t:
                titles[doi] = t
    return titles


def load_missing_order():
    """DOIs in request_list.md order if present, else still_missing order."""
    dois = [l.strip() for l in MISSING.read_text(encoding="utf-8").splitlines() if l.strip()]
    if PRIORITY.exists():
        text = PRIORITY.read_text(encoding="utf-8")
        ordered = []
        for line in text.splitlines():
            for doi in dois:
                if doi in line and doi not in ordered:
                    ordered.append(doi)
        for doi in dois:
            if doi not in ordered:
                ordered.append(doi)
        return ordered
    return dois


def mode_check(client):
    try:
        st = client.checkin_status()
    except AbleSciError as e:
        print("LOGIN_CHECK_FAILED:", e)
        return 1
    print(json.dumps(st, ensure_ascii=False))
    if st.get("can_checkin"):
        try:
            r = client.checkin()
            print("checkin:", json.dumps(r, ensure_ascii=False))
            st = client.checkin_status()
        except AbleSciError as e:
            print("checkin failed:", e)
    print("POINTS:", st.get("points"))
    return 0


def mode_post(client, limit, interval, point, accept_warning=False):
    st = load_state()
    titles = load_titles()
    dois = [d for d in load_missing_order() if d not in st or not st[d].get("id")]
    status = client.checkin_status()
    points = status.get("points") or 0
    print(f"points available: {points}, to post: {len(dois)}")
    budget = int(point)
    posted = []
    for doi in dois:
        if limit and len(posted) >= limit:
            print(f"limit reached ({limit}), stop posting")
            break
        if points - budget < 0:
            print(f"NOT ENOUGH POINTS: stop before {doi}")
            break
        title = titles.get(doi, doi)
        print(f"[POST] {doi} | {title[:60]}", flush=True)
        try:
            lk = client.lookup(doi)
            data = lk.get("data") or {}
            if lk.get("code") != 0 or not data.get("title"):
                print("   lookup failed:", str(lk)[:200])
                st[doi] = {"id": None, "error": "lookup_failed", "detail": str(lk)[:200]}
                save_state(st)
                continue
            min_point = int(data.get("min_point") or 10)
            use_point = max(min_point, int(point))
            if points - use_point < 0:
                print(f"   not enough points for min {min_point}, stop")
                st[doi] = {"id": None, "error": "insufficient_points", "min_point": min_point}
                save_state(st)
                break
            args = argparse.Namespace(
                doi=doi, title=data.get("title") or title, url=data.get("url") or "",
                type=None, point=use_point, note="", remark="",
                supplement=False, close_at=None, yes=True, accept_warning=accept_warning,
            )
            created = client.create(args, data)
            aid = None
            d = created.get("data") or {}
            aid = d.get("id") or (str(d.get("url") or "").split("id=")[-1] or None)
            print(f"   OK assist_id={aid} point={use_point}")
            st[doi] = {"id": aid, "title": data.get("title"), "point": use_point,
                       "status": "posted", "created": datetime.now().isoformat(timespec="seconds")}
            save_state(st)
            points -= use_point
            posted.append(doi)
        except AbleSciError as e:
            msg = str(e)
            print("   ERR:", msg[:200])
            st[doi] = {"id": None, "error": "create_failed", "detail": msg[:300]}
            save_state(st)
            if "积分" in msg or "point" in msg.lower():
                break
        time.sleep(interval)
    print(f"posted {len(posted)} new assists. points left approx: {points}")
    return 0


def mode_poll(client, interval, timeout):
    st = load_state()
    deadline = time.monotonic() + timeout
    got = []
    while time.monotonic() < deadline:
        pending = [d for d, v in st.items() if v.get("id") and v.get("status") != "downloaded"]
        if not pending:
            print("no pending assists.")
            break
        for doi in pending:
            aid = st[doi]["id"]
            try:
                det = client.detail(aid)
            except AbleSciError as e:
                print(f"[{aid}] detail err: {str(e)[:120]}")
                continue
            if det["downloads"]:
                ok = False
                for attempt in range(3):
                    try:
                        tmp_out = PDF_DIR
                        saved = client.download(aid, tmp_out)
                        target = PDF_DIR / (doi.replace("/", "_") + ".pdf")
                        if Path(saved) != target:
                            if target.exists():
                                target.unlink()
                            shutil.move(str(saved), str(target))
                        st[doi]["status"] = "downloaded"
                        st[doi]["saved"] = target.name
                        save_state(st)
                        got.append(doi)
                        print(f"[{aid}] DOWNLOADED -> {target.name}", flush=True)
                        ok = True
                        break
                    except AbleSciError as e:
                        print(f"[{aid}] download err (attempt {attempt+1}/3): {str(e)[:160]}", flush=True)
                    except (TimeoutError, OSError, Exception) as e:
                        print(f"[{aid}] net err (attempt {attempt+1}/3): {type(e).__name__}: {str(e)[:120]}", flush=True)
                    time.sleep(15)
                if not ok:
                    st[doi]["status"] = "download_retry_later"
                    save_state(st)
            else:
                state = "completed_nofile" if det["completed"] else "waiting"
                st[doi]["status"] = state
                save_state(st)
        # update missing file
        remaining = [d for d, v in st.items() if v.get("status") != "downloaded"]
        done = [d for d, v in st.items() if v.get("status") == "downloaded"]
        all_dois = load_missing_order()
        still = [d for d in all_dois if d not in done]
        MISSING.write_text("\n".join(still) + "\n", encoding="utf-8")
        if done:
            print(f"progress: downloaded={len(done)} still={len(still)}", flush=True)
        if not [d for d, v in st.items() if v.get("id") and v.get("status") not in ("downloaded", "completed_nofile")]:
            pass
        time.sleep(interval)
    print("poll ended. downloaded this session:", len(got))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["check", "post", "poll"])
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--interval", type=int, default=20)
    ap.add_argument("--point", type=int, default=10)
    ap.add_argument("--timeout", type=int, default=3600)
    ap.add_argument("--accept-warning", action="store_true")
    args = ap.parse_args()
    client = get_client()
    if args.mode == "check":
        sys.exit(mode_check(client))
    elif args.mode == "post":
        sys.exit(mode_post(client, args.limit, args.interval, args.point, args.accept_warning))
    elif args.mode == "poll":
        sys.exit(mode_poll(client, args.interval, args.timeout))


if __name__ == "__main__":
    main()
