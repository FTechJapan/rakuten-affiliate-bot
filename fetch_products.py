"""
ローカルMacで実行：商品取得 → products.json保存 → GitHubにpush

優先順位：
1. Googleスプレッドシートに登録したURLから取得
2. URLが0件の場合はその日は投稿しない
"""
import json
import csv
import io
import re
import time
import subprocess
import requests
from datetime import datetime, UTC
from pathlib import Path
from rakuten_api import Product, RAKUTEN_APP_ID, RAKUTEN_ACCESS_KEY, RAKUTEN_AFFILIATE_ID
from config import POSTS_PER_DAY

POSTED_LOG = Path("posted_items.json")

# GoogleスプレッドシートのCSVエクスポートURL
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1A886x4q1ZYzj36aMHAi56-gqjuO0OuDkXszMNIytQ1Q/export?format=csv&gid=0"

# 楽天商品検索API
RAKUTEN_SEARCH_URL = "https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20260401"


def load_posted_items() -> set:
    if POSTED_LOG.exists():
        with open(POSTED_LOG, encoding="utf-8") as f:
            return set(json.load(f))
    return set()


def save_posted_items(posted: set):
    items = list(posted)[-1000:]
    with open(POSTED_LOG, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False)


def fetch_spreadsheet_urls() -> list[str]:
    """スプレッドシートのA列からURLを全件取得"""
    try:
        resp = requests.get(SPREADSHEET_URL, timeout=15)
        resp.raise_for_status()
        reader = csv.reader(io.StringIO(resp.text))
        urls = []
        for row in reader:
            if row and row[0].strip().startswith("https://"):
                urls.append(row[0].strip())
        print(f"[スプレッドシート] {len(urls)}件のURLを取得")
        return urls
    except Exception as e:
        print(f"[スプレッドシート] 取得失敗: {e}")
        return []


def extract_item_code_from_url(url: str) -> tuple[str, str] | None:
    """
    楽天商品URLからshop_codeとitem_codeを抽出
    例: https://item.rakuten.co.jp/shop-name/item-id/
    → ("shop-name", "item-id")
    """
    match = re.search(r'item\.rakuten\.co\.jp/([^/]+)/([^/?]+)', url)
    if match:
        return match.group(1), match.group(2)
    return None


def fetch_product_from_url(url: str) -> Product | None:
    """楽天商品URLから商品情報をAPIで取得"""
    extracted = extract_item_code_from_url(url)
    if not extracted:
        print(f"[URL解析] 失敗: {url}")
        return None

    shop_code, item_id = extracted
    item_code = f"{shop_code}:{item_id}"

    # shopCodeとkeywordで検索
    params = {
        "applicationId": RAKUTEN_APP_ID,
        "accessKey": RAKUTEN_ACCESS_KEY,
        "affiliateId": RAKUTEN_AFFILIATE_ID,
        "shopCode": shop_code,
        "hits": 1,
        "formatVersion": 2,
    }

    try:
        resp = requests.get(
            RAKUTEN_SEARCH_URL,
            params=params,
            headers={"Referer": "https://ftechjapan.github.io/"},
            timeout=10
        )
        resp.raise_for_status()
        data = resp.json()
        items = data.get("Items", [])

        if not items:
            # itemCodeで見つからない場合はkeyword検索にフォールバック
            params2 = {
                "applicationId": RAKUTEN_APP_ID,
                "accessKey": RAKUTEN_ACCESS_KEY,
                "affiliateId": RAKUTEN_AFFILIATE_ID,
                "keyword": item_id.replace("-", " "),
                "shopCode": shop_code,
                "hits": 1,
                "formatVersion": 2,
            }
            resp2 = requests.get(
                RAKUTEN_SEARCH_URL,
                params=params2,
                headers={"Referer": "https://ftechjapan.github.io/"},
                timeout=10
            )
            data = resp2.json()
            items = data.get("Items", [])

        if not items:
            print(f"[API] 商品が見つかりません: {url}")
            return None

        item = items[0]
        images = item.get("mediumImageUrls", [])
        if not images:
            return None

        image_url = images[0].replace("?_ex=128x128", "?_ex=500x500")

        return Product(
            item_code=item.get("itemCode", item_code),
            name=item["itemName"][:60],
            price=int(item["itemPrice"]),
            review_count=int(item.get("reviewCount", 0)),
            review_average=float(item.get("reviewAverage", 0)),
            image_url=image_url,
            item_url=item["itemUrl"],
            affiliate_url=item.get("affiliateUrl", item["itemUrl"]),
            shop_name=item.get("shopName", shop_code),
            genre_id=str(item.get("genreId", "")),
            catch_copy=item.get("catchcopy", ""),
            item_caption=item.get("itemCaption", "")[:200],
        )

    except Exception as e:
        print(f"[API] 取得失敗 {url}: {e}")
        return None


def main():
    print("商品取得開始...")

    # 最新データをGitHubから取得
    subprocess.run(["git", "stash"], check=False)
    subprocess.run(["git", "pull", "--rebase", "origin", "main"], check=False)
    subprocess.run(["git", "stash", "pop"], check=False)
    print("[Git] 最新データをpullしました")

    # 投稿済み商品を読み込む
    posted_items = load_posted_items()
    print(f"[重複防止] 過去の投稿済み商品: {len(posted_items)}件")

    # スプレッドシートからURLを取得
    all_urls = fetch_spreadsheet_urls()

    # 未投稿のURLに絞る
    new_urls = [url for url in all_urls if extract_item_code_from_url(url) and
                f"{extract_item_code_from_url(url)[0]}:{extract_item_code_from_url(url)[1]}" not in posted_items]

    print(f"[スプレッドシート] 未投稿URL: {len(new_urls)}件")

    if not new_urls:
        print("本日投稿するURLがありません。スプレッドシートに新しいURLを追加してください。")
        return

    # 上から順にPOSTS_PER_DAY件取得
    selected_products = []
    for url in new_urls:
        if len(selected_products) >= POSTS_PER_DAY:
            break
        print(f"[取得中] {url}")
        product = fetch_product_from_url(url)
        if product:
            selected_products.append(product)
            print(f"[取得完了] {product.name[:40]} / ¥{product.price:,}")
        time.sleep(1)

    if not selected_products:
        print("商品情報の取得に失敗しました。")
        return

    # products.jsonに保存
    data = []
    for p in selected_products:
        data.append({
            "item_code": p.item_code,
            "name": p.name,
            "price": p.price,
            "review_count": p.review_count,
            "review_average": p.review_average,
            "image_url": p.image_url,
            "item_url": p.item_url,
            "affiliate_url": p.affiliate_url,
            "shop_name": p.shop_name,
            "genre_id": p.genre_id,
            "catch_copy": p.catch_copy,
            "item_caption": p.item_caption,
        })

    with open("products.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"{len(data)}件の商品をproducts.jsonに保存しました")

    # 投稿済みリストを更新
    for p in selected_products:
        posted_items.add(p.item_code)
    save_posted_items(posted_items)

    # GitHubにpush
    subprocess.run(["git", "add", "products.json", "posted_items.json"])
    subprocess.run(["git", "commit", "-m", f"update products {datetime.now(UTC).strftime('%Y-%m-%d')}"])
    subprocess.run(["git", "push"])
    print("GitHubにpushしました → GitHub Actionsが自動起動します")


if __name__ == "__main__":
    main()
