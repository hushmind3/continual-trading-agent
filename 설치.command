#!/bin/zsh
set -e
cd "${0:A:h}"
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
if ! command -v python3.14 >/dev/null || ! command -v uv >/dev/null || ! command -v npm >/dev/null; then
  print 'Python 3.14, uv, Node.js가 필요합니다. Homebrew에서 설치한 뒤 다시 실행하세요.'
  exit 1
fi
if ! command -v llama-server >/dev/null; then
  brew install llama.cpp
fi
python3.14 development/scripts/install_windows.py
