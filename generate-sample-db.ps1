# Script zur Generierung einer Beispieldatenbank für Dienstplan
# Generiert eine SQLite-Datenbank mit 17 Mitarbeitern, 3 Teams und 4 Springern

Write-Host "=== Dienstplan Beispieldatenbank Generator ===" -ForegroundColor Cyan
Write-Host ""

# Prüfen ob im richtigen Verzeichnis
if (-Not (Test-Path "Dienstplan.sln")) {
    Write-Host "Fehler: Dieses Skript muss im Hauptverzeichnis des Dienstplan-Projekts ausgeführt werden." -ForegroundColor Red
    exit 1
}

# Generator ausführen
Write-Host "Generiere Beispieldatenbank..." -ForegroundColor Yellow
dotnet run --project src\SampleDataGenerator

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "=== Erfolgreich! ===" -ForegroundColor Green
    Write-Host ""
    Write-Host "Die Beispieldatenbank wurde erstellt: dienstplan-sample.db" -ForegroundColor White
    Write-Host ""
    Write-Host "Um sie zu verwenden, führen Sie aus:" -ForegroundColor Yellow
    Write-Host "  Copy-Item dienstplan-sample.db dienstplan.db" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Oder:" -ForegroundColor Yellow
    Write-Host "  Move-Item dienstplan-sample.db dienstplan.db" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Anmeldedaten:" -ForegroundColor Yellow
    Write-Host "  E-Mail: admin@fritzwinter.de" -ForegroundColor White
    Write-Host "  Passwort: Admin123!" -ForegroundColor White
} else {
    Write-Host ""
    Write-Host "Fehler beim Generieren der Datenbank." -ForegroundColor Red
    exit 1
}
