#!/bin/bash
# Noto Sans Devanagari 800 (SIL Open Font License) from Google Fonts -> $KIT_PROJECT/assets/fonts/NotoSansDevanagari-800.woff2
D="${KIT_PROJECT:-./project}/assets/fonts"; mkdir -p "$D"
CSS=$(curl -s -m 30 -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36" "https://fonts.googleapis.com/css2?family=Noto+Sans+Devanagari:wght@800&display=swap")
URL=$(printf '%s' "$CSS" | awk '/\/\* devanagari \*\//{f=1} f && /src: url\(/{print; exit}' | sed -E 's/.*url\(([^)]*)\).*/\1/')
[ -n "$URL" ] && curl -s -m 60 -o "$D/NotoSansDevanagari-800.woff2" "$URL" && ls -la "$D/NotoSansDevanagari-800.woff2" || echo "font download failed - download it manually"
