using Microsoft.EntityFrameworkCore;
using Microsoft.AspNetCore.Identity;
using Dienstplan.Infrastructure.Data;
using Dienstplan.Infrastructure.Repositories;
using Dienstplan.Infrastructure.Identity;
using Dienstplan.Application.Services;
using Dienstplan.Domain.Interfaces;
using Dienstplan.Domain.Entities;

var builder = WebApplication.CreateBuilder(args);

// Add services to the container
builder.Services.AddControllers();
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddOpenApi();

// Configure database
builder.Services.AddDbContext<DienstplanDbContext>(options =>
    options.UseSqlite(builder.Configuration.GetConnectionString("DefaultConnection") 
        ?? "Data Source=dienstplan.db"));

// Configure Identity
builder.Services.AddIdentity<ApplicationUser, IdentityRole>(options =>
{
    // Password settings
    options.Password.RequireDigit = true;
    options.Password.RequireLowercase = true;
    options.Password.RequireUppercase = true;
    options.Password.RequireNonAlphanumeric = false;
    options.Password.RequiredLength = 8;
    
    // Lockout settings
    options.Lockout.DefaultLockoutTimeSpan = TimeSpan.FromMinutes(30);
    options.Lockout.MaxFailedAccessAttempts = 5;
    
    // User settings
    options.User.RequireUniqueEmail = true;
})
.AddEntityFrameworkStores<DienstplanDbContext>()
.AddDefaultTokenProviders();

// Configure cookie authentication
builder.Services.ConfigureApplicationCookie(options =>
{
    options.Cookie.HttpOnly = true;
    options.ExpireTimeSpan = TimeSpan.FromDays(7);
    options.LoginPath = "/api/auth/login";
    options.LogoutPath = "/api/auth/logout";
    options.AccessDeniedPath = "/api/auth/access-denied";
    options.SlidingExpiration = true;
});

// Register repositories
builder.Services.AddScoped<IEmployeeRepository, EmployeeRepository>();
builder.Services.AddScoped<IShiftAssignmentRepository, ShiftAssignmentRepository>();
builder.Services.AddScoped<IAbsenceRepository, AbsenceRepository>();
builder.Services.AddScoped<IVacationRequestRepository, VacationRequestRepository>();
builder.Services.AddScoped<IShiftExchangeRepository, ShiftExchangeRepository>();
builder.Services.AddScoped<IEmailSettingsRepository, EmailSettingsRepository>();

// Register services
builder.Services.AddScoped<IShiftPlanningService, ShiftPlanningService>();
builder.Services.AddScoped<IStatisticsService, StatisticsService>();
builder.Services.AddScoped<IPdfExportService, PdfExportService>();
builder.Services.AddScoped<INotificationService, NotificationService>();

// Add CORS for web interface
builder.Services.AddCors(options =>
{
    options.AddPolicy("AllowAll", policy =>
    {
        policy.AllowAnyOrigin()
              .AllowAnyMethod()
              .AllowAnyHeader();
    });
});

var app = builder.Build();

