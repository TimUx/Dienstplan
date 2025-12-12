# Schichtplanung - Implementierung und Nutzung

## Was wurde implementiert

Dieser PR behebt die Probleme mit der automatischen Schichtplanung und implementiert ein neues wöchentliches Team-Rotationssystem.

## Behobene Probleme

### 1. Team-Namen werden nicht angezeigt
**Problem:** In den Kalenderansichten wurde überall "ohne Team" angezeigt.  
**Lösung:** Navigation Properties in EmployeeRepository wurden korrigiert (.Include(e => e.Team) hinzugefügt).

### 2. Automatische Schichtplanung hält Regeln nicht ein
**Problem:** Der alte Algorithmus verteilte Schichten nicht regelkonform.  
**Lösung:** Komplette Neuentwicklung mit strikter Regelvalidierung vor jeder Zuweisung.

### 3. Wöchentliche Team-Rotation implementiert
**Neu:** Teams rotieren wöchentlich durch Schichttypen für faire Verteilung.

## Neues Rotationssystem

### 3-Wochen-Zyklus

```
KW 1:
  • Team 1 → Frühdienst
  • Team 2 → Spätdienst
  • Team 3 → Nachtdienst

KW 2:
  • Team 1 → Nachtdienst
  • Team 2 → Frühdienst
  • Team 3 → Spätdienst

KW 3:
  • Team 1 → Spätdienst
  • Team 2 → Nachtdienst
  • Team 3 → Frühdienst

Dann wiederholt sich der Zyklus...
```

### Vorteile
- ✓ Faire Verteilung aller Schichttypen
- ✓ Keine Überlastung einzelner Teams mit Nachtschichten
- ✓ Vorhersehbare Arbeitszeiten für Mitarbeiter
- ✓ Automatische Einhaltung aller Regeln

## Implementierte Regeln

### Dienstserien
- ✅ Maximal 6 Dienste am Stück
- ✅ Nachtschichten maximal 3-5 am Stück
- ✅ Danach zwingend mindestens 1 Ruhetag
- ✅ Keine identische Schicht zweimal hintereinander

### Arbeitszeiten
- ✅ Maximal 48 Wochenstunden
- ✅ Maximal 192 Stunden pro Monat
- ✅ Mindestruhezeit von 11 Stunden
- ✅ Monatsübergreifende Prüfung (30-Tage-Lookback)

### Verbotene Übergänge
- ❌ Spät → Früh (nur 8 Stunden Pause)
- ❌ Nacht → Früh (0 Stunden Pause)

### Mindestbesetzungen
- **Werktags**: Früh min. 4, Spät min. 3, Nacht min. 3
- **Wochenende**: Alle Schichten min. 2

### Springer
- ✅ Können in Teams sein oder teamübergreifend
- ✅ Mindestens ein Springer bleibt verfügbar
- ✅ Nur Springer übernehmen, wenn regulärer Springer ausfällt
- ✅ Fair nach Workload verteilt

### Sonderfunktionen
- ✅ BMT: Mo-Fr 06:00-14:00, genau 1 Person
- ✅ BSB: Mo-Fr 9,5h täglich, genau 1 Person
- ✅ Keine Überschneidung mit regulären Schichten

## Verwendung

### 1. Teams einrichten

Stelle sicher, dass du 3 Teams mit je ca. 5 Mitarbeitern hast:

```
POST /api/teams
{
  "name": "Team Alpha",
  "description": "Erste Schichtgruppe"
}
```

### 2. Mitarbeiter Teams zuweisen

```
PUT /api/employees/{id}
{
  "teamId": 1,
  "isSpringer": false
}
```

**Wichtig:** Weise jedem regulären Mitarbeiter ein Team zu!

### 3. Springer kennzeichnen

```
PUT /api/employees/{id}
{
  "teamId": null,  // oder ein Team
  "isSpringer": true
}
```

### 4. Automatische Planung starten

```
POST /api/shifts/plan?startDate=2026-01-01&endDate=2026-01-31&force=true
```

**Parameter:**
- `startDate`: Startdatum der Planung (YYYY-MM-DD)
- `endDate`: Enddatum der Planung (YYYY-MM-DD)
- `force`: true = überschreibt bestehende Zuweisungen (außer fixierte)

### 5. Ergebnis überprüfen

```
GET /api/shifts/schedule?view=month&startDate=2026-01-01
```

## Beispiel-Wochenplan

