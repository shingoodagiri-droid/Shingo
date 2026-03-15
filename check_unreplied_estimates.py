#!/usr/bin/env python3
"""
未返信の見積もり案件をGmailから検索し、LINEに通知するスクリプト。
毎朝9時にcronで実行することを想定。
"""

import os
import sys
import pickle
import urllib.request
import urllib.parse
import json
from datetime import datetime
from pathlib import Path

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from dotenv import load_dotenv

# .env ファイルの読み込み
SCRIPT_DIR = Path(__file__).resolve().parent
load_dotenv(SCRIPT_DIR / ".env")

# Gmail API のスコープ（読み取り専用）
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

# ファイルパス
CREDENTIALS_FILE = SCRIPT_DIR / "credentials.json"
TOKEN_FILE = SCRIPT_DIR / "token.pickle"

# LINE Messaging API 設定
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
LINE_USER_ID = os.getenv("LINE_USER_ID", "")


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


def get_unreplied_estimates(service):
    """件名に「見積」を含む未返信メールを検索して返す。"""
    query = "subject:見積 -in:sent -in:draft -in:trash -in:spam"

    results = []
    page_token = None

    # 自分のメールアドレスを事前に取得（API呼び出し回数削減）
    profile = service.users().getProfile(userId="me").execute()
    my_email = profile.get("emailAddress", "").lower()

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


def send_line_message(text):
    """LINE Messaging API でプッシュメッセージを送信する。"""
    if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_USER_ID:
        print("エラー: LINE_CHANNEL_ACCESS_TOKEN または LINE_USER_ID が設定されていません。")
        print("SETUP.md を参照して .env ファイルを設定してください。")
        sys.exit(1)

    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
    }
    body = json.dumps({
        "to": LINE_USER_ID,
        "messages": [{"type": "text", "text": text}],
    }).encode("utf-8")

    req = urllib.request.Request(url, data=body, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req) as res:
            print(f"LINE送信成功 (status: {res.status})")
    except urllib.error.HTTPError as e:
        print(f"LINE送信エラー: {e.code} {e.read().decode()}")
        sys.exit(1)


def format_message(emails):
    """検索結果をLINEメッセージ用にフォーマットする。"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    if not emails:
        return f"[{now}]\n未返信の見積もり案件はありません。"

    lines = [
        f"[{now}] 未返信見積もり案件",
        f"全{len(emails)}件",
        "━━━━━━━━━━━━━━━",
    ]

    for i, email in enumerate(emails, 1):
        lines.append(f"\n[{i}] {email['subject']}")
        lines.append(f"  From: {email['from']}")
        lines.append(f"  Date: {email['date']}")

    return "\n".join(lines)


def main():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 未返信見積もり案件の検索を開始...")

    service = authenticate()
    emails = get_unreplied_estimates(service)

    message = format_message(emails)
    print(message)

    send_line_message(message)
    print(f"完了: {len(emails)}件をLINEに送信しました。")


if __name__ == "__main__":
    main()
