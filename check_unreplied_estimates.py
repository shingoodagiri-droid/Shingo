#!/usr/bin/env python3
"""
未返信・未読メールをGmailから検索し、結果を自分宛にメール通知するスクリプト。
毎朝9時にcronで実行することを想定。
"""

import sys
import pickle
import base64
from datetime import datetime
from email.mime.text import MIMEText
from pathlib import Path

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Gmail API のスコープ（読み取り＋送信＋ラベル変更）
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
]

# ファイルパス
SCRIPT_DIR = Path(__file__).resolve().parent
CREDENTIALS_FILE = SCRIPT_DIR / "credentials.json"
TOKEN_FILE = SCRIPT_DIR / "token.pickle"


def authenticate():
    """Gmail API の認証を行い、サービスオブジェクトを返す。"""
    creds = None

    if TOKEN_FILE.exists():
        with open(TOKEN_FILE, "rb") as f:
            creds = pickle.load(f)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDENTIALS_FILE.exists():
                print(f"エラー: {CREDENTIALS_FILE} が見つかりません。")
                print("SETUP.md を参照して Gmail API の認証情報を設定してください。")
                sys.exit(1)
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_FILE), SCOPES
            )
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "wb") as f:
            pickle.dump(creds, f)

    return build("gmail", "v1", credentials=creds)


def get_unreplied_emails(service, my_email):
    """未返信・未読メールを検索して返す。"""
    # is:unread → 未読メール
    # -in:sent -in:draft -in:trash -in:spam → 不要なフォルダを除外
    query = "is:unread -in:sent -in:draft -in:trash -in:spam -from:@wagokoro.co.jp"

    results = []
    page_token = None

    while True:
        response = (
            service.users()
            .messages()
            .list(userId="me", q=query, pageToken=page_token, maxResults=100)
            .execute()
        )

        messages = response.get("messages", [])
        if not messages:
            break

        for msg in messages:
            detail = (
                service.users()
                .messages()
                .get(userId="me", id=msg["id"], format="metadata",
                     metadataHeaders=["Subject", "From", "Date"])
                .execute()
            )

            headers = {
                h["name"]: h["value"]
                for h in detail.get("payload", {}).get("headers", [])
            }

            # 自分が返信済みかチェック
            thread_id = detail.get("threadId")
            if is_replied(service, thread_id, my_email):
                continue

            results.append({
                "id": msg["id"],
                "subject": headers.get("Subject", "(件名なし)"),
                "from": headers.get("From", "(送信元不明)"),
                "date": headers.get("Date", "(日付不明)"),
            })

        page_token = response.get("nextPageToken")
        if not page_token:
            break

    return results


def is_replied(service, thread_id, my_email):
    """スレッド内に自分の送信メールがあるかチェックする。"""
    thread = (
        service.users()
        .threads()
        .get(userId="me", id=thread_id, format="metadata",
             metadataHeaders=["From"])
        .execute()
    )

    for message in thread.get("messages", []):
        headers = {
            h["name"]: h["value"]
            for h in message.get("payload", {}).get("headers", [])
        }
        from_addr = headers.get("From", "").lower()
        if my_email in from_addr:
            return True

    return False


def format_message(emails):
    """検索結果をメール本文用にフォーマットする。"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    if not emails:
        return f"[{now}]\n未返信・未読メールはありません。"

    lines = [
        f"未返信・未読メール一覧（{now}）",
        f"全{len(emails)}件",
        "=" * 40,
    ]

    for i, email in enumerate(emails, 1):
        lines.append(f"\n[{i}] {email['subject']}")
        lines.append(f"  送信元: {email['from']}")
        lines.append(f"  受信日: {email['date']}")

    return "\n".join(lines)


def send_email(service, to_email, subject, body):
    """自分宛にメールを送信する（insertで直接受信トレイに配置し重複を防ぐ）。"""
    msg = MIMEText(body, "plain", "utf-8")
    msg["To"] = to_email
    msg["From"] = to_email
    msg["Subject"] = subject

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
    service.users().messages().insert(
        userId="me",
        body={"raw": raw, "labelIds": ["INBOX"]},
    ).execute()

    print("メール送信完了")


def main():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 未返信・未読メールの検索を開始...")

    service = authenticate()

    # 自分のメールアドレスを取得
    profile = service.users().getProfile(userId="me").execute()
    my_email = profile.get("emailAddress", "").lower()

    emails = get_unreplied_emails(service, my_email)
    body = format_message(emails)
    print(body)

    # 自分宛にメール送信
    today = datetime.now().strftime("%Y/%m/%d")
    send_email(service, my_email, f"【未返信メール通知】{today} {len(emails)}件", body)

    print(f"完了: {len(emails)}件の未返信メールを通知しました。")


if __name__ == "__main__":
    main()
