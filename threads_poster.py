"""
Threads 投稿モジュール
Threads API (Meta) を使ってテキスト＋画像を投稿する

事前準備:
  1. https://developers.facebook.com でアプリを作成
  2. Threadsプロダクトを追加
  3. threads_content_publish パーミッションを取得
  4. 長期アクセストークンを発行（60日有効）
"""
import time
import requests
from pathlib import Path
from config import META_ACCESS_TOKEN, THREADS_USER_ID

GRAPH_API = "https://graph.threads.net/v1.0"


def _upload_image_to_threads(image_path: Path, caption: str) -> str:
    """
    画像コンテナを作成してコンテナIDを返す
    ※ Threads APIはURLからの画像アップロードのため、
       画像を事前にネットワーク上に公開する必要がある
       → GitHub ActionsではArtifactとしてアップするか、
         S3 / Cloudflare R2 などを使う（setup_storage.md参照）
    """
    raise NotImplementedError(
        "画像をThreadsに投稿するには、画像を公開URLにアップロードする必要があります。\n"
        "README の「画像ストレージ設定」を参照してください。"
    )


def post_text_to_threads(text: str) -> str | None:
    """テキストのみをThreadsに投稿してpost_idを返す"""

    # ── Step1: コンテナ作成 ────────────────────────────
    resp = requests.post(
        f"{GRAPH_API}/{THREADS_USER_ID}/threads",
        data={
            "media_type": "TEXT",
            "text": text,
            "access_token": META_ACCESS_TOKEN,
        },
        timeout=30,
    )
    if not resp.ok:
        print(f"[Threads] コンテナ作成失敗: {resp.status_code} {resp.text}")
        return None

    container_id = resp.json().get("id")
    if not container_id:
        print("[Threads] container_id が取得できませんでした")
        return None

    # ── Step2: 公開 ────────────────────────────────────
    time.sleep(5)   # コンテナの処理待ち

    resp2 = requests.post(
        f"{GRAPH_API}/{THREADS_USER_ID}/threads_publish",
        data={
            "creation_id": container_id,
            "access_token": META_ACCESS_TOKEN,
        },
        timeout=30,
    )
    if not resp2.ok:
        print(f"[Threads] 公開失敗: {resp2.status_code} {resp2.text}")
        return None

    post_id = resp2.json().get("id")
    print(f"[Threads] 投稿完了 post_id={post_id}")
    return post_id


def post_image_to_threads(image_url: str, caption: str) -> str | None:
    """
    公開画像URL＋キャプションでThreadsに投稿する
    image_url: ネット上からアクセスできるjpeg/pngのURL
    """

    # ── Step1: 画像コンテナ作成 ───────────────────────
    resp = requests.post(
        f"{GRAPH_API}/{THREADS_USER_ID}/threads",
        data={
            "media_type": "IMAGE",
            "image_url": image_url,
            "text": caption,
            "access_token": META_ACCESS_TOKEN,
        },
        timeout=30,
    )
    if not resp.ok:
        print(f"[Threads] 画像コンテナ作成失敗: {resp.status_code} {resp.text}")
        return None

    container_id = resp.json().get("id")

    # ── Step2: 処理完了待ち（最大60秒） ─────────────────
    for attempt in range(12):
        time.sleep(5)
        status_resp = requests.get(
            f"{GRAPH_API}/{container_id}",
            params={"fields": "status,error_code", "access_token": META_ACCESS_TOKEN},
            timeout=10,
        )
        status = status_resp.json().get("status", "")
        if status == "FINISHED":
            break
        if status == "ERROR":
            print(f"[Threads] 画像処理エラー: {status_resp.json()}")
            return None
        print(f"[Threads] 画像処理中... ({attempt+1}/12)")

    # ── Step3: 公開 ────────────────────────────────────
    resp2 = requests.post(
        f"{GRAPH_API}/{THREADS_USER_ID}/threads_publish",
        data={
            "creation_id": container_id,
            "access_token": META_ACCESS_TOKEN,
        },
        timeout=30,
    )
    if not resp2.ok:
        print(f"[Threads] 公開失敗: {resp2.status_code} {resp2.text}")
        return None

    post_id = resp2.json().get("id")
    print(f"[Threads] 画像投稿完了 post_id={post_id}")
    return post_id
