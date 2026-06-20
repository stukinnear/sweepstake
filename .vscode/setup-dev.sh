#!/bin/bash
WORKSPACE="$1"

# ── Backend venv ──────────────────────────────────────────────────────────────
echo ">>> Backend venv"
rm -rf "$WORKSPACE/backend/.venv" "$WORKSPACE/backend/.venv.nosync"
python3 -m venv "$WORKSPACE/backend/.venv.nosync"
ln -s "$WORKSPACE/backend/.venv.nosync" "$WORKSPACE/backend/.venv"
"$WORKSPACE/backend/.venv.nosync/bin/pip" install --upgrade pip -q
"$WORKSPACE/backend/.venv.nosync/bin/pip" install -r "$WORKSPACE/backend/src/requirements.txt" -r "$WORKSPACE/backend/src/requirements-test.txt"
echo ">>> Backend venv done"

# ── Frontend node_modules ─────────────────────────────────────────────────────
echo ">>> Frontend node_modules"
cd "$WORKSPACE/frontend"
rm -rf node_modules node_modules.nosync
npm install
mv node_modules node_modules.nosync
ln -s node_modules.nosync node_modules
echo ">>> Frontend node_modules done"

echo ">>> Setup complete"
