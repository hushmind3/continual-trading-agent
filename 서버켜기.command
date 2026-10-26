#!/bin/zsh
set -e
cd "${0:A:h}"
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
if [[ ! -x .venv/platform/bin/python ]]; then
  print '먼저 설치.command를 실행하세요.'
  exit 1
fi
.venv/platform/bin/python development/scripts/start_server.py --apply-only --skip-checks
open 'http://127.0.0.1:8766/#ai_agent/choki'
