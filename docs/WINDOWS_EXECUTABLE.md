# Dienstplan - Windows Standalone Distribution

**Version 2.1 - Python Edition**

## 🎯 Übersicht

Dienstplan ist als Windows-Distribution verfügbar. Der Build nutzt den
**One-Dir-Modus** von PyInstaller: Alle DLLs und Python-Bibliotheken liegen
als lose Dateien neben `Dienstplan.exe` – das Programm startet dadurch deutlich
schneller als beim früheren Einzel-EXE-Build, der bei jedem Start alles nach
`%TEMP%` entpacken musste.

- ✅ **Keine Python-Installation erforderlich**
- ✅ **Schnellerer Start** – kein Entpacken beim Starten
- ✅ **Einfaches Doppelklick-Starten**
- ✅ **Automatischer Browser-Start**

## 📥 Download

Laden Sie die neueste Version von den [GitHub Releases](https://github.com/TimUx/Dienstplan/releases) herunter:

| Datei | Beschreibung |
|-------|--------------|
| `Dienstplan-Windows-Setup-v*.exe` | **Empfohlen** – Inno-Setup-Installer (installiert in Programme, legt Startmenü- und Desktop-Verknüpfung an) |
| `Dienstplan-Windows-v*.zip` | **Portabel** – ZIP entpacken und `Dienstplan.exe` starten |

## 🚀 Installation & Start

### Option A: Installer (empfohlen)

1. `Dienstplan-Windows-Setup-v*.exe` herunterladen und ausführen
2. Installationsassistenten folgen
3. Dienstplan über Startmenü oder Desktop-Verknüpfung starten
4. Ein Konsolenfenster öffnet sich mit Serverinformationen
5. Ihr Standard-Webbrowser öffnet sich automatisch auf `http://localhost:5000`

### Option B: Portables ZIP

1. ZIP-Datei von GitHub Releases herunterladen
2. ZIP in einen Ordner Ihrer Wahl entpacken (z. B. `C:\Dienstplan`)
3. Im entpackten Ordner finden Sie:
   - `Dienstplan.exe` – Die Hauptanwendung
   - `_internal\` – Python-Runtime und Bibliotheken (nicht verändern)
   - `README.md` – Dokumentation
   - `LICENSE` – Lizenzinformationen
4. `Dienstplan.exe` doppelklicken

**Wichtig:** Lassen Sie das Konsolenfenster geöffnet, solange Sie die Anwendung nutzen!

### Erste Schritte

1. Beim ersten Start wird automatisch eine leere Datenbank erstellt
2. Melden Sie sich mit dem Administrator-Konto an:
   - **E-Mail:** Wert von `DIENSTPLAN_INITIAL_ADMIN_EMAIL` (Standard: `admin@fritzwinter.de`), sofern beim Packen/Start nicht gesetzt
   - **Passwort:** Wert von `DIENSTPLAN_INITIAL_ADMIN_PASSWORD` oder das bei der **ersten** Datenbank-Erstellung in der Konsole ausgegebene Initialpasswort
3. **WICHTIG:** Ändern Sie das Passwort nach der ersten Anmeldung!

## 🛑 Beenden der Anwendung

Um die Anwendung zu beenden:
1. Schließen Sie das Konsolenfenster, ODER
2. Drücken Sie `Ctrl+C` im Konsolenfenster

## 📊 Datenspeicherung

Die Anwendung speichert alle Daten in einer SQLite-Datenbank:
- **Dateiname:** `dienstplan.db`
- **Speicherort:** Unterordner `data\` neben `Dienstplan.exe`

**Backup-Empfehlung:** Sichern Sie regelmäßig die `data\dienstplan.db` Datei!

## 🔧 Fehlerbehebung

### Problem: "DLL load failed while importing cp_model_helper"

**Symptom:** Die Anwendung startet, zeigt aber folgenden Fehler:
```
❌ Missing dependency: DLL load failed while importing cp_model_helper: Das angegebene Modul wurde nicht gefunden.
```

**Ursache:** OR-Tools native Bibliotheken fehlen.

**Lösung:**
- Laden Sie die neueste Version von GitHub herunter
- Stellen Sie sicher, dass der `_internal\` Ordner vollständig entpackt/installiert wurde und nicht vom Antivirus gelöscht wurde

### Problem: "Windows hat den PC geschützt"
**Ursache:** Windows SmartScreen warnt vor unbekannten Anwendungen.

**Lösung:**
1. Klicken Sie auf "Weitere Informationen"
2. Klicken Sie auf "Trotzdem ausführen"
3. Dies ist normal für Anwendungen ohne Code-Signatur

### Problem: Antivirus-Software blockiert die Anwendung
**Ursache:** Einige Antivirus-Programme blockieren PyInstaller-Executables.

**Lösung:**
1. Fügen Sie den Dienstplan-Ordner zur Whitelist Ihrer Antivirus-Software hinzu
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
1. Benennen Sie `data\dienstplan.db` um (z. B. zu `data\dienstplan.db.backup`)
2. Starten Sie die Anwendung neu – eine neue Datenbank wird erstellt
3. Importieren Sie Ihre Daten aus dem Backup

## 🔐 Sicherheitshinweise

### Für Desktop-Nutzung (Single-User)
Die Distribution ist sicher für Desktop-Nutzung:
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
3. **Installer:** Setup erneut ausführen – er überschreibt die vorhandene Installation
4. **Portables ZIP:** Entpacken Sie in den gleichen Ordner und überschreiben Sie alle Dateien
5. **WICHTIG:** Behalten Sie Ihre `data\dienstplan.db` Datei!
6. Starten Sie die neue Version

## 🛠️ Erweiterte Optionen

### Eigene Distribution erstellen
Falls Sie den Build selbst ausführen möchten:

**Voraussetzungen:**
- Python 3.11+ installiert (empfohlen) oder mindestens Python 3.9
- Git installiert
- Inno Setup 6 installiert (für den Installer-Build)

**Schritte:**
```cmd
REM Repository klonen
git clone https://github.com/TimUx/Dienstplan.git
cd Dienstplan

REM Abhängigkeiten installieren & Build starten (erzeugt ZIP)
build_windows.bat

REM Installer bauen (optional, benötigt Inno Setup)
iscc /DMyAppVersion=2.1.0 installer\Dienstplan.iss
```

Die fertige Distribution befindet sich in `dist\Dienstplan\` (Ordner) sowie
als `Dienstplan-Windows.zip`.

## 📦 Was ist in der Distribution enthalten?

```
Dienstplan\
├── Dienstplan.exe          ← Startprogramm
├── _internal\              ← Python-Runtime + alle Bibliotheken
│   ├── python311.dll
│   ├── ortools\            ← Google OR-Tools
│   ├── wwwroot\            ← Web-UI (HTML/CSS/JS)
│   ├── migrations\         ← Alembic DB-Migrationsskripte
│   └── ...
└── data\                   ← (wird beim ersten Start angelegt)
    └── dienstplan.db       ← SQLite-Datenbank
```

**Ordnergröße:** ~150–200 MB (je nach Version und Python-Runtime)

## 💡 Tipps & Tricks

### Desktop-Verknüpfung erstellen (Portables ZIP)
1. Rechtsklick auf `Dienstplan.exe`
2. "Verknüpfung erstellen"
3. Verschieben Sie die Verknüpfung auf den Desktop

### Autostart einrichten
1. Windows-Taste + R drücken
2. `shell:startup` eingeben und Enter
3. Verknüpfung zu `Dienstplan.exe` in diesen Ordner kopieren
4. Die Anwendung startet nun automatisch mit Windows

## 🆘 Support

Bei Problemen oder Fragen:
- **GitHub Issues:** https://github.com/TimUx/Dienstplan/issues
- **Dokumentation:** Siehe README.md
- **E-Mail:** Siehe GitHub-Profil

## 📄 Lizenz

Dieses Projekt ist unter der MIT-Lizenz lizenziert – siehe LICENSE-Datei für Details.

---

**Version 2.1 - Python Edition** | Entwickelt von Timo Braun

Powered by **Google OR-Tools** und **PyInstaller**

© 2025 Fritz Winter Eisengießerei GmbH & Co. KG
