"""
設定ファイル - 環境変数から全APIキーを読み込む
GitHub ActionsのSecretsに同名で登録してください
"""
import os

# ── 楽天API ──────────────────────────────────────────────
RAKUTEN_APP_ID = os.environ["RAKUTEN_APP_ID"]          # 楽天デベロッパー登録で取得
RAKUTEN_ACCESS_KEY = os.environ["RAKUTEN_ACCESS_KEY"]
RAKUTEN_AFFILIATE_ID = os.environ["RAKUTEN_AFFILIATE_ID"]  # 楽天アフィリエイト登録で取得

# ── Claude API ────────────────────────────────────────────
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]    # console.anthropic.com で取得

# ── Meta (Instagram / Threads) ───────────────────────────
THREADS_ACCESS_TOKEN   = os.environ["THREADS_ACCESS_TOKEN"]
INSTAGRAM_ACCESS_TOKEN = os.environ["INSTAGRAM_ACCESS_TOKEN"]
INSTAGRAM_ACCOUNT_ID = os.environ["INSTAGRAM_ACCOUNT_ID"]
THREADS_USER_ID = os.environ["THREADS_USER_ID"]        # Threadsのユーザーid

# ── 投稿設定 ──────────────────────────────────────────────
POSTS_PER_DAY = 3          # 1日あたりの投稿数
RAKUTEN_GENRE_IDS = [
    "100371",   # コスメ・香水・美容
    "216131",   # 食品
    "100533",   # キッチン・日用品
]
MIN_REVIEW_COUNT = 100     # レビュー件数の下限（信頼性フィルター）
MIN_REVIEW_AVERAGE = 4.0   # 評価スコアの下限

# ── 画像設定 ──────────────────────────────────────────────
IMAGE_SIZES = {
    "instagram": (1080, 1080),   # 正方形
    "threads":   (1080, 1350),   # 縦長4:5
}
BRAND_COLOR  = (255, 90, 36)     # メインカラー（オレンジ系）
ACCENT_COLOR = (255, 255, 255)
BG_COLOR     = (248, 246, 242)

# ── ハッシュタグ（カテゴリ別） ────────────────────────────
HASHTAGS = {
    "default": ["#楽天", "#楽天お買い物", "#PR", "#おすすめ", "#購入品"],
    "100371":  ["#コスメ", "#美容", "#スキンケア", "#メイク", "#美容好きな人と繋がりたい"],
    "216131":  ["#食品", "#グルメ", "#食べ物", "#おいしい", "#食べ物好きな人と繋がりたい"],
    "100533":  ["#キッチン", "#日用品", "#生活雑貨", "#暮らし", "#丁寧な暮らし"],
}
