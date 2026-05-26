"""
投稿文生成モジュール
Claude API を使ってSNS別の宣伝文を生成する

ルール：
- 投稿者は男性・楽天商品を調査・紹介するスタンス
- 自分が購入・使用したような嘘の体験談は絶対に書かない
- APIで取得した事実（レビュー数・評価・価格・商品説明）のみを使用
- 男性らしいシンプル・クールな口調

Threads 2026年ルール：
- トピックタグは1つのみ
- 本文にリンクを貼らず、返信欄にリンクを置く
- 500文字以内で会話を誘発する文体
"""
import json
import random
import anthropic
from config import ANTHROPIC_API_KEY, HASHTAGS
from rakuten_api import Product

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# 投稿スタイルのバリエーション（全て事実ベース・男性口調）
STYLES = [
    {
        "name": "データ重視風",
        "instruction": """レビュー件数・評価スコア・価格などの数字を前面に出す。
男性らしい淡々とした口調で、データが示す事実を伝える。
例：「レビュー4.5万件・評価4.7。この数字は正直すごい。」
「価格帯を考えると、スペックが釣り合っていない。良い意味で。」""",
    },
    {
        "name": "発見報告風",
        "instruction": """楽天を調査していて見つけた商品として報告するスタイル。
「見つけた」「気になった」「調べてみると」などの表現を使う。
例：「楽天でこれ見つけたんだが、レビュー数がおかしい。」
「気になって調べてみたら評価4.7で2万件超え。本物だった。」""",
    },
    {
        "name": "問題提起風",
        "instruction": """読者が抱えるであろう悩みを提起し、この商品が解決策になりうることを伝える。
男性らしい簡潔な文体で。自分が解決したとは書かない。
例：「〜で困ってる人、これ試す価値あるかも。」
「〜の問題、この商品で解決できそう。レビュー見る限り。」""",
    },
    {
        "name": "コスパ指摘風",
        "instruction": """価格と品質・スペックのバランスを客観的に指摘する。
「この価格でこのスペックは正直コスパがおかしい」という切り口で。
例：「¥〇〇でレビュー2万件超えの商品。コスパ見てくれ。」
「この価格帯でこの評価はちょっとおかしいと思う。」""",
    },
    {
        "name": "ランキング報告風",
        "instruction": """商品名・キャッチコピーに含まれるランキング情報や実績を前面に出す。
「楽天上位の商品を調べた」というスタンスで報告する。
例：「楽天で上位取ってるやつ調べたら、これが出てきた。」
「レビュー件数でソートしたらこれが上位だった。」""",
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
あなたは楽天市場の商品を調査・紹介する男性SNSアカウントの担当者です。
以下の商品情報を元に、Instagram用とThreads用の投稿文を日本語で生成してください。

【商品情報】
商品名: {product.name}
価格: ¥{product.price:,}
評価: {product.review_average:.1f}点（{product.review_count:,}件レビュー）
キャッチコピー: {product.catch_copy}
商品説明（抜粋）: {product.item_caption}

【今回の投稿スタイル】
{style['instruction']}

【絶対に守るルール】
- 投稿者は男性。女性的な口調・表現は一切使わない
- 「可愛い」「おしゃれ」「ちゃった」「だよ」などの女性的表現は禁止
- 自分が購入・使用・体験したような表現は絶対に書かない
- 「買ってみた」「使ってみた」「リピート買い」「友達に勧めた」は禁止
- 上記の商品情報に記載されている事実のみを使う
- 確認できない情報（送料無料・割引率など）は書かない
- 嘘・誇大表現は絶対に書かない
- 最初に絵文字で始める（毎回違う絵文字を使う）
- テンプレートのような単調な文章にしない
- シンプル・クール・簡潔な男性らしい文体にする

【Instagram用ルール】
- 5〜8行、適度に絵文字を使う
- 「プロフのリンクからチェック👇」で締める
- 最後に必ず「#PR」を含める
- ハッシュタグ（全て#をつける）：{hashtags}

【Threads用ルール】（重要）
- 3〜5行、500文字以内
- 読んだ人がコメントしたくなる「隙」を作る
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
            f"📦 楽天で注目の商品を見つけた。\n\n"
            f"{product.name}\n"
            f"💰 ¥{product.price:,}\n"
            f"⭐ {product.review_average:.1f}点（{product.review_count:,}件）\n\n"
            f"プロフのリンクからチェック👇\n#PR {hashtags}"
        )
        fallback_th = (
            f"📦 楽天で気になる商品を見つけた。\n\n"
            f"{product.name}\n"
            f"¥{product.price:,} / {product.review_average:.1f}点（{product.review_count:,}件）\n\n"
            f"{topic} #PR"
        )
        result = {
            "instagram": fallback_ig,
            "threads": fallback_th,
            "threads_reply": "詳しくはこちら👇\nプロフのリンクからもチェックできます",
        }

    if "threads_reply" not in result:
        result["threads_reply"] = "詳しくはこちら👇\nプロフのリンクからもチェックできます"

    print(f"[Claude] 投稿文生成完了: {product.name[:30]}...")
    return result
