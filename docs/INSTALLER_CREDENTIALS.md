# Installer: Admin-Benutzer und Passwort uebergeben

Diese Anleitung beschreibt, wie Initial-Credentials beim Installieren gesetzt werden
und was intern beim ersten Start passiert.

## Kurzfassung

- Windows-Installer fragt Admin-E-Mail und optional Passwort direkt im Wizard ab.
- Linux `.deb` und `.rpm` fragen im `postinst`/`%post` interaktiv in der Konsole ab.
- Werte werden als One-Time-Bootstrap in `bootstrap.env` gespeichert.
- Beim ersten Start liest die App diese Werte, erstellt den Admin und loescht die Datei.

## Build-Varianten mit Credential-Uebergabe

- `Windows Setup (.exe)`: interaktive Wizard-Felder fuer E-Mail/Passwort.
- `Linux .deb`: interaktive Abfrage waehrend `dpkg -i`.
- `Linux .rpm`: interaktive Abfrage waehrend `rpm -Uvh`.
- `Windows ZIP` und `Linux tar.gz`: keine Installer-Dialoge; Credentials per ENV oder `bootstrap.env`.

## 1) Windows Installer

Geplanter Screenshot: `docs/screenshots/windows-installer-admin-credentials.png`

### Installation mit Eingabe im Wizard

1. Setup starten: `Dienstplan-Windows-Setup-v<version>.exe`
2. Schritt **Initialen Administrator konfigurieren** ausfuellen:
   - `Administrator E-Mail`
   - `Initiales Passwort (optional)`
3. Installation abschliessen und Anwendung starten.

Beim Install wird erstellt:
- `%LOCALAPPDATA%\\Dienstplan\\data\\bootstrap.env`

Inhalt (Beispiel):

```env
DIENSTPLAN_INITIAL_ADMIN_EMAIL=admin@firma.de
DIENSTPLAN_INITIAL_ADMIN_PASSWORD=MeinStartPasswort123!
```

Beim ersten App-Start:
- Datei wird gelesen
- Admin damit angelegt
- Datei wird automatisch geloescht

### Unattended/Silent (ohne Wizard)

Wenn kein Wizard genutzt wird (z. B. `/VERYSILENT`), kann man alternativ eine
`bootstrap.env` vorab in `%LOCALAPPDATA%\\Dienstplan\\data` ablegen.

## 2) Linux `.deb` Installation

Geplanter Screenshot: `docs/screenshots/linux-deb-postinstall-admin-prompt.png`

### Interaktiv

```bash
sudo dpkg -i dienstplan_<version>_amd64.deb
```

Der Installer fragt:
- `Initiale Admin-E-Mail`
- `Initiales Admin-Passwort`
- Passwort-Bestaetigung

Datei danach:
- `/var/lib/dienstplan/data/bootstrap.env` (Rechte `600`)

### Non-interactive (CI/Automation)

Wenn kein TTY vorhanden ist, wird die interaktive Abfrage uebersprungen.
Dann entweder:

- vor dem ersten Start selbst Datei schreiben:

```bash
sudo install -d -m 750 /var/lib/dienstplan/data
sudo bash -c 'cat > /var/lib/dienstplan/data/bootstrap.env <<EOF
DIENSTPLAN_INITIAL_ADMIN_EMAIL=admin@firma.de
DIENSTPLAN_INITIAL_ADMIN_PASSWORD=MeinStartPasswort123!
EOF'
sudo chown dienstplan:dienstplan /var/lib/dienstplan/data/bootstrap.env
sudo chmod 600 /var/lib/dienstplan/data/bootstrap.env
```

- danach Service starten:

```bash
sudo systemctl start dienstplan
sudo systemctl status dienstplan
```

## 3) Linux `.rpm` Installation

Geplanter Screenshot: `docs/screenshots/linux-rpm-postinstall-admin-prompt.png`

### Interaktiv

```bash
sudo rpm -Uvh dienstplan-<version>-1.x86_64.rpm
```

Verhalten identisch zu `.deb`:
- interaktive Abfrage (wenn TTY vorhanden)
- Speicherung in `/var/lib/dienstplan/data/bootstrap.env`
- One-Time-Verarbeitung beim ersten App-Start

## 4) Portable Varianten (ZIP/tar.gz)

Falls ohne Installer deployt wird:

- per ENV beim Start setzen:

```bash
export DIENSTPLAN_INITIAL_ADMIN_EMAIL="admin@firma.de"
export DIENSTPLAN_INITIAL_ADMIN_PASSWORD="MeinStartPasswort123!"
./Dienstplan
```

- oder `bootstrap.env` im Datenordner ablegen (wird ebenfalls einmalig konsumiert)

## Screenshots

Die folgenden Screenshot-Dateien sind als Platzhalter vorgesehen:

- `docs/screenshots/windows-installer-admin-credentials.png`
- `docs/screenshots/linux-deb-postinstall-admin-prompt.png`
- `docs/screenshots/linux-rpm-postinstall-admin-prompt.png`

Hinweis: In dieser Session konnte ich keine Bilder direkt erzeugen. Sobald ein
Modell mit Bildgenerierung aktiv ist, kann ich diese drei Screenshots sofort
als echte Grafiken nachziehen.
