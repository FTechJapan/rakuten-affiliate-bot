"""
画像ストレージモジュール
生成した画像をCloudflare R2（無料枠あり）にアップロードして公開URLを返す

Cloudflare R2 無料枠:
  - ストレージ: 10GB/月
  - Class A操作(書込): 100万回/月
  - Class B操作(読込): 1000万回/月
  ※ SNS自動投稿用途なら無料枠で十分

代替: AWS S3, Google Cloud Storage なども同じ要領で使える
"""
import os
import boto3
from pathlib import Path
from datetime import datetime, UTC

# Cloudflare R2 の認証情報（GitHub Secrets に登録）
R2_ACCOUNT_ID  = os.environ.get("R2_ACCOUNT_ID", "")
R2_ACCESS_KEY  = os.environ.get("R2_ACCESS_KEY", "")
R2_SECRET_KEY  = os.environ.get("R2_SECRET_KEY", "")
R2_BUCKET_NAME = os.environ.get("R2_BUCKET_NAME", "affiliate-images")
R2_PUBLIC_URL  = os.environ.get("R2_PUBLIC_URL", "")  # 例: https://pub-xxxx.r2.dev


def get_r2_client():
    """boto3でCloudflare R2クライアントを作成"""
    return boto3.client(
        "s3",
        endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
        aws_access_key_id=R2_ACCESS_KEY,
        aws_secret_access_key=R2_SECRET_KEY,
        region_name="auto",
    )


def upload_image(image_path: Path) -> str:
    """
    画像をR2にアップロードして公開URLを返す
    Returns: "https://pub-xxxx.r2.dev/images/2025-01-01_abc123.jpg"
    """
    if not all([R2_ACCOUNT_ID, R2_ACCESS_KEY, R2_SECRET_KEY, R2_PUBLIC_URL]):
        raise EnvironmentError(
            "R2の認証情報が設定されていません。\n"
            "GitHub SecretsにR2_ACCOUNT_ID, R2_ACCESS_KEY, R2_SECRET_KEY, "
            "R2_BUCKET_NAME, R2_PUBLIC_URLを設定してください。"
        )

    client = get_r2_client()
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    key = f"images/{today}/{image_path.name}"

    client.upload_file(
        str(image_path),
        R2_BUCKET_NAME,
        key,
        ExtraArgs={"ContentType": "image/jpeg"},
    )

    public_url = f"{R2_PUBLIC_URL.rstrip('/')}/{key}"
    print(f"[R2] アップロード完了: {public_url}")
    return public_url
