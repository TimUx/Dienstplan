# TTS Service Usage Example

## Verwendung des TTS-Service im Code

### Beispiel 1: Text-to-Speech Generierung

```python
from tts_service import synthesize_speech

# Einfache Verwendung
success, audio_data, error_msg = synthesize_speech("Guten Tag, dies ist eine Test-Nachricht.")

if success:
    # Audio-Daten in eine Datei schreiben
    with open("output.wav", "wb") as f:
        f.write(audio_data)
    print("Audio erfolgreich generiert")
else:
    print(f"Fehler: {error_msg}")
```

### Beispiel 2: Health Check

```python
from tts_service import check_tts_service_health, get_tts_service_info

# Prüfen ob der Service verfügbar ist
if check_tts_service_health():
    print("TTS Service ist verfügbar")
else:
    print("TTS Service ist nicht verfügbar")

# Detaillierte Informationen abrufen
info = get_tts_service_info()
print(f"Service URL: {info['service_url']}")
print(f"Status: {'Healthy' if info['is_healthy'] else 'Unhealthy'}")
```

### Beispiel 3: Integration in Benachrichtigungen

```python
from tts_service import synthesize_speech
import logging

logger = logging.getLogger(__name__)

def send_audio_notification(message_text: str, recipient_id: str):
    """
    Sendet eine Audio-Benachrichtigung an einen Empfänger.
    """
    # TTS generieren
    success, audio_data, error_msg = synthesize_speech(message_text, language='de')
    
    if success:
        # Audio-Datei speichern oder an Client senden
        audio_filename = f"notification_{recipient_id}.wav"
        with open(audio_filename, "wb") as f:
            f.write(audio_data)
        
        logger.info(f"Audio-Benachrichtigung für {recipient_id} erstellt: {audio_filename}")
        return True
    else:
        logger.error(f"Fehler bei Audio-Generierung: {error_msg}")
        return False

# Verwendung
send_audio_notification(
    "Achtung: Die Schicht am Montag ist unterbesetzt.",
    recipient_id="admin_001"
)
```

## Fehlerbehebung

### Problem: Connection Refused

Wenn Sie den Fehler `ECONNREFUSED` erhalten:

1. Stellen Sie sicher, dass der TTS-Service läuft:
   ```bash
   docker-compose ps tts-service
   ```

2. Prüfen Sie die Umgebungsvariable:
   ```python
   import os
   print(os.getenv('TTS_SERVICE_URL'))
   # Sollte ausgeben: http://tts-service:5000
   ```

3. Verwenden Sie **niemals** `localhost` oder `127.0.0.1` im Docker-Container!
   - ❌ Falsch: `http://localhost:5000`
   - ❌ Falsch: `http://127.0.0.1:5000`
   - ✓ Richtig: `http://tts-service:5000`

### Problem: Timeout

Falls TTS-Anfragen zu lange dauern:

1. Erhöhen Sie das Timeout in `tts_service.py`:
   ```python
   TTS_SYNTHESIS_TIMEOUT = 60  # Von 30 auf 60 Sekunden erhöhen
   ```

2. Prüfen Sie die Logs des TTS-Service:
   ```bash
   docker-compose logs -f tts-service
   ```

## Konfiguration

Alle Konfigurationen erfolgen über Umgebungsvariablen in der `docker-compose.yml` oder `.env` Datei:

```yaml
environment:
  - TTS_SERVICE_URL=http://tts-service:5000
  - APP_BASE_URL=http://localhost:8080
```

Oder in `.env`:
```bash
TTS_SERVICE_URL=http://tts-service:5000
APP_BASE_URL=http://localhost:8080
```
