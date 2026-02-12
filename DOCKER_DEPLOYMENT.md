# Docker Deployment Guide

## Übersicht

Diese Anleitung beschreibt die Bereitstellung des Dienstplan-Systems mit Docker Compose, einschließlich der Integration eines TTS (Text-to-Speech) Service.

## Voraussetzungen

- Docker Engine (Version 20.10 oder höher)
- Docker Compose (Version 2.0 oder höher)

## Dienste

### 1. Dienstplan Application (dienstplan-app)

Die Hauptanwendung mit Flask Web API und Frontend.

- **Port**: 8080 (extern) → 5000 (intern)
- **Datenbank**: SQLite in `/app/data`

### 2. TTS Service (tts-service)

Text-to-Speech Service für Audio-Benachrichtigungen.

- **Image**: synesthesiam/coqui-tts:latest
- **Port**: 5000 (intern, nicht extern exponiert)
- **Kommunikation**: Über Docker-Netzwerk mit dienstplan-app

## Verwendung

### Starten der Dienste

```bash
# Alle Dienste starten
docker-compose up -d

# Logs anzeigen
docker-compose logs -f

# Status prüfen
docker-compose ps
```

### Stoppen der Dienste

```bash
# Alle Dienste stoppen
docker-compose down

# Dienste stoppen und Volumes löschen
docker-compose down -v
```

### Neustart nach Code-Änderungen

```bash
# Rebuild und Neustart
docker-compose up -d --build
```

## Umgebungsvariablen

Die folgenden Umgebungsvariablen können in der `docker-compose.yml` oder einer `.env` Datei konfiguriert werden:

### Dienstplan Application

- `TTS_SERVICE_URL`: URL des TTS-Dienstes (Standard: `http://tts-service:5000`)
- `APP_BASE_URL`: Basis-URL der Anwendung für E-Mail-Links (Standard: `http://localhost:8080`)
- `DB_PATH`: Pfad zur Datenbankdatei (Standard: `/app/data/dienstplan.db`)

### Beispiel .env Datei

```bash
# .env
APP_BASE_URL=http://your-domain.com:8080
TTS_SERVICE_URL=http://tts-service:5000
DB_PATH=/app/data/dienstplan.db
```

## Wichtige Hinweise

### Container-zu-Container-Kommunikation

Die Dienstplan-Anwendung kommuniziert mit dem TTS-Service über den **Container-Namen** (`tts-service`), nicht über `localhost` oder `127.0.0.1`. Dies ist wichtig für die korrekte Funktion in der Docker-Umgebung.

### Netzwerk-Isolation

Beide Dienste befinden sich im selben Docker-Netzwerk (`dienstplan-network`), sodass sie sich gegenseitig erreichen können. Der TTS-Service ist **nicht** direkt von außen erreichbar - nur die Dienstplan-Anwendung kann darauf zugreifen.

### Datenpersistenz

Die Datenbank wird in einem Volume (`./data`) auf dem Host gespeichert und überlebt Container-Neustarts.

## Troubleshooting

### TTS Service Connection Errors

Wenn Fehler wie `ECONNREFUSED` beim Verbinden zum TTS-Service auftreten:

1. Prüfen Sie, ob der TTS-Service läuft:
   ```bash
   docker-compose ps tts-service
   ```

2. Prüfen Sie die Logs des TTS-Service:
   ```bash
   docker-compose logs tts-service
   ```

3. Stellen Sie sicher, dass die Umgebungsvariable `TTS_SERVICE_URL` korrekt gesetzt ist:
   ```bash
   docker-compose config
   ```

4. Testen Sie die Verbindung innerhalb des Containers:
   ```bash
   docker-compose exec dienstplan-app curl http://tts-service:5000/api/health
   ```

### Ports bereits belegt

Falls Port 8080 bereits belegt ist, ändern Sie in der `docker-compose.yml`:

```yaml
ports:
  - "8081:5000"  # Verwenden Sie einen anderen externen Port
```

## Weitere Informationen

Für weitere Informationen zur Anwendung siehe:
- [README.md](README.md) - Hauptdokumentation
- [BENUTZERHANDBUCH.md](BENUTZERHANDBUCH.md) - Benutzerhandbuch
- [ARCHITECTURE.md](ARCHITECTURE.md) - Architektur-Dokumentation
