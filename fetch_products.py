"""
ローカルMacで実行：楽天API商品取得 → products.json保存 → GitHubにpush
"""
import json
import subprocess
from datetime import datetime, UTC
from rakuten_api import pick_daily_products
from config import POSTS_PER_DAY

def main():
    print("楽天API商品取得開始...")
    products = pick_daily_products(POSTS_PER_DAY)
    
    data = []
    for p in products:
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
    
    # GitHubにpush
    subprocess.run(["git", "add", "products.json"])
    subprocess.run(["git", "commit", "-m", f"update products {datetime.now(UTC).strftime('%Y-%m-%d')}"])
    subprocess.run(["git", "push"])
    print("GitHubにpushしました → GitHub Actionsが自動起動します")

if __name__ == "__main__":
    main()