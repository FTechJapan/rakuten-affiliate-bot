from datetime import datetime, UTC
from pathlib import Path
import json, sys, os
sys.path.insert(0, '.')

TEMPLATE_PATH  = Path("link-page/index.html")
OUTPUT_PATH    = Path("link-page/index.html")
ALL_PRODUCTS_PATH = Path("link-page/all_products.json")  # 累積ファイル

GENRE_TO_CAT = {
    "100533": "living",
    "565105": "cleaning",
    "215783": "interior",
    "562701": "storage",
    "100371": "beauty",
}


def _star_html(avg):
    full  = int(avg)
    empty = 5 - full
    return "★" * full + "☆" * empty


def load_all_products() -> list:
    """累積商品データを読み込む"""
    if ALL_PRODUCTS_PATH.exists():
        with open(ALL_PRODUCTS_PATH, encoding="utf-8") as f:
            return json.load(f)
    return []


def save_all_products(products: list):
    """累積商品データを保存（最新300件まで）"""
    with open(ALL_PRODUCTS_PATH, "w", encoding="utf-8") as f:
        json.dump(products[-300:], f, ensure_ascii=False, indent=2)


def merge_products(existing: list, new_products: list) -> list:
    """新しい商品を追加（item_codeで重複排除、新しいものを先頭に）"""
    existing_codes = {p["item_code"] for p in existing}
    added = [p for p in new_products if p["item_code"] not in existing_codes]
    # 新しい商品を先頭に追加
    merged = added + existing
    print(f"[蓄積] 新規追加: {len(added)}件 / 累計: {len(merged)}件")
    return merged


def _make_card(p: dict, rank: int) -> str:
    cat   = GENRE_TO_CAT.get(p.get("genre_id", ""), "all")
    stars = _star_html(p.get("review_average", 0))
    date_str = p.get("added_date", "")
    return f"""
    <a class="product-card" href="{p['affiliate_url']}"
       target="_blank" rel="noopener noreferrer" data-cat="{cat}">
      <div class="product-img">
        <img src="{p['image_url']}" alt="{p['name']}" loading="lazy">
        <div class="rank-badge">{rank}</div>
      </div>
      <div class="product-info">
        <div class="product-name">{p['name']}</div>
        <div class="product-meta">
          <span class="stars">{stars}</span>
          <span class="review-count">{p.get('review_average', 0):.1f}（{p.get('review_count', 0):,}件）</span>
        </div>
        <div class="product-bottom">
          <div>
            <div class="price">¥{p['price']:,}</div>
            <div class="price-sub">{date_str} 掲載</div>
          </div>
          <span class="cta-chip">チェック →</span>
        </div>
      </div>
    </a>"""


def generate_from_json():
    # 本日の商品を読み込む
    with open("products.json", encoding="utf-8") as f:
        today_products = json.load(f)

    today_str = datetime.now(UTC).strftime("%Y年%-m月%-d日")

    # 掲載日を付与
    for p in today_products:
        p["added_date"] = today_str

    # 累積データに追加
    existing = load_all_products()
    all_products = merge_products(existing, today_products)
    save_all_products(all_products)

    # カード生成（全累積商品）
    cards = ""
    for i, p in enumerate(all_products):
        cards += _make_card(p, i + 1)

    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    html = (template
        .replace("{{PROFILE_NAME}}",  "楽天おすすめ厳選アイテム")
        .replace("{{UPDATE_DATE}}",   today_str)
        .replace("{{PRODUCT_COUNT}}", str(len(all_products)))
        .replace("{{PRODUCT_CARDS}}", cards)
        .replace("{{INSTAGRAM_URL}}", "https://instagram.com/businessryuya")
        .replace("{{THREADS_URL}}",   "https://threads.net/@businessryuya")
    )
    OUTPUT_PATH.write_text(html, encoding="utf-8")
    print(f"[ページ生成] 累計{len(all_products)}件の商品でページを生成しました")


if __name__ == "__main__":
    generate_from_json()
