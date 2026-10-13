#!/bin/sh
# Double-click to install ROLI for Live into your Ableton User Library.
# First time: macOS may say it's from an unidentified developer. Right-click the file > Open
# (macOS 15+: System Settings > Privacy & Security > Open Anyway).
cd "$(dirname "$0")" || exit 1
sh ./install.sh
status=$?
echo
[ $status -ne 0 ] && echo "Installation failed. See the message above."
printf 'Press Return to close this window. '
read -r _
