using Microsoft.AspNetCore.Mvc;
using Dienstplan.Domain.Entities;
using Dienstplan.Domain.Interfaces;

namespace Dienstplan.Web.Controllers;

[ApiController]
[Route("api/[controller]")]
public class ShiftTypesController : ControllerBase
{
    private readonly IRepository<ShiftType> _shiftTypeRepository;

    public ShiftTypesController(IRepository<ShiftType> shiftTypeRepository)
    {
        _shiftTypeRepository = shiftTypeRepository;
    }

    [HttpGet]
    public async Task<ActionResult<IEnumerable<ShiftType>>> GetAll()
    {
        var shiftTypes = await _shiftTypeRepository.GetAllAsync();
        return Ok(shiftTypes);
    }

    [HttpGet("{id}")]
    public async Task<ActionResult<ShiftType>> GetById(int id)
    {
        var shiftType = await _shiftTypeRepository.GetByIdAsync(id);
        if (shiftType == null)
        {
            return NotFound();
        }
        return Ok(shiftType);
    }
}
