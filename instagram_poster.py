"""
Instagram 投稿モジュール
Meta Graph API を使って画像投稿する

事前準備:
  1. InstagramをBusinessまたはCreatorアカウントに切替
  2. Facebookページにリンク
  3. developers.facebook.com でアプリを作成
  4. instagram_content_publish パーミッションを取得
  5. 長期アクセストークンを発行
"""
import time
import requests
from config import META_ACCESS_TOKEN, INSTAGRAM_ACCOUNT_ID

GRAPH_API = "https://graph.facebook.com/v21.0"


def post_image_to_instagram(image_url: str, caption: str) -> str | None:
    """
    公開画像URL＋キャプションでInstagramフィードに投稿する
    image_url: 公開アクセス可能なJPEG画像のURL（HTTPS必須）
    """

    # ── Step1: メディアコンテナ作成 ──────────────────────
    resp = requests.post(
        f"{GRAPH_API}/{INSTAGRAM_ACCOUNT_ID}/media",
        data={
            "image_url": image_url,
            "caption": caption,
            "access_token": META_ACCESS_TOKEN,
        },
        timeout=30,
    )
    if not resp.ok:
        print(f"[Instagram] コンテナ作成失敗: {resp.status_code} {resp.text}")
        return None

    container_id = resp.json().get("id")
    if not container_id:
        print("[Instagram] container_id が取得できませんでした")
        return None

    # ── Step2: 処理完了待ち（最大90秒） ─────────────────
    for attempt in range(18):
        time.sleep(5)
        status_resp = requests.get(
            f"{GRAPH_API}/{container_id}",
            params={"fields": "status_code", "access_token": META_ACCESS_TOKEN},
            timeout=10,
        )
        status = status_resp.json().get("status_code", "")
        if status == "FINISHED":
            break
        if status == "ERROR":
            print(f"[Instagram] 画像処理エラー: {status_resp.json()}")
            return None
        print(f"[Instagram] 画像処理中... ({attempt+1}/18) status={status}")

    # ── Step3: 公開 ────────────────────────────────────
    resp2 = requests.post(
        f"{GRAPH_API}/{INSTAGRAM_ACCOUNT_ID}/media_publish",
        data={
            "creation_id": container_id,
            "access_token": META_ACCESS_TOKEN,
        },
        timeout=30,
    )
    if not resp2.ok:
        print(f"[Instagram] 公開失敗: {resp2.status_code} {resp2.text}")
        return None

    post_id = resp2.json().get("id")
    print(f"[Instagram] 投稿完了 post_id={post_id}")
    return post_id


def check_daily_limit() -> bool:
    """1日25件の投稿上限を確認する"""
    resp = requests.get(
        f"{GRAPH_API}/{INSTAGRAM_ACCOUNT_ID}/content_publishing_limit",
        params={
            "fields": "config,quota_usage",
            "access_token": META_ACCESS_TOKEN,
        },
        timeout=10,
    )
    if not resp.ok:
        return True   # 確認できない場合は続行

    data = resp.json().get("data", [{}])[0]
    usage = data.get("quota_usage", 0)
    limit = data.get("config", {}).get("quota_total", 25)
    print(f"[Instagram] 本日の投稿数: {usage}/{limit}")
    return usage < limit
