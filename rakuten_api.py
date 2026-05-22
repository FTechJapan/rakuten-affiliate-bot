"""
楽天商品検索モジュール
楽天商品検索API v2 を使ってランキング上位商品を取得する
"""
import requests
import random
import os  
from dataclasses import dataclass, field
from typing import Optional
from config import (
    RAKUTEN_APP_ID, RAKUTEN_ACCESS_KEY, RAKUTEN_AFFILIATE_ID,
    RAKUTEN_GENRE_IDS, MIN_REVIEW_COUNT, MIN_REVIEW_AVERAGE
)

BASE_URL = "https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20260401"


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
    """指定ジャンルのランキング上位商品を取得する"""
    params = {
        "applicationId": RAKUTEN_APP_ID,
        "accessKey": RAKUTEN_ACCESS_KEY,
        "affiliateId": RAKUTEN_AFFILIATE_ID,
        "genreId": genre_id,
        "hits": 30,               # 多めに取得してフィルタ後に絞る
        "sort": "-reviewCount",   # レビュー数降順
        "minReviewCount": MIN_REVIEW_COUNT,
        "imageFlag": 1,           # 画像あり商品のみ
        "formatVersion": 2,
    }

    try:                          
        resp = requests.get(
            BASE_URL,
            params=params,
            headers={
                "Referer": "https://ftechjapan.github.io/",
            },
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
        if avg < MIN_REVIEW_AVERAGE:
            continue

        # 画像URLが存在する場合だけ追加
        images = item.get("mediumImageUrls", [])
        if not images:
            continue
        image_url = images[0].replace("?_ex=128x128", "?_ex=500x500")  # 高解像度に変換

        products.append(Product(
            item_code=item["itemCode"],
            name=item["itemName"][:60],          # 長すぎる商品名は切る
            price=int(item["itemPrice"]),
            review_count=int(item.get("reviewCount", 0)),
            review_average=avg,
            image_url=image_url,
            item_url=item["itemUrl"],
            affiliate_url=item.get("affiliateUrl", item["itemUrl"]),
            shop_name=item.get("shopName", ""),
            genre_id=genre_id,
            catch_copy=item.get("catchcopy", ""),
            item_caption=item.get("itemCaption", "")[:200],
        ))

    # フィルタ後にランダムシャッフルして多様性を出す
    random.shuffle(products)
    return products[:count]


def pick_daily_products(posts_per_day: int = 3) -> list[Product]:
    """全ジャンルからランダムに指定件数の商品を選ぶ"""
    all_products: list[Product] = []
    for genre_id in RAKUTEN_GENRE_IDS:
        products = fetch_trending_products(genre_id, count=5)
        all_products.extend(products)
        print(f"[楽天API] genreId={genre_id}: {len(products)}件取得")

    if not all_products:
        raise RuntimeError("商品が1件も取得できませんでした。APIキーを確認してください。")

    random.shuffle(all_products)
    selected = all_products[:posts_per_day]
    print(f"[楽天API] 本日投稿予定: {len(selected)}件")
    return selected
