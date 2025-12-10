using Dienstplan.Domain.Entities;

namespace Dienstplan.Domain.Interfaces;

/// <summary>
/// Repository interface for data access
/// </summary>
public interface IRepository<T> where T : class
{
    Task<T?> GetByIdAsync(int id);
    Task<IEnumerable<T>> GetAllAsync();
    Task<T> AddAsync(T entity);
    Task<T> UpdateAsync(T entity);
    Task DeleteAsync(int id);
}

public interface IEmployeeRepository : IRepository<Employee>
{
    Task<IEnumerable<Employee>> GetSpringersAsync();
    Task<IEnumerable<Employee>> GetByTeamIdAsync(int teamId);
    Task<Employee?> GetByPersonalnummerAsync(string personalnummer);
}

public interface IShiftAssignmentRepository : IRepository<ShiftAssignment>
{
    Task<IEnumerable<ShiftAssignment>> GetByDateRangeAsync(DateTime startDate, DateTime endDate);
    Task<IEnumerable<ShiftAssignment>> GetByEmployeeIdAsync(int employeeId);
    Task<ShiftAssignment?> GetByEmployeeAndDateAsync(int employeeId, DateTime date);
}

public interface IAbsenceRepository : IRepository<Absence>
{
    Task<IEnumerable<Absence>> GetByEmployeeIdAsync(int employeeId);
    Task<IEnumerable<Absence>> GetByDateRangeAsync(DateTime startDate, DateTime endDate);
}
