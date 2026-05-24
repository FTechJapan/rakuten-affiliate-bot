"""
広告画像生成モジュール
3パターンのデザインをランダムで使用する
- minimal: シンプル・白背景
- bold: ダーク背景・インパクト重視
- elegant: グラデーション・高級感
Instagram(1080x1080)とThreads(1080x1350)でレイアウトを自動調整
"""
import io
import os
import random
import textwrap
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter

from config import BRAND_COLOR, ACCENT_COLOR, BG_COLOR, IMAGE_SIZES
from rakuten_api import Product

OUTPUT_DIR = Path("output/images")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

FONT_PATHS = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/noto-cjk/NotoSansCJKjp-Bold.otf",
    "assets/fonts/NotoSansJP-Bold.ttf",
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
    full  = int(average)
    half  = 1 if (average - full) >= 0.5 else 0
    empty = 5 - full - half
    return "★" * full + "☆" * half + "☆" * empty


def _format_price(price: int) -> str:
    return f"¥{price:,}"


def _crop_square(img: Image.Image, size: int) -> Image.Image:
    min_side = min(img.size)
    left = (img.width  - min_side) // 2
    top  = (img.height - min_side) // 2
    img = img.crop((left, top, left + min_side, top + min_side))
    return img.resize((size, size), Image.LANCZOS)


def _get_product_image(product: Product, size: int) -> Image.Image:
    try:
        img = _download_image(product.image_url)
        return _crop_square(img, size)
    except Exception as e:
        print(f"[画像] 商品画像ダウンロード失敗: {e}")
        return Image.new("RGBA", (size, size), (200, 200, 200, 255))


def _is_instagram(platform: str) -> bool:
    return platform == "instagram"


