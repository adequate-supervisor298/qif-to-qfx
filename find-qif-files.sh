#!/bin/bash
# Scan a directory for QIF and ZIP files, output JSON-like lines for easy parsing.
# Usage: find-qif-files.sh [directory]
# Default: ~/Downloads

dir="${1:-$HOME/Downloads}"

if [ ! -d "$dir" ]; then
    echo "NO_FILES"
    exit 0
fi

found=0
for f in "$dir"/*.QIF "$dir"/*.qif "$dir"/*.zip; do
    [ -f "$f" ] || continue
    size=$(stat -f "%z" "$f" 2>/dev/null || stat -c "%s" "$f" 2>/dev/null)
    mod=$(stat -f "%Sm" -t "%Y-%m-%d" "$f" 2>/dev/null || stat -c "%y" "$f" 2>/dev/null | cut -d' ' -f1)
    name=$(basename "$f")
    ext="${name##*.}"
    echo "$ext|$size|$mod|$f"
    found=1
done

if [ "$found" -eq 0 ]; then
    echo "NO_FILES"
fi
