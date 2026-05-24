"""
Threads 投稿モジュール
Threads API (Meta) を使ってテキスト＋画像を投稿する

2026年Threadsルール対応：
- トピックタグは1つのみ
- アフィリエイトリンクは本文ではなく返信欄に投稿
"""
import time
import requests
from config import THREADS_ACCESS_TOKEN, THREADS_USER_ID

GRAPH_API = "https://graph.threads.net/v1.0"


def _create_container(data: dict) -> str | None:
    """メディアコンテナを作成してIDを返す"""
    resp = requests.post(
        f"{GRAPH_API}/{THREADS_USER_ID}/threads",
        data={**data, "access_token": THREADS_ACCESS_TOKEN},
        timeout=30,
    )
    if not resp.ok:
        print(f"[Threads] コンテナ作成失敗: {resp.status_code} {resp.text}")
        return None
    return resp.json().get("id")


def _publish_container(container_id: str) -> str | None:
    """コンテナを公開してpost_idを返す"""
    resp = requests.post(
        f"{GRAPH_API}/{THREADS_USER_ID}/threads_publish",
        data={
            "creation_id": container_id,
            "access_token": THREADS_ACCESS_TOKEN,
        },
        timeout=30,
    )
    if not resp.ok:
        print(f"[Threads] 公開失敗: {resp.status_code} {resp.text}")
        return None
    return resp.json().get("id")


def _post_reply(post_id: str, text: str) -> str | None:
    """投稿への返信を投稿する"""
    container_id = _create_container({
        "media_type": "TEXT",
        "text": text,
        "reply_to_id": post_id,
    })
    if not container_id:
        return None

    time.sleep(3)
    return _publish_container(container_id)


def post_image_to_threads(
    image_url: str,
    caption: str,
    reply_text: str | None = None,
    affiliate_url: str | None = None,
) -> str | None:
    """
    公開画像URL＋キャプションでThreadsに投稿し、
    返信としてアフィリエイトリンクを投稿する

    image_url: 公開アクセス可能なJPEG画像URL
    caption: 投稿本文（トピックタグ1つのみ）
    reply_text: 返信テキスト
    affiliate_url: 楽天アフィリエイトURL
    """

    # ── Step1: 画像コンテナ作成 ───────────────────────
    container_id = _create_container({
        "media_type": "IMAGE",
        "image_url": image_url,
        "text": caption,
    })
    if not container_id:
        return None

    # ── Step2: 処理完了待ち（最大60秒） ─────────────────
    for attempt in range(12):
        time.sleep(5)
        status_resp = requests.get(
            f"{GRAPH_API}/{container_id}",
            params={"fields": "status,error_code", "access_token": THREADS_ACCESS_TOKEN},
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
    post_id = _publish_container(container_id)
    if not post_id:
        return None

    print(f"[Threads] 画像投稿完了 post_id={post_id}")

    # ── Step4: 返信にアフィリエイトリンクを投稿 ──────────
    if affiliate_url:
        time.sleep(3)
        reply_content = reply_text or "詳しくはこちら👇"
        reply_content += f"\n\n{affiliate_url}"
        reply_id = _post_reply(post_id, reply_content)
        if reply_id:
            print(f"[Threads] 返信投稿完了 reply_id={reply_id}")
        else:
            print("[Threads] 返信投稿失敗（メイン投稿は成功）")

    return post_id
