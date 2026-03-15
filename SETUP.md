# Gmail 未返信メール通知 - セットアップ手順

毎朝9時に未返信・未読メールを検索し、自分のGmailに通知メールを送るツールです。

---

## 1. Google Cloud の設定（済み）

以下は完了済み：
- Google Cloud プロジェクト作成
- Gmail API 有効化
- OAuth 同意画面の設定
- credentials.json の取得・配置

## 2. Python 環境のセットアップ

```bash
cd /home/user/Shingo
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 3. 初回実行（Gmail 認証）

```bash
python3 check_unreplied_estimates.py
```

初回実行時にブラウザが開き、Google アカウントの認証を求められます。
「メールの読み取り」と「メールの送信」の権限を許可してください。
許可すると `token.pickle` が生成され、以降は自動で認証されます。

> **注意**: スコープを変更した場合は `token.pickle` を削除して再認証してください。

## 4. cron の設定（毎朝9時に自動実行）

```bash
bash setup_cron.sh
```

## 通知メールの例

件名: 【未返信メール通知】2026/03/15 5件

```
未返信・未読メール一覧（2026-03-15 09:00）
全5件
========================================

[1] 〇〇の件について
  送信元: tanaka@example.com
  受信日: Mon, 10 Mar 2026 14:30:00 +0900

[2] お見積りの件
  送信元: suzuki@example.co.jp
  受信日: Fri, 07 Mar 2026 10:15:00 +0900
```
