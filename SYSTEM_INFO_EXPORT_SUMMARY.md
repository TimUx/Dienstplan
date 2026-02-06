# System Information Export - Zusammenfassung

## Was wurde erstellt?

Es wurde ein Python-Skript erstellt, das alle wichtigen Informationen aus dem Dienstplan-System exportiert und in einem Format ausgibt, das perfekt für die Analyse durch Copilot Agents geeignet ist.

## Dateien

1. **export_system_info.py** - Das Hauptskript (32 KB)
2. **EXPORT_SCRIPT_README.md** - Vollständige Dokumentation in Deutsch (7 KB)
3. **EXAMPLE_EXPORT.txt** - Beispiel-Ausgabe (666 Zeilen)

## Verwendung

### Einfachste Verwendung:
```bash
python export_system_info.py --output system_info.txt
```

### Mit spezifischer Datenbank:
```bash
python export_system_info.py --db dienstplan.db --output info.txt
```

## Was wird exportiert?

Das Skript exportiert **15 Abschnitte** mit allen wichtigen Informationen:

### 1. Datenbank-Schema
- Alle Tabellen und Spalten
- Primärschlüssel und Constraints
- Anzahl der Datensätze pro Tabelle

### 2. Einstellungen
- Globale Schicht-Einstellungen (max. aufeinanderfolgende Schichten, Ruhezeiten)
- E-Mail/SMTP-Konfiguration

### 3. Schichttypen
- Alle konfigurierten Schichten (F, S, N, etc.)
- Arbeitszeiten, Dauer, Farben
- Arbeitstage und Besetzungsanforderungen
- Maximale aufeinanderfolgende Tage

### 4. Teams
- Teamname, Beschreibung, E-Mail
- Rotationsgruppen-Zuordnung
- Anzahl Mitarbeiter

### 5. Mitarbeiter
- Name, Personalnummer, E-Mail
- Qualifikationen (BMT, BSB, TD, Teamleiter)
- Team-Zugehörigkeit
- Authentifizierungsstatus

### 6. Abwesenheiten
- Alle Abwesenheiten (AU, U, L, benutzerdefiniert)
- Zeiträume und Notizen
- Gruppiert nach Mitarbeiter

### 7. Abwesenheitstypen
- Standard-Typen (U, AU, L)
- Benutzerdefinierte Typen
- Farben

### 8. Urlaubsanträge
- Status (In Bearbeitung, Genehmigt, Nicht Genehmigt)
- Zeiträume
- Antworten vom Disponenten

### 9. Ferienzeiten
- Schulferien, Feiertage
- Zeiträume und Farben

### 10. Schichtzuweisungen
- Neueste 100 Zuweisungen
- Mitarbeiter, Schicht, Datum
- Markierungen (MANUAL, FIXED, SPRINGER)
- Statistiken nach Schichttyp

### 11. Rotationsgruppen
- Rotationsmuster (z.B. F → N → S)
- Zugeordnete Schichttypen
- Verwendung durch Teams

### 12. Team-Schicht-Zuordnungen
- Welche Teams welche Schichten arbeiten können

### 13. Schichttausch
- Angebotene Tausche
- Status und Notizen

### 14. Statistiken
- Mitarbeiter-Übersicht
- Team-Übersicht
- Schicht-Statistiken
- Abwesenheits-Übersicht

## Integration mit Copilot Agents

### Schritt-für-Schritt:

1. **Exportieren:**
   ```bash
   python export_system_info.py --output system_info.txt
   ```

2. **Datei öffnen und Inhalt kopieren:**
   ```bash
   cat system_info.txt
   ```

3. **In Copilot Agent Prompt einfügen:**
   ```
   Hier sind die vollständigen Systeminformationen meines Dienstplan-Systems:

   [Inhalt von system_info.txt hier einfügen]

   Frage: [Deine Analyse-Frage]
   ```

### Beispiel-Fragen für Copilot Agents:

- "Analysiere die Schichtverteilung und finde Optimierungspotenziale"
- "Gibt es Konflikte in den Rotationsgruppen?"
- "Welche Teams sind unterbesetzt?"
- "Sind die Ruhezeiten korrekt konfiguriert?"
- "Prüfe die Einstellungen auf Best Practices"
- "Welche Mitarbeiter haben welche Qualifikationen?"
- "Gibt es Probleme mit der aktuellen Konfiguration?"

## Ausgabeformat

Die Ausgabe ist strukturiert und gut lesbar:

```
================================================================================
DIENSTPLAN SYSTEM INFORMATION EXPORT
================================================================================
Export Date: 2026-02-06 16:50:17
Database: dienstplan.db
================================================================================

--------------------------------------------------------------------------------
SECTION: SHIFT TYPES
--------------------------------------------------------------------------------

Total Shift Types: 3

Shift Type [1]: Frühschicht (F) - ACTIVE
  Time: 05:45 - 13:45 (8.0h)
  Color: #4CAF50
  Weekly Working Hours: 48.0h
  Work Days: Mo, Tu, We, Th, Fr, Sa, Su
  ...

================================================================================
END OF EXPORT
================================================================================
```

## Datenschutz

⚠️ **Wichtig**: Der Export enthält personenbezogene Daten!

- Namen, E-Mails, Personalnummern sind enthalten
- Passwörter werden automatisch maskiert (***)
- Behandle Exporte als vertraulich
- Teile sie nicht öffentlich
- Lösche temporäre Exporte nach der Analyse

## Vorteile

✅ **Vollständig**: Alle relevanten Systeminformationen in einer Datei
✅ **Strukturiert**: Übersichtliche Abschnitte, leicht zu navigieren
✅ **Für KI optimiert**: Perfekt formatiert für Copilot Agent Analyse
✅ **Flexibel**: Wählbare Datenbank und Ausgabeziel
✅ **Sicher**: Fehlerbehandlung, Passwort-Maskierung
✅ **Dokumentiert**: Ausführliche README in Deutsch

## Beispiel-Ausgabe

Eine vollständige Beispiel-Ausgabe findest du in `EXAMPLE_EXPORT.txt` (666 Zeilen).

## Support

Vollständige Dokumentation findest du in `EXPORT_SCRIPT_README.md`.

Bei Fragen:
1. Lies die README-Datei
2. Prüfe die Beispiel-Ausgabe
3. Teste mit `python export_system_info.py --help`

---

Erstellt von: GitHub Copilot Agent
Datum: 2026-02-06
