#!/usr/bin/env python3
"""
Google Calendarから指定日の予定を取得し、
各予定の準備事項をまとめてGmailで通知するスクリプト。
"""

import sys
import pickle
import base64
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from pathlib import Path

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Gmail（送信用）＋ Calendar（読み取り用）のスコープ
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar.readonly",
]

SCRIPT_DIR = Path(__file__).resolve().parent
CREDENTIALS_FILE = SCRIPT_DIR / "credentials.json"
TOKEN_FILE = SCRIPT_DIR / "token_calendar.pickle"


def authenticate():
    """Gmail + Calendar API の認証を行い、両サービスオブジェクトを返す。"""
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
                print("SETUP.md を参照して認証情報を設定してください。")
                sys.exit(1)
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_FILE), SCOPES
            )
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "wb") as f:
            pickle.dump(creds, f)

    gmail_service = build("gmail", "v1", credentials=creds)
    calendar_service = build("calendar", "v3", credentials=creds)
    return gmail_service, calendar_service


def get_events_for_date(calendar_service, target_date):
    """指定日のカレンダーイベントを取得する。"""
    # 日本時間（JST = UTC+9）で指定日の開始・終了を設定
    time_min = f"{target_date.isoformat()}T00:00:00+09:00"
    time_max = f"{target_date.isoformat()}T23:59:59+09:00"

    events_result = (
        calendar_service.events()
        .list(
            calendarId="primary",
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )

    return events_result.get("items", [])


def generate_prep_items(event):
    """イベントの種類に応じた準備事項を生成する。"""
    summary = event.get("summary", "").lower()
    description = event.get("description", "").lower()
    location = event.get("location", "")
    attendees = event.get("attendees", [])
    combined = summary + " " + description

    prep_items = []

    # 会議・ミーティング系
    if any(kw in combined for kw in ["会議", "ミーティング", "mtg", "meeting", "打ち合わせ", "打合せ"]):
        prep_items.append("議題・アジェンダを確認する")
        prep_items.append("前回の議事録を確認する")
        if attendees:
            prep_items.append(f"参加者（{len(attendees)}名）への事前連絡を確認する")

    # プレゼン・発表系
    if any(kw in combined for kw in ["プレゼン", "発表", "presentation", "報告会", "共有会"]):
        prep_items.append("発表資料を最終確認する")
        prep_items.append("スライドの動作チェックをする")
        prep_items.append("想定質問への回答を準備する")

    # 面接・面談系
    if any(kw in combined for kw in ["面接", "面談", "1on1", "1:1", "interview"]):
        prep_items.append("話す内容・トピックを整理する")
        prep_items.append("相手の最近の状況を確認する")

    # レビュー系
    if any(kw in combined for kw in ["レビュー", "review", "コードレビュー"]):
        prep_items.append("レビュー対象を事前に確認する")
        prep_items.append("チェックポイントを整理する")

    # 顧客・クライアント系
    if any(kw in combined for kw in ["顧客", "クライアント", "client", "お客様", "商談", "営業"]):
        prep_items.append("顧客情報・過去のやり取りを確認する")
        prep_items.append("提案資料や見積書を準備する")
        prep_items.append("名刺を準備する")

    # ランチ・食事系
    if any(kw in combined for kw in ["ランチ", "lunch", "食事", "dinner", "懇親会", "飲み会"]):
        prep_items.append("場所・アクセスを確認する")
        prep_items.append("予約の確認をする")

    # 締め切り・期限系
    if any(kw in combined for kw in ["締め切り", "期限", "deadline", "提出", "納品"]):
        prep_items.append("成果物の最終チェックをする")
        prep_items.append("提出先・提出方法を確認する")

    # 研修・セミナー系
    if any(kw in combined for kw in ["研修", "セミナー", "勉強会", "workshop", "seminar", "トレーニング"]):
        prep_items.append("事前資料を読んでおく")
        prep_items.append("質問事項をまとめる")

    # 場所がある場合
    if location:
        prep_items.append(f"場所を確認する: {location}")
        prep_items.append("移動時間・交通手段を確認する")

    # オンライン会議系
    if any(kw in combined for kw in ["zoom", "teams", "meet", "オンライン", "web会議", "リモート"]):
        prep_items.append("会議URLを確認する")
        prep_items.append("マイク・カメラの動作を確認する")

    # 汎用（何もマッチしなかった場合）
    if not prep_items:
        prep_items.append("関連資料を事前に確認する")
        prep_items.append("必要な持ち物を確認する")

    return prep_items


def format_schedule_summary(events, target_date):
    """予定と準備事項をフォーマットする。"""
    date_str = target_date.strftime("%Y年%m月%d日")
    weekdays = ["月", "火", "水", "木", "金", "土", "日"]
    weekday = weekdays[target_date.weekday()]

    if not events:
        return f"{date_str}（{weekday}）の予定はありません。"

    lines = [
        f"📅 {date_str}（{weekday}）のスケジュール＆準備事項",
        f"全{len(events)}件",
        "=" * 50,
    ]

    for i, event in enumerate(events, 1):
        summary = event.get("summary", "(タイトルなし)")

        # 時刻の取得（終日イベント or 時刻指定）
        start = event.get("start", {})
        end = event.get("end", {})
        if "dateTime" in start:
            start_time = datetime.fromisoformat(start["dateTime"]).strftime("%H:%M")
            end_time = datetime.fromisoformat(end["dateTime"]).strftime("%H:%M")
            time_str = f"{start_time} - {end_time}"
        else:
            time_str = "終日"

        location = event.get("location", "")
        attendees = event.get("attendees", [])

        lines.append(f"\n━━━ [{i}] {summary} ━━━")
        lines.append(f"  ⏰ 時間: {time_str}")
        if location:
            lines.append(f"  📍 場所: {location}")
        if attendees:
            attendee_names = [
                a.get("displayName", a.get("email", ""))
                for a in attendees
                if not a.get("self", False)
            ]
            if attendee_names:
                lines.append(f"  👥 参加者: {', '.join(attendee_names)}")

        # 準備事項
        prep_items = generate_prep_items(event)
        lines.append("  📝 準備事項:")
        for item in prep_items:
            lines.append(f"    • {item}")

    lines.append("\n" + "=" * 50)
    lines.append("※ 準備事項はイベント内容から自動生成しています。")

    return "\n".join(lines)


def send_email(service, to_email, subject, body):
    """自分宛にメールを送信する。"""
    msg = MIMEText(body, "plain", "utf-8")
    msg["To"] = to_email
    msg["From"] = to_email
    msg["Subject"] = subject

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
    service.users().messages().send(
        userId="me", body={"raw": raw}
    ).execute()
    print("通知メール送信完了")


def parse_target_date(arg=None):
    """対象日を決定する。引数なしの場合は翌営業日。"""
    if arg:
        return datetime.strptime(arg, "%Y-%m-%d").date()

    today = datetime.now().date()
    # デフォルト: 翌日（金曜なら月曜）
    if today.weekday() == 4:  # 金曜
        return today + timedelta(days=3)
    elif today.weekday() == 5:  # 土曜
        return today + timedelta(days=2)
    else:
        return today + timedelta(days=1)


def main():
    # コマンドライン引数で日付指定（例: 2026-03-16）
    target_date = parse_target_date(sys.argv[1] if len(sys.argv) > 1 else None)

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
          f"{target_date} の予定を取得中...")

    gmail_service, calendar_service = authenticate()

    # カレンダーイベント取得
    events = get_events_for_date(calendar_service, target_date)
    summary = format_schedule_summary(events, target_date)
    print(summary)

    # 自分宛にメール送信
    profile = gmail_service.users().getProfile(userId="me").execute()
    my_email = profile.get("emailAddress", "").lower()

    date_str = target_date.strftime("%Y/%m/%d")
    send_email(
        gmail_service,
        my_email,
        f"【予定準備まとめ】{date_str} {len(events)}件",
        summary,
    )

    print(f"完了: {len(events)}件の予定を通知しました。")


if __name__ == "__main__":
    main()
