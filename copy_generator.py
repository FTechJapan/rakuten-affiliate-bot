"""
投稿文生成モジュール
Claude API を使ってSNS別の宣伝文を生成する
"""
import anthropic
from config import ANTHROPIC_API_KEY, HASHTAGS
from rakuten_api import Product

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def _build_hashtags(genre_id: str) -> str:
    tags = HASHTAGS.get(genre_id, []) + HASHTAGS["default"]
    return " ".join(tags)


def generate_copy(product: Product) -> dict[str, str]:
    """
    Instagram・Threads用の投稿文をそれぞれ生成して返す
    戻り値: {"instagram": "...", "threads": "..."}
    """
    hashtags = _build_hashtags(product.genre_id)

    prompt = f"""
あなたは楽天アフィリエイターのSNS担当です。
以下の商品情報を元に、Instagram用とThreads用の投稿文を日本語で生成してください。

【商品情報】
商品名: {product.name}
価格: ¥{product.price:,}
評価: {product.review_average:.1f}点（{product.review_count:,}件レビュー）
キャッチコピー: {product.catch_copy}
商品説明（抜粋）: {product.item_caption}

【ルール】
- 最初に絵文字で始める
- 実際に使ってみた体験談風の自然な文体にする
- 価格・評価・おすすめポイントを1〜2行で伝える
- 購入導線：「プロフのリンクからチェック👇」で締める
- 最後に必ず「#PR」を含める
- ハッシュタグは必ず全て「#」をつける（例：#ストール #ファッション）
- ハッシュタグ以外の単語をハッシュタグの前後に混入させない
- 嘘・誇大表現は絶対に書かない

【Instagram用】
- 5〜8行、絵文字多め
- ハッシュタグ：{hashtags}

【Threads用】
- 3〜5行、シンプルで読みやすく
- ハッシュタグは最低限（3〜5個）

以下のJSON形式のみで出力してください（説明文なし）:
{{
  "instagram": "投稿文全文",
  "threads": "投稿文全文"
}}
"""

    message = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()

    # JSON部分だけ抽出（```json ... ``` で囲まれている場合に対応）
    if "```" in raw:
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    import json
    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        # フォールバック：シンプルな文章を直接生成
        fallback = f"✨ 楽天で見つけたおすすめ商品！\n\n📦 {product.name}\n💰 ¥{product.price:,}\n⭐ {product.review_average:.1f}点（{product.review_count:,}件）\n\nプロフのリンクからチェック👇\n#PR {hashtags}"
        result = {"instagram": fallback, "threads": fallback}

    print(f"[Claude] 投稿文生成完了: {product.name[:30]}...")
    return result
