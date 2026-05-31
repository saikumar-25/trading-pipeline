#!/bin/bash
# Wrapper that launchd runs. Keeps the pipeline loop alive.
cd "/Users/anvi/Documents/Claude/Projects/Trade app/trading_toolkit" || exit 1

# Make sure python + installed packages are found in launchd's minimal PATH.
export PATH="/Library/Frameworks/Python.framework/Versions/3.14/bin:/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:$PATH"

exec python3 live_pipeline.py loop
