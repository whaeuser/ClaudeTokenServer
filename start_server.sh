#!/usr/bin/env bash
# ClaudeTokenServer – Start-Script
# Erstellt bei Bedarf ein Virtual Environment und startet den lokalen API-Server.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
SERVER="$SCRIPT_DIR/usage_server.py"
PORT="${PORT:-8765}"

# --- Virtual Environment anlegen (einmalig) ---
if [[ ! -d "$VENV_DIR" ]]; then
    echo "Virtual Environment wird erstellt..."
    python3 -m venv "$VENV_DIR"
    echo "Virtual Environment erstellt: $VENV_DIR"
fi

# --- Aktivieren ---
source "$VENV_DIR/bin/activate"

# --- Dependencies installieren / aktuell halten ---
pip install --quiet --upgrade pip
if [[ -f "$SCRIPT_DIR/requirements.txt" ]]; then
    pip install --quiet -r "$SCRIPT_DIR/requirements.txt"
fi

# --- Server starten ---
echo "Starte ClaudeTokenServer auf Port $PORT..."
exec python3 "$SERVER" --port "$PORT"
