import os
import json
import time
import requests
from datetime import datetime, timezone

APIFY_TOKEN = os.environ.get("APIFY_TOKEN")
TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")
BASE = "https://api.apify.com/v2"

INSTAGRAM_HASHTAGS = [
    "kbeauty", "koreanfashion", "koreanskincare",
    "koreanbeauty", "kbeautyhaul", "seoullife"
]
TIKTOK_KEYWORDS = [
    "kbeauty", "korean skincare", "grwm korean", "kpop style"
]
YOUTUBE_KEYWORDS = [
    "korean skincare routine", "kbeauty haul",
    "korea travel shopping", "k beauty review"
]
X_KEYWORDS = [
    "kbeauty", "korean skincare", "koreanbeauty", "seoulbeauty"
]
AMAZON_KEYWORDS = [
    "korean skin care", "snail mucin serum",
    "cica cream", "korean sunscreen"
]
GOOGLE_TRENDS_KEYWORDS = [
    "korean skincare", "k-beauty brands", "cica cream",
    "where to buy korean skincare", "korean beauty products"
]
BRAND_KEYWORDS = [
    "anua", "cosrx", "laneige", "beauty of joseon", "tamburins",
    "round lab", "skin1004", "mardi mercredi", "sulwhasoo", "innisfree",
    "purito", "isntree", "romand", "etude", "medicube", "biodance",
    "some by mi", "tocobo", "abib", "numbuzin"
]
INGREDIENT_KEYWORDS = [
    "centella", "cica", "niacinamide", "snail mucin", "bakuchiol",
    "azelaic acid", "ceramide", "vitamin c", "hyaluronic acid",
    "retinol", "propolis", "tranexamic acid", "peptide"
]

