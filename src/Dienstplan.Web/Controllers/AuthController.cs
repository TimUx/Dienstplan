using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Mvc;
using Dienstplan.Infrastructure.Identity;

namespace Dienstplan.Web.Controllers;

[ApiController]
[Route("api/[controller]")]
public class AuthController : ControllerBase
{
    private readonly SignInManager<ApplicationUser> _signInManager;
    private readonly UserManager<ApplicationUser> _userManager;

    public AuthController(SignInManager<ApplicationUser> signInManager, UserManager<ApplicationUser> userManager)
    {
        _signInManager = signInManager;
        _userManager = userManager;
    }

    [HttpPost("login")]
    public async Task<ActionResult> Login([FromBody] LoginRequest request)
    {
        var user = await _userManager.FindByEmailAsync(request.Email);
        if (user == null)
        {
            return Unauthorized(new { error = "Ungültige Anmeldedaten" });
        }

        var result = await _signInManager.PasswordSignInAsync(user, request.Password, request.RememberMe, lockoutOnFailure: true);
        
        if (result.Succeeded)
        {
            var roles = await _userManager.GetRolesAsync(user);
            return Ok(new 
            { 
                success = true,
                user = new 
                {
                    email = user.Email,
                    fullName = user.FullName,
                    roles = roles
                }
            });
        }
        
        if (result.IsLockedOut)
        {
            return Unauthorized(new { error = "Konto ist gesperrt. Bitte versuchen Sie es später erneut." });
        }
        
        return Unauthorized(new { error = "Ungültige Anmeldedaten" });
    }

    [HttpPost("logout")]
    public async Task<ActionResult> Logout()
    {
        await _signInManager.SignOutAsync();
        return Ok(new { success = true });
    }

    [HttpGet("current-user")]
    public async Task<ActionResult> GetCurrentUser()
    {
        if (User.Identity?.IsAuthenticated != true)
        {
            return Unauthorized();
        }

        var user = await _userManager.GetUserAsync(User);
        if (user == null)
        {
            return Unauthorized();
        }

        var roles = await _userManager.GetRolesAsync(user);
        
        return Ok(new 
        { 
            email = user.Email,
            fullName = user.FullName,
            roles = roles
        });
    }

    [HttpPost("register")]
    [Authorize(Roles = "Admin")]
    public async Task<ActionResult> Register([FromBody] RegisterRequest request)
    {
        if (await _userManager.FindByEmailAsync(request.Email) != null)
        {
            return BadRequest(new { error = "E-Mail-Adresse wird bereits verwendet" });
        }

        var user = new ApplicationUser
        {
            UserName = request.Email,
            Email = request.Email,
            FullName = request.FullName,
            EmailConfirmed = true
        };

        var result = await _userManager.CreateAsync(user, request.Password);
        
        if (!result.Succeeded)
        {
            return BadRequest(new { error = "Benutzer konnte nicht erstellt werden", errors = result.Errors });
        }

        // Assign role
        if (!string.IsNullOrEmpty(request.Role))
        {
            await _userManager.AddToRoleAsync(user, request.Role);
        }

        return Ok(new { success = true, userId = user.Id });
    }

    [HttpPost("change-password")]
    [Authorize]
    public async Task<ActionResult> ChangePassword([FromBody] ChangePasswordRequest request)
    {
        var user = await _userManager.GetUserAsync(User);
        if (user == null)
        {
            return Unauthorized();
        }

        var result = await _userManager.ChangePasswordAsync(user, request.CurrentPassword, request.NewPassword);
        
        if (!result.Succeeded)
        {
            return BadRequest(new { error = "Passwort konnte nicht geändert werden", errors = result.Errors });
        }

        return Ok(new { success = true });
    }
}

public record LoginRequest(string Email, string Password, bool RememberMe = false);
public record RegisterRequest(string Email, string Password, string FullName, string Role = "Mitarbeiter");
public record ChangePasswordRequest(string CurrentPassword, string NewPassword);
