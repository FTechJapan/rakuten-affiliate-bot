from datetime import datetime, UTC
from pathlib import Path
import json, sys, os
sys.path.insert(0, '.')

TEMPLATE_PATH = Path("link-page/index.html")
OUTPUT_PATH   = Path("link-page/index.html")

GENRE_TO_CAT = {
    "559617": "cleaning",
    "213244": "appliance",
    "215783": "interior",
    "100533": "living",
    "565105": "cleaning",
}

def _star_html(avg):
    full  = int(avg)
    empty = 5 - full
    return "★" * full + "☆" * empty

def generate_from_json():
    with open("products.json", encoding="utf-8") as f:
        products = json.load(f)

    cards = ""
    for i, p in enumerate(products):
        cat = GENRE_TO_CAT.get(p.get("genre_id",""), "all")
        stars = _star_html(p.get("review_average", 0))
        cards += f"""
    <a class="product-card" href="{p['affiliate_url']}"
       target="_blank" rel="noopener noreferrer" data-cat="{cat}">
      <div class="product-img">
        <img src="{p['image_url']}" alt="{p['name']}" loading="lazy">
        <div class="rank-badge">{i+1}</div>
      </div>
      <div class="product-info">
        <div class="product-name">{p['name']}</div>
        <div class="product-meta">
          <span class="stars">{stars}</span>
          <span class="review-count">{p.get('review_average',0):.1f}（{p.get('review_count',0):,}件）</span>
        </div>
        <div class="product-bottom">
          <div>
            <div class="price">¥{p['price']:,}</div>
            <div class="price-sub">楽天市場で詳細を確認</div>
          </div>
          <span class="cta-chip">チェック →</span>
        </div>
      </div>
    </a>"""

    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    today = datetime.now(UTC).strftime("%Y年%-m月%-d日")
    html = (template
        .replace("{{PROFILE_NAME}}",  "楽天おすすめ厳選アイテム")
        .replace("{{UPDATE_DATE}}",   today)
        .replace("{{PRODUCT_COUNT}}", str(len(products)))
        .replace("{{PRODUCT_CARDS}}", cards)
        .replace("{{INSTAGRAM_URL}}", "https://instagram.com/businessryuya")
        .replace("{{THREADS_URL}}",   "https://threads.net/@businessryuya")
    )
    OUTPUT_PATH.write_text(html, encoding="utf-8")
    print(f"[ページ生成] {len(products)}件の商品でページを生成しました")

if __name__ == "__main__":
    generate_from_json()