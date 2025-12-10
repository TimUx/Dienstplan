namespace Dienstplan.Domain.Entities;

/// <summary>
/// Represents a team of employees
/// </summary>
public class Team
{
    public int Id { get; set; }
    
    public string Name { get; set; } = string.Empty;
    
    public string? Description { get; set; }
    
    /// <summary>
    /// Employees in this team
    /// </summary>
    public ICollection<Employee> Employees { get; set; } = new List<Employee>();
}
