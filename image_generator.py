"""
広告画像生成モジュール
Pillowで商品画像＋テキスト＋ブランド要素を合成してSNS向け画像を生成する
"""
import io
import os
import textwrap
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter

from config import BRAND_COLOR, ACCENT_COLOR, BG_COLOR, IMAGE_SIZES
from rakuten_api import Product

OUTPUT_DIR = Path("output/images")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# フォント設定（GitHub Actions上ではNotoフォントを使う）
FONT_PATHS = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/noto-cjk/NotoSansCJKjp-Bold.otf",
    "assets/fonts/NotoSansJP-Bold.ttf",
]

EMOJI_FONT_PATHS = [
    "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf",
    "/usr/share/fonts/noto/NotoColorEmoji.ttf",
]


def _get_font(size: int) -> ImageFont.FreeTypeFont:
    for path in FONT_PATHS:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _download_image(url: str) -> Image.Image:
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    return Image.open(io.BytesIO(resp.content)).convert("RGBA")


def _star_rating(average: float) -> str:
    """評価を星文字列に変換 例: 4.5 → ★★★★☆"""
    full  = int(average)
    half  = 1 if (average - full) >= 0.5 else 0
    empty = 5 - full - half
    return "★" * full + "☆" * half + "☆" * empty


def _format_price(price: int) -> str:
    return f"¥{price:,}"


def create_ad_image(product: Product, platform: str = "instagram") -> Path:
    """
    1枚の広告画像を生成してファイルパスを返す
    platform: "instagram" (1080x1080) or "threads" (1080x1350)
    """
    W, H = IMAGE_SIZES[platform]
    canvas = Image.new("RGB", (W, H), BG_COLOR)
    draw = ImageDraw.Draw(canvas)

    # ── 背景グラデーション風ブロック ──────────────────────
    # ヘッダー帯
    draw.rectangle([(0, 0), (W, 80)], fill=BRAND_COLOR)

    # ── ブランドロゴ文字 ────────────────────────────────
    font_logo = _get_font(28)
    draw.text((32, 24), "楽天市場 おすすめアイテム", font=font_logo, fill=ACCENT_COLOR)

    # ── 商品画像（中央に大きく配置） ────────────────────
    try:
        product_img = _download_image(product.image_url)
    except Exception as e:
        print(f"[画像] 商品画像ダウンロード失敗: {e}")
        product_img = Image.new("RGBA", (500, 500), (200, 200, 200, 255))

    # 正方形にクロップしてリサイズ
    min_side = min(product_img.size)
    left = (product_img.width  - min_side) // 2
    top  = (product_img.height - min_side) // 2
    product_img = product_img.crop((left, top, left + min_side, top + min_side))

    img_size = int(W * 0.72)
    product_img = product_img.resize((img_size, img_size), Image.LANCZOS)

    # 白い台紙に配置（影効果）
    card_padding = 20
    card = Image.new("RGB", (img_size + card_padding*2, img_size + card_padding*2), (255, 255, 255))
    card_rgba = card.convert("RGBA")
    card_rgba.paste(product_img, (card_padding, card_padding), mask=product_img.split()[3])

    img_x = (W - card.width) // 2
    img_y = 100
    canvas.paste(card_rgba.convert("RGB"), (img_x, img_y))

    # ── 価格バッジ ────────────────────────────────────
    price_text = _format_price(product.price)
    font_price = _get_font(48)
    badge_w = 240
    badge_x = W - badge_w - 24
    badge_y = img_y + img_size - 20
    draw.rounded_rectangle(
        [(badge_x, badge_y), (badge_x + badge_w, badge_y + 72)],
        radius=12, fill=BRAND_COLOR
    )
    draw.text(
        (badge_x + badge_w // 2, badge_y + 36),
        price_text, font=font_price, fill=ACCENT_COLOR,
        anchor="mm"
    )

    # ── 商品名 ────────────────────────────────────────
    text_top = img_y + img_size + card_padding * 2 + 16
    font_name = _get_font(32)
    name_lines = textwrap.wrap(product.name, width=22)[:3]
    for i, line in enumerate(name_lines):
        draw.text((40, text_top + i * 44), line, font=font_name, fill=(40, 40, 40))

    # ── 星評価 ────────────────────────────────────────
    stars_y = text_top + len(name_lines) * 44 + 12
    font_stars = _get_font(26)
    stars_str = f"{_star_rating(product.review_average)}  {product.review_average:.1f}  ({product.review_count:,}件)"
    draw.text((40, stars_y), stars_str, font=font_stars, fill=(200, 140, 0))

  # ── CTAボタン ─────────────────────────────────────
    btn_y = H - 120
    draw.rounded_rectangle(
    [(40, btn_y), (W - 40, btn_y + 70)],
    radius=30, fill=BRAND_COLOR
    )
    font_btn = _get_font(28)
    draw.text(
    (W // 2, btn_y + 35),
    "プロフのリンクからチェック！",
    font=font_btn, fill=ACCENT_COLOR, anchor="mm"
)

    # ── フッター ─────────────────────────────────────
    font_footer = _get_font(18)
    draw.text(
    (W // 2, H - 30),
    "#PR #楽天 #楽天お買い物",
    font=font_footer, fill=(160, 160, 160), anchor="ms"
    )

    # ── 保存 ─────────────────────────────────────────
    safe_name = product.item_code.replace("/", "_").replace(":", "_")
    out_path = OUTPUT_DIR / f"{safe_name}_{platform}.jpg"
    canvas.convert("RGB").save(out_path, "JPEG", quality=92, optimize=True)
    print(f"[画像] 生成完了: {out_path}")
    return out_path
