"""
広告画像生成モジュール
3パターンのデザインをランダムで使用する
- minimal: シンプル・白背景
- bold: ダーク背景・インパクト重視
- elegant: グラデーション・高級感
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
    """正方形にクロップしてリサイズ"""
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


# ── デザイン1: Minimal（シンプル・白背景） ────────────────────────
def _create_minimal(product: Product, platform: str) -> Path:
    W, H = IMAGE_SIZES[platform]
    canvas = Image.new("RGB", (W, H), (250, 248, 244))
    draw = ImageDraw.Draw(canvas)

    # ヘッダー
    draw.rectangle([(0, 0), (W, 80)], fill=BRAND_COLOR)
    draw.text((32, 40), "楽天市場 おすすめアイテム", font=_get_font(28), fill=ACCENT_COLOR, anchor="lm")
    draw.text((W - 32, 40), "#PR", font=_get_font(22), fill=(255, 200, 180), anchor="rm")

    # 商品画像
    img_size = int(W * 0.72)
    product_img = _get_product_image(product, img_size)
    card_padding = 20
    card = Image.new("RGB", (img_size + card_padding * 2, img_size + card_padding * 2), (255, 255, 255))
    if product_img.mode == "RGBA":
        card.paste(product_img.convert("RGB"), (card_padding, card_padding))
    else:
        card.paste(product_img, (card_padding, card_padding))
    img_x = (W - card.width) // 2
    img_y = 100
    canvas.paste(card, (img_x, img_y))

    # 価格バッジ
    price_text = _format_price(product.price)
    badge_w = 260
    badge_x = W - badge_w - 24
    badge_y = img_y + img_size - 10
    draw.rounded_rectangle([(badge_x, badge_y), (badge_x + badge_w, badge_y + 72)], radius=12, fill=BRAND_COLOR)
    draw.text((badge_x + badge_w // 2, badge_y + 36), price_text, font=_get_font(48), fill=ACCENT_COLOR, anchor="mm")

    # 商品名
    text_top = img_y + img_size + card_padding * 2 + 16
    name_lines = textwrap.wrap(product.name, width=22)[:3]
    for i, line in enumerate(name_lines):
        draw.text((40, text_top + i * 44), line, font=_get_font(32), fill=(40, 40, 40))

    # 星評価
    stars_y = text_top + len(name_lines) * 44 + 12
    stars_str = f"{_star_rating(product.review_average)}  {product.review_average:.1f}  ({product.review_count:,}件)"
    draw.text((40, stars_y), stars_str, font=_get_font(26), fill=(200, 140, 0))

    # CTAボタン
    btn_y = H - 120
    draw.rounded_rectangle([(40, btn_y), (W - 40, btn_y + 70)], radius=30, fill=BRAND_COLOR)
    draw.text((W // 2, btn_y + 35), "プロフのリンクからチェック！", font=_get_font(28), fill=ACCENT_COLOR, anchor="mm")

    # フッター
    draw.text((W // 2, H - 30), "#PR #楽天 #楽天お買い物", font=_get_font(18), fill=(160, 160, 160), anchor="ms")

    return canvas


# ── デザイン2: Bold（ダーク背景・インパクト重視） ─────────────────
def _create_bold(product: Product, platform: str) -> Path:
    W, H = IMAGE_SIZES[platform]
    # ダーク背景
    canvas = Image.new("RGB", (W, H), (28, 28, 35))
    draw = ImageDraw.Draw(canvas)

    # アクセントライン（左側）
    draw.rectangle([(0, 0), (8, H)], fill=BRAND_COLOR)

    # ヘッダー文字
    draw.text((32, 50), "楽天市場", font=_get_font(24), fill=(180, 180, 200), anchor="lm")
    draw.text((32, 80), "厳選アイテム", font=_get_font(36), fill=(255, 255, 255), anchor="lm")
    draw.text((W - 32, 50), "#PR", font=_get_font(22), fill=(255, 100, 80), anchor="rm")

    # 商品画像（角丸）
    img_size = int(W * 0.65)
    product_img = _get_product_image(product, img_size)
    mask = Image.new("L", (img_size, img_size), 0)
    ImageDraw.Draw(mask).rounded_rectangle([(0, 0), (img_size, img_size)], radius=24, fill=255)
    img_x = (W - img_size) // 2
    img_y = 120
    canvas.paste(product_img.convert("RGB"), (img_x, img_y), mask=mask)

    # 価格（大きく中央）
    price_area_y = img_y + img_size + 20
    draw.text((W // 2, price_area_y + 30), _format_price(product.price), font=_get_font(72), fill=BRAND_COLOR, anchor="mm")

    # 商品名
    name_lines = textwrap.wrap(product.name, width=20)[:2]
    for i, line in enumerate(name_lines):
        draw.text((W // 2, price_area_y + 80 + i * 46), line, font=_get_font(30), fill=(220, 220, 230), anchor="mm")

    # 星評価
    stars_y = price_area_y + 80 + len(name_lines) * 46 + 16
    stars_str = f"{_star_rating(product.review_average)} {product.review_average:.1f} ({product.review_count:,}件)"
    draw.text((W // 2, stars_y), stars_str, font=_get_font(24), fill=(255, 200, 80), anchor="mm")

    # CTAボタン
    btn_y = H - 120
    draw.rounded_rectangle([(40, btn_y), (W - 40, btn_y + 70)], radius=35, fill=BRAND_COLOR)
    draw.text((W // 2, btn_y + 35), "プロフのリンクからチェック！", font=_get_font(28), fill=(255, 255, 255), anchor="mm")

    # フッター
    draw.text((W // 2, H - 30), "#PR #楽天 #楽天お買い物", font=_get_font(18), fill=(100, 100, 120), anchor="ms")

    return canvas


# ── デザイン3: Elegant（グラデーション・高級感） ──────────────────
def _create_elegant(product: Product, platform: str) -> Path:
    W, H = IMAGE_SIZES[platform]

    # クリーム色背景
    canvas = Image.new("RGB", (W, H), (252, 248, 240))
    draw = ImageDraw.Draw(canvas)

    # 上部の薄いグラデーション帯
    for i in range(160):
        alpha = int(255 * (1 - i / 160))
        r = int(230 + (252 - 230) * i / 160)
        g = int(60  + (248 - 60)  * i / 160)
        b = int(10  + (240 - 10)  * i / 160)
        draw.line([(0, i), (W, i)], fill=(r, g, b))

    # ヘッダー文字
    draw.text((W // 2, 50), "楽天市場 厳選アイテム", font=_get_font(26), fill=(255, 255, 255), anchor="mm")
    draw.text((W // 2, 82), "RAKUTEN PREMIUM SELECTION", font=_get_font(16), fill=(255, 220, 200), anchor="mm")

    # 商品画像（円形マスク）
    img_size = int(W * 0.6)
    product_img = _get_product_image(product, img_size)
    # 白い円形台紙
    circle_bg = Image.new("RGB", (img_size + 40, img_size + 40), (255, 255, 255))
    circle_mask = Image.new("L", (img_size + 40, img_size + 40), 0)
    ImageDraw.Draw(circle_mask).ellipse([(0, 0), (img_size + 40, img_size + 40)], fill=255)
    canvas.paste(circle_bg, ((W - img_size - 40) // 2, 110), mask=circle_mask)
    img_mask = Image.new("L", (img_size, img_size), 0)
    ImageDraw.Draw(img_mask).ellipse([(0, 0), (img_size, img_size)], fill=255)
    canvas.paste(product_img.convert("RGB"), ((W - img_size) // 2, 130), mask=img_mask)

    # 区切り線
    separator_y = 130 + img_size + 30
    draw.line([(80, separator_y), (W - 80, separator_y)], fill=(220, 210, 200), width=1)

    # 価格
    price_y = separator_y + 50
    draw.text((W // 2, price_y), _format_price(product.price), font=_get_font(64), fill=BRAND_COLOR, anchor="mm")

    # 商品名
    name_lines = textwrap.wrap(product.name, width=22)[:2]
    for i, line in enumerate(name_lines):
        draw.text((W // 2, price_y + 60 + i * 44), line, font=_get_font(28), fill=(60, 45, 35), anchor="mm")

    # 星評価
    stars_y = price_y + 60 + len(name_lines) * 44 + 16
    stars_str = f"{_star_rating(product.review_average)}  {product.review_average:.1f}  ({product.review_count:,}件)"
    draw.text((W // 2, stars_y), stars_str, font=_get_font(24), fill=(200, 160, 60), anchor="mm")

    # CTAボタン（細いアウトライン風）
    btn_y = H - 120
    draw.rounded_rectangle([(40, btn_y), (W - 40, btn_y + 70)], radius=35, fill=BRAND_COLOR)
    draw.text((W // 2, btn_y + 35), "プロフのリンクからチェック！", font=_get_font(28), fill=(255, 255, 255), anchor="mm")

    # フッター
    draw.text((W // 2, H - 30), "#PR #楽天 #楽天お買い物", font=_get_font(18), fill=(180, 165, 150), anchor="ms")

    return canvas


# ── メイン関数 ────────────────────────────────────────────────────
def create_ad_image(product: Product, platform: str = "instagram") -> Path:
    """
    ランダムなデザインで広告画像を生成してファイルパスを返す
    platform: "instagram" (1080x1080) or "threads" (1080x1350)
    """
    design = random.choice(["minimal", "bold", "elegant"])
    print(f"[画像] デザイン: {design}")

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
