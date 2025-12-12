# Sample Data Generator für Dienstplan

Dieses Tool generiert eine vorbefüllte SQLite-Datenbank mit Beispieldaten für Entwicklungs- und Testzwecke.

## 📋 Generierte Daten

Die Beispieldatenbank enthält:

- **3 Teams**: Team Alpha, Team Beta, Team Gamma
- **17 Mitarbeiter**:
  - 15 Mitarbeiter mit Teamzuordnung (je 5 pro Team)
  - 2 Mitarbeiter für Sonderaufgaben (ohne Team)
  - 4 Springer (verteilt über Teams und Sonderaufgaben)
- **Administrator-Benutzer**: admin@fritzwinter.de / Admin123!
- **Benutzerrollen**: Admin, Disponent, Mitarbeiter

## 🚀 Verwendung

### 1. Generator ausführen

```bash
# Im Hauptverzeichnis des Projekts
cd /path/to/Dienstplan

# Generator kompilieren und ausführen
dotnet run --project src/SampleDataGenerator
```

### 2. Datenbank verwenden

Nach erfolgreicher Ausführung finden Sie die Datei `dienstplan-sample.db` im Hauptverzeichnis.

```bash
# Datenbank in die Anwendung kopieren
cp dienstplan-sample.db dienstplan.db

# Oder direkt umbenennen
mv dienstplan-sample.db dienstplan.db
```

### 3. Anwendung starten

```bash
dotnet run --project src/Dienstplan.Web
```

Öffnen Sie den Browser: `http://localhost:5000`

**Anmeldedaten**:
- E-Mail: `admin@fritzwinter.de`
- Passwort: `Admin123!`

## 📊 Mitarbeiterübersicht

### Team Alpha (5 Mitarbeiter)
- MA001: Max Mustermann (Werkschutz)
- MA002: Anna Schmidt (Werkschutz)
- MA003: Peter Müller (Brandmeldetechniker) **[SPRINGER]**
- MA004: Lisa Weber (Werkschutz)
- MA005: Thomas Wagner (Werkschutz)

### Team Beta (5 Mitarbeiter)
- MA006: Julia Becker (Werkschutz)
- MA007: Michael Hoffmann (Werkschutz)
- MA008: Sarah Fischer (Brandschutzbeauftragter) **[SPRINGER]**
- MA009: Daniel Richter (Werkschutz)
- MA010: Laura Klein (Werkschutz)

### Team Gamma (5 Mitarbeiter)
- MA011: Markus Wolf (Werkschutz)
- MA012: Petra Schröder (Werkschutz)
- MA013: Stefan Neumann (Werkschutz) **[SPRINGER]**
- MA014: Claudia Braun (Werkschutz)
- MA015: Andreas Zimmermann (Werkschutz)

### Sonderaufgaben (2 Mitarbeiter ohne Team)
- MA016: Frank Krüger (Technischer Dienst) **[SPRINGER]**
- MA017: Sabine Hartmann (Koordination)

## 🔧 Anpassung

Um die generierten Daten anzupassen, bearbeiten Sie die Datei `Program.cs` und ändern Sie die Mitarbeiterdaten, Teams oder andere Einstellungen nach Bedarf.

## 🧪 Verwendungszweck

Diese Beispieldatenbank ist ideal für:
- Lokale Entwicklung
- Funktionale Tests
- Screenshots und Dokumentation
- Schulungen und Demos

**Hinweis**: Verwenden Sie diese Datenbank NICHT in Produktionsumgebungen!
