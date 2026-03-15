#!/bin/bash
# 毎朝9時にrun_checker.shを実行するcronジョブを登録する

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CRON_CMD="0 9 * * * $SCRIPT_DIR/run_checker.sh >> $SCRIPT_DIR/logs/cron.log 2>&1"

# 既存のcronジョブに同じエントリがないか確認
if crontab -l 2>/dev/null | grep -F "run_checker.sh" > /dev/null; then
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
