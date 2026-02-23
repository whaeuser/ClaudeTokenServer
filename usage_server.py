#!/usr/bin/env python3
"""
TokenEater Usage API Server
Liest den Claude OAuth-Token aus der macOS Keychain und stellt die
Anthropic Usage-Daten als lokale HTTP-API bereit.

Endpunkte:
  GET /usage        – Rohe Nutzungsdaten von Anthropic (gecacht, max. 5 Min.)
  GET /usage/fresh  – Erzwingt einen neuen API-Call (ignoriert Cache)
  GET /health       – Server-Status

Starten: python3 usage_server.py [--port 8765]
"""

import json
import subprocess
import time
import urllib.request
import urllib.error
import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime, timezone

ANTHROPIC_URL = "https://api.anthropic.com/api/oauth/usage"
ANTHROPIC_BETA = "oauth-2025-04-20"
CACHE_TTL_SECONDS = 300  # 5 Minuten, wie in der App

# Einfacher In-Memory-Cache
_cache: dict = {"data": None, "fetched_at": 0.0}


def read_keychain_token() -> str:
    """Liest den Claude Code OAuth-Token aus der macOS Keychain."""
    try:
        raw = subprocess.check_output(
            ["security", "find-generic-password", "-s", "Claude Code-credentials", "-w"],
            stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            "Keychain-Eintrag 'Claude Code-credentials' nicht gefunden. "
            "Stelle sicher, dass Claude Code installiert und angemeldet ist."
        ) from e

    try:
        creds = json.loads(raw.strip())
        token = creds["claudeAiOauth"]["accessToken"]
    except (json.JSONDecodeError, KeyError) as e:
        raise RuntimeError(
            f"Unerwartetes Format des Keychain-Eintrags: {e}"
        ) from e

    if not token:
        raise RuntimeError("accessToken ist leer.")

    return token


def fetch_usage_from_anthropic(token: str) -> dict:
    """Ruft die Usage-Daten direkt von der Anthropic API ab."""
    req = urllib.request.Request(
        ANTHROPIC_URL,
        headers={
            "Authorization": f"Bearer {token}",
            "anthropic-beta": ANTHROPIC_BETA,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            raw = response.read()
            return json.loads(raw)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        if e.code in (401, 403):
            raise RuntimeError(
                f"Token abgelaufen oder ungültig (HTTP {e.code}). "
                "Bitte in Claude Code neu anmelden."
            ) from e
        raise RuntimeError(f"Anthropic API Fehler HTTP {e.code}: {body}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Netzwerkfehler: {e.reason}") from e


def get_usage(force_refresh: bool = False) -> dict:
    """Gibt die Usage-Daten zurück, ggf. aus dem Cache."""
    now = time.monotonic()
    if not force_refresh and _cache["data"] and (now - _cache["fetched_at"]) < CACHE_TTL_SECONDS:
        return {
            "cached": True,
            "cache_age_seconds": round(now - _cache["fetched_at"]),
            "fetched_at": _cache["fetched_at_iso"],
            "usage": _cache["data"],
        }

    token = read_keychain_token()
    data = fetch_usage_from_anthropic(token)

    _cache["data"] = data
    _cache["fetched_at"] = now
    _cache["fetched_at_iso"] = datetime.now(timezone.utc).isoformat()

    return {
        "cached": False,
        "cache_age_seconds": 0,
        "fetched_at": _cache["fetched_at_iso"],
        "usage": data,
    }


class UsageHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] {format % args}")

    def send_json(self, status: int, payload: dict):
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.rstrip("/")

        if path == "/health":
            self.send_json(200, {"status": "ok", "server": "ClaudeTokenServer"})
            return

        if path in ("/usage", "/usage/fresh"):
            force = path == "/usage/fresh"
            try:
                result = get_usage(force_refresh=force)
                self.send_json(200, result)
            except RuntimeError as e:
                self.send_json(500, {"error": str(e)})
            return

        self.send_json(404, {
            "error": "Not found",
            "available_endpoints": ["/usage", "/usage/fresh", "/health"],
        })


def main():
    parser = argparse.ArgumentParser(description="ClaudeTokenServer – lokaler Usage-API-Server")
    parser.add_argument("--port", type=int, default=8765, help="Port (Standard: 8765)")
    parser.add_argument("--host", default="0.0.0.0", help="Host (Standard: 0.0.0.0 – im lokalen Netz erreichbar)")
    args = parser.parse_args()

    server = HTTPServer((args.host, args.port), UsageHandler)
    import socket
    local_ip = socket.gethostbyname(socket.gethostname())
    print(f"ClaudeTokenServer gestartet auf http://{args.host}:{args.port}")
    if args.host == "0.0.0.0":
        print(f"  Im lokalen Netz erreichbar unter: http://{local_ip}:{args.port}")
    print(f"  GET /usage        – Nutzungsdaten (Cache: {CACHE_TTL_SECONDS}s)")
    print(f"  GET /usage/fresh  – Nutzungsdaten (kein Cache)")
    print(f"  GET /health       – Server-Status")
    print("Beenden mit Ctrl+C\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer gestoppt.")


if __name__ == "__main__":
    main()
