"""
投稿文生成モジュール
Claude API を使ってSNS別の宣伝文を生成する

ルール：
- 投稿者は男性・楽天商品を調査・紹介するスタンス
- 自分が購入・使用したような嘘の体験談は絶対に書かない
- APIで取得した事実（レビュー数・評価・価格・商品説明）のみを使用
- クール・簡潔・魅力的な男性口調

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

# 投稿スタイルのバリエーション（全て事実ベース・クール男性口調）
STYLES = [
    {
        "name": "データ重視風",
        "instruction": """レビュー件数・評価・価格の数字を武器にする。
淡々としているのに説得力がある。数字だけで魅せる。
例：「レビュー4.5万件、評価4.7。数字が全部語ってる。」
「¥2,980でこのスペック。正直ズルい。」
「2万件超えのレビューは嘘をつかない。」""",
    },
    {
        "name": "発見報告風",
        "instruction": """楽天を調査していて発見した商品として報告する。
テンションを抑えつつも、確かな発見感を出す。
例：「楽天で掘り出し物を見つけた。」
「これ、普通に知らなかった。レビュー見て納得した。」
「調べてたら出てきた。なんでこれが¥〇〇なんだ。」""",
    },
    {
        "name": "問題解決風",
        "instruction": """読者の潜在的な悩みに静かに刺さる文章を書く。
押しつけがましくなく、でも確実に響く。
例：「〜が気になってる人、これ見といて損はない。」
「この悩み、実はこれで解決できる。レビュー数が証明してる。」
「〜で詰まってるなら、一回調べてみて。」""",
    },
    {
        "name": "コスパ特化風",
        "instruction": """価格対品質の異常なバランスを冷静に指摘する。
感情を抑えつつも「これは買いだ」という空気を作る。
例：「この価格でこのクオリティは普通じゃない。」
「コスパで選ぶならこれ一択かもしれない。」
「¥〇〇でレビュー〇万件。計算が合わない。良い意味で。」""",
    },
    {
        "name": "ランキング特化風",
        "instruction": """楽天での実績・ランキングを冷静に提示する。
「事実を並べるだけ」というスタンスで信頼感を出す。
例：「楽天ランキング上位の商品を調べたらこれが出てきた。」
「レビュー数でソートすると必ず上に来る商品がある。」
「これが〇万人に選ばれてる理由、調べてみた。」""",
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
あなたは楽天市場の商品を調査・紹介するクールな男性SNSアカウントです。
以下の商品情報を元に、Instagram用とThreads用の投稿文を日本語で生成してください。

【商品情報】
商品名: {product.name}
価格: ¥{product.price:,}
評価: {product.review_average:.1f}点（{product.review_count:,}件レビュー）
キャッチコピー: {product.catch_copy}
商品説明（抜粋）: {product.item_caption}

【今回の投稿スタイル】
{style['instruction']}

【文体・トーンの指針】
- クール・簡潔・無駄がない。一言一言に重みがある文体
- 「。」で終わる短い文を積み重ねるスタイルが効果的
- 感情的にならない。でも確実に魅力が伝わる
- 読んだ人が「気になる」「見てみたい」と思わせる
- 押しつけがましくない。でも引力がある

【絶対に守るルール】
- 投稿者は男性。女性的な口調・表現は一切使わない
- 「可愛い」「おしゃれ」「ちゃった」「だよ」などは禁止
- 自分が購入・使用・体験したような表現は絶対に書かない
- 「買ってみた」「使ってみた」「リピート買い」「友達に勧めた」は禁止
- 商品情報に記載されている事実のみを使う
- 確認できない情報（送料無料・割引率など）は書かない
- 嘘・誇大表現は絶対に書かない
- 最初に絵文字1つで始める（毎回違う絵文字）
- テンプレートのような単調な文章にしない

【Instagram用ルール】
- 5〜8行、適度に絵文字を挟む
- 「プロフのリンクからチェック👇」で締める
- 最後に必ず「#PR」を含める
- ハッシュタグ（全て#をつける）：{hashtags}

【Threads用ルール】（厳守）
- 3〜5行、500文字以内
- 読んだ人がコメントしたくなる余白を残す
- リンクは絶対に本文に入れない
- 購入導線（「プロフのリンク」など）も本文に入れない
- 文末は必ず「{topic} #PR」のみで終わること
- それ以外のハッシュタグ・単語を末尾に追加しない

以下のJSON形式のみで出力してください（説明文・Markdownなし）:
{{
  "instagram": "投稿文全文",
  "threads": "投稿文本文\\n\\n{topic} #PR",
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
            f"📦 楽天で気になる商品を見つけた。\n\n"
            f"{product.name}\n"
            f"💰 ¥{product.price:,}\n"
            f"⭐ {product.review_average:.1f}点（{product.review_count:,}件）\n\n"
            f"プロフのリンクからチェック👇\n#PR {hashtags}"
        )
        fallback_th = (
            f"楽天で気になる商品を見つけた。\n\n"
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