```
KW 1 (6. - 12. Januar 2026):

Montag:
  Früh: Anna (T1), Max (T1), Lisa (T1), Thomas (T1)
  Spät: Julia (T2), Michael (T2), Daniel (T2)
  Nacht: Markus (T3), Petra (T3), Andreas (T3)

Dienstag:
  Früh: Max (T1), Lisa (T1), Thomas (T1), Anna (T1)
  Spät: Michael (T2), Daniel (T2), Julia (T2)
  Nacht: Petra (T3), Andreas (T3), Markus (T3)

... (ähnlich für Mi-Fr)

Samstag:
  Früh: Anna (T1), Max (T1)
  Spät: Julia (T2), Michael (T2)
  Nacht: Markus (T3), Petra (T3)

Sonntag:
  Früh: Lisa (T1), Thomas (T1)
  Spät: Daniel (T2), Julia (T2)
  Nacht: Andreas (T3), Markus (T3)
```

In **KW 2** würde dann Team 1 auf Nacht wechseln, Team 2 auf Früh, etc.

## Abwesenheiten und fixierte Zuweisungen

### Abwesenheit eintragen

```
POST /api/absences
{
  "employeeId": 1,
  "type": "Urlaub",
  "startDate": "2026-01-15",
  "endDate": "2026-01-20"
}
```

Der Algorithmus überspringt automatisch abwesende Mitarbeiter.

### Fixierte Zuweisung (z.B. Feiertage)

```
POST /api/shifts/assignments
{
  "employeeId": 5,
  "shiftTypeId": 1,
  "date": "2026-01-01",
  "isFixed": true
}
```

Fixierte Zuweisungen werden nie überschrieben, auch nicht mit `force=true`.

## Fehlerbehandlung

### Warnung: "Regelverstoß"

Wenn eine Zuweisung gegen Regeln verstößt, wird eine Warnung zurückgegeben:

```json
{
  "warning": "Maximum von 6 aufeinanderfolgenden Schichten erreicht"
}
```

Du kannst mit `forceOverride=true` trotzdem zuweisen (nicht empfohlen).

### Keine Assignments erstellt

**Mögliche Ursachen:**
- Zu wenige Mitarbeiter verfügbar (Abwesenheiten)
- Teams nicht korrekt zugewiesen
- Zu viele fixierte Assignments blockieren

**Lösung:**
1. Prüfe Teamzuweisungen: `GET /api/employees`
2. Prüfe Abwesenheiten: `GET /api/absences`
3. Prüfe verfügbare Mitarbeiter pro Team

## Best Practices

### 1. Team-Größen ausbalancieren
- Jedes Team sollte 4-6 Mitarbeiter haben
- Mehr Teams = mehr Flexibilität
- Weniger Teams = einfachere Planung

### 2. Springer-Pool aufrechterhalten
- Mindestens 2-3 Springer für Flexibilität
- Nicht alle Springer gleichzeitig verplanen
- Springer können auch in Teams sein

### 3. Regelmäßige Neu-Planung
- Monatlich neu planen mit `force=true`
- Vor neuen Monaten prüfen
- Nach größeren Änderungen (neue Mitarbeiter, Teams)

### 4. Fixierte Assignments sparsam nutzen
- Nur für Sonderfälle (Feiertage, Schulungen)
- Zu viele fixierte Assignments schränken Algorithmus ein

### 5. Validierung nach manuellen Änderungen
- Manuelle Änderungen können Regeln verletzen
- Prüfe mit API-Validierung vor dem Speichern
- Besser: Automatische Planung nutzen

## Technische Details

### Performance
- O(1) Lookups durch HashSet/Dictionary
- Batch-Queries für bessere Datenbanknutzung
- Optimiert für große Mitarbeiter-Zahlen

### Sicherheit
- CodeQL Scan: 0 Vulnerabilities
- Alle Eingaben validiert
- Keine SQL-Injection möglich (EF Core)

### Wartbarkeit
- Klare Trennung: Algorithmus, Validierung, Persistierung
- Unit-testbar durch Dependency Injection
- Dokumentierte Konstanten in ShiftRules

## Weitere Dokumentation

- **Algorithmus-Details:** [docs/SHIFT_PLANNING_ALGORITHM.md](SHIFT_PLANNING_ALGORITHM.md)
- **Architektur:** [ARCHITECTURE.md](../ARCHITECTURE.md)
- **API-Dokumentation:** OpenAPI/Swagger unter `/swagger`

## Support

Bei Problemen oder Fragen:
1. Prüfe Logs in der Anwendung
2. Konsultiere Dokumentation
3. Erstelle Issue mit Details zu:
   - Erwartetes Verhalten
   - Tatsächliches Verhalten
   - Schritte zur Reproduktion
   - Relevante Daten (Teams, Mitarbeiter-Anzahl, etc.)
