#!/usr/bin/env python3
"""BODY SPA - Sanity CMS からスケジュール・セラピストデータを収集"""

import urllib.parse
import json
import urllib.request
import os
from datetime import datetime, timedelta, timezone

JST = timezone(timedelta(hours=9))
SANITY_PROJECT = "64ec3zln"
SANITY_DATASET = "production"
API_VERSION = "2021-03-25"
BASE_URL = f"https://{SANITY_PROJECT}.api.sanity.io/v{API_VERSION}/data/query/{SANITY_DATASET}"

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


def query_sanity(groq_query: str):
    """Sanity GROQ クエリ実行"""
    url = f"{BASE_URL}?query={urllib.parse.quote(groq_query)}"
    req = urllib.request.Request(url, headers={"User-Agent": "BodySPA-Analytics/1.0"})
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())
    return data.get("result", [])


def collect():
    now = datetime.now(JST)
    print(f"[{now.strftime('%Y-%m-%d %H:%M JST')}] データ収集開始")

    # 1. 全在籍セラピスト
    therapists = query_sanity('''
        *[_type=="therapist" && enrollment==true]{
            _id, name, newTherapist, englishOk,
            "enrollDate": from,
            body[]{children[]{text}},
            image{asset->{_id,url}},
            profileImageItems[]{image{asset->{_id,url}}},
            lineUrl, slug,
            store->{_id,name}
        } | order(orderRank asc)
    ''')
    print(f"  セラピスト: {len(therapists)}名")

    # 2. スケジュール（直近6ヶ月分）
    six_months_ago = (now - timedelta(days=180)).strftime("%Y-%m-%d")
    schedules = query_sanity(f'''
        *[_type=="schedule" && defined(therapist) && defined(from) && from >= "{six_months_ago}"]{{
            from, to,
            therapist->{{_id,name}},
            store->{{_id,name}}
        }} | order(from asc)
    ''')
    print(f"  スケジュール: {len(schedules)}件")

    # 3. 店舗
    stores = query_sanity('*[_type=="store"]{_id,name}')
    print(f"  店舗: {len(stores)}")

    data = {
        "therapists": therapists,
        "schedules": schedules,
        "stores": stores,
        "fetched_at": now.isoformat(),
    }

    os.makedirs(DATA_DIR, exist_ok=True)
    path = os.path.join(DATA_DIR, "raw_data.json")
    with open(path, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)

    print(f"  保存: {path} ({os.path.getsize(path)/1024:.0f} KB)")
    return data


if __name__ == "__main__":
    collect()