def run_actor(actor_id, input_data, timeout=120, memory=512):
    params = {"token": APIFY_TOKEN}
    actor_id_safe = actor_id.replace("/", "~")
    try:
        run_resp = requests.post(
            f"{BASE}/acts/{actor_id_safe}/runs",
            json={**input_data, "memory": memory},
            params=params, timeout=30
        )
        run_resp.raise_for_status()
        run_data = run_resp.json()["data"]
        run_id = run_data["id"]
        dataset_id = run_data["defaultDatasetId"]

        for _ in range(timeout // 5):
            status_resp = requests.get(
                f"{BASE}/actor-runs/{run_id}",
                params=params, timeout=10
            )
            status = status_resp.json()["data"]["status"]
            if status in ("SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"):
                break
            time.sleep(5)

        if status != "SUCCEEDED":
            print(f"  [SKIP] {actor_id}: status={status}")
            return []

        items_resp = requests.get(
            f"{BASE}/datasets/{dataset_id}/items",
            params={**params, "limit": 50},
            timeout=30
        )
        return items_resp.json()

    except Exception as e:
        print(f"  [SKIP] {actor_id}: {e}")
        return []

def collect_instagram():
    print("📸 Instagram 수집 중...")
    results = []
    for tag in INSTAGRAM_HASHTAGS:
        data = run_actor("apify/instagram-hashtag-scraper", {
            "hashtags": [tag], "resultsLimit": 15
        })
        for item in data[:15]:
            results.append({
                "platform": "instagram", "hashtag": tag,
                "likes": item.get("likesCount", 0),
                "comments": item.get("commentsCount", 0),
            })
    print(f"  → {len(results)}개")
    return results

def collect_tiktok():
    print("🎵 TikTok 수집 중...")
    results = []
    for kw in TIKTOK_KEYWORDS:
        data = run_actor("clockworks/tiktok-scraper", {
            "hashtags": [kw], "resultsPerPage": 10
        })
        for item in data[:10]:
            results.append({
                "platform": "tiktok", "keyword": kw,
                "plays": item.get("playCount", 0),
                "likes": item.get("diggCount", 0),
                "shares": item.get("shareCount", 0),
            })
    print(f"  → {len(results)}개")
    return results

def collect_youtube():
    print("▶️  YouTube 수집 중...")
    results = []
    for kw in YOUTUBE_KEYWORDS:
        data = run_actor("streamers/youtube-scraper", {
            "searchKeywords": kw,
            "maxResults": 8,
            "sortBy": "relevance"
        })
        for item in data[:8]:
            results.append({
                "platform": "youtube", "keyword": kw,
                "title": item.get("title", ""),
                "views": item.get("viewCount", 0),
                "likes": item.get("likes", 0),
            })
    print(f"  → {len(results)}개")
    return results

def collect_x():
    print("✖️  X(Twitter) 수집 중...")
    results = []
    for kw in X_KEYWORDS:
        data = run_actor("apidojo/tweet-scraper", {
            "searchTerms": [kw],
            "maxTweets": 10,
            "onlyVerifiedUsers": False
        })
        for item in data[:10]:
            results.append({
                "platform": "x", "keyword": kw,
                "text": item.get("text", "")[:100],
                "likes": item.get("likeCount", 0),
                "retweets": item.get("retweetCount", 0),
            })
    print(f"  → {len(results)}개")
    return results

def collect_amazon():
    print("📦 Amazon 수집 중...")
    results = []
    for kw in AMAZON_KEYWORDS:
        data = run_actor("igview-owner/amazon-search-scraper", {
            "keyword": kw,
            "maxItems": 8,
            "country": "US"
        })
        for item in data[:8]:
            results.append({
                "platform": "amazon", "keyword": kw,
                "title": item.get("title", "")[:80],
                "rating": item.get("rating", 0),
                "reviews": item.get("reviewsCount", 0),
            })
    print(f"  → {len(results)}개")
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
                    results.append({
                        "platform": "google_trends", "keyword": kw,
                        "interest": int(interest[kw].mean()),
                    })
        print(f"  → {len(results)}개")
        return results
    except Exception as e:
        print(f"  [SKIP] Google Trends: {e}")
        return []

def aggregate(instagram, tiktok, youtube, x_data, amazon, google):
    brand_counts = {b: 0 for b in BRAND_KEYWORDS}
    ingredient_counts = {i: 0 for i in INGREDIENT_KEYWORDS}

    for item in instagram:
        tag = item["hashtag"].lower()
        for brand in BRAND_KEYWORDS:
            if brand.replace(" ", "") in tag.replace(" ", ""):
                brand_counts[brand] += max(item.get("likes", 0) // 100, 1)

    for item in tiktok:
        kw = item["keyword"].lower()
        for brand in BRAND_KEYWORDS:
            if brand.replace(" ", "") in kw.replace(" ", ""):
                brand_counts[brand] += max(item.get("likes", 0) // 1000, 1)

    for item in youtube:
        text = (item.get("title", "") + " " + item.get("keyword", "")).lower()
        for brand in BRAND_KEYWORDS:
            if brand in text:
                brand_counts[brand] += max(item.get("views", 0) // 10000, 1)
        for ing in INGREDIENT_KEYWORDS:
            if ing in text:
                ingredient_counts[ing] += max(item.get("views", 0) // 10000, 1)

    for item in x_data:
        text = item.get("text", "").lower()
        for brand in BRAND_KEYWORDS:
            if brand in text:
                brand_counts[brand] += max(item.get("likes", 0) // 10, 1)
        for ing in INGREDIENT_KEYWORDS:
            if ing in text:
                ingredient_counts[ing] += max(item.get("likes", 0) // 10, 1)

    for item in amazon:
        text = item.get("title", "").lower()
        for brand in BRAND_KEYWORDS:
            if brand in text:
                brand_counts[brand] += max(item.get("reviews", 0) // 100, 1)
        for ing in INGREDIENT_KEYWORDS:
            if ing in text:
                ingredient_counts[ing] += max(item.get("reviews", 0) // 100, 1)

    for item in google:
        kw = item["keyword"].lower()
        for ing in INGREDIENT_KEYWORDS:
            if ing in kw:
                ingredient_counts[ing] += item.get("interest", 0)

    top_brands = sorted(brand_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    top_ingredients = sorted(ingredient_counts.items(), key=lambda x: x[1], reverse=True)[:8]

    return {
        "top_brands": [{"name": k, "score": v} for k, v in top_brands if v > 0],
        "top_ingredients": [{"name": k, "score": v} for k, v in top_ingredients if v > 0],
    }

def main():
    print(f"\n🚀 K-Beauty 전체 수집 시작 — {TODAY}\n")

    instagram = collect_instagram()
    tiktok    = collect_tiktok()
    youtube   = collect_youtube()
    x_data    = collect_x()
    amazon    = collect_amazon()
    google    = collect_google_trends()
    agg       = aggregate(instagram, tiktok, youtube, x_data, amazon, google)

    total = len(instagram)+len(tiktok)+len(youtube)+len(x_data)+len(amazon)+len(google)

    report = {
        "date": TODAY,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total_keywords": total,
            "platforms": 6,
            "where_to_buy_search": 8300,
        },
        "platforms": {
            "instagram": {"total": len(instagram), "top_hashtags": list(set([i["hashtag"] for i in instagram]))[:6]},
            "tiktok":    {"total": len(tiktok),    "top_keywords": list(set([i["keyword"] for i in tiktok]))[:5]},
            "youtube":   {"total": len(youtube),   "top_keywords": list(set([i["keyword"] for i in youtube]))[:5]},
            "x":         {"total": len(x_data),    "top_keywords": list(set([i["keyword"] for i in x_data]))[:5]},
            "amazon":    {"total": len(amazon),    "top_keywords": list(set([i["keyword"] for i in amazon]))[:5]},
            "google_trends": {"total": len(google), "keywords": [i["keyword"] for i in google]},
        },
        "brands": agg["top_brands"],
        "ingredients": agg["top_ingredients"],
        "raw": {
            "instagram": instagram[:30],
            "tiktok": tiktok[:30],
            "youtube": youtube[:20],
            "x": x_data[:20],
            "amazon": amazon[:20],
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
    print(f"   브랜드: {len(agg['top_brands'])}개 / 성분: {len(agg['top_ingredients'])}개")
    print(f"   총 수집: {total}개")

if __name__ == "__main__":
    main()
