#!/bin/bash
# cron実行用ラッパースクリプト
# 仮想環境を有効化してメインスクリプトを実行する

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# ログディレクトリ作成
mkdir -p logs

# ロックファイルで二重実行を防止
LOCKFILE="$SCRIPT_DIR/logs/.checker.lock"
if [ -f "$LOCKFILE" ]; then
    # 1時間以上前のロックファイルは古いとみなして削除
    find "$LOCKFILE" -mmin +60 -delete 2>/dev/null
    if [ -f "$LOCKFILE" ]; then
        echo "[$(date)] 既に実行中のため、スキップします。" >> "$SCRIPT_DIR/logs/cron.log"
        exit 0
    fi
fi
touch "$LOCKFILE"
trap "rm -f '$LOCKFILE'" EXIT

# 仮想環境の有効化
source "$SCRIPT_DIR/venv/bin/activate"

# メインスクリプトの実行
python3 "$SCRIPT_DIR/check_unreplied_estimates.py"
