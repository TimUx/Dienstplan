using Microsoft.EntityFrameworkCore;
using Dienstplan.Domain.Entities;

namespace Dienstplan.Infrastructure.Data;

public class DienstplanDbContext : DbContext
{
    public DienstplanDbContext(DbContextOptions<DienstplanDbContext> options)
        : base(options)
    {
    }
    
    public DbSet<Employee> Employees => Set<Employee>();
    public DbSet<Team> Teams => Set<Team>();
    public DbSet<ShiftType> ShiftTypes => Set<ShiftType>();
    public DbSet<ShiftAssignment> ShiftAssignments => Set<ShiftAssignment>();
    public DbSet<Absence> Absences => Set<Absence>();
    
    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        base.OnModelCreating(modelBuilder);
        
        // Employee configuration
        modelBuilder.Entity<Employee>(entity =>
        {
            entity.HasKey(e => e.Id);
            entity.Property(e => e.Vorname).IsRequired().HasMaxLength(100);
            entity.Property(e => e.Name).IsRequired().HasMaxLength(100);
            entity.Property(e => e.Personalnummer).IsRequired().HasMaxLength(50);
            entity.HasIndex(e => e.Personalnummer).IsUnique();
            
            entity.HasOne(e => e.Team)
                .WithMany(t => t.Employees)
                .HasForeignKey(e => e.TeamId)
                .OnDelete(DeleteBehavior.SetNull);
        });
        
        // Team configuration
        modelBuilder.Entity<Team>(entity =>
        {
            entity.HasKey(t => t.Id);
            entity.Property(t => t.Name).IsRequired().HasMaxLength(100);
        });
        
        // ShiftType configuration
        modelBuilder.Entity<ShiftType>(entity =>
        {
            entity.HasKey(s => s.Id);
            entity.Property(s => s.Code).IsRequired().HasMaxLength(20);
            entity.Property(s => s.Name).IsRequired().HasMaxLength(100);
            entity.HasIndex(s => s.Code).IsUnique();
        });
        
        // ShiftAssignment configuration
        modelBuilder.Entity<ShiftAssignment>(entity =>
        {
            entity.HasKey(s => s.Id);
            
            entity.HasOne(s => s.Employee)
                .WithMany(e => e.ShiftAssignments)
                .HasForeignKey(s => s.EmployeeId)
                .OnDelete(DeleteBehavior.Cascade);
                
            entity.HasOne(s => s.ShiftType)
                .WithMany()
                .HasForeignKey(s => s.ShiftTypeId)
                .OnDelete(DeleteBehavior.Restrict);
                
            entity.HasIndex(s => new { s.EmployeeId, s.Date });
        });
        
        // Absence configuration
        modelBuilder.Entity<Absence>(entity =>
        {
            entity.HasKey(a => a.Id);
            
            entity.HasOne(a => a.Employee)
                .WithMany(e => e.Absences)
                .HasForeignKey(a => a.EmployeeId)
                .OnDelete(DeleteBehavior.Cascade);
                
            entity.HasIndex(a => new { a.EmployeeId, a.StartDate, a.EndDate });
        });
        
        // Seed default shift types
        SeedShiftTypes(modelBuilder);
    }
    
    private void SeedShiftTypes(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<ShiftType>().HasData(
            new ShiftType
            {
                Id = 1,
                Code = "F",
                Name = "Frühdienst",
                StartTime = new TimeSpan(5, 45, 0),
                EndTime = new TimeSpan(13, 45, 0),
                ColorCode = "#FFD700"
            },
            new ShiftType
            {
                Id = 2,
                Code = "S",
                Name = "Spätdienst",
                StartTime = new TimeSpan(13, 45, 0),
                EndTime = new TimeSpan(21, 45, 0),
                ColorCode = "#FF6347"
            },
            new ShiftType
            {
                Id = 3,
                Code = "N",
                Name = "Nachtdienst",
                StartTime = new TimeSpan(21, 45, 0),
                EndTime = new TimeSpan(5, 45, 0),
                ColorCode = "#4169E1"
            },
            new ShiftType
            {
                Id = 4,
                Code = "ZD",
                Name = "Zwischendienst",
                StartTime = new TimeSpan(8, 0, 0),
                EndTime = new TimeSpan(16, 0, 0),
                ColorCode = "#32CD32"
            }
        );
    }
}
