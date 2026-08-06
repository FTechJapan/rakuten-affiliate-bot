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
import sys
import time
import subprocess
import requests
from datetime import datetime, UTC
from pathlib import Path
from rakuten_api import Product, RAKUTEN_APP_ID, RAKUTEN_ACCESS_KEY, RAKUTEN_AFFILIATE_ID
from config import POSTS_PER_DAY

SYNC_SCRIPT = Path(__file__).parent / "scripts" / "git_sync_json.py"

POSTED_LOG = Path("posted_items.json")

# GoogleスプレッドシートのCSVエクスポートURL
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1A886x4q1ZYzj36aMHAi56-gqjuO0OuDkXszMNIytQ1Q/export?format=csv&gid=0"

# 楽天商品検索API
RAKUTEN_SEARCH_URL = "https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20260401"


def load_posted_items() -> set:
    if not POSTED_LOG.exists():
        return set()
    with open(POSTED_LOG, encoding="utf-8") as f:
        text = f.read()
    try:
        return set(json.loads(text))
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"{POSTED_LOG} がJSONとして読み込めません（壊れています）: {e}\n"
            "おそらくgitのマージコンフリクトマーカーが混入しています。"
            "`git log -- posted_items.json` で直近の正常なコミットを確認し、"
            "手動で復元してから再実行してください。"
        ) from e


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

    # shopCode + item_idをkeywordで検索（特定商品を狙い打ち）
    params = {
        "applicationId": RAKUTEN_APP_ID,
        "accessKey": RAKUTEN_ACCESS_KEY,
        "affiliateId": RAKUTEN_AFFILIATE_ID,
        "shopCode": shop_code,
        "keyword": item_id,
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
            # keywordで見つからない場合はshopCodeのみで再検索
            params2 = {
                "applicationId": RAKUTEN_APP_ID,
                "accessKey": RAKUTEN_ACCESS_KEY,
                "affiliateId": RAKUTEN_AFFILIATE_ID,
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
    # fast-forwardできる場合のみ取り込む（stash/pull --rebase/stash pop は
    # テキストレベルのマージコンフリクトでJSONが壊れる事故につながるため使わない。
    # 取り込めなくても実害はない: posted_items.json は最後にgit_sync_json.pyが
    # リモートとJSONレベルで安全にマージしてからpushする）
    subprocess.run(["git", "fetch", "origin", "main"], check=False)
    ff = subprocess.run(["git", "merge", "--ff-only", "origin/main"], check=False)
    if ff.returncode == 0:
        print("[Git] 最新データをpullしました")
    else:
        print("[Git] fast-forwardできなかったため、ローカルの状態のまま続行します")

    # 投稿済み商品を読み込む
    posted_items = load_posted_items()
    print(f"[重複防止] 過去の投稿済み商品: {len(posted_items)}件")

    # スプレッドシートからURLを取得
    all_urls = fetch_spreadsheet_urls()

    # 未投稿のURLに絞る
    new_urls = [url for url in all_urls if url not in posted_items]

    print(f"[スプレッドシート] 未投稿URL: {len(new_urls)}件")

    if not new_urls:
        print("本日投稿するURLがありません。スプレッドシートに新しいURLを追加してください。")
        return

    # 上から順にPOSTS_PER_DAY件取得
    selected_products = []
    selected_urls = []  # ← 追加
    for url in new_urls:
        if len(selected_products) >= POSTS_PER_DAY:
            break
        print(f"[取得中] {url}")
        product = fetch_product_from_url(url)
        if product:
            selected_products.append(product)
            selected_urls.append(url)  # ← 追加
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
    for url in selected_urls:
        posted_items.add(url)
    save_posted_items(posted_items)

    # GitHubにpush
    # products.json は「今日の内容で完全に置き換え」、posted_items.json は
    # 「リモートとJSONレベルで安全にマージ」してからpushする（git_sync_json.py参照）。
    # git stash/pull --rebase/stash pop によるコンフリクトマーカー混入事故を避けるため。
    date_str = datetime.now(UTC).strftime("%Y-%m-%d")
    r1 = subprocess.run([
        sys.executable, str(SYNC_SCRIPT), "products.json",
        "--mode", "overwrite", "--message", f"update products {date_str}",
    ])
    r2 = subprocess.run([
        sys.executable, str(SYNC_SCRIPT), "posted_items.json",
        "--mode", "merge", "--limit", "1000",
        "--message", f"update posted items {date_str} [skip ci]",
    ])
    if r1.returncode == 0 and r2.returncode == 0:
        print("GitHubにpushしました → GitHub Actionsが自動起動します")
    else:
        print("⚠️ pushに失敗した可能性があります。git log / git status を確認してください。")


if __name__ == "__main__":
    main()
