# Benachrichtigungssystem für Mindestschichtstärke

## Übersicht

Dieses Feature implementiert ein Benachrichtigungssystem für Administratoren und Disponenten, das automatisch Warnungen ausgibt, wenn die Mindestschichtstärke (Mindestanzahl an Mitarbeitern pro Schicht) unterschritten wird.

## Problem

Die Mindestschichtstärke kann unterschritten werden durch:
- Ungeplante Abwesenheit (AU - Arbeitsunfähigkeit/Krank)
- Kurzfristigen Urlaub (U)
- Lehrgänge/Fortbildungen (L)
- Andere unvorhergesehene Ereignisse

Bisher wurden solche Situationen möglicherweise nicht sofort erkannt, was zu Personalengpässen führen konnte.

## Lösung

Das System prüft automatisch bei jeder Abwesenheitseintragung, ob dadurch die Mindestschichtstärke unterschritten wird, und erstellt bei Bedarf Benachrichtigungen für Administratoren und Disponenten.

## Funktionsweise

### Backend

#### 1. Datenbank
Eine neue Tabelle `AdminNotifications` speichert alle Benachrichtigungen:
- **Type**: Art der Benachrichtigung (z.B. "UNDERSTAFFING")
- **Severity**: Schweregrad (CRITICAL, HIGH, WARNING)
- **Title**: Kurzbeschreibung
- **Message**: Detaillierte Nachricht
- **ShiftDate**: Betroffenes Datum
- **ShiftCode**: Betroffene Schicht (F, S, N)
- **RequiredStaff**: Erforderliche Mitarbeiteranzahl
- **ActualStaff**: Tatsächlich verfügbare Mitarbeiteranzahl
- **IsRead**: Gelesen-Status

#### 2. Notification Manager (`notification_manager.py`)
Kernlogik für die Benachrichtigungserstellung:

```python
# Prüft Besetzung für ein bestimmtes Datum und Schicht
check_staffing_for_date(conn, check_date, shift_code)

# Prüft Auswirkungen einer Abwesenheit
check_absence_impact(conn, absence_id, employee_id, start_date, end_date, absence_type)

# Erstellt Benachrichtigung für Unterbesetzung
create_understaffing_notification(conn, issue, created_by)

# Verarbeitet Abwesenheit und erstellt Benachrichtigungen
process_absence_for_notifications(conn, absence_id, ...)
```

#### 3. API-Endpunkte

**GET /api/notifications**
- Liefert Liste aller Benachrichtigungen
- Parameter: `unreadOnly=true/false`, `limit=50`
- Nur für Admin/Disponent

**GET /api/notifications/count**
- Liefert Anzahl ungelesener Benachrichtigungen
- Nur für Admin/Disponent

**POST /api/notifications/{id}/read**
- Markiert einzelne Benachrichtigung als gelesen
- Nur für Admin/Disponent

**POST /api/notifications/mark-all-read**
- Markiert alle Benachrichtigungen als gelesen
- Nur für Admin/Disponent

#### 4. Integration
Das System wird automatisch aktiviert bei:
- Erstellung einer neuen Abwesenheit via `/api/absences` POST
- Die Benachrichtigungserstellung läuft asynchron und schlägt nicht die Abwesenheitserstellung fehl

### Frontend

#### 1. Benachrichtigungsglocke
- Im Header-Bereich für Admin/Disponent
- Zeigt Badge mit Anzahl ungelesener Benachrichtigungen
- Aktualisiert sich automatisch alle 60 Sekunden

#### 2. Benachrichtigungs-Modal
- Auflistung aller Benachrichtigungen
- Filter: Alle / Nur ungelesen
- Farbcodierung nach Schweregrad:
  - **CRITICAL**: Rot (keine Mitarbeiter verfügbar)
  - **HIGH**: Orange (2+ Mitarbeiter fehlen)
  - **WARNING**: Blau (1 Mitarbeiter fehlt)

#### 3. Funktionen
- Einzelne Benachrichtigung als gelesen markieren
- Alle Benachrichtigungen als gelesen markieren
- Auto-Refresh alle 60 Sekunden

## Mindestschichtstärke-Anforderungen

### Wochentage (Montag - Freitag)
- **Früh (F)**: 4-5 Mitarbeiter (Minimum: 4)
- **Spät (S)**: 3-4 Mitarbeiter (Minimum: 3)
- **Nacht (N)**: 3 Mitarbeiter (Minimum: 3)

### Wochenende (Samstag - Sonntag)
- **Früh (F)**: 2-3 Mitarbeiter (Minimum: 2)
- **Spät (S)**: 2-3 Mitarbeiter (Minimum: 2)
- **Nacht (N)**: 2-3 Mitarbeiter (Minimum: 2)

## Schweregrad-Bestimmung

