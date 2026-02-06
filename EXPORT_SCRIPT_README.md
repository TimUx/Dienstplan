# Dienstplan System Information Export Script

## Übersicht

Das `export_system_info.py` Skript exportiert alle wichtigen Informationen, Einstellungen und geplanten Schichten aus dem Dienstplan-System in einem strukturierten, lesbaren Format. Die Ausgabe ist speziell für die Analyse durch Copilot Agents optimiert.

## Zweck

Dieses Skript wurde entwickelt, um:
- Alle Systemkonfigurationen und Einstellungen zu exportieren
- Schichttypen, Teams und Mitarbeiter zu dokumentieren
- Abwesenheiten, Urlaubsanträge und Schichtzuweisungen anzuzeigen
- Rotationsgruppen und Muster zu erfassen
- Statistiken über das System bereitzustellen
- Ein vollständiges Bild des Dienstplan-Systems für Analysezwecke zu liefern

## Verwendung

### Grundlegende Verwendung

```bash
# Export auf die Konsole ausgeben
python export_system_info.py

# Export in eine Datei speichern
python export_system_info.py --output system_info.txt

# Spezifische Datenbank verwenden
python export_system_info.py --db /pfad/zur/dienstplan.db --output info.txt
```

### Optionen

- `--db PATH`: Pfad zur SQLite-Datenbank (Standard: `dienstplan.db`)
- `--output PATH`: Ausgabedatei (Standard: Ausgabe auf Konsole)
- `--help`: Hilfe anzeigen

### Beispiele

```bash
# 1. System-Info für aktuelle Datenbank anzeigen
python export_system_info.py

# 2. System-Info in eine Datei exportieren für spätere Analyse
python export_system_info.py --output dienstplan_export_$(date +%Y%m%d).txt

# 3. Verschiedene Datenbanken vergleichen
python export_system_info.py --db prod.db --output prod_info.txt
python export_system_info.py --db test.db --output test_info.txt
```

## Exportierte Informationen

Das Skript exportiert folgende Abschnitte:

### 1. DATABASE SCHEMA
- Alle Tabellen mit Spaltendetails
- Primärschlüssel und Constraints
- Zeilenanzahl pro Tabelle

### 2. GLOBAL SETTINGS
- Maximale aufeinanderfolgende Schichten
- Maximale aufeinanderfolgende Nachtschichten
- Mindestruhezeit zwischen Schichten

### 3. EMAIL SETTINGS
- SMTP-Konfiguration
- Absender-Informationen
- Aktivierungsstatus

### 4. SHIFT TYPES (Schichttypen)
Für jeden Schichttyp:
- Name, Code und Farbe
- Arbeitszeiten (Start, Ende, Dauer)
- Wöchentliche Arbeitsstunden
- Arbeitstage (Mo-So)
- Mindest- und Maximalbesetzung
- Maximale aufeinanderfolgende Tage

### 5. TEAMS
- Teamname und Beschreibung
- E-Mail-Adresse
- Rotationsgruppen-Zuordnung
- Mitarbeiteranzahl
- Virtuelle Teams (falls vorhanden)

### 6. EMPLOYEES (Mitarbeiter)
Für jeden Mitarbeiter:
- Name und Personalnummer
- E-Mail und Geburtsdatum
- Funktion/Rolle
- Qualifikationen (BMT, BSB, TD, Team Leader, etc.)
- Team-Zugehörigkeit
- Authentifizierungsstatus

### 7. ABSENCES (Abwesenheiten)
- Mitarbeiter und Zeitraum
- Abwesenheitstyp (AU, U, L, oder benutzerdefiniert)
- Notizen

### 8. ABSENCE TYPES (Abwesenheitstypen)
- Standard-Typen (U, AU, L)
- Benutzerdefinierte Typen
- Farben für Darstellung

### 9. VACATION REQUESTS (Urlaubsanträge)
- Mitarbeiter und Zeitraum
- Status (In Bearbeitung, Genehmigt, Nicht Genehmigt)
- Notizen und Antworten
- Bearbeitungsinformationen

### 10. VACATION PERIODS (Ferienzeiten)
- Name der Ferienzeit (z.B. "Sommerferien")
- Zeitraum
- Farbcode

