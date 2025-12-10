using Microsoft.EntityFrameworkCore;
using Dienstplan.Infrastructure.Data;
using Dienstplan.Infrastructure.Repositories;
using Dienstplan.Application.Services;
using Dienstplan.Domain.Interfaces;

var builder = WebApplication.CreateBuilder(args);

// Add services to the container
builder.Services.AddControllers();
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddOpenApi();

// Configure database
builder.Services.AddDbContext<DienstplanDbContext>(options =>
    options.UseSqlite(builder.Configuration.GetConnectionString("DefaultConnection") 
        ?? "Data Source=dienstplan.db"));

// Register repositories
builder.Services.AddScoped<IEmployeeRepository, EmployeeRepository>();
builder.Services.AddScoped<IShiftAssignmentRepository, ShiftAssignmentRepository>();
builder.Services.AddScoped<IAbsenceRepository, AbsenceRepository>();

// Register services
builder.Services.AddScoped<IShiftPlanningService, ShiftPlanningService>();
builder.Services.AddScoped<IStatisticsService, StatisticsService>();

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

// Initialize database
using (var scope = app.Services.CreateScope())
{
    var db = scope.ServiceProvider.GetRequiredService<DienstplanDbContext>();
    db.Database.EnsureCreated();
}

// Configure the HTTP request pipeline
if (app.Environment.IsDevelopment())
{
    app.MapOpenApi();
    app.UseDeveloperExceptionPage();
}

app.UseHttpsRedirection();
app.UseCors("AllowAll");
app.UseAuthorization();

app.MapControllers();

// Serve static files for web interface
app.UseDefaultFiles();
app.UseStaticFiles();

app.Run();
