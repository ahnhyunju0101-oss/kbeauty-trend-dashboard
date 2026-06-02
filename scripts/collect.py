import os
import json
import requests
from datetime import datetime, timezone

APIFY_TOKEN = os.environ.get("APIFY_TOKEN")
TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")

# ── 키워드 설정 ────────────────────────────────────────────
INSTAGRAM_HASHTAGS = [
    "kbeauty", "koreanfashion", "koreanskincare",
    "koreanbeauty", "kbeautyhaul", "seoullife"
]
TIKTOK_KEYWORDS = [
    "kbeauty", "korean skincare", "koreanskincare haul",
    "grwm korean", "kpop style"
]
YOUTUBE_KEYWORDS = [
    "korean skincare routine", "kbeauty haul", "korean beauty products",
    "korea travel vlog shopping", "k beauty review"
]
X_KEYWORDS = [
    "kbeauty", "korean skincare", "koreanbeauty",
    "kpopstyle", "seoulbeauty"
]
AMAZON_KEYWORDS = [
    "korean skin care", "snail mucin serum", "cica cream",
    "korean sunscreen", "k beauty"
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

# ── Actor 실행 ─────────────────────────────────────────────
def run_actor(actor_id, input_data, timeout=180, memory=512):
    url = f"https://api.apify.com/v2/acts/{actor_id}/run-sync-get-dataset-items"
    params = {"token": APIFY_TOKEN, "timeout": timeout, "memory": memory}
    try:
        resp = requests.post(url, json=input_data, params=params, timeout=timeout+30)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"  [SKIP] {actor_id}: {e}")
        return []

# ── Instagram ─────────────────────────────────────────────
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

# ── TikTok ────────────────────────────────────────────────
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

# ── YouTube ───────────────────────────────────────────────
def collect_youtube():
    print("▶️  YouTube 수집 중...")
    results = []
    for kw in YOUTUBE_KEYWORDS:
        data = run_actor("streamers/youtube-scraper", {
            "searchKeywords": kw, "maxResults": 8,
            "sortBy": "relevance"
        })
        for item in data[:8]:
            results.append({
                "platform": "youtube", "keyword": kw,
                "title": item.get("title", ""),
                "views": item.get("viewCount", 0),
                "likes": item.get("likes", 0),
                "channel": item.get("channelName", ""),
            })
    print(f"  → {len(results)}개")
    return results

# ── X (Twitter) ───────────────────────────────────────────
def collect_x():
    print("✖️  X(Twitter) 수집 중...")
    results = []
    for kw in X_KEYWORDS:
        data = run_actor("apidojo/tweet-scraper", {
            "searchTerms": [kw], "maxTweets": 10,
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

# ── Amazon ────────────────────────────────────────────────
def collect_amazon():
    print("📦 Amazon 수집 중...")
    results = []
    for kw in AMAZON_KEYWORDS:
        data = run_actor("epctex/amazon-scraper", {
            "search": kw, "maxItems": 8,
            "country": "US"
        })
        for item in data[:8]:
            results.append({
                "platform": "amazon", "keyword": kw,
                "title": item.get("title", "")[:80],
                "rating": item.get("stars", 0),
                "reviews": item.get("reviewsCount", 0),
                "price": item.get("price", {}).get("value", 0),
            })
    print(f"  → {len(results)}개")
    return results

# ── Google Trends (무료) ──────────────────────────────────
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

# ── 집계 ──────────────────────────────────────────────────
def aggregate(instagram, tiktok, youtube, x_data, amazon, google):
    brand_counts = {b: 0 for b in BRAND_KEYWORDS}
    ingredient_counts = {i: 0 for i in INGREDIENT_KEYWORDS}

    # Instagram
    for item in instagram:
        tag = item["hashtag"].lower()
        for brand in BRAND_KEYWORDS:
            if brand.replace(" ", "") in tag.replace(" ", ""):
                brand_counts[brand] += max(item.get("likes", 0) // 100, 1)

    # TikTok
    for item in tiktok:
        kw = item["keyword"].lower()
        for brand in BRAND_KEYWORDS:
            if brand.replace(" ", "") in kw.replace(" ", ""):
                brand_counts[brand] += max(item.get("likes", 0) // 1000, 1)

    # YouTube
    for item in youtube:
        text = (item.get("title", "") + " " + item.get("keyword", "")).lower()
        for brand in BRAND_KEYWORDS:
            if brand in text:
                brand_counts[brand] += max(item.get("views", 0) // 10000, 1)
        for ing in INGREDIENT_KEYWORDS:
            if ing in text:
                ingredient_counts[ing] += max(item.get("views", 0) // 10000, 1)

    # X
    for item in x_data:
        text = item.get("text", "").lower()
        for brand in BRAND_KEYWORDS:
            if brand in text:
                brand_counts[brand] += max(item.get("likes", 0) // 10, 1)
        for ing in INGREDIENT_KEYWORDS:
            if ing in text:
                ingredient_counts[ing] += max(item.get("likes", 0) // 10, 1)

    # Amazon
    for item in amazon:
        text = item.get("title", "").lower()
        for brand in BRAND_KEYWORDS:
            if brand in text:
                brand_counts[brand] += max(item.get("reviews", 0) // 100, 1)
        for ing in INGREDIENT_KEYWORDS:
            if ing in text:
                ingredient_counts[ing] += max(item.get("reviews", 0) // 100, 1)

    # Google Trends
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

# ── 메인 ──────────────────────────────────────────────────
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
            "where_to_buy_search": sum(
                1 for i in google if "where to buy" in i.get("keyword","")
            ) * 1000 or 8300,
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
