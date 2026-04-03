#!/usr/bin/env python3
"""raw_data.json → dashboard_data.json + docs/index.html に埋め込み"""

import json
import os
from datetime import datetime, timedelta, timezone
from collections import defaultdict, Counter

JST = timezone(timedelta(hours=9))
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DOCS_DIR = os.path.join(BASE_DIR, "docs")

DAY_NAMES_JP = ["月", "火", "水", "木", "金", "土", "日"]


def clean_store(name):
    if not name:
        return "不明"
    for suffix in [" -Shinbashi-", " -Nishikasai-", " -Chiba-"]:
        name = name.replace(suffix, "")
    if name == "BODYSPA.Group":
        return "本部"
    return name


def img_url(asset, w=400):
    if isinstance(asset, dict):
        url = asset.get("url", "")
        if url:
            return f"{url}?w={w}&h={int(w*1.5)}&fit=crop"
    return ""


def body_text(body):
    if not body:
        return ""
    lines = []
    for block in body:
        for c in block.get("children", []):
            t = c.get("text", "").strip()
            if t:
                lines.append(t)
    return "\n".join(lines)


def parse_datetime(s):
    if not s:
        return None
    try:
        if "Z" in s:
            return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(JST)
        elif "+" in s[10:] or (len(s) > 19 and "-" in s[19:]):
            return datetime.fromisoformat(s).astimezone(JST)
        else:
            return datetime.fromisoformat(s).replace(tzinfo=JST)
    except Exception:
        return None


def export():
    now = datetime.now(JST)
    today = now.date().isoformat()
    print(f"[{now.strftime('%Y-%m-%d %H:%M JST')}] ダッシュボードデータ生成")

    with open(os.path.join(DATA_DIR, "raw_data.json")) as f:
        raw = json.load(f)

    therapists = raw["therapists"]
    schedules = raw["schedules"]
    stores = raw["stores"]

    # セラピストマップ
    t_map = {}
    for t in therapists:
        tid = t["_id"]
        store = clean_store((t.get("store") or {}).get("name", ""))
        main_img = ""
        if t.get("image") and t["image"].get("asset"):
            main_img = img_url(t["image"]["asset"])
        t_map[tid] = {
            "id": tid,
            "name": t["name"],
            "store": store,
            "new": t.get("newTherapist", False),
            "english": t.get("englishOk", False),
            "enroll_date": t.get("enrollDate", ""),
            "description": body_text(t.get("body")),
            "image": main_img,
            "line_url": t.get("lineUrl", ""),
            "slug": (t.get("slug") or {}).get("current", ""),
        }

    # スケジュール集計
    stats = defaultdict(lambda: {
        "total_days": 0,
        "month_counts": Counter(),
        "weekday_counts": Counter(),
        "avg_hours": [],
        "recent_dates": [],
        "stores_worked": set(),
    })

    # 4/18 の週
    target_week_start = "2026-04-13"
    target_week_end = "2026-04-20"
    week_schedules = defaultdict(list)

    for s in schedules:
        tid = (s.get("therapist") or {}).get("_id")
        if not tid or tid not in t_map:
            continue

        fr = parse_datetime(s.get("from"))
        to = parse_datetime(s.get("to"))
        if not fr or not to:
            continue

        date_str = fr.strftime("%Y-%m-%d")
        month_str = fr.strftime("%Y-%m")
        wd = fr.weekday()
        hours = (to - fr).total_seconds() / 3600
        store_name = clean_store((s.get("store") or {}).get("name", ""))

        st = stats[tid]
        st["total_days"] += 1
        st["month_counts"][month_str] += 1
        st["weekday_counts"][wd] += 1
        st["avg_hours"].append(hours)
        st["recent_dates"].append(date_str)
        st["stores_worked"].add(store_name)

        if target_week_start <= date_str <= target_week_end:
            week_schedules[date_str].append({
                "name": t_map[tid]["name"],
                "store": t_map[tid]["store"],
                "from": fr.strftime("%H:%M"),
                "to": to.strftime("%H:%M"),
            })

    # ダッシュボード用セラピストデータ構築
    dashboard_therapists = []
    for tid, info in t_map.items():
        st = stats.get(tid, defaultdict(lambda: None))
        total = st.get("total_days", 0) if isinstance(st, dict) else 0
        hrs = st.get("avg_hours", []) if isinstance(st, dict) else []
        avg_h = round(sum(hrs) / len(hrs), 1) if hrs else 0

        wd_counts = st.get("weekday_counts", Counter()) if isinstance(st, dict) else Counter()
        wd_dist = [wd_counts.get(i, 0) for i in range(7)]

        mc = dict(sorted((st.get("month_counts", Counter()) if isinstance(st, dict) else Counter()).items()))
        recent = sorted(set(st.get("recent_dates", []) if isinstance(st, dict) else []))[-10:]

        if recent and len(recent) > 1:
            first = datetime.strptime(recent[0], "%Y-%m-%d")
            last = datetime.strptime(recent[-1], "%Y-%m-%d")
            weeks = max(1, (last - first).days / 7)
            freq = round(total / weeks, 1)
        else:
            freq = 0

        shifts_recent = st.get("recent_dates", [])[-20:] if isinstance(st, dict) else []
        stores_worked = list(st.get("stores_worked", set()) if isinstance(st, dict) else set())

        dashboard_therapists.append({
            **info,
            "total_days": total,
            "avg_hours": avg_h,
            "weekday_dist": wd_dist,
            "monthly": mc,
            "recent_dates": recent,
            "freq_per_week": freq,
            "stores_worked": stores_worked,
        })

    dashboard_therapists.sort(key=lambda x: x["total_days"], reverse=True)

    dashboard = {
        "therapists": dashboard_therapists,
        "week_apr18": {k: v for k, v in sorted(week_schedules.items())},
        "total_schedules": len(schedules),
        "date_range": {
            "from": min((s.get("from", "")[:10] for s in schedules if s.get("from")), default=""),
            "to": max((s.get("from", "")[:10] for s in schedules if s.get("from")), default=""),
        },
        "generated_at": now.isoformat(),
        "today": today,
        "stores": [{"id": s["_id"], "name": clean_store(s["name"])} for s in stores],
    }

    # Save dashboard data
    with open(os.path.join(DATA_DIR, "dashboard_data.json"), "w") as f:
        json.dump(dashboard, f, ensure_ascii=False, indent=1)

    # Embed into HTML
    html_path = os.path.join(DOCS_DIR, "index.html")
    with open(html_path) as f:
        html = f.read()

    placeholder = "const DATA = DASHBOARD_DATA_PLACEHOLDER;"
    replacement = f"const DATA = {json.dumps(dashboard, ensure_ascii=False)};"

    if placeholder in html:
        html = html.replace(placeholder, replacement)
        with open(html_path, "w") as f:
            f.write(html)
        print(f"  HTML にデータ埋め込み完了")
    else:
        print(f"  ⚠️ プレースホルダーなし（既に埋め込み済みか初回生成）")

    print(f"  セラピスト: {len(dashboard_therapists)}名")
    print(f"  4/18の週: {sum(len(v) for v in week_schedules.values())}件")


if __name__ == "__main__":
    export()
