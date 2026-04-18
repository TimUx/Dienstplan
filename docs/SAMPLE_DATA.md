# Beispieldaten für Dienstplan System

Dieses Dokument beschreibt, wie Beispieldaten im Dienstplan-System (Python-Version) verwendet werden können.

## 📋 Übersicht der Beispieldaten

Das System kann automatisch Beispieldaten generieren mit:

- **17 Mitarbeiter** insgesamt
- **3 Teams** (Alpha, Beta, Gamma)
- **15 Techniker** (je 5 pro Team)
- **2 qualifizierte Mitarbeiter**: BMT (Brandmeldetechniker) und BSB (Brandschutzbeauftragter)
- **Beispiel-Abwesenheiten**

### Teams (3)
1. **Team Alpha** - 5 Mitarbeiter
2. **Team Beta** - 5 Mitarbeiter  
3. **Team Gamma** - 5 Mitarbeiter

### Techniker (alle Mitarbeiter)
- Robert Franke
- Maria Lange
- Thomas Zimmermann
- Katharina Krüger

---

## 🔧 Beispieldaten generieren

### Empfohlener Ablauf für aktuelle Doku-Screenshots

```bash
python main.py init-db --db /tmp/dienstplan_docs.db --with-sample-data
python main.py plan --start-date 2026-03-01 --end-date 2026-03-31 --db /tmp/dienstplan_docs.db --time-limit 90
python main.py serve --db /tmp/dienstplan_docs.db --host 127.0.0.1 --port 5000
```

Damit stehen Teams, Mitarbeiter, Abwesenheiten und geplante Schichten bereit, um alle UI-Screenshots mit realistischen Daten zu befüllen.

### Option 1: Automatische Generierung mit CLI

Der einfachste Weg ist die Verwendung des integrierten Sample-Data-Generators:

```bash
# Schichtplanung mit automatisch generierten Beispieldaten
python main.py plan \
  --start-date 2025-01-06 \
  --end-date 2025-01-31 \
  --sample-data \
  --time-limit 120
```

Dies erstellt automatisch:
- 17 Mitarbeiter mit Namen, Personalnummern und Qualifikationen
- 3 Teams mit je 5 Mitarbeitern
- 15 Techniker (je 5 pro Team)
- Qualifikationen (BMT/BSB)
- Geplante Schichten für den angegebenen Zeitraum

**Hinweis:** Die Datenbank wird nur temporär im Speicher erstellt. Sie wird nicht als Datei gespeichert, wenn `--sample-data` verwendet wird.

### Option 2: Web-Server mit Sample-Daten starten

Für Tests und Entwicklung können Sie direkt mit dem generierten Datenbank arbeiten:

```bash
# 1. Beispieldaten generieren und Schichten planen
python main.py plan \
  --start-date 2025-01-01 \
  --end-date 2025-01-31 \
  --sample-data

# 2. Web-Server starten
python main.py serve
```

Öffnen Sie dann den Browser: `http://localhost:5000`

---

## 🌐 API-Aufrufe zur Datenerzeugung

Falls Sie die Daten manuell über die REST API einspielen möchten:

### Voraussetzungen

1. Anwendung starten: `python main.py serve`
2. Browser öffnen: `http://localhost:5000`

### Teams erstellen

```bash
# Team Alpha
curl -X POST http://localhost:5000/api/teams \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Team Alpha",
    "description": "Frühschicht-Team"
  }'

# Team Beta
curl -X POST http://localhost:5000/api/teams \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Team Beta",
    "description": "Spätschicht-Team"
  }'

# Team Gamma
curl -X POST http://localhost:5000/api/teams \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Team Gamma",
    "description": "Nachtschicht-Team"
  }'
```

### Mitarbeiter erstellen

```bash
# Mitarbeiter in Team Alpha
curl -X POST http://localhost:5000/api/employees \
  -H "Content-Type: application/json" \
  -d '{
    "vorname": "Max",
    "name": "Müller",
    "personalnummer": "MA001",
    
    "teamId": 1,
    "isBmt": false,
    "isBsb": false
  }'

# Mitarbeiter mit BMT-Qualifikation
curl -X POST http://localhost:5000/api/employees \
  -H "Content-Type: application/json" \
  -d '{
    "vorname": "Robert",
    "name": "Franke",
    "personalnummer": "MA016",
    
    "teamId": null,
    "isBmt": true,
    "isBsb": false
  }'

# Mitarbeiter mit BSB-Qualifikation
curl -X POST http://localhost:5000/api/employees \
  -H "Content-Type: application/json" \
  -d '{
    "vorname": "Maria",
    "name": "Lange",
    "personalnummer": "MA017",
    
    "teamId": null,
    "isBmt": false,
    "isBsb": true
  }'
```

### Abwesenheiten erstellen

```bash
# Urlaub
curl -X POST http://localhost:5000/api/absences \
  -H "Content-Type: application/json" \
  -d '{
    "employeeId": 1,
    "type": "Urlaub",
    "startDate": "2025-02-10",
    "endDate": "2025-02-20",
    "notes": "Winterurlaub"
  }'

# Krankheit
curl -X POST http://localhost:5000/api/absences \
  -H "Content-Type: application/json" \
  -d '{
    "employeeId": 2,
    "type": "Krank",
    "startDate": "2025-01-15",
    "endDate": "2025-01-17",
    "notes": "Grippe"
  }'
```

