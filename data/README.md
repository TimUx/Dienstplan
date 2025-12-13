# Datenbank-Verzeichnis / Database Directory

## Deutsch

Dieses Verzeichnis enthält die produktionsfähige SQLite-Datenbank für das Dienstplan-System.

### Inhalt

- **dienstplan.db** - Vorkonfigurierte SQLite-Datenbank

### Datenbank-Inhalt

Die Datenbank ist bereits initialisiert und enthält:

✅ **Produktionsfertige Struktur:**
- Alle erforderlichen Tabellen und Indizes
- Standard-Rollen (Admin, Disponent, Mitarbeiter)
- Standard-Schichttypen (F, S, N, Z, BMT, BSB, K, U, L)
- Administrator-Benutzer (siehe unten)

❌ **Keine Beispieldaten:**
- Keine Teams (leer)
- Keine Mitarbeiter (leer)
- Keine Schichten (leer)

### Standard-Anmeldedaten

- **E-Mail:** admin@fritzwinter.de
- **Passwort:** Admin123!
- ⚠️ **WICHTIG:** Ändern Sie das Passwort nach der ersten Anmeldung!

### Persistenz

Die Datenbank ist **persistent**:
- Alle Änderungen werden dauerhaft gespeichert
- Daten bleiben nach Neustart des Programms erhalten
- Sichern Sie diesen Ordner für Backups

### Backup & Wiederherstellung

**Backup erstellen:**
```bash
# Kopieren Sie den gesamten data-Ordner
cp -r data data_backup_2025-01-15
```

**Backup wiederherstellen:**
```bash
# Ersetzen Sie die aktuelle Datenbank
cp data_backup_2025-01-15/dienstplan.db data/
```

---

## English

This directory contains the production-ready SQLite database for the Dienstplan system.

### Contents

- **dienstplan.db** - Pre-configured SQLite database

### Database Contents

The database is pre-initialized and includes:

✅ **Production-ready structure:**
- All required tables and indexes
- Default roles (Admin, Disponent, Mitarbeiter)
- Standard shift types (F, S, N, Z, BMT, BSB, K, U, L)
- Administrator user (see below)

❌ **No sample data:**
- No teams (empty)
- No employees (empty)
- No shifts (empty)

### Default Login Credentials

- **Email:** admin@fritzwinter.de
- **Password:** Admin123!
- ⚠️ **IMPORTANT:** Change the password after first login!

### Persistence

The database is **persistent**:
- All changes are saved permanently
- Data remains after program restart
- Back up this folder for backups

### Backup & Restore

**Create backup:**
```bash
# Copy the entire data folder
cp -r data data_backup_2025-01-15
```

**Restore backup:**
```bash
# Replace the current database
cp data_backup_2025-01-15/dienstplan.db data/
```
