"""
メイン実行スクリプト
GitHub Actions の Cron または ローカルから実行する

使い方:
  python main.py             # 全SNSに投稿
  python main.py --dry-run   # 投稿せずにプレビューのみ
  python main.py --threads-only   # Threadsのみ（画像なし、無料）
"""
import sys
import time
import json
import argparse
from datetime import datetime, UTC
from pathlib import Path

from rakuten_api import Product
from image_generator import create_ad_image
from copy_generator import generate_copy
from storage import upload_image
from threads_poster import post_image_to_threads
from instagram_poster import post_image_to_instagram, check_daily_limit

LOG_FILE = Path("output/log.jsonl")
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)


def log(data: dict):
    """実行結果をJSONL形式で記録（毎日の成果確認用）"""
    data["timestamp"] = datetime.now(UTC).isoformat()
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False) + "\n")
    print(f"[LOG] {data}")


def run(dry_run: bool = False, threads_only: bool = False):
    print(f"\n{'='*50}")
    print(f" 楽天アフィリエイトBot 起動 {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f" dry_run={dry_run}, threads_only={threads_only}")
    print(f"{'='*50}\n")

    # ── 1. 商品取得 ─────────────────────────────────────
    with open("products.json", encoding="utf-8") as f:
        data = json.load(f)
    products = [Product(**p) for p in data]
    print(f"[商品] products.jsonから{len(products)}件読み込み完了")

    for idx, product in enumerate(products):
        print(f"\n[{idx+1}/{len(products)}] {product.name[:40]}")
        print(f"  価格: ¥{product.price:,}  評価: {product.review_average:.1f}点")

        try:
            # ── 2. 投稿文生成 ────────────────────────────
            copies = generate_copy(product)

            # ── 3. 画像生成 ──────────────────────────────
            ig_image_path    = create_ad_image(product, "instagram")
            th_image_path    = create_ad_image(product, "threads")

            if dry_run:
                print("\n[DRY RUN] 投稿内容プレビュー:")
                print("--- Instagram ---")
                print(copies["instagram"])
                print("--- Threads ---")
                print(copies["threads"])
                log({"product": product.name, "price": product.price, "status": "dry_run"})
                continue

            # ── 4. 画像アップロード（R2） ─────────────────
            ig_image_url = upload_image(ig_image_path)
            th_image_url = upload_image(th_image_path)

            # ── 5. Threads に投稿 ────────────────────────
            threads_post_id = post_image_to_threads(th_image_url, copies["threads"])
            log({
                "platform": "threads",
                "product": product.name,
                "price": product.price,
                "affiliate_url": product.affiliate_url,
                "post_id": threads_post_id,
                "status": "success" if threads_post_id else "failed",
            })

            # ── 6. Instagram に投稿 ──────────────────────
            if not threads_only:
                if check_daily_limit():
                    ig_post_id = post_image_to_instagram(ig_image_url, copies["instagram"])
                    log({
                        "platform": "instagram",
                        "product": product.name,
                        "price": product.price,
                        "affiliate_url": product.affiliate_url,
                        "post_id": ig_post_id,
                        "status": "success" if ig_post_id else "failed",
                    })
                else:
                    print("[Instagram] 本日の投稿上限に達しました")

        except Exception as e:
            print(f"[エラー] {product.name[:30]}: {e}")
            log({"product": product.name, "status": "error", "error": str(e)})

        # 投稿間隔（連続投稿によるスパム判定を避ける）
        if idx < len(products) - 1:
            wait = 600  # 10分待機
            print(f"\n[待機] 次の投稿まで {wait//60}分 待機...")
            if not dry_run:
                time.sleep(wait)

    print("\n✅ 本日の投稿処理が完了しました\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run",       action="store_true", help="投稿せずプレビューのみ")
    parser.add_argument("--threads-only",  action="store_true", help="Threadsのみ投稿")
    args = parser.parse_args()

    run(dry_run=args.dry_run, threads_only=args.threads_only)
