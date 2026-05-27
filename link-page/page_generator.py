from datetime import datetime, UTC
from pathlib import Path
import json, sys
sys.path.insert(0, '.')

TEMPLATE_PATH     = Path("link-page/index.html")
OUTPUT_PATH       = Path("link-page/index.html")
ALL_PRODUCTS_PATH = Path("link-page/all_products.json")


def _star_html(avg):
    full  = int(avg)
    empty = 5 - full
    return "★" * full + "☆" * empty


def load_all_products() -> list:
    if ALL_PRODUCTS_PATH.exists():
        with open(ALL_PRODUCTS_PATH, encoding="utf-8") as f:
            return json.load(f)
    return []


def save_all_products(products: list):
    with open(ALL_PRODUCTS_PATH, "w", encoding="utf-8") as f:
        json.dump(products[-300:], f, ensure_ascii=False, indent=2)


def merge_products(existing: list, new_products: list) -> list:
    existing_codes = {p["item_code"] for p in existing}
    added = [p for p in new_products if p["item_code"] not in existing_codes]
    merged = added + existing
    print(f"[蓄積] 新規追加: {len(added)}件 / 累計: {len(merged)}件")
    return merged


def _make_today_card(p: dict, rank: int) -> str:
    stars = _star_html(p.get("review_average", 0))
    return f"""
    <a class="today-card" href="{p['affiliate_url']}"
       target="_blank" rel="noopener noreferrer">
      <div class="today-img">
        <img src="{p['image_url']}" alt="{p['name']}" loading="lazy">
        <div class="today-rank">{rank}</div>
      </div>
      <div class="today-info">
        <div class="today-name">{p['name']}</div>
        <div class="today-stars">{stars} {p.get('review_average', 0):.1f}</div>
        <div class="today-price">¥{p['price']:,}</div>
        <span class="today-cta">チェック →</span>
      </div>
    </a>"""


def _make_product_card(p: dict) -> str:
    stars = _star_html(p.get("review_average", 0))
    date_str = p.get("added_date", "")
    return f"""
    <a class="product-card" href="{p['affiliate_url']}"
       target="_blank" rel="noopener noreferrer">
      <div class="product-img">
        <img src="{p['image_url']}" alt="{p['name']}" loading="lazy">
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
            <div class="date-badge">{date_str} 掲載</div>
          </div>
          <span class="cta-chip">チェック →</span>
        </div>
      </div>
    </a>"""


def generate_from_json():
    with open("products.json", encoding="utf-8") as f:
        today_products = json.load(f)

    today_str = datetime.now(UTC).strftime("%Y年%-m月%-d日")

    for p in today_products:
        p["added_date"] = today_str

    existing = load_all_products()
    all_products = merge_products(existing, today_products)
    save_all_products(all_products)

    today_cards = ""
    for i, p in enumerate(today_products):
        today_cards += _make_today_card(p, i + 1)

    all_cards = ""
    for p in all_products:
        all_cards += _make_product_card(p)

    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    html = (template
        .replace("{{PROFILE_NAME}}",  "楽天おすすめ厳選アイテム")
        .replace("{{UPDATE_DATE}}",   today_str)
        .replace("{{TODAY_CARDS}}",   today_cards)
        .replace("{{ALL_CARDS}}",     all_cards)
        .replace("{{TOTAL_COUNT}}",   str(len(all_products)))
        .replace("{{INSTAGRAM_URL}}", "https://instagram.com/businessryuya")
        .replace("{{THREADS_URL}}",   "https://threads.net/@businessryuya")
    )
    OUTPUT_PATH.write_text(html, encoding="utf-8")
    print(f"[ページ生成] 本日{len(today_products)}件 / 累計{len(all_products)}件")


if __name__ == "__main__":
    generate_from_json()
