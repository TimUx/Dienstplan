# Schichtplanungs-Algorithmus

## Übersicht

Der automatische Schichtplanungs-Algorithmus erstellt faire und regelkonforme Schichtpläne basierend auf einem wöchentlichen Team-Rotationssystem.

## Hauptprinzipien

### 1. Wöchentliche Team-Rotation

Das System arbeitet mit 3 Teams, die wöchentlich durch die Schichttypen rotieren:

**Rotationsmuster:**
- **KW 1**: Team 1 → Früh, Team 2 → Spät, Team 3 → Nacht
- **KW 2**: Team 1 → Nacht, Team 2 → Früh, Team 3 → Spät
- **KW 3**: Team 1 → Spät, Team 2 → Nacht, Team 3 → Früh
- Dann wiederholt sich der Zyklus

Dieser 3-Wochen-Zyklus sorgt für:
- Faire Verteilung aller Schichttypen über Teams
- Gleichmäßige Belastung mit Nachtschichten
- Vorhersehbare Arbeitszeiten
- Reduzierte Planungskomplexität

### 2. Strikte Regelvalidierung

Der Algorithmus validiert **vor jeder Schichtzuweisung** alle Regeln:

#### Dienstserien
- ✓ Maximal 6 Dienste am Stück
- ✓ Nachtschichten maximal 3–5 am Stück
- ✓ Danach zwingend mindestens 1 Ruhetag
- ✓ Keine identische Schicht zweimal hintereinander

#### Arbeitszeiten
- ✓ Maximal 48 Wochenstunden
- ✓ Maximal 192 Stunden pro Monat
- ✓ Mindestruhezeit von 11 Stunden zwischen Schichten
- ✓ Monatsübergreifende Prüfung (30-Tage-Lookback)

#### Verbotene Übergänge (Ruhezeit-Verstöße)
- ✗ Spät → Früh (nur 8 Stunden Pause)
- ✗ Nacht → Früh (0 Stunden Pause)

### 3. Mindestbesetzungen

**Werktags (Mo–Fr):**
- Früh: mindestens 4 Personen
- Spät: mindestens 3 Personen
- Nacht: mindestens 3 Personen

**Wochenende (Sa–So):**
- Alle Schichten: mindestens 2 Personen

### 4. Springer-Management

**Regeln für Springer:**
- Können in Teams sein oder teamübergreifend arbeiten
- Mindestens ein Springer muss immer verfügbar bleiben
- Werden nicht in reguläre Team-Rotation einbezogen
- Werden nach Workload priorisiert
- Können Ausfälle übernehmen

### 5. Sonderfunktionen

**Brandmeldetechniker (BMT):**
- Mo–Fr, 06:00–14:00
- Genau 1 qualifizierte Person pro Tag
- Rotiert fair zwischen qualifizierten Mitarbeitern
- Keine Überschneidung mit regulären Schichten

**Brandschutzbeauftragter (BSB):**
- Mo–Fr, 9,5 Stunden täglich
- Genau 1 qualifizierte Person pro Tag
- Rotiert fair zwischen qualifizierten Mitarbeitern
- Keine Überschneidung mit regulären Schichten

## Algorithmus-Ablauf

### Schritt 1: Initialisierung
```
1. Lade alle Mitarbeiter und Teams
2. Trenne Springer von regulären Mitarbeitern
3. Lade Abwesenheiten für den Zeitraum
4. Behalte fixierte Zuweisungen (IsFixed = true)
```

### Schritt 2: Wochenweise Planung
```
Für jede Woche im Zeitraum:
  1. Bestimme Wochennummer (ISO 8601)
  2. Berechne Team-Schicht-Rotation für diese Woche
  3. Plane jeden Tag der Woche:
     - Bestimme Schichtanforderungen (Werktag/Wochenende)
     - Für jede benötigte Schicht:
       a) Finde zugewiesenes Team für diese Schicht
       b) Filtere verfügbare Teammitglieder (ohne Abwesenheit)
       c) Sortiere nach Workload (Fairness)
       d) Versuche Zuweisung mit Regelvalidierung
       e) Bei Fehlschlag: Versuche andere Teams
```

### Schritt 3: Spezialfunktionen
```
Nach regulärer Planung:
  1. Weise BMT für Mo–Fr zu
  2. Weise BSB für Mo–Fr zu
```

### Schritt 4: Rückgabe
```
Gebe alle gültigen Zuweisungen zurück
```

## Fairness-Mechanismen

### Workload-Basierte Sortierung
- Mitarbeiter mit weniger Schichten in den letzten 30 Tagen werden bevorzugt
- Wochenend-Schichten werden separat getrackt und fair verteilt
- Schichttyp-spezifische Fairness (z.B. für Nachtschichten)

