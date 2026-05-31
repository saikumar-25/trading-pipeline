#!/bin/bash
# Stop and remove the always-on trading pipeline service.
# Run:  bash uninstall_service.sh
LABEL="com.vishnu.tradingpipeline"
PLIST_DST="$HOME/Library/LaunchAgents/$LABEL.plist"

launchctl unload "$PLIST_DST" 2>/dev/null || true
rm -f "$PLIST_DST"
echo "Stopped and removed $LABEL. The pipeline will no longer auto-start."
