#!/bin/sh
# Mice control hub launcher (Ubuntu/Linux/macOS): sh run_hub.sh
# A Windows .exe cannot run here - but the hub is plain Python (stdlib only),
# so this is all that is needed. Android/phones: open the hub's WiFi URL
# (printed below) in the browser - nothing to install.
cd "$(dirname "$0")"
python3 main.py
