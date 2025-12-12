# Beispieldaten für Dienstplan System

Dieses Dokument beschreibt, wie Beispieldaten in das Dienstplan-System eingespielt werden können. Es enthält vordefinierte Datensätze für:

- **17 Mitarbeiter** insgesamt
- **3 Teams** mit je 5 Mitarbeitern (15 Mitarbeiter)
- **2 Sonderaufgaben** (Mitarbeiter ohne Team)
- **3-4 Springer** innerhalb der 17 Mitarbeiter

## 📋 Übersicht der Beispieldaten

### Teams (3)
1. **Team Alpha** - Frühschicht-Team
2. **Team Beta** - Spätschicht-Team  
3. **Team Gamma** - Nachtschicht-Team

### Mitarbeiter (17)

#### Team Alpha (5 Mitarbeiter)
- MA001: Max Mustermann - Werkschutz
- MA002: Anna Schmidt - Werkschutz
- MA003: Peter Müller - Brandmeldetechniker (Springer)
- MA004: Lisa Weber - Werkschutz
- MA005: Thomas Wagner - Werkschutz

#### Team Beta (5 Mitarbeiter)
- MA006: Julia Becker - Werkschutz
- MA007: Michael Hoffmann - Werkschutz
- MA008: Sarah Fischer - Brandschutzbeauftragter (Springer)
- MA009: Daniel Richter - Werkschutz
- MA010: Laura Klein - Werkschutz

#### Team Gamma (5 Mitarbeiter)
- MA011: Markus Wolf - Werkschutz
- MA012: Petra Schröder - Werkschutz
- MA013: Stefan Neumann - Werkschutz (Springer)
- MA014: Claudia Braun - Werkschutz
- MA015: Andreas Zimmermann - Werkschutz

#### Sonderaufgaben ohne Team (2 Mitarbeiter)
- MA016: Frank Krüger - Technischer Dienst (Springer)
- MA017: Sabine Hartmann - Koordination

#### Springer (4 von 17 Mitarbeitern)
- MA003: Peter Müller (Team Alpha)
- MA008: Sarah Fischer (Team Beta)
- MA013: Stefan Neumann (Team Gamma)
- MA016: Frank Krüger (ohne Team)

---

## 🔧 Option 1: Vorgefertigte Datenbank nutzen

Die einfachste Methode ist, die vorgefertigte Beispieldatenbank zu verwenden:

### Schritt 1: Beispieldatenbank-Datei erstellen

Führen Sie das mitgelieferte Skript aus:

```bash
# Linux/macOS
cd /path/to/Dienstplan
dotnet run --project src/SampleDataGenerator

# Windows PowerShell
cd C:\path\to\Dienstplan
dotnet run --project src\SampleDataGenerator
```

### Schritt 2: Datenbank verwenden

Die Beispieldatenbank wird als `dienstplan-sample.db` generiert. Kopieren Sie diese Datei:

```bash
# Linux/macOS
cp dienstplan-sample.db dienstplan.db

# Windows PowerShell
Copy-Item dienstplan-sample.db dienstplan.db
```

### Schritt 3: Anwendung starten

```bash
# Linux/macOS/Windows
dotnet run --project src/Dienstplan.Web
```

Öffnen Sie den Browser: `http://localhost:5000`

---

## 🌐 Option 2: API-Aufrufe zur Datenerzeugung

Falls Sie die Daten über die REST API einspielen möchten (z.B. für automatisierte Tests oder Integration), folgen Sie dieser Anleitung.

### Voraussetzungen

1. Anwendung muss gestartet sein: `dotnet run --project src/Dienstplan.Web`
2. Browser öffnen: `http://localhost:5000`
3. Als Administrator anmelden:
   - E-Mail: `admin@fritzwinter.de`
   - Passwort: `Admin123!`

### Windows - PowerShell

Speichern Sie folgendes Skript als `create-sample-data.ps1`:

