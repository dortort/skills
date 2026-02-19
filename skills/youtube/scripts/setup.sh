#!/usr/bin/env bash
# YouTube Creator CLI — setup script
# Installs Python dependencies and prepares the credentials directory.
set -euo pipefail

CREDS_DIR="$HOME/.youtube-skill"
SECRETS_FILE="$CREDS_DIR/client_secrets.json"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== YouTube Creator CLI — Setup ==="
echo ""

# ── Python check ─────────────────────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
  echo "ERROR: python3 is required. Install it from https://python.org" >&2
  exit 1
fi

PYTHON_OK=$(python3 -c "import sys; print('ok' if sys.version_info >= (3, 8) else 'old')")
if [ "$PYTHON_OK" != "ok" ]; then
  echo "ERROR: Python 3.8 or higher is required. Found: $(python3 --version)" >&2
  exit 1
fi

echo "Python: $(python3 --version)"

# ── pip check ─────────────────────────────────────────────────────────────────
if ! python3 -m pip --version &>/dev/null; then
  echo "ERROR: pip is not available. Install pip for Python 3." >&2
  exit 1
fi

# ── Install dependencies ──────────────────────────────────────────────────────
echo "Installing Google API dependencies..."
python3 -m pip install --quiet --upgrade \
  "google-api-python-client>=2.100.0" \
  "google-auth-httplib2>=0.1.0" \
  "google-auth-oauthlib>=1.1.0"

echo "Dependencies installed."

# ── Create credentials directory ─────────────────────────────────────────────
mkdir -p "$CREDS_DIR"
echo "Credentials directory: $CREDS_DIR"
echo ""

# ── Check for client_secrets.json ────────────────────────────────────────────
if [ -f "$SECRETS_FILE" ]; then
  echo "client_secrets.json found. Running authentication..."
  echo ""
  python3 "$SCRIPT_DIR/yt.py" auth
else
  echo "Next: Download your OAuth 2.0 credentials from Google Cloud Console."
  echo ""
  echo "  1. Go to https://console.cloud.google.com"
  echo "  2. Create or select a project"
  echo "  3. Navigate to APIs & Services > Library"
  echo "  4. Search for 'YouTube Data API v3' and enable it"
  echo "  5. Navigate to APIs & Services > Credentials"
  echo "  6. Click 'Create Credentials' > 'OAuth 2.0 Client ID'"
  echo "  7. Select 'Desktop app', give it a name, click Create"
  echo "  8. Click 'Download JSON' and save the file as:"
  echo "       $SECRETS_FILE"
  echo ""
  echo "  Then run: python3 scripts/yt.py auth"
  echo ""
  echo "Note: On first run a browser window will open to authorise access."
  echo "      After that, credentials are cached and all operations are silent."
fi

echo ""
echo "Setup complete."