# ── デザイン1: Minimal（シンプル・白背景） ────────────────────────
def _create_minimal(product: Product, platform: str) -> Image.Image:
    W, H = IMAGE_SIZES[platform]
    ig = _is_instagram(platform)

    canvas = Image.new("RGB", (W, H), (250, 248, 244))
    draw = ImageDraw.Draw(canvas)

    # ヘッダー
    header_h = 72 if ig else 80
    draw.rectangle([(0, 0), (W, header_h)], fill=BRAND_COLOR)
    draw.text((32, header_h // 2), "楽天市場 おすすめアイテム",
              font=_get_font(24 if ig else 28), fill=ACCENT_COLOR, anchor="lm")
    draw.text((W - 32, header_h // 2), "#PR",
              font=_get_font(20 if ig else 22), fill=(255, 200, 180), anchor="rm")

    # 商品画像（Instagram:小さめ、Threads:大きめ）
    img_ratio = 0.58 if ig else 0.72
    img_size = int(W * img_ratio)
    product_img = _get_product_image(product, img_size)
    card_padding = 16 if ig else 20
    card = Image.new("RGB", (img_size + card_padding * 2, img_size + card_padding * 2), (255, 255, 255))
    if product_img.mode == "RGBA":
        card.paste(product_img.convert("RGB"), (card_padding, card_padding))
    else:
        card.paste(product_img, (card_padding, card_padding))
    img_x = (W - card.width) // 2
    img_y = header_h + 16
    canvas.paste(card, (img_x, img_y))

    # 価格バッジ
    price_text = _format_price(product.price)
    badge_w = 220 if ig else 260
    badge_h = 60 if ig else 72
    badge_x = W - badge_w - 20
    badge_y = img_y + img_size - 10
    draw.rounded_rectangle([(badge_x, badge_y), (badge_x + badge_w, badge_y + badge_h)],
                            radius=12, fill=BRAND_COLOR)
    draw.text((badge_x + badge_w // 2, badge_y + badge_h // 2), price_text,
              font=_get_font(40 if ig else 48), fill=ACCENT_COLOR, anchor="mm")

    # 商品名
    text_top = img_y + img_size + card_padding * 2 + 10
    font_name_size = 26 if ig else 32
    line_h = 36 if ig else 44
    name_lines = textwrap.wrap(product.name, width=24 if ig else 22)[:2]
    for i, line in enumerate(name_lines):
        draw.text((40, text_top + i * line_h), line, font=_get_font(font_name_size), fill=(40, 40, 40))

    # 星評価
    stars_y = text_top + len(name_lines) * line_h + 8
    stars_str = f"{_star_rating(product.review_average)}  {product.review_average:.1f}  ({product.review_count:,}件)"
    draw.text((40, stars_y), stars_str, font=_get_font(22 if ig else 26), fill=(200, 140, 0))

    # CTAボタン
    btn_h = 60
    btn_y = H - btn_h - 44
    draw.rounded_rectangle([(40, btn_y), (W - 40, btn_y + btn_h)], radius=30, fill=BRAND_COLOR)
    draw.text((W // 2, btn_y + btn_h // 2), "プロフのリンクからチェック！",
              font=_get_font(24 if ig else 28), fill=ACCENT_COLOR, anchor="mm")

    # フッター
    draw.text((W // 2, H - 20), "#PR #楽天 #楽天お買い物",
              font=_get_font(16 if ig else 18), fill=(160, 160, 160), anchor="ms")

    return canvas


# ── デザイン2: Bold（ダーク背景・インパクト重視） ─────────────────
def _create_bold(product: Product, platform: str) -> Image.Image:
    W, H = IMAGE_SIZES[platform]
    ig = _is_instagram(platform)

    canvas = Image.new("RGB", (W, H), (28, 28, 35))
    draw = ImageDraw.Draw(canvas)

    draw.rectangle([(0, 0), (8, H)], fill=BRAND_COLOR)

    header_y1 = 44 if ig else 50
    header_y2 = 70 if ig else 80
    draw.text((32, header_y1), "楽天市場", font=_get_font(22 if ig else 24), fill=(180, 180, 200), anchor="lm")
    draw.text((32, header_y2), "厳選アイテム", font=_get_font(30 if ig else 36), fill=(255, 255, 255), anchor="lm")
    draw.text((W - 32, header_y1), "#PR", font=_get_font(20 if ig else 22), fill=(255, 100, 80), anchor="rm")

    img_ratio = 0.56 if ig else 0.65
    img_size = int(W * img_ratio)
    product_img = _get_product_image(product, img_size)
    mask = Image.new("L", (img_size, img_size), 0)
    ImageDraw.Draw(mask).rounded_rectangle([(0, 0), (img_size, img_size)], radius=24, fill=255)
    img_x = (W - img_size) // 2
    img_y = 105 if ig else 120
    canvas.paste(product_img.convert("RGB"), (img_x, img_y), mask=mask)

    price_area_y = img_y + img_size + 16
    draw.text((W // 2, price_area_y + 24), _format_price(product.price),
              font=_get_font(58 if ig else 72), fill=BRAND_COLOR, anchor="mm")

    name_lines = textwrap.wrap(product.name, width=22 if ig else 20)[:2]
    name_font = 24 if ig else 30
    name_line_h = 38 if ig else 46
    for i, line in enumerate(name_lines):
        draw.text((W // 2, price_area_y + 66 + i * name_line_h), line,
                  font=_get_font(name_font), fill=(220, 220, 230), anchor="mm")

    stars_y = price_area_y + 66 + len(name_lines) * name_line_h + 12
    stars_str = f"{_star_rating(product.review_average)} {product.review_average:.1f} ({product.review_count:,}件)"
    draw.text((W // 2, stars_y), stars_str, font=_get_font(20 if ig else 24), fill=(255, 200, 80), anchor="mm")

    btn_h = 60
    btn_y = H - btn_h - 44
    draw.rounded_rectangle([(40, btn_y), (W - 40, btn_y + btn_h)], radius=35, fill=BRAND_COLOR)
    draw.text((W // 2, btn_y + btn_h // 2), "プロフのリンクからチェック！",
              font=_get_font(24 if ig else 28), fill=(255, 255, 255), anchor="mm")

    draw.text((W // 2, H - 20), "#PR #楽天 #楽天お買い物",
              font=_get_font(16 if ig else 18), fill=(100, 100, 120), anchor="ms")

    return canvas


# ── デザイン3: Elegant（グラデーション・高級感） ──────────────────
def _create_elegant(product: Product, platform: str) -> Image.Image:
    W, H = IMAGE_SIZES[platform]
    ig = _is_instagram(platform)

    canvas = Image.new("RGB", (W, H), (252, 248, 240))
    draw = ImageDraw.Draw(canvas)

    grad_h = 140 if ig else 160
    for i in range(grad_h):
        r = int(230 + (252 - 230) * i / grad_h)
        g = int(60  + (248 - 60)  * i / grad_h)
        b = int(10  + (240 - 10)  * i / grad_h)
        draw.line([(0, i), (W, i)], fill=(r, g, b))

    draw.text((W // 2, 44 if ig else 50), "楽天市場 厳選アイテム",
              font=_get_font(22 if ig else 26), fill=(255, 255, 255), anchor="mm")
    draw.text((W // 2, 70 if ig else 80), "RAKUTEN PREMIUM SELECTION",
              font=_get_font(14 if ig else 16), fill=(255, 220, 200), anchor="mm")

    img_ratio = 0.52 if ig else 0.6
    img_size = int(W * img_ratio)
    product_img = _get_product_image(product, img_size)

    circle_bg = Image.new("RGB", (img_size + 40, img_size + 40), (255, 255, 255))
    circle_mask = Image.new("L", (img_size + 40, img_size + 40), 0)
    ImageDraw.Draw(circle_mask).ellipse([(0, 0), (img_size + 40, img_size + 40)], fill=255)
    img_top = 100 if ig else 110
    canvas.paste(circle_bg, ((W - img_size - 40) // 2, img_top), mask=circle_mask)

    img_mask = Image.new("L", (img_size, img_size), 0)
    ImageDraw.Draw(img_mask).ellipse([(0, 0), (img_size, img_size)], fill=255)
    canvas.paste(product_img.convert("RGB"), ((W - img_size) // 2, img_top + 20), mask=img_mask)

    separator_y = img_top + 20 + img_size + 20
    draw.line([(80, separator_y), (W - 80, separator_y)], fill=(220, 210, 200), width=1)

    price_y = separator_y + 40
    draw.text((W // 2, price_y), _format_price(product.price),
              font=_get_font(52 if ig else 64), fill=BRAND_COLOR, anchor="mm")

    name_lines = textwrap.wrap(product.name, width=24 if ig else 22)[:2]
    name_line_h = 38 if ig else 44
    for i, line in enumerate(name_lines):
        draw.text((W // 2, price_y + 50 + i * name_line_h), line,
                  font=_get_font(24 if ig else 28), fill=(60, 45, 35), anchor="mm")

    stars_y = price_y + 50 + len(name_lines) * name_line_h + 12
    stars_str = f"{_star_rating(product.review_average)}  {product.review_average:.1f}  ({product.review_count:,}件)"
    draw.text((W // 2, stars_y), stars_str, font=_get_font(20 if ig else 24), fill=(200, 160, 60), anchor="mm")

    btn_h = 60
    btn_y = H - btn_h - 44
    draw.rounded_rectangle([(40, btn_y), (W - 40, btn_y + btn_h)], radius=35, fill=BRAND_COLOR)
    draw.text((W // 2, btn_y + btn_h // 2), "プロフのリンクからチェック！",
              font=_get_font(24 if ig else 28), fill=(255, 255, 255), anchor="mm")

    draw.text((W // 2, H - 20), "#PR #楽天 #楽天お買い物",
              font=_get_font(16 if ig else 18), fill=(180, 165, 150), anchor="ms")

    return canvas


# ── メイン関数 ────────────────────────────────────────────────────
def create_ad_image(product: Product, platform: str = "instagram") -> Path:
    """
    ランダムなデザインで広告画像を生成してファイルパスを返す
    platform: "instagram" (1080x1080) or "threads" (1080x1350)
    """
    design = random.choice(["minimal", "bold", "elegant"])
    print(f"[画像] デザイン: {design} / platform: {platform}")

    if design == "minimal":
        canvas = _create_minimal(product, platform)
    elif design == "bold":
        canvas = _create_bold(product, platform)
    else:
        canvas = _create_elegant(product, platform)

    safe_name = product.item_code.replace("/", "_").replace(":", "_")
    out_path = OUTPUT_DIR / f"{safe_name}_{platform}.jpg"
    canvas.convert("RGB").save(out_path, "JPEG", quality=92, optimize=True)
    print(f"[画像] 生成完了: {out_path}")
    return out_path
