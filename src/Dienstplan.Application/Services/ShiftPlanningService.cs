using Dienstplan.Domain.Entities;
using Dienstplan.Domain.Interfaces;
using Dienstplan.Domain.Rules;

namespace Dienstplan.Application.Services;

public class ShiftPlanningService : IShiftPlanningService
{
    private readonly IEmployeeRepository _employeeRepository;
    private readonly IShiftAssignmentRepository _shiftAssignmentRepository;
    private readonly IAbsenceRepository _absenceRepository;

    public ShiftPlanningService(
        IEmployeeRepository employeeRepository,
        IShiftAssignmentRepository shiftAssignmentRepository,
        IAbsenceRepository absenceRepository)
    {
        _employeeRepository = employeeRepository;
        _shiftAssignmentRepository = shiftAssignmentRepository;
        _absenceRepository = absenceRepository;
    }

    public async Task<List<ShiftAssignment>> PlanShifts(DateTime startDate, DateTime endDate, bool force = false)
    {
        var assignments = new List<ShiftAssignment>();
        
        if (!force)
        {
            // Check if there are already assignments
            var existing = await _shiftAssignmentRepository.GetByDateRangeAsync(startDate, endDate);
            if (existing.Any())
            {
                return existing.ToList();
            }
        }
        
        var employees = (await _employeeRepository.GetAllAsync())
            .Where(e => !e.IsSpringer) // Exclude Springers from regular planning
            .ToList();
            
        var absences = await _absenceRepository.GetByDateRangeAsync(startDate, endDate);
        
        // Plan for each day
        for (var date = startDate; date <= endDate; date = date.AddDays(1))
        {
            var dayAssignments = await PlanDayShifts(date, employees, absences.ToList());
            assignments.AddRange(dayAssignments);
        }
        
        return assignments;
    }

    private async Task<List<ShiftAssignment>> PlanDayShifts(DateTime date, List<Employee> employees, List<Absence> absences)
    {
        var assignments = new List<ShiftAssignment>();
        var isWeekend = date.DayOfWeek == DayOfWeek.Saturday || date.DayOfWeek == DayOfWeek.Sunday;
        
        // Get available employees for this date
        var availableEmployees = employees.Where(e => 
            !absences.Any(a => a.EmployeeId == e.Id && 
                               a.StartDate <= date && 
                               a.EndDate >= date)).ToList();
        
        // Determine required shifts and counts
        var shiftRequirements = GetShiftRequirements(isWeekend);
        
        // Assign shifts following the ideal rotation (Früh → Nacht → Spät)
        var employeeIndex = 0;
        foreach (var (shiftCode, count) in shiftRequirements)
        {
            for (int i = 0; i < count && employeeIndex < availableEmployees.Count; i++)
            {
                var employee = availableEmployees[employeeIndex % availableEmployees.Count];
                
                // Check if assignment is valid
                var assignment = new ShiftAssignment
                {
                    EmployeeId = employee.Id,
                    ShiftTypeId = GetShiftTypeIdByCode(shiftCode),
                    Date = date,
                    IsManual = false
                };
                
                var (isValid, _) = await ValidateShiftAssignment(assignment);
                if (isValid)
                {
                    assignments.Add(assignment);
                }
                
                employeeIndex++;
            }
        }
        
        return assignments;
    }

    private List<(string ShiftCode, int Count)> GetShiftRequirements(bool isWeekend)
    {
        if (isWeekend)
        {
            return new List<(string, int)>
            {
                (ShiftTypeCodes.Frueh, ShiftRules.WeekendStaffing.MaxPerShift),
                (ShiftTypeCodes.Spaet, ShiftRules.WeekendStaffing.MaxPerShift),
                (ShiftTypeCodes.Nacht, ShiftRules.WeekendStaffing.MaxPerShift)
            };
        }
        else
        {
            return new List<(string, int)>
            {
                (ShiftTypeCodes.Frueh, ShiftRules.WeekdayStaffing.FruehMin),
                (ShiftTypeCodes.Spaet, ShiftRules.WeekdayStaffing.SpaetMin),
                (ShiftTypeCodes.Nacht, ShiftRules.WeekdayStaffing.NachtMin)
            };
        }
    }

