#!/bin/bash

# Script zur Generierung einer Beispieldatenbank für Dienstplan
# Generiert eine SQLite-Datenbank mit 17 Mitarbeitern, 3 Teams und 4 Springern

echo "=== Dienstplan Beispieldatenbank Generator ==="
echo ""

# Prüfen ob im richtigen Verzeichnis
if [ ! -f "Dienstplan.sln" ]; then
    echo "Fehler: Dieses Skript muss im Hauptverzeichnis des Dienstplan-Projekts ausgeführt werden."
    exit 1
fi

# Generator ausführen
echo "Generiere Beispieldatenbank..."
dotnet run --project src/SampleDataGenerator

if [ $? -eq 0 ]; then
    echo ""
    echo "=== Erfolgreich! ==="
    echo ""
    echo "Die Beispieldatenbank wurde erstellt: dienstplan-sample.db"
    echo ""
    echo "Um sie zu verwenden, führen Sie aus:"
    echo "  cp dienstplan-sample.db dienstplan.db"
    echo ""
    echo "Oder:"
    echo "  mv dienstplan-sample.db dienstplan.db"
    echo ""
    echo "Anmeldedaten:"
    echo "  E-Mail: admin@fritzwinter.de"
    echo "  Passwort: Admin123!"
else
    echo ""
    echo "Fehler beim Generieren der Datenbank."
    exit 1
fi