```python
if actual_staff == 0:
    severity = 'CRITICAL'  # Keine Mitarbeiter verfügbar
elif deficit >= 2:
    severity = 'HIGH'      # 2 oder mehr Mitarbeiter fehlen
else:
    severity = 'WARNING'   # 1 Mitarbeiter fehlt
```

## Beispiel-Benachrichtigung

```
Titel: Mindestschichtstärke unterschritten: Früh am 12.01.2026

Die Mindestschichtstärke für die Früh Schicht (F) am Montag, 12.01.2026 
wurde unterschritten.

Grund: Urlaub von Max Mustermann (Team Alpha)
Erforderlich: 4 Mitarbeiter
Verfügbar: 3 Mitarbeiter
Fehlend: 1 Mitarbeiter
```

## Installation / Migration

### Für bestehende Datenbanken

```bash
# Migration ausführen
python migrate_add_admin_notifications.py dienstplan.db
```

### Für neue Installationen

Die `AdminNotifications`-Tabelle wird automatisch erstellt bei:
```bash
python main.py init-db
```

## Testen

Ein Testskript ist verfügbar:

```bash
# Testdatenbank erstellen und Benachrichtigungssystem testen
python test_notifications.py
```

Das Testskript:
1. Erstellt Test-Team und Mitarbeiter
2. Weist 4 Mitarbeiter einer Früh-Schicht zu
3. Erstellt Abwesenheit für einen Mitarbeiter
4. Prüft, ob Benachrichtigung erstellt wurde
5. Zeigt Details der Benachrichtigung an

## Sicherheit

- Benachrichtigungen sind nur für Benutzer mit Rolle **Admin** oder **Disponent** sichtbar
- Alle API-Endpunkte sind mit Authentifizierung und Autorisierung geschützt
- Keine sensitiven Daten in Benachrichtigungen (nur Mitarbeiternamen und Teamzuordnung)
- SQL-Injection-Schutz durch parametrisierte Queries
- XSS-Schutz im Frontend durch `escapeHtml()`

## Wartung

### Alte Benachrichtigungen löschen

Empfohlener SQL-Query zum Löschen alter, gelesener Benachrichtigungen:

```sql
-- Löscht gelesene Benachrichtigungen älter als 30 Tage
DELETE FROM AdminNotifications 
WHERE IsRead = 1 
  AND julianday('now') - julianday(ReadAt) > 30;
```

### Monitoring

Anzahl ungelesener Benachrichtigungen prüfen:

```sql
SELECT COUNT(*) as UnreadCount
FROM AdminNotifications
WHERE IsRead = 0;
```

Benachrichtigungen nach Schweregrad:

```sql
SELECT Severity, COUNT(*) as Count
FROM AdminNotifications
WHERE IsRead = 0
GROUP BY Severity;
```

## Zukünftige Erweiterungen (Optional)

Mögliche zukünftige Verbesserungen:
1. **E-Mail-Benachrichtigungen**: Automatische E-Mail bei kritischen Unterbesetzungen
2. **Push-Benachrichtigungen**: Browser-Push-Notifications
3. **SMS-Benachrichtigungen**: Bei kritischen Situationen
4. **Automatische Springer-Zuweisung**: System schlägt automatisch verfügbare Springer vor
5. **Eskalation**: Bei längerer Nichtreaktion automatische Eskalation

## Dateien

### Backend
- `notification_manager.py` - Kernlogik für Benachrichtigungen
- `migrate_add_admin_notifications.py` - Migrations-Skript
- `db_init.py` - Erweitert um AdminNotifications-Tabelle
- `web_api.py` - API-Endpunkte für Benachrichtigungen

### Frontend
- `wwwroot/index.html` - Benachrichtigungsglocke und Modal
- `wwwroot/js/app.js` - JavaScript für Benachrichtigungsfunktionalität
- `wwwroot/css/styles.css` - Styling für Benachrichtigungen

### Tests
- `test_notifications.py` - Testskript für Benachrichtigungssystem

## Support

Bei Fragen oder Problemen:
1. Prüfen Sie die Logs auf Fehlermeldungen
2. Stellen Sie sicher, dass die Datenbank-Migration durchgeführt wurde
3. Überprüfen Sie die Berechtigungen (nur Admin/Disponent sehen Benachrichtigungen)
4. Kontaktieren Sie den Systemadministrator

## Changelog

### Version 1.0 (Januar 2026)
- Initiales Release
- Benachrichtigungen bei Unterschreitung der Mindestschichtstärke
- UI mit Benachrichtigungsglocke und Modal
- Auto-Refresh alle 60 Sekunden
- Schweregrad-basierte Farbcodierung
- Test-Suite für Validierung

---

**Entwickelt von:** Timo Braun  
**Datum:** Januar 2026  
**Version:** 1.0
