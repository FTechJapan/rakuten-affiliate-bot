"""
広告画像生成モジュール
クールな3パターンのデザイン
- dark_minimal: 純黒背景・余白重視・シンプル
- neon_accent: ダーク背景・蛍光オレンジアクセント
- magazine: 白黒ベース・雑誌風タイポグラフィ
"""
import io
import os
import random
import textwrap
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont

from config import IMAGE_SIZES
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
        return Image.new("RGBA", (size, size), (40, 40, 40, 255))


def _format_price(price: int) -> str:
    return f"¥{price:,}"


def _star_rating(average: float) -> str:
    full  = int(average)
    half  = 1 if (average - full) >= 0.5 else 0
    empty = 5 - full - half
    return "★" * full + "☆" * half + "☆" * empty


def _is_ig(platform: str) -> bool:
    return platform == "instagram"


# ── Design 1: Dark Minimal ────────────────────────────────────────
def _create_dark_minimal(product: Product, platform: str) -> Image.Image:
    W, H = IMAGE_SIZES[platform]
    ig = _is_ig(platform)

    # 純黒背景
    canvas = Image.new("RGB", (W, H), (10, 10, 10))
    draw = ImageDraw.Draw(canvas)

    # 細いトップライン
    draw.rectangle([(0, 0), (W, 3)], fill=(230, 60, 14))

    # ヘッダーテキスト
    draw.text((40, 28), "RAKUTEN", font=_get_font(16), fill=(80, 80, 80))
    draw.text((W - 40, 28), "#PR", font=_get_font(16), fill=(80, 80, 80), anchor="rm")

    # 商品画像（左寄せ）
    img_size = int(W * 0.52) if ig else int(W * 0.58)
    product_img = _get_product_image(product, img_size)
    img_x = 40
    img_y = 60
    # 薄いグレーの枠
    draw.rectangle([(img_x - 1, img_y - 1), (img_x + img_size + 1, img_y + img_size + 1)],
                   fill=(30, 30, 30))
    canvas.paste(product_img.convert("RGB"), (img_x, img_y))

    # 右側テキストエリア
    tx = img_x + img_size + 30
    tw = W - tx - 30

    # 価格（大きく）
    price_font_size = 52 if ig else 64
    draw.text((tx, img_y + 10), _format_price(product.price),
              font=_get_font(price_font_size), fill=(230, 60, 14))

    # 評価
    stars_y = img_y + (60 if ig else 80)
    draw.text((tx, stars_y), _star_rating(product.review_average),
              font=_get_font(20), fill=(180, 140, 60))
    draw.text((tx, stars_y + 28), f"{product.review_average:.1f}  ({product.review_count:,}件)",
              font=_get_font(16), fill=(100, 100, 100))

    # 商品名
    name_y = stars_y + 70
    name_lines = textwrap.wrap(product.name, width=10 if ig else 12)[:3]
    for i, line in enumerate(name_lines):
        draw.text((tx, name_y + i * 30), line, font=_get_font(20 if ig else 22), fill=(220, 220, 220))

    # ボトムライン
    draw.rectangle([(0, H - 3), (W, H)], fill=(230, 60, 14))

    # CTA
    btn_y = H - 70
    draw.text((W // 2, btn_y), "プロフのリンクからチェック",
              font=_get_font(20 if ig else 22), fill=(150, 150, 150), anchor="mm")

    return canvas


# ── Design 2: Neon Accent ─────────────────────────────────────────
def _create_neon_accent(product: Product, platform: str) -> Image.Image:
    W, H = IMAGE_SIZES[platform]
    ig = _is_ig(platform)

    # ダーク背景
    canvas = Image.new("RGB", (W, H), (18, 18, 22))
    draw = ImageDraw.Draw(canvas)

    # 左側のネオンライン
    draw.rectangle([(0, 0), (4, H)], fill=(255, 80, 20))

    # ヘッダー帯
    draw.rectangle([(0, 0), (W, 72)], fill=(22, 22, 28))
    draw.text((24, 36), "楽天市場 厳選", font=_get_font(22), fill=(255, 255, 255), anchor="lm")
    draw.text((W - 24, 36), "#PR", font=_get_font(20), fill=(255, 80, 20), anchor="rm")

    # 商品画像（中央上）
    img_size = int(W * 0.60) if ig else int(W * 0.65)
    product_img = _get_product_image(product, img_size)

    # グロー効果風の枠
    glow_pad = 6
    draw.rectangle(
        [(W//2 - img_size//2 - glow_pad, 82 - glow_pad),
         (W//2 + img_size//2 + glow_pad, 82 + img_size + glow_pad)],
        fill=(40, 20, 10)
    )
    canvas.paste(product_img.convert("RGB"), (W//2 - img_size//2, 82))

    # 価格ブロック
    price_y = 82 + img_size + 20
    draw.rectangle([(20, price_y), (W - 20, price_y + 80)], fill=(28, 28, 35))
    draw.text((W//2, price_y + 40), _format_price(product.price),
              font=_get_font(58 if ig else 68), fill=(255, 80, 20), anchor="mm")

    # 評価・件数
    review_y = price_y + 96
    draw.text((W//2, review_y), f"{_star_rating(product.review_average)}  {product.review_average:.1f}  ({product.review_count:,}件)",
              font=_get_font(22 if ig else 26), fill=(180, 140, 40), anchor="mm")

    # 商品名
    name_y = review_y + 44
    name_lines = textwrap.wrap(product.name, width=22 if ig else 24)[:2]
    for i, line in enumerate(name_lines):
        draw.text((W//2, name_y + i * 36), line,
                  font=_get_font(24 if ig else 28), fill=(200, 200, 210), anchor="mm")

    # CTAボタン
    btn_y = H - 110
    draw.rounded_rectangle([(40, btn_y), (W - 40, btn_y + 60)],
                            radius=4, fill=(255, 80, 20))
    draw.text((W//2, btn_y + 30), "プロフのリンクからチェック",
              font=_get_font(22 if ig else 26), fill=(255, 255, 255), anchor="mm")

    # フッター
    draw.text((W//2, H - 28), "#PR",
              font=_get_font(16), fill=(60, 60, 70), anchor="mm")

    return canvas


# ── Design 3: Magazine ────────────────────────────────────────────
def _create_magazine(product: Product, platform: str) -> Image.Image:
    W, H = IMAGE_SIZES[platform]
    ig = _is_ig(platform)

    # オフホワイト背景
    canvas = Image.new("RGB", (W, H), (245, 243, 240))
    draw = ImageDraw.Draw(canvas)

    # トップバー（黒）
    draw.rectangle([(0, 0), (W, 80)], fill=(15, 15, 15))
    draw.text((40, 40), "RAKUTEN SELECTION", font=_get_font(20), fill=(255, 255, 255), anchor="lm")
    draw.text((W - 40, 40), "#PR", font=_get_font(18), fill=(230, 60, 14), anchor="rm")

    # 商品画像（全幅）
    img_h = int(H * 0.45) if ig else int(H * 0.48)
    product_img = _get_product_image(product, W)
    # 横長にリサイズ
    try:
        orig = _download_image(product.image_url)
        orig_w, orig_h = orig.size
        scale = W / orig_w
        new_h = int(orig_h * scale)
        orig_resized = orig.resize((W, new_h), Image.LANCZOS)
        if new_h >= img_h:
            top = (new_h - img_h) // 3
            orig_cropped = orig_resized.crop((0, top, W, top + img_h))
        else:
            orig_cropped = Image.new("RGB", (W, img_h), (200, 200, 200))
            orig_cropped.paste(orig_resized.convert("RGB"), (0, (img_h - new_h) // 2))
        canvas.paste(orig_cropped.convert("RGB"), (0, 80))
    except Exception:
        canvas.paste(product_img.convert("RGB"), (0, 80))
        img_h = product_img.size[1]

    # 黒帯オーバーレイ（画像下部）
    overlay_y = 80 + img_h - 60
    draw.rectangle([(0, overlay_y), (W, 80 + img_h)], fill=(15, 15, 15))
    draw.text((40, overlay_y + 30), _format_price(product.price),
              font=_get_font(44 if ig else 52), fill=(230, 60, 14), anchor="lm")
    draw.text((W - 40, overlay_y + 30),
              f"{_star_rating(product.review_average)} {product.review_average:.1f}",
              font=_get_font(22), fill=(200, 160, 60), anchor="rm")

    # テキストエリア
    text_y = 80 + img_h + 20
    draw.line([(40, text_y), (W - 40, text_y)], fill=(15, 15, 15), width=2)
    text_y += 16

    # 商品名
    name_lines = textwrap.wrap(product.name, width=24 if ig else 26)[:2]
    for i, line in enumerate(name_lines):
        draw.text((40, text_y + i * 38), line,
                  font=_get_font(26 if ig else 30), fill=(20, 20, 20))

    # レビュー件数
    review_y = text_y + len(name_lines) * 38 + 12
    draw.text((40, review_y), f"レビュー {product.review_count:,}件",
              font=_get_font(18 if ig else 20), fill=(120, 120, 120))

    # CTAライン
    btn_y = H - 90
    draw.rectangle([(0, btn_y - 1), (W, btn_y)], fill=(15, 15, 15))
    draw.rectangle([(0, btn_y), (W, H)], fill=(15, 15, 15))
    draw.text((W//2, btn_y + 44), "プロフのリンクからチェック",
              font=_get_font(22 if ig else 26), fill=(255, 255, 255), anchor="mm")

    return canvas


# ── メイン関数 ────────────────────────────────────────────────────
def create_ad_image(product: Product, platform: str = "instagram") -> Path:
    """
    ランダムなクールデザインで広告画像を生成してファイルパスを返す
    platform: "instagram" (1080x1080) or "threads" (1080x1350)
    """
    design = random.choice(["dark_minimal", "neon_accent", "magazine"])
    print(f"[画像] デザイン: {design} / platform: {platform}")

    if design == "dark_minimal":
        canvas = _create_dark_minimal(product, platform)
    elif design == "neon_accent":
        canvas = _create_neon_accent(product, platform)
    else:
        canvas = _create_magazine(product, platform)

    safe_name = product.item_code.replace("/", "_").replace(":", "_")
    out_path = OUTPUT_DIR / f"{safe_name}_{platform}.jpg"
    canvas.convert("RGB").save(out_path, "JPEG", quality=92, optimize=True)
    print(f"[画像] 生成完了: {out_path}")
    return out_path