```powershell
# Beispieldaten für Dienstplan System erstellen
# Autor: Timo Braun
# Datum: 2025-12-12

$baseUrl = "http://localhost:5000/api"
$headers = @{
    "Content-Type" = "application/json"
}

Write-Host "=== Dienstplan Beispieldaten Creator ===" -ForegroundColor Cyan
Write-Host ""

# Funktion für API-Aufrufe mit Fehlerbehandlung
function Invoke-ApiCall {
    param(
        [string]$Method,
        [string]$Endpoint,
        [object]$Body
    )
    
    try {
        $url = "$baseUrl/$Endpoint"
        if ($Body) {
            $jsonBody = $Body | ConvertTo-Json -Depth 10
            $response = Invoke-RestMethod -Uri $url -Method $Method -Headers $headers -Body $jsonBody -SessionVariable session
        } else {
            $response = Invoke-RestMethod -Uri $url -Method $Method -Headers $headers -SessionVariable session
        }
        return $response
    }
    catch {
        Write-Host "Fehler bei $Method $Endpoint : $($_.Exception.Message)" -ForegroundColor Red
        return $null
    }
}

# 1. Authentifizierung
Write-Host "1. Authentifizierung als Administrator..." -ForegroundColor Yellow
$loginData = @{
    email = "admin@fritzwinter.de"
    password = "Admin123!"
    rememberMe = $true
}

$session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
$loginResponse = Invoke-WebRequest -Uri "$baseUrl/auth/login" -Method POST -Headers $headers -Body ($loginData | ConvertTo-Json) -SessionVariable session -UseBasicParsing
Write-Host "✓ Anmeldung erfolgreich" -ForegroundColor Green

# 2. Teams erstellen
Write-Host ""
Write-Host "2. Teams erstellen..." -ForegroundColor Yellow

$teams = @(
    @{ Name = "Team Alpha"; Description = "Frühschicht-Team"; Email = "team-alpha@fritzwinter.de" },
    @{ Name = "Team Beta"; Description = "Spätschicht-Team"; Email = "team-beta@fritzwinter.de" },
    @{ Name = "Team Gamma"; Description = "Nachtschicht-Team"; Email = "team-gamma@fritzwinter.de" }
)

$teamIds = @{}
foreach ($team in $teams) {
    $response = Invoke-WebRequest -Uri "$baseUrl/teams" -Method POST -Headers $headers -Body ($team | ConvertTo-Json) -WebSession $session -UseBasicParsing
    $teamData = $response.Content | ConvertFrom-Json
    $teamIds[$team.Name] = $teamData.id
    Write-Host "  ✓ $($team.Name) erstellt (ID: $($teamData.id))" -ForegroundColor Green
}

# 3. Mitarbeiter erstellen
Write-Host ""
Write-Host "3. Mitarbeiter erstellen..." -ForegroundColor Yellow

$employees = @(
    # Team Alpha (5)
    @{ Vorname = "Max"; Name = "Mustermann"; Personalnummer = "MA001"; Email = "max.mustermann@fritzwinter.de"; Geburtsdatum = "1985-05-15"; Funktion = "Werkschutz"; TeamId = $teamIds["Team Alpha"]; IsSpringer = $false; IsFerienjobber = $false },
    @{ Vorname = "Anna"; Name = "Schmidt"; Personalnummer = "MA002"; Email = "anna.schmidt@fritzwinter.de"; Geburtsdatum = "1990-08-22"; Funktion = "Werkschutz"; TeamId = $teamIds["Team Alpha"]; IsSpringer = $false; IsFerienjobber = $false },
    @{ Vorname = "Peter"; Name = "Müller"; Personalnummer = "MA003"; Email = "peter.mueller@fritzwinter.de"; Geburtsdatum = "1988-03-10"; Funktion = "Brandmeldetechniker"; TeamId = $teamIds["Team Alpha"]; IsSpringer = $true; IsFerienjobber = $false },
    @{ Vorname = "Lisa"; Name = "Weber"; Personalnummer = "MA004"; Email = "lisa.weber@fritzwinter.de"; Geburtsdatum = "1992-11-05"; Funktion = "Werkschutz"; TeamId = $teamIds["Team Alpha"]; IsSpringer = $false; IsFerienjobber = $false },
    @{ Vorname = "Thomas"; Name = "Wagner"; Personalnummer = "MA005"; Email = "thomas.wagner@fritzwinter.de"; Geburtsdatum = "1987-07-18"; Funktion = "Werkschutz"; TeamId = $teamIds["Team Alpha"]; IsSpringer = $false; IsFerienjobber = $false },
    
    # Team Beta (5)
    @{ Vorname = "Julia"; Name = "Becker"; Personalnummer = "MA006"; Email = "julia.becker@fritzwinter.de"; Geburtsdatum = "1991-02-28"; Funktion = "Werkschutz"; TeamId = $teamIds["Team Beta"]; IsSpringer = $false; IsFerienjobber = $false },
    @{ Vorname = "Michael"; Name = "Hoffmann"; Personalnummer = "MA007"; Email = "michael.hoffmann@fritzwinter.de"; Geburtsdatum = "1989-09-14"; Funktion = "Werkschutz"; TeamId = $teamIds["Team Beta"]; IsSpringer = $false; IsFerienjobber = $false },
    @{ Vorname = "Sarah"; Name = "Fischer"; Personalnummer = "MA008"; Email = "sarah.fischer@fritzwinter.de"; Geburtsdatum = "1993-06-07"; Funktion = "Brandschutzbeauftragter"; TeamId = $teamIds["Team Beta"]; IsSpringer = $true; IsFerienjobber = $false },
    @{ Vorname = "Daniel"; Name = "Richter"; Personalnummer = "MA009"; Email = "daniel.richter@fritzwinter.de"; Geburtsdatum = "1986-12-21"; Funktion = "Werkschutz"; TeamId = $teamIds["Team Beta"]; IsSpringer = $false; IsFerienjobber = $false },
    @{ Vorname = "Laura"; Name = "Klein"; Personalnummer = "MA010"; Email = "laura.klein@fritzwinter.de"; Geburtsdatum = "1994-04-16"; Funktion = "Werkschutz"; TeamId = $teamIds["Team Beta"]; IsSpringer = $false; IsFerienjobber = $false },
    
    # Team Gamma (5)
    @{ Vorname = "Markus"; Name = "Wolf"; Personalnummer = "MA011"; Email = "markus.wolf@fritzwinter.de"; Geburtsdatum = "1990-10-09"; Funktion = "Werkschutz"; TeamId = $teamIds["Team Gamma"]; IsSpringer = $false; IsFerienjobber = $false },
    @{ Vorname = "Petra"; Name = "Schröder"; Personalnummer = "MA012"; Email = "petra.schroeder@fritzwinter.de"; Geburtsdatum = "1988-01-25"; Funktion = "Werkschutz"; TeamId = $teamIds["Team Gamma"]; IsSpringer = $false; IsFerienjobber = $false },
    @{ Vorname = "Stefan"; Name = "Neumann"; Personalnummer = "MA013"; Email = "stefan.neumann@fritzwinter.de"; Geburtsdatum = "1992-05-30"; Funktion = "Werkschutz"; TeamId = $teamIds["Team Gamma"]; IsSpringer = $true; IsFerienjobber = $false },
    @{ Vorname = "Claudia"; Name = "Braun"; Personalnummer = "MA014"; Email = "claudia.braun@fritzwinter.de"; Geburtsdatum = "1987-08-12"; Funktion = "Werkschutz"; TeamId = $teamIds["Team Gamma"]; IsSpringer = $false; IsFerienjobber = $false },
    @{ Vorname = "Andreas"; Name = "Zimmermann"; Personalnummer = "MA015"; Email = "andreas.zimmermann@fritzwinter.de"; Geburtsdatum = "1991-03-19"; Funktion = "Werkschutz"; TeamId = $teamIds["Team Gamma"]; IsSpringer = $false; IsFerienjobber = $false },
    
    # Sonderaufgaben ohne Team (2)
    @{ Vorname = "Frank"; Name = "Krüger"; Personalnummer = "MA016"; Email = "frank.krueger@fritzwinter.de"; Geburtsdatum = "1985-11-08"; Funktion = "Technischer Dienst"; TeamId = $null; IsSpringer = $true; IsFerienjobber = $false },
    @{ Vorname = "Sabine"; Name = "Hartmann"; Personalnummer = "MA017"; Email = "sabine.hartmann@fritzwinter.de"; Geburtsdatum = "1989-07-23"; Funktion = "Koordination"; TeamId = $null; IsSpringer = $false; IsFerienjobber = $false }
)

foreach ($employee in $employees) {
    $response = Invoke-WebRequest -Uri "$baseUrl/employees" -Method POST -Headers $headers -Body ($employee | ConvertTo-Json) -WebSession $session -UseBasicParsing
    $empData = $response.Content | ConvertFrom-Json
    $springerText = if ($employee.IsSpringer) { " [SPRINGER]" } else { "" }
    $teamText = if ($employee.TeamId) { "(Team)" } else { "(Sonderaufgabe)" }
    Write-Host "  ✓ $($employee.Personalnummer): $($employee.Vorname) $($employee.Name)$springerText $teamText" -ForegroundColor Green
}

Write-Host ""
Write-Host "=== Fertig! ===" -ForegroundColor Cyan
Write-Host "Es wurden erfolgreich erstellt:" -ForegroundColor White
Write-Host "  • 3 Teams" -ForegroundColor White
Write-Host "  • 17 Mitarbeiter (15 mit Team, 2 Sonderaufgaben)" -ForegroundColor White
Write-Host "  • 4 Springer" -ForegroundColor White
Write-Host ""
Write-Host "Sie können sich jetzt unter http://localhost:5000 anmelden." -ForegroundColor Yellow
```