### Automatische Schichtplanung ausführen

```bash
curl -X POST "http://localhost:5000/api/shifts/plan?startDate=2025-01-01&endDate=2025-01-31&force=false"
```

---

## 🔍 Beispieldaten überprüfen

### Alle Mitarbeiter abrufen
```bash
curl http://localhost:5000/api/employees | python -m json.tool
```

### Alle Teams abrufen
```bash
curl http://localhost:5000/api/teams | python -m json.tool
```

### Dienstplan für Zeitraum abrufen
```bash
curl "http://localhost:5000/api/shifts/schedule?startDate=2025-01-01&view=month" | python -m json.tool
```

### Statistiken abrufen
```bash
curl "http://localhost:5000/api/statistics/dashboard?startDate=2025-01-01&endDate=2025-01-31" | python -m json.tool
```

---

## 📝 Beispiel-Skript für vollständige Datenerfassung

Hier ein vollständiges Bash-Skript zum Einspielen von Beispieldaten:

```bash
#!/bin/bash

API_BASE="http://localhost:5000/api"

echo "Creating teams..."
# Teams erstellen und IDs speichern
TEAM_ALPHA=$(curl -s -X POST $API_BASE/teams \
  -H "Content-Type: application/json" \
  -d '{"name":"Team Alpha","description":"Frühschicht-Team"}' | jq -r '.id')

TEAM_BETA=$(curl -s -X POST $API_BASE/teams \
  -H "Content-Type: application/json" \
  -d '{"name":"Team Beta","description":"Spätschicht-Team"}' | jq -r '.id')

TEAM_GAMMA=$(curl -s -X POST $API_BASE/teams \
  -H "Content-Type: application/json" \
  -d '{"name":"Team Gamma","description":"Nachtschicht-Team"}' | jq -r '.id')

echo "Teams created: Alpha=$TEAM_ALPHA, Beta=$TEAM_BETA, Gamma=$TEAM_GAMMA"

echo "Creating employees..."
# Mitarbeiter für Team Alpha
for i in {1..5}; do
  curl -s -X POST $API_BASE/employees \
    -H "Content-Type: application/json" \
    -d "{\"vorname\":\"Mitarbeiter\",\"name\":\"Alpha$i\",\"personalnummer\":\"MA00$i\",\"\"teamId\":$TEAM_ALPHA}" > /dev/null
done

# Mitarbeiter für Team Beta
for i in {6..10}; do
  curl -s -X POST $API_BASE/employees \
    -H "Content-Type: application/json" \
    -d "{\"vorname\":\"Mitarbeiter\",\"name\":\"Beta$i\",\"personalnummer\":\"MA0$i\",\"\"teamId\":$TEAM_BETA}" > /dev/null
done

# Mitarbeiter für Team Gamma
for i in {11..15}; do
  curl -s -X POST $API_BASE/employees \
    -H "Content-Type: application/json" \
    -d "{\"vorname\":\"Mitarbeiter\",\"name\":\"Gamma$i\",\"personalnummer\":\"MA0$i\",\"\"teamId\":$TEAM_GAMMA}" > /dev/null
done

# Reguläre Mitarbeiter (Beispiel)
curl -s -X POST $API_BASE/employees \
  -H "Content-Type: application/json" \
  -d '{"vorname":"Robert","name":"Franke","personalnummer":"MA016","isBmt":true}' > /dev/null

curl -s -X POST $API_BASE/employees \
  -H "Content-Type: application/json" \
  -d '{"vorname":"Maria","name":"Lange","personalnummer":"MA017","isBsb":true}' > /dev/null

echo "Employees created."

echo "Creating sample absences..."
curl -s -X POST $API_BASE/absences \
  -H "Content-Type: application/json" \
  -d '{"employeeId":1,"type":"Urlaub","startDate":"2025-02-10","endDate":"2025-02-14"}' > /dev/null

echo "Running automatic shift planning..."
curl -s -X POST "$API_BASE/shifts/plan?startDate=2025-01-01&endDate=2025-01-31"

echo "Done! Sample data created successfully."
```

Speichern Sie dies als `create-sample-data.sh` und führen Sie es aus:

```bash
chmod +x create-sample-data.sh
./create-sample-data.sh
```

---

## 💡 Tipps

1. **Datenbank zurücksetzen**: Löschen Sie einfach die `dienstplan.db` Datei und starten Sie neu
2. **Mehr Mitarbeiter**: Passen Sie die Skripte an, um mehr Mitarbeiter zu erstellen
3. **Verschiedene Zeiträume**: Ändern Sie Start- und Enddatum in den API-Aufrufen
4. **Sample-Data-Flag**: Verwenden Sie `--sample-data` für schnelle Tests ohne Datenbankdatei

---

**Version 2.1 - Python Edition**

© 2025 Fritz Winter Eisengießerei GmbH & Co. KG
