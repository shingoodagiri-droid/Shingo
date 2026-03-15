# Gmail 未返信見積もり案件チェッカー - セットアップ手順

毎朝9時にGmailの未返信見積もり案件を検索し、LINEに通知するツールです。

---

## 1. Google Cloud プロジェクトの作成と Gmail API 設定

### 1-1. プロジェクト作成
1. [Google Cloud Console](https://console.cloud.google.com/) にアクセス
2. 「プロジェクトを作成」→ プロジェクト名（例: `gmail-estimate-checker`）を入力して作成

### 1-2. Gmail API の有効化
1. 左メニュー「APIとサービス」→「ライブラリ」
2. 「Gmail API」を検索 →「有効にする」

### 1-3. OAuth 同意画面の設定
1. 「APIとサービス」→「OAuth 同意画面」
2. ユーザータイプ: 「外部」を選択
3. アプリ名、サポートメールを入力
4. スコープ: `https://www.googleapis.com/auth/gmail.readonly` を追加
5. テストユーザーに自分の Gmail アドレスを追加して保存

### 1-4. OAuth クライアント ID の作成
1. 「APIとサービス」→「認証情報」→「認証情報を作成」→「OAuth クライアント ID」
2. アプリケーションの種類: 「デスクトップアプリ」
3. 名前を入力して「作成」
4. **JSON をダウンロード**し、プロジェクトルートに `credentials.json` として保存

---

## 2. LINE Messaging API の設定

### 2-1. LINE Developers でチャネル作成
1. [LINE Developers](https://developers.line.biz/) にログイン
2. 「プロバイダー」を作成（未作成の場合）
3. 「Messaging API」チャネルを新規作成
   - チャネル名: 任意（例: 見積チェッカー）
   - チャネル説明: 任意
4. 作成後、チャネル設定画面へ

### 2-2. チャネルアクセストークンの取得
1. チャネル設定 →「Messaging API設定」タブ
2. 一番下の「チャネルアクセストークン（長期）」→「発行」
3. 表示されたトークンをコピー

### 2-3. ユーザー ID の取得
1. チャネル設定 →「チャネル基本設定」タブ
2. 「あなたのユーザーID」をコピー（`U` から始まる文字列）

### 2-4. LINE公式アカウントを友だち追加
1. チャネル設定 →「Messaging API設定」タブ → QRコード
2. スマホのLINEアプリでQRコードを読み取り、友だち追加

---

## 3. 環境構築

```bash
# Python 仮想環境の作成
python3 -m venv venv
source venv/bin/activate

# 依存パッケージのインストール
pip install -r requirements.txt
```

## 4. 環境変数の設定

`.env.example` をコピーして `.env` を作成:

```bash
cp .env.example .env
```

`.env` を編集して、LINE の認証情報を入力:

```
LINE_CHANNEL_ACCESS_TOKEN=あなたのチャネルアクセストークン
LINE_USER_ID=あなたのユーザーID
```

## 5. 初回実行（Gmail 認証）

```bash
python3 check_unreplied_estimates.py
```

初回実行時にブラウザが開き、Google アカウントの認証を求められます。
許可すると `token.pickle` が生成され、以降は自動で認証されます。

## 6. cron の設定（毎朝9時に自動実行）

```bash
bash setup_cron.sh
```

または手動で:

```bash
crontab -e
# 以下の行を追加:
0 9 * * * /home/user/Shingo/run_checker.sh >> /home/user/Shingo/logs/cron.log 2>&1
```

---

## ファイル構成

```
Shingo/
├── check_unreplied_estimates.py  # メインスクリプト
├── credentials.json              # Google OAuth認証情報（要配置）
├── token.pickle                  # 認証トークン（自動生成）
├── requirements.txt              # Python依存パッケージ
├── .env                          # LINE認証情報（要設定）
├── .env.example                  # .envテンプレート
├── run_checker.sh                # cron実行用ラッパー
├── setup_cron.sh                 # cron自動設定スクリプト
├── SETUP.md                      # このファイル
└── .gitignore                    # Git除外設定
```

## LINE通知の例

```
[2026-03-15 09:00] 未返信見積もり案件
全3件
━━━━━━━━━━━━━━━

[1] 【見積依頼】〇〇システム開発の件
  From: tanaka@example.com
  Date: Mon, 10 Mar 2026 14:30:00 +0900

[2] Re: 御見積書の送付について
  From: suzuki@example.co.jp
  Date: Fri, 07 Mar 2026 10:15:00 +0900

[3] 見積もりのご確認
  From: yamada@example.net
  Date: Wed, 05 Mar 2026 16:45:00 +0900
```