**Ausführung:**

```powershell
# PowerShell Execution Policy ggf. anpassen
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

# Skript ausführen
.\create-sample-data.ps1
```

### Windows - curl (Command Prompt oder PowerShell)

Alternativ können Sie curl verwenden. Speichern Sie als `create-sample-data.bat`:

```batch
@echo off
echo === Dienstplan Beispieldaten Creator (curl) ===
echo.

set BASE_URL=http://localhost:5000/api

echo 1. Authentifizierung...
curl -c cookies.txt -X POST %BASE_URL%/auth/login ^
  -H "Content-Type: application/json" ^
  -d "{\"email\":\"admin@fritzwinter.de\",\"password\":\"Admin123!\",\"rememberMe\":true}"

echo.
echo 2. Teams erstellen...

curl -b cookies.txt -X POST %BASE_URL%/teams ^
  -H "Content-Type: application/json" ^
  -d "{\"name\":\"Team Alpha\",\"description\":\"Frühschicht-Team\",\"email\":\"team-alpha@fritzwinter.de\"}"

curl -b cookies.txt -X POST %BASE_URL%/teams ^
  -H "Content-Type: application/json" ^
  -d "{\"name\":\"Team Beta\",\"description\":\"Spätschicht-Team\",\"email\":\"team-beta@fritzwinter.de\"}"

curl -b cookies.txt -X POST %BASE_URL%/teams ^
  -H "Content-Type: application/json" ^
  -d "{\"name\":\"Team Gamma\",\"description\":\"Nachtschicht-Team\",\"email\":\"team-gamma@fritzwinter.de\"}"

echo.
echo 3. Mitarbeiter erstellen...
echo Hinweis: Ersetzen Sie TEAM_ID_ALPHA, TEAM_ID_BETA, TEAM_ID_GAMMA mit den tatsächlichen IDs aus Schritt 2

curl -b cookies.txt -X POST %BASE_URL%/employees ^
  -H "Content-Type: application/json" ^
  -d "{\"vorname\":\"Max\",\"name\":\"Mustermann\",\"personalnummer\":\"MA001\",\"email\":\"max.mustermann@fritzwinter.de\",\"geburtsdatum\":\"1985-05-15\",\"funktion\":\"Werkschutz\",\"teamId\":1,\"isSpringer\":false,\"isFerienjobber\":false}"

REM ... weitere Mitarbeiter analog ...

echo.
echo === Fertig! ===
pause
```

