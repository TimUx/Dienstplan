# 🚀 Installationsanleitung – Dienstplan

**Version 2.1 - Python Edition**

Diese Anleitung beschreibt alle verfügbaren Installationsarten für das Dienstplan-System.

---

## Übersicht der Installationsmethoden

| Methode | Voraussetzungen | Geeignet für |
|---------|-----------------|--------------|
| [Native Python](#1-native-python-installation) | Python 3.9+ | Entwickler, fortgeschrittene Benutzer |
| [1-Klick-Installation (Executable)](#2-1-klick-installation-standalone-executable) | Keine | Endbenutzer, Einzelplatz |
| [Docker Compose](#3-docker-compose-container) | Docker | Server, Mehrbenutzer-Betrieb |

**Standard-Zugangsdaten nach der Installation:**
- **E-Mail:** `admin@fritzwinter.de`
- **Passwort:** `Admin123!`

> ⚠️ **WICHTIG:** Ändern Sie das Standard-Passwort nach der ersten Anmeldung!

---

## 1. Native Python Installation

Die Python-Installation gibt Ihnen volle Kontrolle über Konfiguration und Deployment.

### 1.1 Voraussetzungen

| Anforderung | Windows | Linux |
|-------------|---------|-------|
| Python | 3.9 oder höher (3.11 empfohlen) | 3.9 oder höher (3.11 empfohlen) |
| pip | Mitgeliefert mit Python | Mitgeliefert mit Python |
| Git | Optional | Optional |

---

### 1.2 Windows – Native Python

#### Schritt 1: Python installieren

1. Laden Sie Python von [python.org](https://www.python.org/downloads/) herunter
2. Führen Sie den Installer aus
3. **Wichtig:** Aktivieren Sie die Option **"Add Python to PATH"**
4. Klicken Sie auf **"Install Now"**

Überprüfung in der Eingabeaufforderung (CMD):
```cmd
python --version
pip --version
```

#### Schritt 2: Repository herunterladen

**Option A: Mit Git**
```cmd
git clone https://github.com/TimUx/Dienstplan.git
cd Dienstplan
```

**Option B: Als ZIP**
1. Öffnen Sie https://github.com/TimUx/Dienstplan
2. Klicken Sie auf **"Code"** → **"Download ZIP"**
3. Entpacken Sie das Archiv in einen Ordner Ihrer Wahl (z.B. `C:\Dienstplan`)
4. Öffnen Sie eine Eingabeaufforderung in diesem Ordner

#### Schritt 3: Abhängigkeiten installieren

```cmd
pip install -r requirements.txt
```

#### Schritt 4: Datenbank initialisieren

```cmd
REM Ohne Beispieldaten (Produktionsstart)
python main.py init-db

REM Mit Beispieldaten (Demo/Test)
python main.py init-db --with-sample-data
```

#### Schritt 5: Server starten

```cmd
python main.py serve
```

Der Server ist nun unter **http://localhost:5000** erreichbar.

**Optionale Parameter:**
```cmd
REM Anderen Port verwenden
python main.py serve --port 8080

REM Für Netzwerkzugriff (alle Interfaces)
python main.py serve --host 0.0.0.0 --port 5000

REM Andere Datenbankdatei
python main.py serve --db C:\Daten\dienstplan.db
```

---

### 1.3 Linux – Native Python

#### Schritt 1: Python installieren

**Ubuntu / Debian:**
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv git -y
```

**RHEL / CentOS / Rocky Linux:**
```bash
sudo dnf install python3 python3-pip git -y
```

**openSUSE / SLES:**
```bash
sudo zypper install python3 python3-pip git
```

Überprüfung:
```bash
python3 --version
pip3 --version
```

#### Schritt 2: Repository herunterladen

```bash
git clone https://github.com/TimUx/Dienstplan.git
cd Dienstplan
```

#### Schritt 3: Virtuelle Umgebung erstellen (empfohlen)

```bash
python3 -m venv venv
source venv/bin/activate
```

#### Schritt 4: Abhängigkeiten installieren

```bash
pip install -r requirements.txt
```

#### Schritt 5: Datenbank initialisieren

```bash
# Ohne Beispieldaten (Produktionsstart)
python main.py init-db

# Mit Beispieldaten (Demo/Test)
python main.py init-db --with-sample-data
```

#### Schritt 6: Server starten

```bash
python main.py serve
```

Der Server ist nun unter **http://localhost:5000** erreichbar.

**Optionale Parameter:**
```bash
# Anderen Port verwenden
python main.py serve --port 8080

# Für Netzwerkzugriff (alle Interfaces)
python main.py serve --host 0.0.0.0 --port 5000
```

#### Optionaler Schritt: Als systemd-Dienst einrichten (Autostart)

Erstellen Sie die Dienstdatei `/etc/systemd/system/dienstplan.service`:

```ini
[Unit]
Description=Dienstplan Schichtverwaltungssystem
After=network.target

[Service]
Type=simple
User=dienstplan
WorkingDirectory=/opt/dienstplan
ExecStart=/opt/dienstplan/venv/bin/python main.py serve --host 0.0.0.0 --port 5000
Restart=always
RestartSec=10
Environment=DB_PATH=/opt/dienstplan/data/dienstplan.db

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable dienstplan
sudo systemctl start dienstplan
sudo systemctl status dienstplan
```

---

## 2. 1-Klick-Installation (Standalone Executable)

Die Standalone-Executable ist die einfachste Installationsmethode – **keine Python-Installation erforderlich**.

### 2.1 Windows – Executable

#### Schritt 1: Herunterladen

1. Öffnen Sie https://github.com/TimUx/Dienstplan/releases
2. Laden Sie die neueste `Dienstplan-Windows-vX.X.X.exe` Datei herunter
3. Erstellen Sie einen Ordner (z.B. `C:\Dienstplan`)
4. Kopieren Sie die `.exe` Datei in diesen Ordner

#### Schritt 2: Starten

1. **Doppelklick** auf `Dienstplan-Windows-vX.X.X.exe`
2. Ein Konsolenfenster öffnet sich (zeigt Serverinformationen)
3. Der Standard-Webbrowser öffnet sich automatisch mit der Anwendung
4. Falls der Browser sich nicht öffnet: Navigieren Sie manuell zu **http://localhost:5000**

> **Wichtig:** Lassen Sie das Konsolenfenster geöffnet, solange Sie die Anwendung nutzen!

#### Datenspeicherung

- Die Datenbank wird automatisch erstellt: `data\dienstplan.db` (neben der `.exe`)
- **Backup:** Kopieren Sie regelmäßig die `data\` Ordner

#### Beenden

- Schließen Sie das Konsolenfenster, oder
- Drücken Sie `Ctrl+C` im Konsolenfenster

#### Fehlerbehebung

**Windows hat den PC geschützt (SmartScreen)**
→ Klicken Sie auf "Weitere Informationen" → "Trotzdem ausführen"

**Antivirus blockiert die Datei**
→ Fügen Sie `Dienstplan.exe` zur Whitelist Ihrer Antivirus-Software hinzu

**Port 5000 bereits belegt**
→ Beenden Sie die andere Anwendung oder nutzen Sie die Python-Installation mit `--port 8080`

---

### 2.2 Linux – Executable

#### Schritt 1: Herunterladen

```bash
# Neueste Version von GitHub Releases herunterladen
wget https://github.com/TimUx/Dienstplan/releases/latest/download/Dienstplan-Linux-vX.X.X

# Oder mit curl
curl -L -o Dienstplan-Linux https://github.com/TimUx/Dienstplan/releases/latest/download/Dienstplan-Linux-vX.X.X
```

#### Schritt 2: Ausführbar machen und starten

```bash
# Ausführbarkeit setzen
chmod +x Dienstplan-Linux-vX.X.X

# Starten
./Dienstplan-Linux-vX.X.X
```

Der Server startet auf **http://localhost:5000**.

#### Datenspeicherung

- Die Datenbank wird automatisch erstellt: `data/dienstplan.db` (neben dem Binary)

#### Als Hintergrunddienst starten

```bash
# Im Hintergrund starten (nohup)
nohup ./Dienstplan-Linux-vX.X.X > dienstplan.log 2>&1 &
echo "PID: $!"

# Log beobachten
tail -f dienstplan.log

# Beenden
kill <PID>
```

---

### 2.3 Executable selbst erstellen (Build)

Falls Sie die Executable selbst bauen möchten, lesen Sie [docs/BUILD_GUIDE.md](BUILD_GUIDE.md).

---

## 3. Docker Compose (Container)

Die Container-Installation ist ideal für Server-Deployment und Mehrbenutzer-Betrieb.

### 3.1 Voraussetzungen

| Anforderung | Windows | Linux |
|-------------|---------|-------|
| Docker Desktop / Docker Engine | 20.10+ | 20.10+ |
| Docker Compose | V2 (in Docker Desktop enthalten) | V2 (`docker compose`) |

---

### 3.2 Windows – Docker Compose

#### Schritt 1: Docker Desktop installieren

1. Laden Sie [Docker Desktop für Windows](https://www.docker.com/products/docker-desktop/) herunter
2. Führen Sie den Installer aus
3. Starten Sie Docker Desktop
4. Warten Sie bis Docker vollständig gestartet ist (Systray-Icon grün)

Überprüfung in PowerShell:
```powershell
docker --version
docker compose version
```

#### Schritt 2: Repository herunterladen

```powershell
git clone https://github.com/TimUx/Dienstplan.git
cd Dienstplan
```

Oder laden Sie das Repository als ZIP herunter und entpacken Sie es.

#### Schritt 3: Container starten

```powershell
# Container erstellen und starten
docker compose up -d

# Logs ansehen
docker compose logs -f

# Status prüfen
docker compose ps
```

Die Anwendung ist nach dem Start unter **http://localhost:5000** erreichbar.

#### Schritt 4: Verwaltung

```powershell
# Container stoppen
docker compose down

# Container stoppen und Daten löschen (VORSICHT!)
docker compose down -v

# Container neu starten
docker compose restart

# Auf neue Version aktualisieren
git pull
docker compose down
docker compose up -d --build
```

#### Datenpersistenz

Die Datenbank wird in einem Docker-Volume gespeichert:
- **Volume:** `dienstplan_dienstplan-data`
- **Pfad im Container:** `/data/dienstplan.db`

```powershell
# Backup der Datenbank erstellen
docker cp dienstplan:/data/dienstplan.db ./backup-dienstplan.db

# Datenbank wiederherstellen
docker cp ./backup-dienstplan.db dienstplan:/data/dienstplan.db
```

---

### 3.3 Linux – Docker Compose

#### Schritt 1: Docker installieren

**Ubuntu / Debian:**
```bash
# Docker Engine installieren
sudo apt update
sudo apt install ca-certificates curl gnupg -y
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin -y

# Aktuellen Benutzer zur Docker-Gruppe hinzufügen (kein sudo erforderlich)
sudo usermod -aG docker $USER
newgrp docker
```

**RHEL / CentOS / Rocky Linux:**
```bash
sudo dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
sudo dnf install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin -y
sudo systemctl enable --now docker
sudo usermod -aG docker $USER
newgrp docker
```

Überprüfung:
```bash
docker --version
docker compose version
```

#### Schritt 2: Repository herunterladen

```bash
git clone https://github.com/TimUx/Dienstplan.git
cd Dienstplan
```

#### Schritt 3: Container starten

```bash
# Container erstellen und starten
docker compose up -d

# Logs ansehen
docker compose logs -f

# Status prüfen
docker compose ps
```

Die Anwendung ist nach dem Start unter **http://localhost:5000** erreichbar.

#### Schritt 4: Verwaltung

```bash
# Container stoppen
docker compose down

# Container stoppen und Daten löschen (VORSICHT!)
docker compose down -v

# Container neu starten
docker compose restart

# Auf neue Version aktualisieren
git pull
docker compose down
docker compose up -d --build
```

#### Datenpersistenz

Die Datenbank wird in einem Docker-Volume gespeichert:
- **Volume:** `dienstplan_dienstplan-data`
- **Pfad im Container:** `/data/dienstplan.db`

```bash
# Backup der Datenbank erstellen
docker cp dienstplan:/data/dienstplan.db ./backup-dienstplan.db

# Datenbank wiederherstellen
docker cp ./backup-dienstplan.db dienstplan:/data/dienstplan.db
```

#### Optional: Mit Reverse Proxy (HTTPS)

Für produktiven Einsatz mit HTTPS empfehlen wir einen Reverse Proxy (nginx):

```bash
# nginx installieren
sudo apt install nginx -y

# Konfiguration erstellen
sudo nano /etc/nginx/sites-available/dienstplan
```

nginx-Konfiguration:
```nginx
server {
    listen 80;
    server_name dienstplan.example.com;

    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/dienstplan /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# HTTPS mit Let's Encrypt
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d dienstplan.example.com
```

---

## 4. Erste Schritte nach der Installation

Unabhängig von der gewählten Installationsmethode:

### 4.1 Erste Anmeldung

1. Öffnen Sie **http://localhost:5000** im Browser
2. Klicken Sie auf **Anmelden**
3. Melden Sie sich mit den Standard-Zugangsdaten an:
   - **E-Mail:** `admin@fritzwinter.de`
   - **Passwort:** `Admin123!`

### 4.2 Pflichtaufgaben nach der Installation

- [ ] **Admin-Passwort ändern:** Administration → Benutzerverwaltung → Admin bearbeiten
- [ ] **Teams erstellen:** Administration → Teams
- [ ] **Mitarbeiter anlegen:** Mitarbeiter → Mitarbeiter hinzufügen
- [ ] **Mitarbeitern Teams zuweisen**
- [ ] **Schichtplanung testen:** Dienstplan → Schichten planen

### 4.3 Weiterlesen

- **[Benutzerhandbuch](../BENUTZERHANDBUCH.md)** – Vollständige Anleitung für alle Funktionen
- **[Schnellstart (Englisch)](QUICKSTART.md)** – Kurzanleitung
- **[Architektur](../ARCHITECTURE.md)** – Technische Details
- **[Build-Anleitung](BUILD_GUIDE.md)** – Executable selbst erstellen

---

## 5. Übersicht: Welche Methode passt zu mir?

```
Bin ich ein Endbenutzer auf Windows?
  └─► 1-Klick-Installation (Executable) → Einfachste Option

Bin ich ein Entwickler oder Admin?
  └─► Native Python → Volle Kontrolle und Flexibilität

Soll die Anwendung dauerhaft auf einem Server laufen?
  └─► Docker Compose → Empfohlen für Server und Produktivbetrieb
```

---

**Dienstplan Version 2.1 - Python Edition**  
Entwickelt von Timo Braun | Powered by Google OR-Tools  
© 2025 Fritz Winter Eisengießerei GmbH & Co. KG
