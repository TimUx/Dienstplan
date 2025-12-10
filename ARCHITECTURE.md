# Architektur-Dokumentation

## Übersicht

Das Dienstplan-System folgt einer mehrschichtigen Clean Architecture mit klarer Trennung der Verantwortlichkeiten.

## Architekturprinzipien

### 1. Layer-Trennung

```
┌─────────────────────────────────────────┐
│         Dienstplan.Web                  │
│    (Presentation Layer)                 │
│  - Controllers (REST API)               │
│  - Web UI (HTML/CSS/JS)                 │
└─────────────┬───────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│      Dienstplan.Application             │
│    (Application Layer)                  │
│  - Services (Business Logic)            │
│  - DTOs (Data Transfer)                 │
└─────────────┬───────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│      Dienstplan.Domain                  │
│    (Domain Layer)                       │
│  - Entities (Core Models)               │
│  - Rules (Business Rules)               │
│  - Interfaces                           │
└─────────────────────────────────────────┘
              ▲
              │
┌─────────────┴───────────────────────────┐
│    Dienstplan.Infrastructure            │
│    (Infrastructure Layer)               │
│  - DbContext (EF Core)                  │
│  - Repositories (Data Access)           │
└─────────────────────────────────────────┘
```

### 2. Dependency Rule

- **Domain** hat keine Abhängigkeiten zu anderen Projekten
- **Application** hängt nur von Domain ab
- **Infrastructure** implementiert Domain-Interfaces
- **Web** koordiniert alle Layer

### 3. Inversion of Control

Abhängigkeiten werden über Dependency Injection aufgelöst:
```csharp
// In Program.cs
builder.Services.AddScoped<IEmployeeRepository, EmployeeRepository>();
builder.Services.AddScoped<IShiftPlanningService, ShiftPlanningService>();
```

## Domain Layer

### Entities

**Kerngeschäftsobjekte ohne Infrastrukturabhängigkeiten:**

- `Employee`: Repräsentiert einen Mitarbeiter
- `Team`: Gruppierung von Mitarbeitern
- `ShiftType`: Definition einer Schichtart
- `ShiftAssignment`: Zuweisung einer Schicht zu einem Mitarbeiter
- `Absence`: Abwesenheit eines Mitarbeiters

### Rules

**ShiftRules** definiert alle Geschäftsregeln:

```csharp
public static class ShiftRules
{
    public const int MinimumRestHours = 11;
    
    public static readonly Dictionary<string, List<string>> ForbiddenTransitions = new()
    {
        { ShiftTypeCodes.Spaet, new List<string> { ShiftTypeCodes.Frueh } },
        { ShiftTypeCodes.Nacht, new List<string> { ShiftTypeCodes.Spaet } }
    };
    
    // ... weitere Regeln
}
```

### Interfaces

Repository-Interfaces definieren Datenoperationen ohne Implementierungsdetails:

```csharp
public interface IEmployeeRepository : IRepository<Employee>
{
    Task<IEnumerable<Employee>> GetSpringersAsync();
    Task<Employee?> GetByPersonalnummerAsync(string personalnummer);
}
```

## Application Layer

### Services

**ShiftPlanningService**: Kernlogik für Schichtplanung

- `PlanShifts()`: Automatische Schichtplanung für Zeitraum
- `ValidateShiftAssignment()`: Prüfung gegen Regeln
- `AssignSpringer()`: Automatische Springer-Zuweisung

**StatisticsService**: Berechnung von Statistiken

- `GetDashboardStatisticsAsync()`: Aggregierte Statistiken
- Berechnet Arbeitsstunden, Schichtverteilung, Fehltage, Workload

### DTOs

Data Transfer Objects für API-Kommunikation:
- Entkopplung von Domain-Modellen
- Kontrolle über exponierte Daten
- Vereinfachte Serialisierung

## Infrastructure Layer

### Database Context

**DienstplanDbContext** konfiguriert EF Core:

```csharp
public class DienstplanDbContext : DbContext
{
    public DbSet<Employee> Employees => Set<Employee>();
    public DbSet<Team> Teams => Set<Team>();
    // ... weitere DbSets
    
    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        // Konfiguration der Entities
        // Seed-Daten für ShiftTypes
    }
}
```

### Repositories

Implementierung der Repository-Interfaces:
- Kapseln Datenbankzugriff
- Verwenden EF Core
- Bieten typsichere Queries

## Web Layer

### Controllers

REST API Endpoints nach Ressourcen:

- **EmployeesController**: CRUD für Mitarbeiter
- **ShiftsController**: Schichtplanung und Anzeige
- **AbsencesController**: Abwesenheitsverwaltung
- **StatisticsController**: Dashboard-Daten

### Web UI

Single-Page Application mit Vanilla JavaScript:

```
wwwroot/
├── index.html          # Haupt-HTML
├── css/
│   └── styles.css     # Responsive Styling
└── js/
    └── app.js         # Client-seitige Logik
```

**Features:**
- Responsive Design (Mobile-First)
- Asynchrone API-Aufrufe
- Dynamisches Rendering
- Modal-Dialoge

## Datenzugriffsmuster

### Repository Pattern

Abstrahiert Datenzugriff:

```csharp
public class EmployeeRepository : IEmployeeRepository
{
    private readonly DienstplanDbContext _context;
    
    public async Task<Employee?> GetByIdAsync(int id)
    {
        return await _context.Employees
            .Include(e => e.Team)
            .Include(e => e.Absences)
            .FirstOrDefaultAsync(e => e.Id == id);
    }
}
```

### Unit of Work

