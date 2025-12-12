using Dienstplan.Domain.Entities;
using Dienstplan.Domain.Interfaces;
using Dienstplan.Domain.Rules;

namespace Dienstplan.Application.Services;

/// <summary>
/// Enhanced service for managing Springer (backup worker) assignments
/// </summary>
public class SpringerManagementService
{
    private readonly IEmployeeRepository _employeeRepository;
    private readonly IShiftAssignmentRepository _shiftAssignmentRepository;
    private readonly IAbsenceRepository _absenceRepository;

    public SpringerManagementService(
        IEmployeeRepository employeeRepository,
        IShiftAssignmentRepository shiftAssignmentRepository,
        IAbsenceRepository absenceRepository)
    {
        _employeeRepository = employeeRepository;
        _shiftAssignmentRepository = shiftAssignmentRepository;
        _absenceRepository = absenceRepository;
    }

    /// <summary>
    /// Ensures at least one springer is available for the given date
    /// </summary>
    public async Task<bool> IsSpringerAvailable(DateTime date)
    {
        var springers = await _employeeRepository.GetSpringersAsync();
        var absences = await _absenceRepository.GetByDateRangeAsync(date, date);
        var assignments = await _shiftAssignmentRepository.GetByDateRangeAsync(date, date);

        foreach (var springer in springers)
        {
            // Check if springer is absent
            var isAbsent = absences.Any(a => 
                a.EmployeeId == springer.Id && 
                a.StartDate <= date && 
                a.EndDate >= date);

            if (isAbsent)
                continue;

            // Check if springer already has a shift
            var hasShift = assignments.Any(a => a.EmployeeId == springer.Id && a.Date.Date == date.Date);

            if (!hasShift)
                return true;
        }

        return false;
    }

    /// <summary>
    /// Gets all available springers for a given date and shift type
    /// </summary>
    public async Task<List<Employee>> GetAvailableSpringers(DateTime date, int? shiftTypeId = null)
    {
        var springers = (await _employeeRepository.GetSpringersAsync()).ToList();
        var absences = await _absenceRepository.GetByDateRangeAsync(date, date);
        var assignments = await _shiftAssignmentRepository.GetByDateRangeAsync(date, date);

        var availableSpringers = new List<Employee>();

        foreach (var springer in springers)
        {
            // Check if springer is absent
            var isAbsent = absences.Any(a => 
                a.EmployeeId == springer.Id && 
                a.StartDate <= date && 
                a.EndDate >= date);

            if (isAbsent)
                continue;

            // Check if springer already has a shift
            var hasShift = assignments.Any(a => a.EmployeeId == springer.Id && a.Date.Date == date.Date);

            if (hasShift)
                continue;

            // If specific shift type requested, validate rest periods
            if (shiftTypeId.HasValue)
            {
                var previousShift = await _shiftAssignmentRepository.GetByEmployeeAndDateAsync(
                    springer.Id, date.AddDays(-1));

                if (previousShift != null)
                {
                    var previousShiftCode = GetShiftCodeById(previousShift.ShiftTypeId);
                    var currentShiftCode = GetShiftCodeById(shiftTypeId.Value);

                    // Check forbidden transitions
                    if (ShiftRules.ForbiddenTransitions.ContainsKey(previousShiftCode))
                    {
                        if (ShiftRules.ForbiddenTransitions[previousShiftCode].Contains(currentShiftCode))
                            continue;
                    }
                }
            }

            availableSpringers.Add(springer);
        }

        return availableSpringers;
    }

    /// <summary>
    /// Assigns a springer to cover a shift for an absent employee
    /// </summary>
    public async Task<ShiftAssignment?> AssignSpringerForAbsence(int absentEmployeeId, DateTime date)
    {
        // Get the original shift assignment
        var originalShift = await _shiftAssignmentRepository.GetByEmployeeAndDateAsync(absentEmployeeId, date);
        
        if (originalShift == null)
            return null;

        // Get available springers for this shift type
        var availableSpringers = await GetAvailableSpringers(date, originalShift.ShiftTypeId);

        if (!availableSpringers.Any())
            return null;

        // Select springer with lowest recent workload
        var springer = await SelectSpringerByWorkload(availableSpringers, date);

        if (springer == null)
            return null;

        // Get the absent employee name for the note
        var absentEmployee = await _employeeRepository.GetByIdAsync(absentEmployeeId);
        var absentEmployeeName = absentEmployee?.FullName ?? $"Mitarbeiter {absentEmployeeId}";

        // Create springer assignment
        var springerAssignment = new ShiftAssignment
        {
            EmployeeId = springer.Id,
            ShiftTypeId = originalShift.ShiftTypeId,
            Date = date,
            IsManual = false,
            IsSpringerAssignment = true,
            Notes = $"Vertretung für {absentEmployeeName}"
        };

        return await _shiftAssignmentRepository.AddAsync(springerAssignment);
    }

    /// <summary>
    /// Validates that springer allocation doesn't leave the system without backup
    /// </summary>
    public async Task<(bool IsValid, string? ErrorMessage)> ValidateSpringerAllocation(
        List<ShiftAssignment> proposedAssignments, DateTime date)
    {
        var springers = await _employeeRepository.GetSpringersAsync();
        var absences = await _absenceRepository.GetByDateRangeAsync(date, date);

        var assignedSpringerIds = proposedAssignments
            .Where(a => a.Date.Date == date.Date)
            .Where(a => springers.Any(s => s.Id == a.EmployeeId))
            .Select(a => a.EmployeeId)
            .ToHashSet();

        var availableSpringerCount = 0;

        foreach (var springer in springers)
        {
            var isAbsent = absences.Any(a => 
                a.EmployeeId == springer.Id && 
                a.StartDate <= date && 
                a.EndDate >= date);

            if (!isAbsent && !assignedSpringerIds.Contains(springer.Id))
            {
                availableSpringerCount++;
            }
        }

        if (availableSpringerCount == 0)
        {
            return (false, "Mindestens ein Springer muss verfügbar bleiben");
        }

        return (true, null);
    }

    /// <summary>
    /// Selects the best springer based on workload distribution
    /// </summary>
    private async Task<Employee?> SelectSpringerByWorkload(List<Employee> springers, DateTime upToDate)
    {
        if (!springers.Any())
            return null;

        var startDate = upToDate.AddDays(-30);
        var recentAssignments = await _shiftAssignmentRepository.GetByDateRangeAsync(startDate, upToDate);

        var workloadMap = springers.ToDictionary(s => s.Id, s => 0);

        foreach (var assignment in recentAssignments)
        {
            if (workloadMap.ContainsKey(assignment.EmployeeId))
            {
                workloadMap[assignment.EmployeeId]++;
            }
        }

        // Return springer with lowest workload
        return springers.OrderBy(s => workloadMap[s.Id]).First();
    }

    private string GetShiftCodeById(int id)
    {
        return id switch
        {
            1 => ShiftTypeCodes.Frueh,
            2 => ShiftTypeCodes.Spaet,
            3 => ShiftTypeCodes.Nacht,
            4 => ShiftTypeCodes.Zwischendienst,
            5 => ShiftTypeCodes.BMT,
            6 => ShiftTypeCodes.BSB,
            _ => ShiftTypeCodes.Frueh
        };
    }
}
