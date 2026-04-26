# API Security Matrix (Phase 1)

Stand: Phase-1 Security-Baseline Umsetzung.

## Default-Regel

- Alle `/api/*`-Routen sind standardmaessig authentifizierungspflichtig.
- Explizit oeffentliche Endpunkte werden in `web_api.py` in `public_api_paths` freigeschaltet.

## Explizit oeffentliche Endpunkte

- `GET /api/health`
- `GET /api/csrf-token`
- `POST /api/auth/login`
- `POST /api/auth/forgot-password`
- `POST /api/auth/reset-password`
- `POST /api/auth/validate-reset-token`
- `GET /api/settings/branding`

## Authentifiziert (Default) + rollenbasiert

- `Admin`: Benutzer-/Rollenverwaltung, Audit-Logs, E-Mail-Settings, mutierende Einstellungen.
- `Admin|Disponent`: Planungsjob-Start/Status/Cancel.
- `Authenticated`: sonstige API-Endpunkte, sofern nicht explizit als Public definiert.

## Sicherheitsrelevante Ergaenzungen in Phase 1

- SQLite Foreign Keys werden auf jeder API-Connection per `PRAGMA foreign_keys = ON` aktiviert.
- Passwort-Reset-Tokens werden nur noch gehasht in `PasswordResetTokens.Token` abgelegt.
- SMTP-Passwort kann via `DIENSTPLAN_SMTP_PASSWORD` aus der Umgebung bezogen werden (bevorzugt vor DB-Wert).
