#!/bin/sh
# Installs ROLI for Live into the Ableton User Library (macOS).
# Usage: sh install.sh ["/path/to/User Library"]
#    or: curl -fsSL https://raw.githubusercontent.com/ehsuun/ROLI-for-Live/main/install.sh | sh
# (In a release download you can also double-click "Install on Mac.command".)
set -e
REPO=ehsuun/ROLI-for-Live
here=$(cd "$(dirname "$0")" && pwd)

# Works from a git checkout (src/ROLI_for_Live) and from a release zip (ROLI_for_Live).
# Run on its own (e.g. piped from curl), it downloads the latest release's source first.
if [ -f "$here/ROLI_for_Live/__init__.py" ]; then
  src="$here/ROLI_for_Live"
elif [ -f "$here/src/ROLI_for_Live/__init__.py" ]; then
  src="$here/src/ROLI_for_Live"
else
  tag=$(curl -fsSI "https://github.com/$REPO/releases/latest" | tr -d '\r' |
    sed -n 's#^[Ll]ocation: .*/releases/tag/##p')
  [ -n "$tag" ] || { echo "Couldn't find the latest ROLI for Live release." >&2; exit 1; }
  tmp=$(mktemp -d)
  trap 'rm -rf "$tmp"' EXIT
  echo "Downloading ROLI for Live $tag..."
  curl -fsSL "https://github.com/$REPO/archive/refs/tags/$tag.tar.gz" | tar -xz -C "$tmp"
  src=$(echo "$tmp"/*/src/ROLI_for_Live)
  [ -f "$src/__init__.py" ] || { echo "The download didn't contain ROLI_for_Live." >&2; exit 1; }
fi

if pgrep -f "Ableton Live" >/dev/null 2>&1; then
  printf 'Ableton Live is running. Please quit Live first, then press Return to continue. '
  read -r _ < /dev/tty
fi

lib="$1"
if [ -z "$lib" ]; then
  cfg=$(ls -t "$HOME"/Library/Preferences/Ableton/Live\ */Library.cfg 2>/dev/null | head -n 1)
  if [ -n "$cfg" ]; then
    path=$(tr -d '\000' < "$cfg" | awk '/<UserLibrary>/{f=1} f && /ProjectPath Value=/{sub(/.*ProjectPath Value="/,""); sub(/".*/,""); print; exit}')
    [ -n "$path" ] && lib="$path/User Library"
  fi
fi
[ -z "$lib" ] && lib="$HOME/Music/Ableton/User Library"

dest="$lib/Remote Scripts/ROLI_for_Live"
mkdir -p "$dest"
cp "$src"/*.py "$dest"/

echo
echo "ROLI for Live installed to: $dest"
echo
echo "Next, once only:"
echo "  1. Connect your ROLI keyboard and start Ableton Live."
echo "  2. Settings > Tempo & MIDI: in an empty Control Surface row choose \"ROLI for Live\","
echo "     with Input and Output \"ROLI Piano\"."
echo "  3. Under Input Ports, turn on Track and MPE for \"ROLI Piano\"."
