import os
import json
import requests
from datetime import datetime, timezone

APIFY_TOKEN = os.environ.get("APIFY_TOKEN")
TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")

HEADERS = {"Authorization": f"Bearer {APIFY_TOKEN}"}

INSTAGRAM_HASHTAGS = [
    "kbeauty", "koreanfashion", "koreanskincare",
    "koreanbeauty", "kbeautyhaul", "seoullife"
]

TIKTOK_KEYWORDS = [
    "kbeauty", "korean skincare", "koreanskincare haul",
    "grwm korean", "kpop style"
]

GOOGLE_TRENDS_KEYWORDS = [
    "korean skincare", "k-beauty brands", "cica cream",
    "duty free korea", "where to buy korean skincare"
]

def run_actor(actor_id, input_data):
    url = f"https://api.apify.com/v2/acts/{actor_id}/run-sync-get-dataset-items"
    params = {"token": APIFY_TOKEN, "timeout": 120, "memory": 256}
    try:
        resp = requests.post(url, json=input_data, params=params, timeout=150)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"[ERROR] Actor {actor_id} 실패: {e}")
        return []

def collect_instagram():
    print("📸 Instagram 수집 중...")
    results = []
    for tag in INSTAGRAM_HASHTAGS:
        data = run_actor("apify/instagram-hashtag-scraper", {
            "hashtags": [tag],
            "resultsLimit": 20
        })
        for item in data[:20]:
            results.append({
                "platform": "instagram",
                "hashtag": tag,
                "likes": item.get("likesCount", 0),
                "comments": item.get("commentsCount", 0),
                "timestamp": item.get("timestamp", ""),
            })
    print(f"  → {len(results)}개 수집")
    return results

def collect_tiktok():
    print("🎵 TikTok 수집 중...")
    results = []
    for kw in TIKTOK_KEYWORDS:
        data = run_actor("clockworks/tiktok-scraper", {
            "hashtags": [kw],
            "resultsPerPage": 10
        })
        for item in data[:10]:
            results.append({
                "platform": "tiktok",
                "keyword": kw,
                "plays": item.get("playCount", 0),
                "likes": item.get("diggCount", 0),
                "shares": item.get("shareCount", 0),
            })
    print(f"  → {len(results)}개 수집")
    return results

def collect_google_trends():
    print("🔍 Google Trends 수집 중...")
    try:
        from pytrends.request import TrendReq
        pytrends = TrendReq(hl="en-US", tz=0)
        results = []
        pytrends.build_payload(GOOGLE_TRENDS_KEYWORDS[:5], timeframe="now 7-d", geo="")
        interest = pytrends.interest_over_time()
        if not interest.empty:
            for kw in GOOGLE_TRENDS_KEYWORDS[:5]:
                if kw in interest.columns:
                    avg = int(interest[kw].mean())
                    results.append({
                        "platform": "google_trends",
                        "keyword": kw,
                        "interest": avg,
                    })
        print(f"  → {len(results)}개 수집")
        return results
    except Exception as e:
        print(f"[ERROR] Google Trends 실패: {e}")
        return []

def aggregate(instagram, tiktok, google):
    brand_keywords = [
        "anua", "cosrx", "laneige", "beauty of joseon", "tamburins",
        "round lab", "skin1004", "mardi mercredi", "sulwhasoo", "innisfree",
        "purito", "isntree", "romand", "etude", "medicube", "biodance"
    ]
    ingredient_keywords = [
        "centella", "cica", "niacinamide", "snail mucin", "bakuchiol",
        "azelaic acid", "ceramide", "vitamin c", "hyaluronic acid", "retinol"
    ]
    brand_counts = {b: 0 for b in brand_keywords}
    ingredient_counts = {i: 0 for i in ingredient_keywords}

    for item in instagram:
        tag = item["hashtag"].lower()
        for brand in brand_keywords:
            if brand.replace(" ", "") in tag.replace(" ", ""):
                brand_counts[brand] += item.get("likes", 0) // 100

    for item in google:
        kw = item["keyword"].lower()
        for ing in ingredient_keywords:
            if ing in kw:
                ingredient_counts[ing] += item.get("interest", 0)

    top_brands = sorted(brand_counts.items(), key=lambda x: x[1], reverse=True)[:8]
    top_ingredients = sorted(ingredient_counts.items(), key=lambda x: x[1], reverse=True)[:6]

    return {
        "top_brands": [{"name": k, "score": v} for k, v in top_brands if v > 0],
        "top_ingredients": [{"name": k, "score": v} for k, v in top_ingredients if v > 0],
    }

def main():
    print(f"\n🚀 K-Beauty 트렌드 수집 시작 — {TODAY}\n")
    instagram = collect_instagram()
    tiktok = collect_tiktok()
    google = collect_google_trends()
    aggregated = aggregate(instagram, tiktok, google)

    report = {
        "date": TODAY,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total_keywords": len(instagram) + len(tiktok) + len(google),
            "platforms": 3,
            "where_to_buy_search": 8300,
        },
        "platforms": {
            "instagram": {"total": len(instagram), "top_hashtags": list(set([i["hashtag"] for i in instagram]))[:6]},
            "tiktok": {"total": len(tiktok), "top_keywords": list(set([i["keyword"] for i in tiktok]))[:5]},
            "google_trends": {"total": len(google), "keywords": [i["keyword"] for i in google]}
        },
        "brands": aggregated["top_brands"],
        "ingredients": aggregated["top_ingredients"],
        "raw": {
            "instagram": instagram[:50],
            "tiktok": tiktok[:50],
            "google": google
        }
    }

    os.makedirs("data", exist_ok=True)
    filepath = f"data/{TODAY}.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    with open("data/latest.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 완료! {filepath}")

if __name__ == "__main__":
    main()
