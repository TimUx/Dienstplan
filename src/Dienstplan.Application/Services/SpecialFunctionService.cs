using Dienstplan.Domain.Entities;
using Dienstplan.Domain.Interfaces;

namespace Dienstplan.Application.Services;

/// <summary>
/// Service for managing special function assignments (BMT, BSB)
/// </summary>
public class SpecialFunctionService
{
    private readonly IEmployeeRepository _employeeRepository;
    private readonly IShiftAssignmentRepository _shiftAssignmentRepository;
    private readonly IAbsenceRepository _absenceRepository;

    public SpecialFunctionService(
        IEmployeeRepository employeeRepository,
        IShiftAssignmentRepository shiftAssignmentRepository,
        IAbsenceRepository absenceRepository)
    {
        _employeeRepository = employeeRepository;
        _shiftAssignmentRepository = shiftAssignmentRepository;
        _absenceRepository = absenceRepository;
    }

    /// <summary>
    /// Assigns BMT (Brandmeldetechniker) for the given date range
    /// Requirements: Mo-Fr, 06:00-14:00, exactly 1 qualified person per day
    /// </summary>
    public async Task<List<ShiftAssignment>> AssignBMT(DateTime startDate, DateTime endDate)
    {
        var assignments = new List<ShiftAssignment>();
        var qualifiedEmployees = (await _employeeRepository.GetAllAsync())
            .Where(e => e.IsBrandmeldetechniker)
            .ToList();

        if (!qualifiedEmployees.Any())
            return assignments;

        var absences = await _absenceRepository.GetByDateRangeAsync(startDate, endDate);
        var existingBmtAssignments = (await _shiftAssignmentRepository.GetByDateRangeAsync(startDate, endDate))
            .Where(a => a.ShiftTypeId == 5) // BMT shift type ID
            .ToList();

        // Track rotation for fairness
        var rotationIndex = 0;
        var lastAssignments = existingBmtAssignments
            .OrderByDescending(a => a.Date)
            .Take(qualifiedEmployees.Count)
            .ToList();

        for (var date = startDate; date <= endDate; date = date.AddDays(1))
        {
            // BMT only on weekdays
            if (date.DayOfWeek == DayOfWeek.Saturday || date.DayOfWeek == DayOfWeek.Sunday)
                continue;

            // Check if already assigned
            if (existingBmtAssignments.Any(a => a.Date.Date == date.Date))
                continue;

            // Find available qualified employee
            Employee? assignedEmployee = null;
            int attempts = 0;

            while (assignedEmployee == null && attempts < qualifiedEmployees.Count)
            {
                var candidate = qualifiedEmployees[rotationIndex % qualifiedEmployees.Count];
                
                // Check if available (not absent, not already has a shift that day)
                var isAbsent = absences.Any(a => 
                    a.EmployeeId == candidate.Id && 
                    a.StartDate <= date && 
                    a.EndDate >= date);

                var hasShift = await _shiftAssignmentRepository.GetByEmployeeAndDateAsync(candidate.Id, date) != null;

                if (!isAbsent && !hasShift)
                {
                    assignedEmployee = candidate;
                }

                rotationIndex++;
                attempts++;
            }

            if (assignedEmployee != null)
            {
                assignments.Add(new ShiftAssignment
                {
                    EmployeeId = assignedEmployee.Id,
                    ShiftTypeId = 5, // BMT
                    Date = date,
                    IsManual = false
                });
            }
        }

        return assignments;
    }

    /// <summary>
    /// Assigns BSB (Brandschutzbeauftragter) for the given date range
    /// Requirements: Mo-Fr, 9.5 hours daily, exactly 1 qualified person per day
    /// </summary>
    public async Task<List<ShiftAssignment>> AssignBSB(DateTime startDate, DateTime endDate)
    {
        var assignments = new List<ShiftAssignment>();
        var qualifiedEmployees = (await _employeeRepository.GetAllAsync())
            .Where(e => e.IsBrandschutzbeauftragter)
            .ToList();

        if (!qualifiedEmployees.Any())
            return assignments;

        var absences = await _absenceRepository.GetByDateRangeAsync(startDate, endDate);
        var existingBsbAssignments = (await _shiftAssignmentRepository.GetByDateRangeAsync(startDate, endDate))
            .Where(a => a.ShiftTypeId == 6) // BSB shift type ID
            .ToList();

        // Track rotation for fairness
        var rotationIndex = 0;

        for (var date = startDate; date <= endDate; date = date.AddDays(1))
        {
            // BSB only on weekdays
            if (date.DayOfWeek == DayOfWeek.Saturday || date.DayOfWeek == DayOfWeek.Sunday)
                continue;

            // Check if already assigned
            if (existingBsbAssignments.Any(a => a.Date.Date == date.Date))
                continue;

            // Find available qualified employee
            Employee? assignedEmployee = null;
            int attempts = 0;

            while (assignedEmployee == null && attempts < qualifiedEmployees.Count)
            {
                var candidate = qualifiedEmployees[rotationIndex % qualifiedEmployees.Count];
                
                // Check if available (not absent, not already has a shift that day)
                var isAbsent = absences.Any(a => 
                    a.EmployeeId == candidate.Id && 
                    a.StartDate <= date && 
                    a.EndDate >= date);

                var hasShift = await _shiftAssignmentRepository.GetByEmployeeAndDateAsync(candidate.Id, date) != null;

                if (!isAbsent && !hasShift)
                {
                    assignedEmployee = candidate;
                }

                rotationIndex++;
                attempts++;
            }

            if (assignedEmployee != null)
            {
                assignments.Add(new ShiftAssignment
                {
                    EmployeeId = assignedEmployee.Id,
                    ShiftTypeId = 6, // BSB
                    Date = date,
                    IsManual = false
                });
            }
        }

        return assignments;
    }
}