Automatisch durch EF Core DbContext implementiert:
- Transaktionsmanagement
- Change Tracking
- Optimistic Concurrency

## Schichtplanungs-Algorithmus

### Ablauf

1. **Initialisierung**: Lade Mitarbeiter und Abwesenheiten
2. **Tag-Iteration**: Für jeden Tag im Zeitraum:
   - Filtere verfügbare Mitarbeiter (ohne Abwesenheit)
   - Bestimme Schichtanforderungen (Wochentag vs. Wochenende)
   - Weise Schichten zu nach idealem Rhythmus
3. **Validierung**: Prüfe jede Zuweisung gegen Regeln
4. **Persistierung**: Speichere gültige Zuweisungen

### Springer-Logik

Bei Ausfall eines Mitarbeiters:

1. Identifiziere betroffene Schicht
2. Suche verfügbare Springer (nicht abwesend)
3. Weise ersten verfügbaren Springer zu
4. Markiere als `IsSpringerAssignment = true`

## API-Design

### REST-Prinzipien

- **Ressourcen-basiert**: `/api/employees`, `/api/shifts`
- **HTTP-Verben**: GET, POST, PUT, DELETE
- **Status-Codes**: 200, 201, 204, 400, 404
- **JSON**: Content-Type: application/json

### Fehlerbehandlung

```csharp
if (!isValid)
{
    return BadRequest(new { error = errorMessage });
}
```

### Pagination

Für große Datenmengen geplant (aktuell noch nicht implementiert):
```
GET /api/employees?page=1&pageSize=20
```

## Sicherheitsarchitektur

### Geplante Implementierung

1. **Authentication**: ASP.NET Core Identity
2. **Authorization**: Policy-basiert
3. **Claims**: Rolleninformationen (Admin, Disponent, Read-Only)

### CORS

Aktuell: Offene Konfiguration für Entwicklung
Produktion: Whitelist spezifischer Origins

## Performance-Überlegungen

### Database

- **Indizes**: Auf häufig abgefragte Felder (PersonalNummer, EmployeeId+Date)
- **Eager Loading**: Include() für verwandte Daten
- **Connection Pooling**: Automatisch durch EF Core

### Caching

Zukünftige Optimierung:
- Response Caching für statische Daten
- In-Memory Cache für häufige Abfragen

### API

- **Asynchrone Operationen**: Alle I/O-Operationen async
- **Minimale Datenübertragung**: DTOs statt voller Entities

## Erweiterbarkeit

### Neue Schichtart hinzufügen

1. Seed-Daten in `DienstplanDbContext` ergänzen
2. Konstante in `ShiftTypeCodes` hinzufügen (optional)
3. CSS-Klasse für Farbe definieren
4. Keine Code-Änderung in Business-Logik nötig

### Neue Regel implementieren

1. In `ShiftRules` definieren
2. In `ShiftPlanningService.ValidateShiftAssignment()` prüfen
3. Unit-Tests hinzufügen

### Neue Statistik

1. Methode in `StatisticsService` hinzufügen
2. DTO erweitern
3. Controller-Endpoint erstellen
4. UI-Komponente implementieren

## Testing-Strategie

### Unit Tests

- Domain-Logik (Regeln, Validierung)
- Service-Logik (ohne DB)
- Mock-Repositories

### Integration Tests

- Controller mit echter DB
- Repository-Implementierungen
- End-to-End API-Tests

### UI Tests

- Geplant: Playwright/Selenium
- Aktuell: Manuelle Tests

## Deployment-Architektur

### Self-Contained Deployment

```
dotnet publish -c Release -r win-x64 --self-contained true
```

Vorteile:
- Keine .NET-Installation erforderlich
- Version-Isolation
- Einfache Distribution

### Database

SQLite für Einfachheit:
- Single-File Database
- Keine separate Installation
- Einfaches Backup

Migrierbar zu SQL Server, PostgreSQL, MySQL durch EF Core Abstraktion.

## Monitoring & Logging

### Logging

ASP.NET Core Logging Framework:
- Console Logger (Entwicklung)
- File Logger (Produktion geplant)
- Log-Levels: Trace, Debug, Info, Warning, Error, Critical

### Health Checks

Geplant:
```csharp
builder.Services.AddHealthChecks()
    .AddDbContextCheck<DienstplanDbContext>();
```

## Technologie-Entscheidungen

### Warum ASP.NET Core?

✅ Performant und modern
✅ Cross-Platform (Windows, Linux, macOS)
✅ Integrierte DI und Middleware
✅ Große Community und Support

### Warum SQLite?

✅ Zero-Configuration
✅ Serverless
✅ Portable
✅ Ausreichend für < 1000 Benutzer

### Warum Vanilla JavaScript?

✅ Keine Build-Tools nötig
✅ Schnelles Laden
✅ Einfach zu verstehen
✅ Keine Framework-Overhead

## Best Practices

### Code-Organisation

- Eine Klasse pro Datei
- Namespaces entsprechen Ordnerstruktur
- Interfaces in eigenem Ordner

### Naming Conventions

- PascalCase für public Members
- camelCase für private Members
- Descriptive Namen (GetEmployeesByTeam statt Get)

### Error Handling

- Exceptions nur für außergewöhnliche Fälle
- Validation mit Result-Pattern
- Structured Logging

## Zukünftige Verbesserungen

1. **CQRS**: Command/Query Separation für komplexe Operationen
2. **Event Sourcing**: Für Audit Trail
3. **GraphQL**: Alternative zu REST
4. **WebSockets**: Real-Time Updates
5. **Microservices**: Bei Skalierung über 10.000 Mitarbeiter
