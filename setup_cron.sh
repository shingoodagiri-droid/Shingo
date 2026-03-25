#!/bin/bash
# 毎朝9時にrun_checker.shを実行するcronジョブを登録する

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CRON_CMD="0 9 * * * $SCRIPT_DIR/run_checker.sh >> $SCRIPT_DIR/logs/cron.log 2>&1"

# 既存のrun_checker.shエントリを全て削除してから1つだけ登録（重複防止）
EXISTING=$(crontab -l 2>/dev/null | grep -c "run_checker.sh")
if [ "$EXISTING" -gt 1 ]; then
    echo "重複したcronジョブを検出しました（${EXISTING}件）。整理します..."
    crontab -l 2>/dev/null | grep -v "run_checker.sh" | crontab -
elif [ "$EXISTING" -eq 1 ]; then
    echo "既にcronジョブが登録されています。"
    echo "現在の設定:"
    crontab -l | grep "run_checker.sh"
    exit 0
fi

# 既存のcrontabに追加
(crontab -l 2>/dev/null; echo "$CRON_CMD") | crontab -

echo "cronジョブを登録しました:"
echo "  $CRON_CMD"
echo ""
echo "毎朝9:00にGmail未返信見積もりチェックが実行されます。"