    public async Task<(bool IsValid, string? ErrorMessage)> ValidateShiftAssignment(ShiftAssignment assignment)
    {
        // Get previous shift
        var previousShift = await _shiftAssignmentRepository.GetByEmployeeAndDateAsync(
            assignment.EmployeeId, 
            assignment.Date.AddDays(-1));
        
        if (previousShift != null)
        {
            var previousShiftCode = GetShiftCodeById(previousShift.ShiftTypeId);
            var currentShiftCode = GetShiftCodeById(assignment.ShiftTypeId);
            
            // Check forbidden transitions
            if (ShiftRules.ForbiddenTransitions.ContainsKey(previousShiftCode))
            {
                if (ShiftRules.ForbiddenTransitions[previousShiftCode].Contains(currentShiftCode))
                {
                    return (false, $"Verbotener Schichtwechsel: {previousShiftCode} → {currentShiftCode}");
                }
            }
            
            // Check for same shift twice in a row
            if (previousShiftCode == currentShiftCode)
            {
                return (false, "Dieselbe Schicht darf nicht zweimal hintereinander zugewiesen werden");
            }
        }
        
        // Check if employee is absent
        var absences = await _absenceRepository.GetByEmployeeIdAsync(assignment.EmployeeId);
        if (absences.Any(a => a.StartDate <= assignment.Date && a.EndDate >= assignment.Date))
        {
            return (false, "Mitarbeiter ist an diesem Tag abwesend");
        }
        
        return (true, null);
    }

    public async Task<ShiftAssignment?> AssignSpringer(int employeeId, DateTime date)
    {
        // Find the shift that needs to be covered
        var originalAssignment = await _shiftAssignmentRepository.GetByEmployeeAndDateAsync(employeeId, date);
        if (originalAssignment == null)
        {
            return null;
        }
        
        // Get the employee to determine their team
        var employee = await _employeeRepository.GetByIdAsync(employeeId);
        if (employee == null)
        {
            return null;
        }
        
        // Get available Springers from the same team
        var springers = await _employeeRepository.GetSpringersAsync(employee.TeamId);
        var absences = await _absenceRepository.GetByDateRangeAsync(date, date);
        
        var availableSpringers = springers.Where(s => 
            !absences.Any(a => a.EmployeeId == s.Id && 
                               a.StartDate <= date && 
                               a.EndDate >= date)).ToList();
        
        if (!availableSpringers.Any())
        {
            return null;
        }
        
        // Assign first available Springer
        var springer = availableSpringers.First();
        var springerAssignment = new ShiftAssignment
        {
            EmployeeId = springer.Id,
            ShiftTypeId = originalAssignment.ShiftTypeId,
            Date = date,
            IsManual = false,
            IsSpringerAssignment = true
        };
        
        return await _shiftAssignmentRepository.AddAsync(springerAssignment);
    }
    
    private int GetShiftTypeIdByCode(string code)
    {
        return code switch
        {
            ShiftTypeCodes.Frueh => 1,
            ShiftTypeCodes.Spaet => 2,
            ShiftTypeCodes.Nacht => 3,
            ShiftTypeCodes.Zwischendienst => 4,
            _ => 1
        };
    }
    
    private string GetShiftCodeById(int id)
    {
        return id switch
        {
            1 => ShiftTypeCodes.Frueh,
            2 => ShiftTypeCodes.Spaet,
            3 => ShiftTypeCodes.Nacht,
            4 => ShiftTypeCodes.Zwischendienst,
            _ => ShiftTypeCodes.Frueh
        };
    }
}