### Linux/macOS - Bash Script

Speichern Sie folgendes Skript als `create-sample-data.sh`:

```bash
#!/bin/bash

# Beispieldaten für Dienstplan System erstellen
# Autor: Timo Braun
# Datum: 2025-12-12

BASE_URL="http://localhost:5000/api"
COOKIE_FILE="cookies.txt"

echo "=== Dienstplan Beispieldaten Creator ==="
echo ""

# Funktion für API-Aufrufe
api_call() {
    local method=$1
    local endpoint=$2
    local data=$3
    
    if [ -n "$data" ]; then
        curl -s -b $COOKIE_FILE -c $COOKIE_FILE -X $method "$BASE_URL/$endpoint" \
            -H "Content-Type: application/json" \
            -d "$data"
    else
        curl -s -b $COOKIE_FILE -c $COOKIE_FILE -X $method "$BASE_URL/$endpoint" \
            -H "Content-Type: application/json"
    fi
}

# 1. Authentifizierung
echo "1. Authentifizierung als Administrator..."
api_call POST "auth/login" '{
    "email": "admin@fritzwinter.de",
    "password": "Admin123!",
    "rememberMe": true
}' > /dev/null
echo "✓ Anmeldung erfolgreich"

# 2. Teams erstellen
echo ""
echo "2. Teams erstellen..."

team_alpha_response=$(api_call POST "teams" '{
    "name": "Team Alpha",
    "description": "Frühschicht-Team",
    "email": "team-alpha@fritzwinter.de"
}')
team_alpha_id=$(echo $team_alpha_response | grep -o '"id":[0-9]*' | grep -o '[0-9]*')
echo "  ✓ Team Alpha erstellt (ID: $team_alpha_id)"

team_beta_response=$(api_call POST "teams" '{
    "name": "Team Beta",
    "description": "Spätschicht-Team",
    "email": "team-beta@fritzwinter.de"
}')
team_beta_id=$(echo $team_beta_response | grep -o '"id":[0-9]*' | grep -o '[0-9]*')
echo "  ✓ Team Beta erstellt (ID: $team_beta_id)"

team_gamma_response=$(api_call POST "teams" '{
    "name": "Team Gamma",
    "description": "Nachtschicht-Team",
    "email": "team-gamma@fritzwinter.de"
}')
team_gamma_id=$(echo $team_gamma_response | grep -o '"id":[0-9]*' | grep -o '[0-9]*')
echo "  ✓ Team Gamma erstellt (ID: $team_gamma_id)"

# 3. Mitarbeiter erstellen
echo ""
echo "3. Mitarbeiter erstellen..."

# Team Alpha (5)
api_call POST "employees" "{
    \"vorname\": \"Max\",
    \"name\": \"Mustermann\",
    \"personalnummer\": \"MA001\",
    \"email\": \"max.mustermann@fritzwinter.de\",
    \"geburtsdatum\": \"1985-05-15\",
    \"funktion\": \"Werkschutz\",
    \"teamId\": $team_alpha_id,
    \"isSpringer\": false,
    \"isFerienjobber\": false
}" > /dev/null
echo "  ✓ MA001: Max Mustermann (Team Alpha)"

api_call POST "employees" "{
    \"vorname\": \"Anna\",
    \"name\": \"Schmidt\",
    \"personalnummer\": \"MA002\",
    \"email\": \"anna.schmidt@fritzwinter.de\",
    \"geburtsdatum\": \"1990-08-22\",
    \"funktion\": \"Werkschutz\",
    \"teamId\": $team_alpha_id,
    \"isSpringer\": false,
    \"isFerienjobber\": false
}" > /dev/null
echo "  ✓ MA002: Anna Schmidt (Team Alpha)"

api_call POST "employees" "{
    \"vorname\": \"Peter\",
    \"name\": \"Müller\",
    \"personalnummer\": \"MA003\",
    \"email\": \"peter.mueller@fritzwinter.de\",
    \"geburtsdatum\": \"1988-03-10\",
    \"funktion\": \"Brandmeldetechniker\",
    \"teamId\": $team_alpha_id,
    \"isSpringer\": true,
    \"isFerienjobber\": false
}" > /dev/null
echo "  ✓ MA003: Peter Müller [SPRINGER] (Team Alpha)"

api_call POST "employees" "{
    \"vorname\": \"Lisa\",
    \"name\": \"Weber\",
    \"personalnummer\": \"MA004\",
    \"email\": \"lisa.weber@fritzwinter.de\",
    \"geburtsdatum\": \"1992-11-05\",
    \"funktion\": \"Werkschutz\",
    \"teamId\": $team_alpha_id,
    \"isSpringer\": false,
    \"isFerienjobber\": false
}" > /dev/null
echo "  ✓ MA004: Lisa Weber (Team Alpha)"

api_call POST "employees" "{
    \"vorname\": \"Thomas\",
    \"name\": \"Wagner\",
    \"personalnummer\": \"MA005\",
    \"email\": \"thomas.wagner@fritzwinter.de\",
    \"geburtsdatum\": \"1987-07-18\",
    \"funktion\": \"Werkschutz\",
    \"teamId\": $team_alpha_id,
    \"isSpringer\": false,
    \"isFerienjobber\": false
}" > /dev/null
echo "  ✓ MA005: Thomas Wagner (Team Alpha)"

# Team Beta (5)
api_call POST "employees" "{
    \"vorname\": \"Julia\",
    \"name\": \"Becker\",
    \"personalnummer\": \"MA006\",
    \"email\": \"julia.becker@fritzwinter.de\",
    \"geburtsdatum\": \"1991-02-28\",
    \"funktion\": \"Werkschutz\",
    \"teamId\": $team_beta_id,
    \"isSpringer\": false,
    \"isFerienjobber\": false
}" > /dev/null
echo "  ✓ MA006: Julia Becker (Team Beta)"

api_call POST "employees" "{
    \"vorname\": \"Michael\",
    \"name\": \"Hoffmann\",
    \"personalnummer\": \"MA007\",
    \"email\": \"michael.hoffmann@fritzwinter.de\",
    \"geburtsdatum\": \"1989-09-14\",
    \"funktion\": \"Werkschutz\",
    \"teamId\": $team_beta_id,
    \"isSpringer\": false,
    \"isFerienjobber\": false
}" > /dev/null
echo "  ✓ MA007: Michael Hoffmann (Team Beta)"

api_call POST "employees" "{
    \"vorname\": \"Sarah\",
    \"name\": \"Fischer\",
    \"personalnummer\": \"MA008\",
    \"email\": \"sarah.fischer@fritzwinter.de\",
    \"geburtsdatum\": \"1993-06-07\",
    \"funktion\": \"Brandschutzbeauftragter\",
    \"teamId\": $team_beta_id,
    \"isSpringer\": true,
    \"isFerienjobber\": false
}" > /dev/null
echo "  ✓ MA008: Sarah Fischer [SPRINGER] (Team Beta)"

api_call POST "employees" "{
    \"vorname\": \"Daniel\",
    \"name\": \"Richter\",
    \"personalnummer\": \"MA009\",
    \"email\": \"daniel.richter@fritzwinter.de\",
    \"geburtsdatum\": \"1986-12-21\",
    \"funktion\": \"Werkschutz\",
    \"teamId\": $team_beta_id,
    \"isSpringer\": false,
    \"isFerienjobber\": false
}" > /dev/null
echo "  ✓ MA009: Daniel Richter (Team Beta)"

api_call POST "employees" "{
    \"vorname\": \"Laura\",
    \"name\": \"Klein\",
    \"personalnummer\": \"MA010\",
    \"email\": \"laura.klein@fritzwinter.de\",
    \"geburtsdatum\": \"1994-04-16\",
    \"funktion\": \"Werkschutz\",
    \"teamId\": $team_beta_id,
    \"isSpringer\": false,
    \"isFerienjobber\": false
}" > /dev/null
echo "  ✓ MA010: Laura Klein (Team Beta)"

# Team Gamma (5)
api_call POST "employees" "{
    \"vorname\": \"Markus\",
    \"name\": \"Wolf\",
    \"personalnummer\": \"MA011\",
    \"email\": \"markus.wolf@fritzwinter.de\",
    \"geburtsdatum\": \"1990-10-09\",
    \"funktion\": \"Werkschutz\",
    \"teamId\": $team_gamma_id,
    \"isSpringer\": false,
    \"isFerienjobber\": false
}" > /dev/null
echo "  ✓ MA011: Markus Wolf (Team Gamma)"

api_call POST "employees" "{
    \"vorname\": \"Petra\",
    \"name\": \"Schröder\",
    \"personalnummer\": \"MA012\",
    \"email\": \"petra.schroeder@fritzwinter.de\",
    \"geburtsdatum\": \"1988-01-25\",
    \"funktion\": \"Werkschutz\",
    \"teamId\": $team_gamma_id,
    \"isSpringer\": false,
    \"isFerienjobber\": false
}" > /dev/null
echo "  ✓ MA012: Petra Schröder (Team Gamma)"

api_call POST "employees" "{
    \"vorname\": \"Stefan\",
    \"name\": \"Neumann\",
    \"personalnummer\": \"MA013\",
    \"email\": \"stefan.neumann@fritzwinter.de\",
    \"geburtsdatum\": \"1992-05-30\",
    \"funktion\": \"Werkschutz\",
    \"teamId\": $team_gamma_id,
    \"isSpringer\": true,
    \"isFerienjobber\": false
}" > /dev/null
echo "  ✓ MA013: Stefan Neumann [SPRINGER] (Team Gamma)"

api_call POST "employees" "{
    \"vorname\": \"Claudia\",
    \"name\": \"Braun\",
    \"personalnummer\": \"MA014\",
    \"email\": \"claudia.braun@fritzwinter.de\",
    \"geburtsdatum\": \"1987-08-12\",
    \"funktion\": \"Werkschutz\",
    \"teamId\": $team_gamma_id,
    \"isSpringer\": false,
    \"isFerienjobber\": false
}" > /dev/null
echo "  ✓ MA014: Claudia Braun (Team Gamma)"

api_call POST "employees" "{
    \"vorname\": \"Andreas\",
    \"name\": \"Zimmermann\",
    \"personalnummer\": \"MA015\",
    \"email\": \"andreas.zimmermann@fritzwinter.de\",
    \"geburtsdatum\": \"1991-03-19\",
    \"funktion\": \"Werkschutz\",
    \"teamId\": $team_gamma_id,
    \"isSpringer\": false,
    \"isFerienjobber\": false
}" > /dev/null
echo "  ✓ MA015: Andreas Zimmermann (Team Gamma)"

# Sonderaufgaben ohne Team (2)
api_call POST "employees" "{
    \"vorname\": \"Frank\",
    \"name\": \"Krüger\",
    \"personalnummer\": \"MA016\",
    \"email\": \"frank.krueger@fritzwinter.de\",
    \"geburtsdatum\": \"1985-11-08\",
    \"funktion\": \"Technischer Dienst\",
    \"teamId\": null,
    \"isSpringer\": true,
    \"isFerienjobber\": false
}" > /dev/null
echo "  ✓ MA016: Frank Krüger [SPRINGER] (Sonderaufgabe)"

api_call POST "employees" "{
    \"vorname\": \"Sabine\",
    \"name\": \"Hartmann\",
    \"personalnummer\": \"MA017\",
    \"email\": \"sabine.hartmann@fritzwinter.de\",
    \"geburtsdatum\": \"1989-07-23\",
    \"funktion\": \"Koordination\",
    \"teamId\": null,
    \"isSpringer\": false,
    \"isFerienjobber\": false
}" > /dev/null
echo "  ✓ MA017: Sabine Hartmann (Sonderaufgabe)"

# Aufräumen
rm -f $COOKIE_FILE

echo ""
echo "=== Fertig! ==="
echo "Es wurden erfolgreich erstellt:"
echo "  • 3 Teams"
echo "  • 17 Mitarbeiter (15 mit Team, 2 Sonderaufgaben)"
echo "  • 4 Springer"
echo ""
echo "Sie können sich jetzt unter http://localhost:5000 anmelden."
```