### 11. SHIFT ASSIGNMENTS (Schichtzuweisungen)
- Neueste Zuweisungen (bis zu 100)
- Mitarbeiter und Schichttyp
- Datum
- Markierungen (MANUAL, FIXED, SPRINGER)
- Statistiken nach Schichttyp

### 12. ROTATION GROUPS (Rotationsgruppen)
- Name und Beschreibung
- Rotationsmuster (z.B. F → N → S)
- Zugeordnete Schichttypen in Reihenfolge
- Verwendung durch Teams

### 13. TEAM-SHIFT ASSIGNMENTS
- Welche Teams welche Schichten arbeiten können
- Zuordnung von Teams zu Schichttypen

### 14. SHIFT EXCHANGES (Schichttausch)
- Angebotene Schichten
- Anfragende Mitarbeiter
- Status und Notizen

### 15. STATISTICS (Statistiken)
- Anzahl aktiver/inaktiver Mitarbeiter
- Team-Statistiken
- Schichtzuweisungs-Übersicht
- Abwesenheits-Übersicht
- Urlaubsantrags-Statistiken

## Ausgabeformat

Die Ausgabe ist strukturiert und für Menschen sowie KI-Assistenten gut lesbar:

```
================================================================================
DIENSTPLAN SYSTEM INFORMATION EXPORT
================================================================================
Export Date: 2026-02-06 16:49:02
Database: dienstplan.db
================================================================================

--------------------------------------------------------------------------------
SECTION: [ABSCHNITTSNAME]
--------------------------------------------------------------------------------

[Abschnittsdaten hier...]

================================================================================
END OF EXPORT
================================================================================
```

## Verwendung mit Copilot Agents

### Schritt 1: Exportieren
```bash
python export_system_info.py --output system_info.txt
```

### Schritt 2: In Copilot Agent einfügen
Kopieren Sie den Inhalt der `system_info.txt` Datei und fügen Sie ihn in den Copilot Agent Prompt ein mit einer Frage wie:

```
Hier sind die vollständigen Systeminformationen meines Dienstplan-Systems:

[Inhalt von system_info.txt hier einfügen]

Frage: [Ihre Analyse-Frage hier]
```

### Beispiel-Fragen für Copilot Agents:
- "Analysiere die Schichtverteilung und finde Optimierungspotenziale"
- "Gibt es Konflikte in den Rotationsgruppen?"
- "Welche Teams sind unterbesetzt?"
- "Sind die Ruhezeiten zwischen Schichten korrekt konfiguriert?"
- "Prüfe die Einstellungen auf Best Practices"

## Datenschutz

⚠️ **Wichtig**: Der Export enthält personenbezogene Daten (Namen, E-Mails, etc.).
- Teilen Sie exportierte Dateien nicht öffentlich
- Behandeln Sie Exporte als vertraulich
- Löschen Sie temporäre Exporte nach der Analyse
- Passwörter werden automatisch maskiert (***), aber andere sensible Daten sind sichtbar

## Fehlerbehandlung

Wenn eine Tabelle nicht existiert oder ein Fehler auftritt:
- Das Skript zeigt eine Fehlermeldung im entsprechenden Abschnitt an
- Der Export wird fortgesetzt
- Andere Abschnitte werden normal exportiert

## Voraussetzungen

- Python 3.8 oder höher
- SQLite3 (in Python integriert)
- Zugriff auf die Dienstplan-Datenbank

## Entwicklung

### Einen neuen Export-Abschnitt hinzufügen

1. Erstellen Sie eine neue Methode in der `SystemInfoExporter` Klasse:
```python
def _export_neue_daten(self) -> str:
    output = []
    # Ihre Logik hier
    return "\n".join(output)
```

2. Fügen Sie den Abschnitt zur `export_all()` Methode hinzu:
```python
sections = [
    # ...
    ("NEUE DATEN", self._export_neue_daten),
    # ...
]
```

## Support

Bei Problemen oder Fragen:
1. Prüfen Sie, ob die Datenbankdatei existiert
2. Stellen Sie sicher, dass Sie Leserechte haben
3. Prüfen Sie die Python-Version (mindestens 3.8)
4. Kontaktieren Sie den Entwickler

## Lizenz

Teil des Dienstplan-Systems. Siehe LICENSE-Datei im Hauptverzeichnis.
