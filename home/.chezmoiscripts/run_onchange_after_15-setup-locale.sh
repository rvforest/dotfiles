#!/usr/bin/env bash
set -euo pipefail

available_locales="$(locale -a 2>/dev/null || true)"

if grep -Eiq '^en_US\.(utf8|utf-8)$' <<<"$available_locales"; then
  echo "en_US.UTF-8 locale already available."
  exit 0
fi

if ! command -v locale-gen >/dev/null 2>&1 || ! command -v update-locale >/dev/null 2>&1; then
  echo "Locale tools unavailable, skipping en_US.UTF-8 generation."
  exit 0
fi

echo "en_US.UTF-8 locale missing, generating..."
sudo locale-gen en_US.UTF-8
sudo update-locale LANG=en_US.UTF-8