### Team-Rotation
- Garantiert gleichmäßige Verteilung aller Schichttypen
- Verhindert, dass ein Team dauerhaft Nachtschichten hat
- 3-Wochen-Zyklus sorgt für Abwechslung

### Springer-Fairness
- Springer mit niedrigstem Workload wird bevorzugt
- Mindestens ein Springer bleibt verfügbar für Notfälle

## Konfliktauflösung

### Bei Regelverstoß
1. Überspringe Mitarbeiter
2. Versuche nächsten Mitarbeiter (nach Workload sortiert)
3. Falls Team nicht ausreicht: Versuche andere Teams
4. Falls keine Lösung: Protokolliere Warnung (Assignment wird nicht erstellt)

### Bei unzureichenden Mitarbeitern
- Fallback auf Legacy-Algorithmus wenn < 3 Teams vorhanden
- Legacy-Algorithmus verteilt ohne Team-Rotation

## Performance-Optimierungen

- **O(1) Lookups**: HashSet/Dictionary für Datums-Lookups
- **Batch-Queries**: Alle Assignments für 30 Tage auf einmal laden
- **Caching**: Workload-Map einmal pro Tag erstellen
- **Frühe Abbrüche**: Bei offensichtlichen Regelverstößen

## Validierungs-Beispiele

### ✓ Gültige Sequenz
```
Mo: Mitarbeiter A → Früh (Team 1)
Di: Mitarbeiter A → Ruhetag
Mi: Mitarbeiter A → Nacht (Team 1 rotiert zu Nacht in KW2)
Do: Mitarbeiter A → Nacht
Fr: Mitarbeiter A → Nacht
```

### ✗ Ungültige Sequenz
```
Mo: Mitarbeiter A → Spät
Di: Mitarbeiter A → Früh  ❌ Verbotener Übergang (< 11h Ruhe)
```

### ✗ Ungültige Sequenz
```
Mo: Mitarbeiter A → Früh
Di: Mitarbeiter A → Früh  ❌ Gleiche Schicht zweimal hintereinander
```

### ✗ Ungültige Sequenz
```
Mo-Sa: Mitarbeiter A → Nacht (6 Tage)
So: Mitarbeiter A → Nacht  ❌ Zu viele Nachtschichten (> 5)
```

## Konfiguration

### ShiftRules.cs Konstanten
```csharp
MaximumConsecutiveShifts = 6
MaximumConsecutiveNightShifts = 5
MinimumRestHours = 11
MaximumHoursPerWeek = 48
MaximumHoursPerMonth = 192
```

### Mindestbesetzungen
```csharp
WeekdayStaffing:
  FruehMin = 4, SpaetMin = 3, NachtMin = 3

WeekendStaffing:
  MinPerShift = 2
```

## Wartung und Erweiterung

### Neue Regel hinzufügen
1. Konstante in `ShiftRules.cs` definieren
2. Validierung in `ValidateShiftAssignment()` implementieren
3. Tests hinzufügen
4. Dokumentation aktualisieren

### Team-Anzahl ändern
- Aktuell: 3 Teams (fest codiert in Rotation)
- Für andere Anzahl: `GetTeamShiftRotationForWeek()` anpassen
- Rotationsmuster entsprechend erweitern

### Neue Schichttypen
- Keine Code-Änderung nötig (außer ShiftTypeCodes)
- Automatisch in Rotation integriert
- CSS-Klasse für Farbe hinzufügen

## Fehlerbehebung

### "Keine Assignments erstellt"
→ Prüfe: Sind Teams korrekt zugewiesen?
→ Prüfe: Sind genug Mitarbeiter ohne Abwesenheit verfügbar?
→ Prüfe: Existierende fixierte Assignments könnten blockieren

### "Regelverstöße trotz Validierung"
→ Prüfe: Cross-month Boundaries (30-Tage-Lookback aktiv?)
→ Prüfe: Wurden manuelle Assignments ohne Validierung erstellt?

### "Ungleiche Verteilung"
→ Prüfe: Workload-Tracking über ausreichenden Zeitraum
→ Prüfe: Fairness-Service korrekt registriert in DI

## Best Practices

1. **Immer mit force=true neu planen** wenn grundlegende Änderungen
2. **Fixierte Assignments** für Feiertage/Sonderregelungen nutzen
3. **Regelmäßig validieren** dass keine manuellen Verstöße existieren
4. **Teams ausgewogen halten** (je 5 Mitarbeiter)
5. **Springer-Pool** nicht vollständig verplanen