// Initialize database and seed roles
using (var scope = app.Services.CreateScope())
{
    var db = scope.ServiceProvider.GetRequiredService<DienstplanDbContext>();
    db.Database.EnsureCreated();
    
    // Seed roles and admin user
    var roleManager = scope.ServiceProvider.GetRequiredService<RoleManager<IdentityRole>>();
    var userManager = scope.ServiceProvider.GetRequiredService<UserManager<ApplicationUser>>();
    
    // Create roles
    string[] roles = { "Admin", "Disponent", "Mitarbeiter" };
    foreach (var role in roles)
    {
        if (!await roleManager.RoleExistsAsync(role))
        {
            await roleManager.CreateAsync(new IdentityRole(role));
        }
    }
    
    // Create default admin user
    var adminEmail = "admin@fritzwinter.de";
    if (await userManager.FindByEmailAsync(adminEmail) == null)
    {
        var admin = new ApplicationUser
        {
            UserName = adminEmail,
            Email = adminEmail,
            EmailConfirmed = true,
            FullName = "Administrator"
        };
        
        var result = await userManager.CreateAsync(admin, "Admin123!");
        if (result.Succeeded)
        {
            await userManager.AddToRoleAsync(admin, "Admin");
        }
    }
    
    // Seed example data (teams, employees, shifts) if database is empty
    var employeeRepo = scope.ServiceProvider.GetRequiredService<IEmployeeRepository>();
    var teamRepo = scope.ServiceProvider.GetRequiredService<IRepository<Team>>();
    var shiftRepo = scope.ServiceProvider.GetRequiredService<IShiftAssignmentRepository>();
    
    var existingEmployees = await employeeRepo.GetAllAsync();
    if (!existingEmployees.Any())
    {
        // Create teams
        var team1 = new Team { Name = "Team Alpha", Description = "Frühschicht-Team", Email = "team-alpha@fritzwinter.de" };
        var team2 = new Team { Name = "Team Beta", Description = "Spätschicht-Team", Email = "team-beta@fritzwinter.de" };
        var team3 = new Team { Name = "Team Gamma", Description = "Nachtschicht-Team", Email = "team-gamma@fritzwinter.de" };
        
        await teamRepo.AddAsync(team1);
        await teamRepo.AddAsync(team2);
        await teamRepo.AddAsync(team3);
        
        // Create example employees
        var employees = new[]
        {
            new Employee { Vorname = "Max", Name = "Mustermann", Personalnummer = "MA001", Email = "max.mustermann@fritzwinter.de", Geburtsdatum = new DateTime(1985, 5, 15), Funktion = "Werkschutz", TeamId = team1.Id },
            new Employee { Vorname = "Anna", Name = "Schmidt", Personalnummer = "MA002", Email = "anna.schmidt@fritzwinter.de", Geburtsdatum = new DateTime(1990, 8, 22), Funktion = "Werkschutz", TeamId = team1.Id },
            new Employee { Vorname = "Peter", Name = "Müller", Personalnummer = "MA003", Email = "peter.mueller@fritzwinter.de", Geburtsdatum = new DateTime(1988, 3, 10), Funktion = "Brandmeldetechniker", TeamId = team1.Id },
            new Employee { Vorname = "Lisa", Name = "Weber", Personalnummer = "MA004", Email = "lisa.weber@fritzwinter.de", Geburtsdatum = new DateTime(1992, 11, 5), Funktion = "Werkschutz", TeamId = team1.Id },
            new Employee { Vorname = "Thomas", Name = "Wagner", Personalnummer = "MA005", Email = "thomas.wagner@fritzwinter.de", Geburtsdatum = new DateTime(1987, 7, 18), Funktion = "Werkschutz", TeamId = team1.Id },
            
            new Employee { Vorname = "Julia", Name = "Becker", Personalnummer = "MA006", Email = "julia.becker@fritzwinter.de", Geburtsdatum = new DateTime(1991, 2, 28), Funktion = "Werkschutz", TeamId = team2.Id },
            new Employee { Vorname = "Michael", Name = "Hoffmann", Personalnummer = "MA007", Email = "michael.hoffmann@fritzwinter.de", Geburtsdatum = new DateTime(1989, 9, 14), Funktion = "Werkschutz", TeamId = team2.Id },
            new Employee { Vorname = "Sarah", Name = "Fischer", Personalnummer = "MA008", Email = "sarah.fischer@fritzwinter.de", Geburtsdatum = new DateTime(1993, 6, 7), Funktion = "Brandschutzbeauftragter", TeamId = team2.Id },
            new Employee { Vorname = "Daniel", Name = "Richter", Personalnummer = "MA009", Email = "daniel.richter@fritzwinter.de", Geburtsdatum = new DateTime(1986, 12, 21), Funktion = "Werkschutz", TeamId = team2.Id },
            new Employee { Vorname = "Laura", Name = "Klein", Personalnummer = "MA010", Email = "laura.klein@fritzwinter.de", Geburtsdatum = new DateTime(1994, 4, 16), Funktion = "Werkschutz", TeamId = team2.Id },
            
            new Employee { Vorname = "Markus", Name = "Wolf", Personalnummer = "MA011", Email = "markus.wolf@fritzwinter.de", Geburtsdatum = new DateTime(1990, 10, 9), Funktion = "Werkschutz", TeamId = team3.Id },
            new Employee { Vorname = "Petra", Name = "Schröder", Personalnummer = "MA012", Email = "petra.schroeder@fritzwinter.de", Geburtsdatum = new DateTime(1988, 1, 25), Funktion = "Werkschutz", TeamId = team3.Id },
            new Employee { Vorname = "Stefan", Name = "Neumann", Personalnummer = "MA013", Email = "stefan.neumann@fritzwinter.de", Geburtsdatum = new DateTime(1992, 5, 30), Funktion = "Werkschutz", TeamId = team3.Id },
            new Employee { Vorname = "Claudia", Name = "Braun", Personalnummer = "MA014", Email = "claudia.braun@fritzwinter.de", Geburtsdatum = new DateTime(1987, 8, 12), Funktion = "Werkschutz", TeamId = team3.Id },
            new Employee { Vorname = "Andreas", Name = "Zimmermann", Personalnummer = "MA015", Email = "andreas.zimmermann@fritzwinter.de", Geburtsdatum = new DateTime(1991, 3, 19), Funktion = "Werkschutz", TeamId = team3.Id },
            
            new Employee { Vorname = "Frank", Name = "Krüger", Personalnummer = "MA016", Email = "frank.krueger@fritzwinter.de", Geburtsdatum = new DateTime(1985, 11, 8), Funktion = "Springer", IsSpringer = true },
            new Employee { Vorname = "Sabine", Name = "Hartmann", Personalnummer = "MA017", Email = "sabine.hartmann@fritzwinter.de", Geburtsdatum = new DateTime(1989, 7, 23), Funktion = "Springer", IsSpringer = true },
        };
        
        foreach (var emp in employees)
        {
            await employeeRepo.AddAsync(emp);
        }
        
        // Create some example shifts for the current week
        var today = DateTime.Today;
        var startOfWeek = today.AddDays(-(int)today.DayOfWeek + (int)DayOfWeek.Monday);
        var shiftTypes = db.ShiftTypes.ToList();
        var frueh = shiftTypes.FirstOrDefault(s => s.Code == "F");
        var spaet = shiftTypes.FirstOrDefault(s => s.Code == "S");
        var nacht = shiftTypes.FirstOrDefault(s => s.Code == "N");
        
        if (frueh != null && spaet != null && nacht != null)
        {
            var allEmployees = employees.Where(e => !e.IsSpringer).ToArray();
            var random = new Random(42); // Fixed seed for reproducibility
            
            for (int dayOffset = 0; dayOffset < 7; dayOffset++)
            {
                var date = startOfWeek.AddDays(dayOffset);
                var isWeekend = date.DayOfWeek == DayOfWeek.Saturday || date.DayOfWeek == DayOfWeek.Sunday;
                
                // Frühdienst: 4-5 Mitarbeiter (Wochentag), 2-3 (Wochenende)
                var fruehCount = isWeekend ? random.Next(2, 4) : random.Next(4, 6);
                for (int i = 0; i < fruehCount && i < allEmployees.Length; i++)
                {
                    await shiftRepo.AddAsync(new ShiftAssignment
                    {
                        EmployeeId = allEmployees[(i + dayOffset * 3) % allEmployees.Length].Id,
                        ShiftTypeId = frueh.Id,
                        Date = date,
                        IsManual = false,
                        CreatedAt = DateTime.UtcNow,
                        CreatedBy = "System"
                    });
                }
                
                // Spätdienst: 3-4 Mitarbeiter (Wochentag), 2-3 (Wochenende)
                var spaetCount = isWeekend ? random.Next(2, 4) : random.Next(3, 5);
                for (int i = 0; i < spaetCount && i < allEmployees.Length; i++)
                {
                    await shiftRepo.AddAsync(new ShiftAssignment
                    {
                        EmployeeId = allEmployees[(i + fruehCount + dayOffset * 3) % allEmployees.Length].Id,
                        ShiftTypeId = spaet.Id,
                        Date = date,
                        IsManual = false,
                        CreatedAt = DateTime.UtcNow,
                        CreatedBy = "System"
                    });
                }
                
                // Nachtdienst: 3 Mitarbeiter (Wochentag), 2-3 (Wochenende)
                var nachtCount = isWeekend ? random.Next(2, 4) : 3;
                for (int i = 0; i < nachtCount && i < allEmployees.Length; i++)
                {
                    await shiftRepo.AddAsync(new ShiftAssignment
                    {
                        EmployeeId = allEmployees[(i + fruehCount + spaetCount + dayOffset * 3) % allEmployees.Length].Id,
                        ShiftTypeId = nacht.Id,
                        Date = date,
                        IsManual = false,
                        CreatedAt = DateTime.UtcNow,
                        CreatedBy = "System"
                    });
                }
            }
        }
    }
}

// Configure the HTTP request pipeline
if (app.Environment.IsDevelopment())
{
    app.MapOpenApi();
    app.UseDeveloperExceptionPage();
}

app.UseHttpsRedirection();
app.UseCors("AllowAll");

app.UseAuthentication();
app.UseAuthorization();

app.MapControllers();

// Serve static files for web interface
app.UseDefaultFiles();
app.UseStaticFiles();

app.Run();
