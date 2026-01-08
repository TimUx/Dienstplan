# Dienstplan - Windows Standalone Executable

**Version 2.1 - Python Edition**

## 🎯 Übersicht

Dienstplan ist nun als standalone Windows-Executable verfügbar! Das bedeutet:
- ✅ **Keine Python-Installation erforderlich**
- ✅ **Keine manuellen Abhängigkeiten**
- ✅ **Einfaches Doppelklick-Starten**
- ✅ **Automatischer Browser-Start**

## 📥 Download

Laden Sie die neueste Version von den [GitHub Releases](https://github.com/TimUx/Dienstplan/releases) herunter:
- **Dienstplan-Windows-v2.1.x.zip**

## 🚀 Installation & Start

### Schritt 1: Herunterladen und Entpacken
1. ZIP-Datei von GitHub Releases herunterladen
2. ZIP-Datei in einen Ordner Ihrer Wahl entpacken (z.B. `C:\Dienstplan`)
3. Im entpackten Ordner finden Sie:
   - `Dienstplan.exe` - Die Hauptanwendung
   - `README.md` - Dokumentation
   - `LICENSE` - Lizenzinformationen
   - `VERSION.txt` - Versionsinformationen

### Schritt 2: Starten
1. Doppelklick auf `Dienstplan.exe`
2. Ein Konsolenfenster öffnet sich mit Serverinformationen
3. Ihr Standard-Webbrowser öffnet sich automatisch
4. Die Anwendung ist unter `http://localhost:5000` erreichbar

**Wichtig:** Lassen Sie das Konsolenfenster geöffnet, solange Sie die Anwendung nutzen!

### Schritt 3: Erste Schritte
1. Beim ersten Start wird automatisch eine leere Datenbank erstellt
2. Melden Sie sich mit den Standard-Zugangsdaten an:
   - **E-Mail:** admin@fritzwinter.de
   - **Passwort:** Admin123!
3. **WICHTIG:** Ändern Sie das Passwort nach der ersten Anmeldung!

## 🛑 Beenden der Anwendung

Um die Anwendung zu beenden:
1. Schließen Sie das Konsolenfenster, ODER
2. Drücken Sie `Ctrl+C` im Konsolenfenster

## 📊 Datenspeicherung

Die Anwendung speichert alle Daten in einer SQLite-Datenbank:
- **Dateiname:** `dienstplan.db`
- **Speicherort:** Im gleichen Ordner wie `Dienstplan.exe`

**Backup-Empfehlung:** Sichern Sie regelmäßig die `dienstplan.db` Datei!

## 🔧 Fehlerbehebung

### Problem: "DLL load failed while importing cp_model_helper"

**Symptom:** Die Anwendung startet, zeigt aber folgenden Fehler:
```
❌ Missing dependency: DLL load failed while importing cp_model_helper: Das angegebene Modul wurde nicht gefunden.
```

**Ursache:** OR-Tools native Bibliotheken fehlen in der Executable

**Lösung:**
- Dies wurde in neueren Versionen behoben (ab v2.1.x)
- Laden Sie die neueste Version von GitHub herunter
- Falls das Problem weiterhin besteht, melden Sie es auf GitHub Issues

### Problem: "Windows hat den PC geschützt"
**Ursache:** Windows SmartScreen warnt vor unbekannten Anwendungen.

**Lösung:**
1. Klicken Sie auf "Weitere Informationen"
2. Klicken Sie auf "Trotzdem ausführen"
3. Dies ist normal für neue Anwendungen ohne Code-Signatur

### Problem: Antivirus-Software blockiert die Anwendung
**Ursache:** Einige Antivirus-Programme blockieren PyInstaller-Executables.

**Lösung:**
1. Fügen Sie `Dienstplan.exe` zur Whitelist Ihrer Antivirus-Software hinzu
2. Alternativ: Deaktivieren Sie temporär die Antivirus-Software für die Installation

### Problem: Browser öffnet sich nicht automatisch
**Lösung:**
1. Öffnen Sie manuell Ihren Browser
2. Navigieren Sie zu `http://localhost:5000`

### Problem: Port 5000 ist bereits belegt
**Symptom:** Fehlermeldung "Address already in use" im Konsolenfenster.

**Lösung:**
1. Beenden Sie andere Anwendungen, die Port 5000 verwenden
2. Alternative: Verwenden Sie die Python-Version mit eigenem Port:
   ```bash
   python main.py serve --port 8080
   ```

### Problem: Datenbank ist beschädigt
**Lösung:**
1. Benennen Sie `dienstplan.db` um (z.B. zu `dienstplan.db.backup`)
2. Starten Sie die Anwendung neu - eine neue Datenbank wird erstellt
3. Importieren Sie Ihre Daten aus dem Backup

## 🔐 Sicherheitshinweise

### Für Desktop-Nutzung (Single-User)
Die Executable ist sicher für Desktop-Nutzung:
- Server läuft nur lokal (`127.0.0.1`)
- Nur vom eigenen PC erreichbar
- Keine Netzwerkexposition

### Für Server-Deployment
**NICHT EMPFOHLEN!** Für produktive Server-Umgebungen verwenden Sie:
1. Die Python-Version mit WSGI-Server (Gunicorn, uWSGI)
2. Reverse Proxy (nginx, Apache)
3. HTTPS mit gültigem SSL-Zertifikat
4. Firewall und Zugriffsbeschränkungen

## 📈 Aktualisierung

Um auf eine neue Version zu aktualisieren:
1. Laden Sie die neue Version herunter
2. Schließen Sie die laufende Anwendung
3. Ersetzen Sie `Dienstplan.exe` durch die neue Version
4. **WICHTIG:** Behalten Sie Ihre `dienstplan.db` Datei!
5. Starten Sie die neue Version

## 🛠️ Erweiterte Optionen

### Eigene Executable erstellen
Falls Sie die Executable selbst bauen möchten:

**Voraussetzungen:**
- Python 3.11+ installiert (empfohlen) oder mindestens Python 3.9
- Git installiert

**Schritte:**
```bash
# Repository klonen
git clone https://github.com/TimUx/Dienstplan.git
cd Dienstplan

# Abhängigkeiten installieren
pip install -r requirements.txt

# Build-Skript ausführen
build_windows.bat
```

Die fertige `Dienstplan.exe` finden Sie im Hauptverzeichnis.

## 📦 Was ist in der Executable enthalten?

Die `Dienstplan.exe` enthält:
- ✅ Python 3.11 Runtime
- ✅ Flask Web-Framework
- ✅ Google OR-Tools Solver
- ✅ Alle Python-Bibliotheken
- ✅ Web UI (HTML/CSS/JavaScript)
- ✅ SQLite Datenbank-Engine

**Dateigröße:** ~120-150 MB (je nach Version)

## 💡 Tipps & Tricks

### Desktop-Verknüpfung erstellen
1. Rechtsklick auf `Dienstplan.exe`
2. "Verknüpfung erstellen"
3. Verschieben Sie die Verknüpfung auf den Desktop

### Autostart einrichten
1. Windows-Taste + R drücken
2. `shell:startup` eingeben und Enter
3. Verknüpfung zu `Dienstplan.exe` in diesen Ordner kopieren
4. Die Anwendung startet nun automatisch mit Windows

### Mehrere Instanzen
Sie können mehrere Instanzen mit verschiedenen Datenbanken laufen lassen, aber:
- Nur eine Instanz kann Port 5000 verwenden
- Nutzen Sie verschiedene Ports für weitere Instanzen (Python-Version erforderlich)

## 🆘 Support

Bei Problemen oder Fragen:
- **GitHub Issues:** https://github.com/TimUx/Dienstplan/issues
- **Dokumentation:** Siehe README.md
- **E-Mail:** Siehe GitHub-Profil

## 📄 Lizenz

Dieses Projekt ist unter der MIT-Lizenz lizenziert - siehe LICENSE-Datei für Details.

---

**Version 2.1 - Python Edition** | Entwickelt von Timo Braun

Powered by **Google OR-Tools** und **PyInstaller**

© 2025 Fritz Winter Eisengießerei GmbH & Co. KG
