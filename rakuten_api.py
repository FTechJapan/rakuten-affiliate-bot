"""
楽天商品検索モジュール
楽天商品検索API v2 を使ってランキング上位商品を取得する
Step1: フィルター条件で絞り込み
Step2: Claude APIでバズりそうな商品を最終選別
"""
import json
import requests
import random
import time
from dataclasses import dataclass
import anthropic
from config import (
    RAKUTEN_APP_ID, RAKUTEN_ACCESS_KEY, RAKUTEN_AFFILIATE_ID,
    RAKUTEN_GENRE_IDS, MIN_REVIEW_COUNT, MIN_REVIEW_AVERAGE,
    ANTHROPIC_API_KEY,
)

BASE_URL = "https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20260401"

# ── フィルター条件 ────────────────────────────────────────
MIN_REVIEW_COUNT_BUZZ = 300    # バズ商品は最低500件レビュー
MIN_REVIEW_AVERAGE_BUZZ = 4.1  # 評価4.1以上
MIN_PRICE = 500                # 最低価格（安すぎる商品は除外）
MAX_PRICE = 15000              # 最高価格（高すぎる商品は衝動買いされにくい）
MIN_AFFILIATE_RATE = 1.5       # アフィリエイト率2%以上

# ── 除外キーワード（服・下着・ファッション系） ────────────
EXCLUDE_KEYWORDS = [
    "ブラ", "ブラトップ", "ブラジャー", "下着", "ランジェリー",
    "タイツ", "レギンス", "授乳ブラ", "ショーツ", "インナー",
    "ガードル", "補正", "ワンピース", "スカート", "デニム",
    "ジーンズ", "トップス", "カットソー", "ニット", "セーター",
    "パジャマ", "ルームウェア", "水着", "ビキニ", "レオタード",
    "スパッツ", "レギンスパンツ", "スキニー", "チュニック",
    "カーディガン", "ブラウス", "シャツ", "ポロシャツ",
]


@dataclass
class Product:
    item_code: str
    name: str
    price: int
    review_count: int
    review_average: float
    image_url: str
    item_url: str
    affiliate_url: str
    shop_name: str
    genre_id: str
    catch_copy: str = ""
    item_caption: str = ""


def fetch_trending_products(genre_id: str, count: int = 10) -> list[Product]:
    """指定ジャンルのランキング上位商品を取得・フィルタリングする"""
    params = {
        "applicationId": RAKUTEN_APP_ID,
        "accessKey": RAKUTEN_ACCESS_KEY,
        "affiliateId": RAKUTEN_AFFILIATE_ID,
        "genreId": genre_id,
        "hits": 30,
        "sort": "-reviewCount",
        "minReviewCount": MIN_REVIEW_COUNT,
        "imageFlag": 1,
        "formatVersion": 2,
    }

    try:
        resp = requests.get(
            BASE_URL,
            params=params,
            headers={"Referer": "https://ftechjapan.github.io/"},
            timeout=10
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"[楽天API] 取得失敗 genreId={genre_id}: {e}")
        return []

    products = []
    for item in data.get("Items", []):
        avg = float(item.get("reviewAverage", 0))
        review_count = int(item.get("reviewCount", 0))
        price = int(item.get("itemPrice", 0))
        affiliate_rate = float(item.get("affiliateRate", 0))
        item_name = item.get("itemName", "")

        # ── 除外キーワードチェック ────────────────────────
        if any(kw in item_name for kw in EXCLUDE_KEYWORDS):
            continue

        # ── フィルター条件 ────────────────────────────────
        if avg < MIN_REVIEW_AVERAGE_BUZZ:
            continue
        if review_count < MIN_REVIEW_COUNT_BUZZ:
            continue
        if price < MIN_PRICE or price > MAX_PRICE:
            continue
        if affiliate_rate < MIN_AFFILIATE_RATE:
            continue

        # 割引商品のみ
        price_max = int(item.get("itemPriceMax1", 0))
        if price_max > 0 and price >= price_max:
            continue

        # 画像あり
        images = item.get("mediumImageUrls", [])
        if not images:
            continue

        image_url = images[0].replace("?_ex=128x128", "?_ex=500x500")

        products.append(Product(
            item_code=item["itemCode"],
            name=item_name[:60],
            price=price,
            review_count=review_count,
            review_average=avg,
            image_url=image_url,
            item_url=item["itemUrl"],
            affiliate_url=item.get("affiliateUrl", item["itemUrl"]),
            shop_name=item.get("shopName", ""),
            genre_id=genre_id,
            catch_copy=item.get("catchcopy", ""),
            item_caption=item.get("itemCaption", "")[:200],
        ))

    random.shuffle(products)
    return products[:count]


def select_buzz_products(products: list[Product], need: int) -> list[Product]:
    """
    Claude APIで商品をバズりやすさでスコアリングして上位を返す
    """
    if not products:
        return []

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    product_list = "\n".join([
        f"{i+1}. 商品名:{p.name} / 価格:¥{p.price:,} / 評価:{p.review_average}点({p.review_count:,}件) / キャッチ:{p.catch_copy[:50]}"
        for i, p in enumerate(products)
    ])

    prompt = f"""
あなたはSNSマーケティングの専門家です。
以下の楽天商品リストを見て、InstagramやThreadsでバズりやすい商品を選んでください。

【バズりやすい商品の条件】
- 見た目がわかりやすく、画像映えしそう
- 「これ欲しい！」「知らなかった！」と思わせる商品
- 日常生活の悩みを解決する実用的な商品
- コスパが良く、衝動買いしやすい価格帯
- レビュー件数が多く信頼性が高い
- ターゲット（主婦・20〜40代女性）に刺さりやすい
- 服・ファッション・下着・ランジェリー系は選ばない

【商品リスト】
{product_list}

上記から特にバズりやすいと思う商品の番号を{need}つ選び、
以下のJSON形式のみで出力してください（説明文なし）:
{{"selected": [1, 3, 5]}}
"""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text.strip()
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        result = json.loads(raw)
        selected_indices = [i - 1 for i in result.get("selected", []) if 1 <= i <= len(products)]

        selected = [products[i] for i in selected_indices if i < len(products)]
        for p in selected:
            print(f"[Claude選別] ✅ {p.name[:40]}")

        return selected[:need]

    except Exception as e:
        print(f"[Claude選別] エラー: {e} → ランダム選択にフォールバック")
        return products[:need]


def pick_daily_products(posts_per_day: int = 3) -> list[Product]:
    """
    全ジャンルから商品を取得→フィルター→Claude選別で最終選択
    """
    all_products: list[Product] = []
    for genre_id in RAKUTEN_GENRE_IDS:
        products = fetch_trending_products(genre_id, count=8)
        all_products.extend(products)
        print(f"[楽天API] genreId={genre_id}: {len(products)}件取得")
        time.sleep(2)

    if not all_products:
        raise RuntimeError("商品が1件も取得できませんでした。APIキーを確認してください。")

    print(f"[フィルター後] 合計: {len(all_products)}件 → Claude選別開始...")

    # Claude APIでバズりそうな商品を選別
    selected = select_buzz_products(all_products, posts_per_day)

    # Claude選別で足りない場合はランダム補完
    if len(selected) < posts_per_day:
        remaining = [p for p in all_products if p not in selected]
        random.shuffle(remaining)
        selected += remaining[:posts_per_day - len(selected)]

    print(f"[最終選別] 本日投稿予定: {len(selected)}件")
    return selected
