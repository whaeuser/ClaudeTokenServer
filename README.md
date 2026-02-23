# ClaudeTokenServer

Lokaler HTTP-API-Server, der die Claude AI Nutzungsdaten (Token-Verbrauch) aus der macOS Keychain liest und als JSON-Endpunkt bereitstellt.

Inspiriert von [TokenEater](https://github.com/whaeuser/TokenEater).

## Voraussetzungen

- macOS 12+
- Python 3.9+
- [Claude Code](https://claude.ai/code) installiert und angemeldet

## Starten

```bash
./start_server.sh
```

Optionaler Port (Standard: 8765):

```bash
PORT=9000 ./start_server.sh
```

## Endpunkte

| Endpunkt | Beschreibung |
|----------|--------------|
| `GET /usage` | Nutzungsdaten (In-Memory-Cache, max. 5 Min.) |
| `GET /usage/fresh` | Nutzungsdaten, erzwingt neuen API-Call |
| `GET /health` | Server-Status |

## Beispiel-Antwort

```json
{
  "cached": false,
  "cache_age_seconds": 0,
  "fetched_at": "2026-02-23T16:00:00+00:00",
  "usage": {
    "five_hour": {
      "utilization": 49.0,
      "resets_at": "2026-02-23T19:00:00+00:00"
    },
    "seven_day": null,
    "seven_day_sonnet": null
  }
}
```

## Funktionsweise

1. **Keychain** – liest den OAuth-Token aus dem Keychain-Eintrag `Claude Code-credentials`
2. **API-Call** – `GET https://api.anthropic.com/api/oauth/usage` mit dem Token
3. **Cache** – Antworten werden 5 Minuten gecacht, um die API nicht zu überlasten
