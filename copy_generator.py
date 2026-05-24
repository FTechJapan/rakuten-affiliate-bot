"""
投稿文生成モジュール
Claude API を使ってSNS別の宣伝文を生成する
毎回異なるスタイル・切り口で文章を生成する

Threads 2026年ルール：
- トピックタグは1つのみ（ハッシュタグ複数は非推奨）
- 本文にリンクを貼らず、返信欄にリンクを置く
- 500文字以内で会話を誘発する文体
"""
import json
import random
import anthropic
from config import ANTHROPIC_API_KEY, HASHTAGS
from rakuten_api import Product

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# 投稿スタイルのバリエーション
STYLES = [
    {
        "name": "体験談風",
        "instruction": "実際に自分が買って使ってみた体験談として書く。「買ってみた」「使ってみたら」などの表現を使う。驚きや感動を自然に表現する。",
    },
    {
        "name": "問題解決風",
        "instruction": "読者が抱えているであろう悩みや問題から始め、この商品がどう解決してくれるかを伝える。「〜で困っていませんか？」「〜が解決しました」などの表現を使う。",
    },
    {
        "name": "発見・驚き風",
        "instruction": "楽天でたまたま見つけた掘り出し物として書く。「こんな商品あったの！？」「見つけてしまいました」などの表現で読者の興味を引く。",
    },
    {
        "name": "比較・コスパ風",
        "instruction": "コスパの良さや品質の高さを強調して書く。「この価格でこのクオリティは反則」「コスパ最強」などの表現を使いながら具体的な良さを伝える。",
    },
    {
        "name": "季節・トレンド風",
        "instruction": "今の季節や生活シーンに合わせた切り口で書く。「この季節に絶対欲しい」「生活が変わった」などのリアルな表現を使う。",
    },
    {
        "name": "リピート買い風",
        "instruction": "何度もリピートしている、または周りにも勧めているという設定で書く。「もう何個目か」「友達にも勧めまくってる」などの表現で信頼感を出す。",
    },
]

# ジャンル別トピックタグ（Threads用・1つのみ）
THREADS_TOPIC = {
    "100533": "#キッチン",
    "565105": "#掃除",
    "215783": "#インテリア",
    "562701": "#収納",
    "100371": "#美容",
    "default": "#楽天",
}


def _build_hashtags(genre_id: str) -> str:
    """Instagram用ハッシュタグ"""
    tags = HASHTAGS.get(genre_id, []) + HASHTAGS["default"]
    return " ".join(tags)


def _get_threads_topic(genre_id: str) -> str:
    """Threads用トピックタグ（1つのみ）"""
    return THREADS_TOPIC.get(genre_id, THREADS_TOPIC["default"])


def generate_copy(product: Product) -> dict[str, str]:
    """
    Instagram・Threads用の投稿文をそれぞれ生成して返す
    戻り値: {
        "instagram": "投稿文全文（ハッシュタグ含む）",
        "threads": "投稿文（トピックタグ1つのみ・リンクなし）",
        "threads_reply": "返信用リンクテキスト"
    }
    """
    hashtags = _build_hashtags(product.genre_id)
    topic = _get_threads_topic(product.genre_id)
    style = random.choice(STYLES)
    print(f"[Claude] 投稿スタイル: {style['name']}")

    prompt = f"""
あなたは楽天アフィリエイターのSNS担当です。
以下の商品情報を元に、Instagram用とThreads用の投稿文を日本語で生成してください。

【商品情報】
商品名: {product.name}
価格: ¥{product.price:,}
評価: {product.review_average:.1f}点（{product.review_count:,}件レビュー）
キャッチコピー: {product.catch_copy}
商品説明（抜粋）: {product.item_caption}

【今回の投稿スタイル】
{style['instruction']}

【共通ルール】
- 最初に絵文字で始める（毎回違う絵文字を使う）
- 指定されたスタイルに合った自然な文体にする
- 価格・評価・おすすめポイントを具体的に伝える
- 嘘・誇大表現は絶対に書かない
- テンプレートのような単調な文章にしない

【Instagram用ルール】
- 5〜8行、絵文字多め、読者が思わず保存したくなる内容
- 「プロフのリンクからチェック👇」で締める
- 最後に必ず「#PR」を含める
- ハッシュタグ（全て#をつける）：{hashtags}

【Threads用ルール】（重要）
- 3〜5行、500文字以内
- 読んだ人がコメントしたくなる「隙」を作る自然な文体
- リンクは絶対に本文に入れない（返信欄に置くため）
- 「プロフのリンク」などの購入導線も本文に入れない
- トピックタグは末尾に「{topic}」を1つだけ追加
- それ以外のハッシュタグは一切使わない
- 最後に「#PR」を追加する

以下のJSON形式のみで出力してください（説明文・Markdownなし）:
{{
  "instagram": "投稿文全文",
  "threads": "投稿文（トピックタグ1つ・#PRのみ）",
  "threads_reply": "詳しくはこちら👇\\nプロフのリンクからもチェックできます"
}}
"""

    message = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1200,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()

    if "```" in raw:
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        fallback_ig = (
            f"✨ 楽天で見つけたおすすめ商品！\n\n"
            f"📦 {product.name}\n"
            f"💰 ¥{product.price:,}\n"
            f"⭐ {product.review_average:.1f}点（{product.review_count:,}件）\n\n"
            f"プロフのリンクからチェック👇\n#PR {hashtags}"
        )
        fallback_th = (
            f"✨ 楽天で見つけたおすすめ商品！\n\n"
            f"¥{product.price:,} / {product.review_average:.1f}点\n\n"
            f"{topic} #PR"
        )
        result = {
            "instagram": fallback_ig,
            "threads": fallback_th,
            "threads_reply": "詳しくはこちら👇\nプロフのリンクからもチェックできます",
        }

    # threads_replyがない場合のフォールバック
    if "threads_reply" not in result:
        result["threads_reply"] = "詳しくはこちら👇\nプロフのリンクからもチェックできます"

    print(f"[Claude] 投稿文生成完了: {product.name[:30]}...")
    return result
