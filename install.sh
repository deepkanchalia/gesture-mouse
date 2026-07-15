#!/bin/bash
# Gesture Mouse installer — macOS only.
# Finds Python 3.11/3.12, creates the venv, installs deps.
set -euo pipefail

if [ "$(uname)" != "Darwin" ]; then
    echo "ERROR: Gesture Mouse is macOS-only (it moves the Mac cursor via Quartz)."
    exit 1
fi

# If run via curl, clone the repo first.
if [ ! -f "main.py" ]; then
    if [ -d "$HOME/gesture-mouse" ]; then
        echo "Found existing ~/gesture-mouse — updating it."
        cd "$HOME/gesture-mouse"
        git pull --ff-only || true
    else
        echo "Cloning into ~/gesture-mouse ..."
        git clone https://github.com/deepkanchalia/gesture-mouse.git "$HOME/gesture-mouse"
        cd "$HOME/gesture-mouse"
    fi
fi

# MediaPipe needs Python 3.11 or 3.12.
PY=""
for candidate in python3.12 python3.11; do
    if command -v "$candidate" >/dev/null 2>&1; then
        PY="$candidate"
        break
    fi
done

if [ -z "$PY" ]; then
    echo ""
    echo "ERROR: Python 3.11 or 3.12 not found (MediaPipe needs one of these)."
    echo "Install with Homebrew:"
    echo "    brew install python@3.11"
    echo "then re-run this script."
    exit 1
fi

echo "Using $PY ($($PY --version))"
"$PY" -m venv venv
./venv/bin/pip install --upgrade pip --quiet
./venv/bin/pip install -r requirements.txt

echo ""
echo "✅ Installed."
echo ""
echo "BEFORE FIRST RUN — grant two Mac permissions:"
echo "  1. System Settings > Privacy & Security > Camera        -> enable your Terminal"
echo "  2. System Settings > Privacy & Security > Accessibility -> add + enable your Terminal"
echo "     (without #2 the cursor will not move)"
echo ""
echo "Run it:"
echo "  cd $(pwd) && ./venv/bin/python main.py"
