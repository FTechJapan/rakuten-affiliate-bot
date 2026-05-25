"""
ローカルMacで実行：楽天API商品取得 → products.json保存 → GitHubにpush
過去に投稿した商品は除外して重複を防ぐ
"""
import json
import subprocess
from datetime import datetime, UTC
from pathlib import Path
from rakuten_api import pick_daily_products
from config import POSTS_PER_DAY

POSTED_LOG = Path("posted_items.json")


def load_posted_items() -> set:
    """過去に投稿したitem_codeの一覧を読み込む"""
    if POSTED_LOG.exists():
        with open(POSTED_LOG, encoding="utf-8") as f:
            return set(json.load(f))
    return set()


def save_posted_items(posted: set):
    """投稿済みitem_codeを保存（最新1000件まで保持）"""
    items = list(posted)[-1000:]
    with open(POSTED_LOG, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False)


def main():
    print("楽天API商品取得開始...")

    # 最新のposted_items.jsonをGitHubから取得
    subprocess.run(["git", "pull", "--rebase"], check=False)
    print("[Git] 最新データをpullしました")

    # 過去の投稿済み商品を読み込む
    posted_items = load_posted_items()
    print(f"[重複防止] 過去の投稿済み商品: {len(posted_items)}件")

    # 多めに取得してフィルタリング
    all_products = pick_daily_products(POSTS_PER_DAY * 5)

    # 投稿済み商品を除外
    new_products = [p for p in all_products if p.item_code not in posted_items]
    print(f"[重複防止] 未投稿商品: {len(new_products)}件")

    if len(new_products) < POSTS_PER_DAY:
        print("[重複防止] 未投稿商品が不足しています。投稿済みリストをリセットします。")
        posted_items = set()
        new_products = all_products

    # 必要件数に絞る
    selected = new_products[:POSTS_PER_DAY]

    # products.jsonに保存
    data = []
    for p in selected:
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
    for p in selected:
        posted_items.add(p.item_code)
    save_posted_items(posted_items)

    # GitHubにpush
    subprocess.run(["git", "add", "products.json", "posted_items.json"])
    subprocess.run(["git", "commit", "-m", f"update products {datetime.now(UTC).strftime('%Y-%m-%d')}"])
    subprocess.run(["git", "push"])
    print("GitHubにpushしました → GitHub Actionsが自動起動します")


if __name__ == "__main__":
    main()
