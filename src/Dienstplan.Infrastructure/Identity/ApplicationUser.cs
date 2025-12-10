using Microsoft.AspNetCore.Identity;
using Dienstplan.Domain.Entities;

namespace Dienstplan.Infrastructure.Identity;

/// <summary>
/// Application user for authentication
/// </summary>
public class ApplicationUser : IdentityUser
{
    public string? FullName { get; set; }
    
    /// <summary>
    /// Link to employee if this user is an employee
    /// </summary>
    public int? EmployeeId { get; set; }
    public Employee? Employee { get; set; }
}