**Ausführung:**

```bash
# Ausführbar machen
chmod +x create-sample-data.sh

# Ausführen
./create-sample-data.sh
```

---

## 📊 Datenübersicht

Nach erfolgreicher Ausführung haben Sie folgende Daten im System:

### Zusammenfassung
- **Teams**: 3 (Alpha, Beta, Gamma)
- **Mitarbeiter gesamt**: 17
  - Mit Team: 15 (je 5 pro Team)
  - Sonderaufgaben: 2 (ohne Team)
  - Springer: 4 (verteilt über alle Kategorien)

### Anmeldedaten
- **Administrator**:
  - E-Mail: `admin@fritzwinter.de`
  - Passwort: `Admin123!`

### Nächste Schritte
1. Melden Sie sich als Administrator an
2. Navigieren Sie zu "Mitarbeiter" um alle 17 Mitarbeiter zu sehen
3. Navigieren Sie zu "Dienstplan" und klicken Sie auf "Automatisch planen" um Schichten zu generieren
4. Prüfen Sie die Springer-Liste unter "Mitarbeiter" → Filter "Nur Springer"

---

## 🔧 Fehlerbehebung

### Problem: API gibt 401 Unauthorized zurück
**Lösung**: Stellen Sie sicher, dass Sie angemeldet sind. Die Cookie-Datei muss korrekt gespeichert werden.

### Problem: Team IDs sind nicht bekannt
**Lösung**: 
1. Rufen Sie `GET http://localhost:5000/api/teams` auf um alle Teams und ihre IDs zu sehen
2. Verwenden Sie die korrekten IDs beim Erstellen der Mitarbeiter

### Problem: Personalnummer bereits vergeben
**Lösung**: Jede Personalnummer muss eindeutig sein. Löschen Sie ggf. existierende Mitarbeiter oder verwenden Sie andere Nummern.

### Problem: Skript schlägt fehl bei Windows Execution Policy
**Lösung**: 
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

---

## 📝 Zusätzliche Hinweise

- Alle E-Mail-Adressen verwenden die Domain `@fritzwinter.de`
- Alle Geburtsdaten liegen zwischen 1985 und 1994
- Die Springer sind gleichmäßig über die Teams verteilt plus einer ohne Team
- Sonderaufgaben (ohne Team) sind für spezielle Funktionen vorgesehen
- Nach dem Import können Sie weitere Mitarbeiter über die Web-Oberfläche oder API hinzufügen

---

**Autor**: Timo Braun  
**Version**: 1.0  
**Datum**: 2025-12-12
