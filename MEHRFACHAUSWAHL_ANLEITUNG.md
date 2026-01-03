# Mehrfachauswahl für Schichtbearbeitung - Benutzerhandbuch

## Überblick

Die neue Mehrfachauswahl-Funktion ermöglicht es Administratoren und Disponenten, mehrere Schichten gleichzeitig zu bearbeiten. Dies spart Zeit und reduziert Fehler bei Massenänderungen.

## Funktionen

### 1. Mehrfachauswahl aktivieren

1. Navigieren Sie zur **Dienstplan**-Ansicht
2. Klicken Sie auf die Schaltfläche **☑ Mehrfachauswahl** in der Steuerleiste
3. Die Schaltfläche ändert sich zu **✓ Mehrfachauswahl aktiv** und leuchtet blau
4. Zusätzliche Schaltflächen erscheinen:
   - **✏ Auswahl bearbeiten** - Öffnet den Dialog für Massenbearbeitung
   - **✖ Auswahl löschen** - Löscht alle Auswahlen

### 2. Schichten auswählen

Im Mehrfachauswahl-Modus:
- Klicken Sie auf einzelne Schicht-Badges (F, S, N, etc.), um sie auszuwählen
- Ausgewählte Schichten werden mit einem blauen Rahmen und Hintergrund hervorgehoben
- Ein Zähler zeigt die Anzahl der ausgewählten Schichten an: "X Schichten ausgewählt"
- Klicken Sie erneut auf eine Schicht, um die Auswahl aufzuheben

**Hinweis:** Im Mehrfachauswahl-Modus öffnet das Klicken auf eine Schicht NICHT den Bearbeitungsdialog, sondern wählt sie aus.

### 3. Ausgewählte Schichten bearbeiten

1. Wählen Sie die gewünschten Schichten aus (mindestens eine)
2. Klicken Sie auf **✏ Auswahl bearbeiten**
3. Der Dialog "Mehrere Schichten bearbeiten" öffnet sich und zeigt:
   - Die Anzahl der ausgewählten Schichten
   - Eine Liste aller ausgewählten Schichten (Mitarbeiter, Datum, Schichttyp)
   - Bearbeitungsoptionen

### 4. Bearbeitungsoptionen

Sie können eine oder mehrere der folgenden Änderungen vornehmen:

#### Mitarbeiter ändern
- Wählen Sie einen neuen Mitarbeiter aus der Dropdown-Liste
- Leer lassen, wenn der Mitarbeiter nicht geändert werden soll
- **Anwendungsfall:** Alle ausgewählten Schichten einem anderen Mitarbeiter zuweisen

#### Schichttyp ändern
- Wählen Sie einen neuen Schichttyp (F, S, N, ZD, etc.)
- Leer lassen, wenn der Schichttyp nicht geändert werden soll
- **Anwendungsfall:** Alle Früh-Schichten zu Spät-Schichten ändern

#### Feste Schichten markieren
- Aktivieren Sie das Kontrollkästchen "Alle als feste Schichten markieren"
- Feste Schichten werden bei automatischer Planung nicht geändert
- **Anwendungsfall:** Manuell geplante Schichten vor automatischen Änderungen schützen

#### Notizen hinzufügen
- Geben Sie einen Text ein, der allen ausgewählten Schichten hinzugefügt wird
- Bestehende Notizen werden nicht überschrieben, sondern erweitert
- **Anwendungsfall:** Dokumentation der Massenänderung (z.B. "Umplanung wegen Krankheitswelle")

### 5. Änderungen speichern

1. Überprüfen Sie die vorgenommenen Änderungen
2. Klicken Sie auf **Alle ausgewählten Schichten aktualisieren**
3. Bestätigen Sie die Aktion im Bestätigungsdialog
4. Bei Erfolg werden alle Schichten aktualisiert und der Dienstplan neu geladen
5. Die Mehrfachauswahl wird automatisch deaktiviert

### 6. Mehrfachauswahl beenden

- Klicken Sie erneut auf **✓ Mehrfachauswahl aktiv**, um den Modus zu deaktivieren
- Oder klicken Sie auf **✖ Auswahl löschen**, um nur die Auswahl zu löschen
- Der normale Bearbeitungsmodus wird wiederhergestellt

## Beispiel-Workflows

### Workflow 1: Mehrere Schichten einem anderen Mitarbeiter zuweisen

1. Aktivieren Sie die Mehrfachauswahl
2. Wählen Sie alle betroffenen Schichten aus
3. Klicken Sie auf "Auswahl bearbeiten"
4. Wählen Sie den neuen Mitarbeiter aus der Dropdown-Liste
5. Speichern Sie die Änderungen

### Workflow 2: Alle Schichten einer Woche als fest markieren

1. Aktivieren Sie die Mehrfachauswahl
2. Wählen Sie alle Schichten der Woche aus
3. Klicken Sie auf "Auswahl bearbeiten"
4. Aktivieren Sie "Alle als feste Schichten markieren"
5. Optional: Fügen Sie eine Notiz hinzu (z.B. "Woche vor Feiertag - nicht ändern")
6. Speichern Sie die Änderungen

### Workflow 3: Schichttyp für mehrere Tage ändern

1. Aktivieren Sie die Mehrfachauswahl
2. Wählen Sie die zu ändernden Schichten aus
3. Klicken Sie auf "Auswahl bearbeiten"
4. Wählen Sie den neuen Schichttyp (z.B. von F zu S)
5. Speichern Sie die Änderungen

## Berechtigungen

- **Administrator:** Vollzugriff auf alle Mehrfachauswahl-Funktionen
- **Disponent:** Vollzugriff auf alle Mehrfachauswahl-Funktionen
- **Mitarbeiter:** Kein Zugriff auf Mehrfachauswahl (nur Lesezugriff)

## Technische Hinweise

- Alle Änderungen werden in der Audit-Log protokolliert
- Die Validierung erfolgt serverseitig
- Bei Fehlern wird eine entsprechende Warnung angezeigt
- Änderungen sind irreversibel (außer durch manuelle Rückgängig-Machung)

## Tipps

- **Visuelle Überprüfung:** Überprüfen Sie die Liste der ausgewählten Schichten im Dialog vor dem Speichern
- **Schrittweise vorgehen:** Bei großen Änderungen ist es ratsam, kleinere Gruppen zu bearbeiten
- **Notizen nutzen:** Dokumentieren Sie Massenänderungen immer mit einer Notiz
- **Feste Schichten:** Nutzen Sie feste Schichten, um wichtige manuelle Planungen zu schützen

## Fehlerbehebung

**Problem:** Schichten lassen sich nicht auswählen
- **Lösung:** Stellen Sie sicher, dass der Mehrfachauswahl-Modus aktiviert ist (blauer Button)
- **Lösung:** Überprüfen Sie, ob Sie als Administrator oder Disponent angemeldet sind

**Problem:** "Auswahl bearbeiten" ist nicht verfügbar
- **Lösung:** Wählen Sie mindestens eine Schicht aus

**Problem:** Änderungen werden nicht gespeichert
- **Lösung:** Überprüfen Sie die Fehlermeldung - möglicherweise verletzt die Änderung Validierungsregeln
- **Lösung:** Stellen Sie sicher, dass Sie mindestens eine Änderung vorgenommen haben

## Support

Bei weiteren Fragen oder Problemen wenden Sie sich an den Systemadministrator.
