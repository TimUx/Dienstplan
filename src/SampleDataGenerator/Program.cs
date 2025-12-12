using Microsoft.EntityFrameworkCore;
using Microsoft.AspNetCore.Identity;
using Dienstplan.Infrastructure.Data;
using Dienstplan.Infrastructure.Identity;
using Dienstplan.Domain.Entities;

namespace SampleDataGenerator;

/// <summary>
/// Generiert eine vorbefüllte SQLite-Datenbank mit Beispieldaten für das Dienstplan-System.
/// 
/// Erzeugt:
/// - 3 Teams (Alpha, Beta, Gamma)
/// - 17 Mitarbeiter (15 mit Team, 2 Sonderaufgaben)
/// - 4 Springer
/// - Administrator-Benutzer
/// </summary>
class Program
{
    static async Task Main(string[] args)
    {
        Console.WriteLine("=== Dienstplan Beispieldatenbank Generator ===");
        Console.WriteLine();
        
        // Datenbankpfad
        var dbPath = "dienstplan-sample.db";
        
        // Wenn Datei existiert, löschen für saubere Neuerstellung
        if (File.Exists(dbPath))
        {
            Console.WriteLine($"Lösche existierende Datenbankdatei: {dbPath}");
            File.Delete(dbPath);
        }
        
        // DbContext erstellen
        var options = new DbContextOptionsBuilder<DienstplanDbContext>()
            .UseSqlite($"Data Source={dbPath}")
            .Options;
            
        using var context = new DienstplanDbContext(options);
        
        // Datenbank erstellen mit Schema
        Console.WriteLine("Erstelle Datenbankschema...");
        await context.Database.EnsureCreatedAsync();
        Console.WriteLine("✓ Datenbankschema erstellt");
        Console.WriteLine();
        
        // Identity-Rollen erstellen
        Console.WriteLine("Erstelle Benutzerrollen...");
        var roles = new[] { "Admin", "Disponent", "Mitarbeiter" };
        foreach (var roleName in roles)
        {
            var role = new IdentityRole
            {
                Id = Guid.NewGuid().ToString(),
                Name = roleName,
                NormalizedName = roleName.ToUpper(),
                ConcurrencyStamp = Guid.NewGuid().ToString()
            };
            context.Roles.Add(role);
        }
        await context.SaveChangesAsync();
        Console.WriteLine("✓ Rollen erstellt: Admin, Disponent, Mitarbeiter");
        Console.WriteLine();
        
        // Administrator-Benutzer erstellen
        Console.WriteLine("Erstelle Administrator-Benutzer...");
        var hasher = new PasswordHasher<ApplicationUser>();
        var adminUser = new ApplicationUser
        {
            Id = Guid.NewGuid().ToString(),
            UserName = "admin@fritzwinter.de",
            NormalizedUserName = "ADMIN@FRITZWINTER.DE",
            Email = "admin@fritzwinter.de",
            NormalizedEmail = "ADMIN@FRITZWINTER.DE",
            EmailConfirmed = true,
            FullName = "Administrator",
            SecurityStamp = Guid.NewGuid().ToString(),
            ConcurrencyStamp = Guid.NewGuid().ToString()
        };
        adminUser.PasswordHash = hasher.HashPassword(adminUser, "Admin123!");
        context.Users.Add(adminUser);
        await context.SaveChangesAsync();
        
        // Admin-Rolle zuweisen
        var adminRole = await context.Roles.FirstAsync(r => r.Name == "Admin");
        context.UserRoles.Add(new IdentityUserRole<string>
        {
            UserId = adminUser.Id,
            RoleId = adminRole.Id
        });
        await context.SaveChangesAsync();
        Console.WriteLine("✓ Administrator erstellt (admin@fritzwinter.de / Admin123!)");
        Console.WriteLine();
        
        // Teams erstellen
        Console.WriteLine("Erstelle Teams...");
        var teamAlpha = new Team
        {
            Name = "Team Alpha",
            Description = "Frühschicht-Team",
            Email = "team-alpha@fritzwinter.de"
        };
        var teamBeta = new Team
        {
            Name = "Team Beta",
            Description = "Spätschicht-Team",
            Email = "team-beta@fritzwinter.de"
        };
        var teamGamma = new Team
        {
            Name = "Team Gamma",
            Description = "Nachtschicht-Team",
            Email = "team-gamma@fritzwinter.de"
        };
        
        context.Teams.AddRange(teamAlpha, teamBeta, teamGamma);
        await context.SaveChangesAsync();
        Console.WriteLine($"✓ Team Alpha erstellt (ID: {teamAlpha.Id})");
        Console.WriteLine($"✓ Team Beta erstellt (ID: {teamBeta.Id})");
        Console.WriteLine($"✓ Team Gamma erstellt (ID: {teamGamma.Id})");
        Console.WriteLine();
        
        // Mitarbeiter erstellen
        Console.WriteLine("Erstelle Mitarbeiter...");
        
        var employees = new List<Employee>
        {
            // Team Alpha (5 Mitarbeiter)
            new Employee
            {
                Vorname = "Max",
                Name = "Mustermann",
                Personalnummer = "MA001",
                Email = "max.mustermann@fritzwinter.de",
                Geburtsdatum = new DateTime(1985, 5, 15),
                Funktion = "Werkschutz",
                TeamId = teamAlpha.Id,
                IsSpringer = false,
                IsFerienjobber = false
            },
            new Employee
            {
                Vorname = "Anna",
                Name = "Schmidt",
                Personalnummer = "MA002",
                Email = "anna.schmidt@fritzwinter.de",
                Geburtsdatum = new DateTime(1990, 8, 22),
                Funktion = "Werkschutz",
                TeamId = teamAlpha.Id,
                IsSpringer = false,
                IsFerienjobber = false
            },
            new Employee
            {
                Vorname = "Peter",
                Name = "Müller",
                Personalnummer = "MA003",
                Email = "peter.mueller@fritzwinter.de",
                Geburtsdatum = new DateTime(1988, 3, 10),
                Funktion = "Brandmeldetechniker",
                TeamId = teamAlpha.Id,
                IsSpringer = true,  // Springer
                IsFerienjobber = false,
                IsBrandmeldetechniker = true
            },
            new Employee
            {
                Vorname = "Lisa",
                Name = "Weber",
                Personalnummer = "MA004",
                Email = "lisa.weber@fritzwinter.de",
                Geburtsdatum = new DateTime(1992, 11, 5),
                Funktion = "Werkschutz",
                TeamId = teamAlpha.Id,
                IsSpringer = false,
                IsFerienjobber = false
            },
            new Employee
            {
                Vorname = "Thomas",
                Name = "Wagner",
                Personalnummer = "MA005",
                Email = "thomas.wagner@fritzwinter.de",
                Geburtsdatum = new DateTime(1987, 7, 18),
                Funktion = "Werkschutz",
                TeamId = teamAlpha.Id,
                IsSpringer = false,
                IsFerienjobber = false
            },
            
            // Team Beta (5 Mitarbeiter)
            new Employee
            {
                Vorname = "Julia",
                Name = "Becker",
                Personalnummer = "MA006",
                Email = "julia.becker@fritzwinter.de",
                Geburtsdatum = new DateTime(1991, 2, 28),
                Funktion = "Werkschutz",
                TeamId = teamBeta.Id,
                IsSpringer = false,
                IsFerienjobber = false
            },
            new Employee
            {
                Vorname = "Michael",
                Name = "Hoffmann",
                Personalnummer = "MA007",
                Email = "michael.hoffmann@fritzwinter.de",
                Geburtsdatum = new DateTime(1989, 9, 14),
                Funktion = "Werkschutz",
                TeamId = teamBeta.Id,
                IsSpringer = false,
                IsFerienjobber = false
            },
            new Employee
            {
                Vorname = "Sarah",
                Name = "Fischer",
                Personalnummer = "MA008",
                Email = "sarah.fischer@fritzwinter.de",
                Geburtsdatum = new DateTime(1993, 6, 7),
                Funktion = "Brandschutzbeauftragter",
                TeamId = teamBeta.Id,
                IsSpringer = true,  // Springer
                IsFerienjobber = false,
                IsBrandschutzbeauftragter = true
            },
            new Employee
            {
                Vorname = "Daniel",
                Name = "Richter",
                Personalnummer = "MA009",
                Email = "daniel.richter@fritzwinter.de",
                Geburtsdatum = new DateTime(1986, 12, 21),
                Funktion = "Werkschutz",
                TeamId = teamBeta.Id,
                IsSpringer = false,
                IsFerienjobber = false
            },
            new Employee
            {
                Vorname = "Laura",
                Name = "Klein",
                Personalnummer = "MA010",
                Email = "laura.klein@fritzwinter.de",
                Geburtsdatum = new DateTime(1994, 4, 16),
                Funktion = "Werkschutz",
                TeamId = teamBeta.Id,
                IsSpringer = false,
                IsFerienjobber = false
            },
            
            // Team Gamma (5 Mitarbeiter)
            new Employee
            {
                Vorname = "Markus",
                Name = "Wolf",
                Personalnummer = "MA011",
                Email = "markus.wolf@fritzwinter.de",
                Geburtsdatum = new DateTime(1990, 10, 9),
                Funktion = "Werkschutz",
                TeamId = teamGamma.Id,
                IsSpringer = false,
                IsFerienjobber = false
            },
            new Employee
            {
                Vorname = "Petra",
                Name = "Schröder",
                Personalnummer = "MA012",
                Email = "petra.schroeder@fritzwinter.de",
                Geburtsdatum = new DateTime(1988, 1, 25),
                Funktion = "Werkschutz",
                TeamId = teamGamma.Id,
                IsSpringer = false,
                IsFerienjobber = false
            },
            new Employee
            {
                Vorname = "Stefan",
                Name = "Neumann",
                Personalnummer = "MA013",
                Email = "stefan.neumann@fritzwinter.de",
                Geburtsdatum = new DateTime(1992, 5, 30),
                Funktion = "Werkschutz",
                TeamId = teamGamma.Id,
                IsSpringer = true,  // Springer
                IsFerienjobber = false
            },
            new Employee
            {
                Vorname = "Claudia",
                Name = "Braun",
                Personalnummer = "MA014",
                Email = "claudia.braun@fritzwinter.de",
                Geburtsdatum = new DateTime(1987, 8, 12),
                Funktion = "Werkschutz",
                TeamId = teamGamma.Id,
                IsSpringer = false,
                IsFerienjobber = false
            },
            new Employee
            {
                Vorname = "Andreas",
                Name = "Zimmermann",
                Personalnummer = "MA015",
                Email = "andreas.zimmermann@fritzwinter.de",
                Geburtsdatum = new DateTime(1991, 3, 19),
                Funktion = "Werkschutz",
                TeamId = teamGamma.Id,
                IsSpringer = false,
                IsFerienjobber = false
            },
            
            // Sonderaufgaben ohne Team (2 Mitarbeiter)
            new Employee
            {
                Vorname = "Frank",
                Name = "Krüger",
                Personalnummer = "MA016",
                Email = "frank.krueger@fritzwinter.de",
                Geburtsdatum = new DateTime(1985, 11, 8),
                Funktion = "Technischer Dienst",
                TeamId = null,  // Keine Teamzuordnung
                IsSpringer = true,  // Springer
                IsFerienjobber = false
            },
            new Employee
            {
                Vorname = "Sabine",
                Name = "Hartmann",
                Personalnummer = "MA017",
                Email = "sabine.hartmann@fritzwinter.de",
                Geburtsdatum = new DateTime(1989, 7, 23),
                Funktion = "Koordination",
                TeamId = null,  // Keine Teamzuordnung
                IsSpringer = false,
                IsFerienjobber = false
            }
        };
        
        context.Employees.AddRange(employees);
        await context.SaveChangesAsync();
        
        // Mitarbeiter ausgeben
        foreach (var emp in employees)
        {
            var teamInfo = emp.TeamId.HasValue 
                ? $"(Team {(emp.TeamId == teamAlpha.Id ? "Alpha" : emp.TeamId == teamBeta.Id ? "Beta" : "Gamma")})" 
                : "(Sonderaufgabe)";
            var springerInfo = emp.IsSpringer ? " [SPRINGER]" : "";
            Console.WriteLine($"  ✓ {emp.Personalnummer}: {emp.Vorname} {emp.Name}{springerInfo} {teamInfo}");
        }
        
        Console.WriteLine();
        Console.WriteLine("=== Zusammenfassung ===");
        Console.WriteLine($"✓ 3 Teams erstellt");
        Console.WriteLine($"✓ 17 Mitarbeiter erstellt");
        Console.WriteLine($"  - 15 mit Teamzuordnung (je 5 pro Team)");
        Console.WriteLine($"  - 2 Sonderaufgaben (ohne Team)");
        Console.WriteLine($"  - 4 Springer");
        Console.WriteLine();
        Console.WriteLine($"Datenbank gespeichert: {Path.GetFullPath(dbPath)}");
        Console.WriteLine();
        Console.WriteLine("Sie können diese Datei jetzt als 'dienstplan.db' verwenden.");
        Console.WriteLine("Anmeldedaten: admin@fritzwinter.de / Admin123!");
    }
}
