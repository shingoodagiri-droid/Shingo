#!/bin/bash
# cron実行用ラッパースクリプト
# 仮想環境を有効化してメインスクリプトを実行する

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# ログディレクトリ作成
mkdir -p logs

# 仮想環境の有効化
source "$SCRIPT_DIR/venv/bin/activate"

# メインスクリプトの実行
python3 "$SCRIPT_DIR/check_unreplied_estimates.py"
