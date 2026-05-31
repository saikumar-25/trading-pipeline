#!/bin/bash
# One-shot installer for the always-on trading pipeline (macOS launchd).
# Run:  bash install_service.sh
set -e

DIR="/Users/anvi/Documents/Claude/Projects/Trade app/trading_toolkit"
LABEL="com.vishnu.tradingpipeline"
PLIST_SRC="$DIR/$LABEL.plist"
PLIST_DST="$HOME/Library/LaunchAgents/$LABEL.plist"

cd "$DIR"

echo "1/4  Installing Python dependencies for python3..."
python3 -m pip install --quiet --upgrade dhanhq pyotp pandas truststore certifi tabulate 2>/dev/null \
  || python3 -m pip install --quiet --break-system-packages dhanhq pyotp pandas truststore certifi tabulate

echo "2/4  Making the loop wrapper executable..."
chmod +x "$DIR/run_loop.sh"

echo "3/4  Installing the LaunchAgent..."
mkdir -p "$HOME/Library/LaunchAgents"
cp "$PLIST_SRC" "$PLIST_DST"

echo "4/4  Loading the service..."
launchctl unload "$PLIST_DST" 2>/dev/null || true
launchctl load "$PLIST_DST"

echo ""
echo "Done. The pipeline is now running and will auto-start on every login/reboot."
echo "  Watch it:   tail -f \"$DIR/pipeline.out.log\""
echo "  Errors:     tail -f \"$DIR/pipeline.err.log\""
echo "  Stop it:    bash \"$DIR/uninstall_service.sh\""
echo ""
echo "Note: it only acts during market hours (9:15-15:30 IST, Mon-Fri); outside"
echo "those hours it idles quietly. PAPER_MODE is ON until you change config.py."
