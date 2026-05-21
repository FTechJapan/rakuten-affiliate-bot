# 楽天アフィリエイト自動投稿Bot

Instagram・Threadsに毎日自動で楽天アフィリエイト商品を投稿するBotです。

---

## 全体の流れ

```
楽天API → 商品取得 → Pillow画像生成 → Claude API投稿文生成
→ Cloudflare R2に画像アップ → Threads / Instagram に自動投稿
```

---

## セットアップ手順（順番どおりに進めてください）

### Step 1 — 楽天APIキー取得（10分）

1. https://webservice.rakuten.co.jp/ にアクセス
2. 「新規アプリ登録」→ アプリ名・URLを適当に入力
3. **アプリID** をメモ
4. https://affiliate.rakuten.co.jp/ に別途登録
5. **アフィリエイトID** をメモ（`12345.6789abcd`形式）

### Step 2 — Claude APIキー取得（5分）

1. https://console.anthropic.com/ にアクセス（claude.aiとは別サービス）
2. 「API Keys」→「Create Key」
3. **APIキー** をメモ（`sk-ant-...`形式）
4. 支払い方法を登録（1日3投稿で月100〜300円程度）

### Step 3 — Cloudflare R2セットアップ（20分）

画像をInstagram/Threadsに渡すための公開ストレージです。

1. https://cloudflare.com/ に登録（無料）
2. ダッシュボード → 「R2」→「バケットを作成」
   - バケット名: `affiliate-images`
3. 「パブリックアクセスを許可」をON
   - **公開URL** (`https://pub-xxxx.r2.dev`) をメモ
4. 「APIトークン」→「R2トークンを作成」（Read & Write）
   - **Account ID**・**Access Key**・**Secret Key** をメモ

### Step 4 — Meta（Instagram/Threads）APIセットアップ（30分）

**Instagram側の準備:**
1. InstagramをBusinessアカウントに切替（設定→アカウント→プロアカウントに切替）
2. Facebookページを作成してInstagramと連携

**Meta Developersでアプリ作成:**
1. https://developers.facebook.com/ → 「マイアプリ」→「アプリを作成」
2. 「その他」→「ビジネス」を選択
3. 「プロダクトを追加」→ **Instagram** と **Threads** を両方追加
4. 「Instagram → APIの設定」でInstagramアカウントを連携
5. 「アクセストークンを生成」→ **長期アクセストークン**（60日有効）を取得
6. 設定 → 基本設定 → **Instagram アカウントID** をメモ

**Threads ユーザーIDの確認:**
```bash
curl "https://graph.threads.net/v1.0/me?access_token=YOUR_TOKEN"
# → "id" の値をメモ
```

### Step 5 — GitHubリポジトリにSecretsを登録（10分）

1. このリポジトリをGitHubにpush
2. Settings → Secrets and variables → Actions → 「New repository secret」
3. 以下を全て登録:

| Secret名 | 内容 |
|---|---|
| `RAKUTEN_APP_ID` | 楽天アプリID |
| `RAKUTEN_AFFILIATE_ID` | 楽天アフィリエイトID |
| `ANTHROPIC_API_KEY` | Claude APIキー |
| `META_ACCESS_TOKEN` | Metaの長期アクセストークン |
| `INSTAGRAM_ACCOUNT_ID` | InstagramアカウントID |
| `THREADS_USER_ID` | ThreadsユーザーID |
| `R2_ACCOUNT_ID` | CloudflareアカウントID |
| `R2_ACCESS_KEY` | R2アクセスキー |
| `R2_SECRET_KEY` | R2シークレットキー |
| `R2_BUCKET_NAME` | `affiliate-images` |
| `R2_PUBLIC_URL` | R2の公開URL |

### Step 6 — 動作テスト

```bash
# ローカルでテスト（投稿はしない）
pip install -r requirements.txt
export RAKUTEN_APP_ID="your_id"  # ... 他も同様
python main.py --dry-run

# Threadsのみで本番テスト
python main.py --threads-only
```

GitHubのActions → 「楽天アフィリエイト 日次投稿」→「Run workflow」でも手動実行できます。

---

## カスタマイズ

### 投稿する商品ジャンルを変更

`config.py` の `RAKUTEN_GENRE_IDS` を変更してください。
ジャンルIDは https://webservice.rakuten.co.jp/api/ichibagenresearch/ で確認できます。

### 投稿時間を変更

`.github/workflows/daily.yml` の `cron` を変更してください。
```yaml
- cron: "0 0 * * *"  # UTC 00:00 = JST 09:00
- cron: "0 3 * * *"  # UTC 03:00 = JST 12:00（昼投稿）
```

### アクセストークンの自動更新

Metaのアクセストークンは60日で期限切れになります。
自動更新Actionを追加することも可能です（詳細はissueで）。

---

## コスト目安（1日3投稿・月90投稿の場合）

| サービス | 月額 |
|---|---|
| Claude API | 〜200円 |
| Cloudflare R2 | 無料 |
| GitHub Actions | 無料 |
| 楽天API | 無料 |
| Instagram / Threads API | 無料 |
| **合計** | **〜200円/月** |

---

## 注意事項（法的に重要）

- 投稿には必ず `#PR` または `#広告` を含めてください（景品表示法）
- 楽天アフィリエイト規約を遵守してください
- 虚偽・誇大な表現は絶対に使用しないでください
- Instagramの1日投稿上限は25件です（Botは3件なので問題なし）
