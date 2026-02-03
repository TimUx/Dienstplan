# Changelog

## Version 2.1 - Python Edition (January 2026)

### Updates
- Version bump to 2.1
- Updated build and release workflows to use v2.1.x versioning scheme
- Updated documentation and UI to reflect version 2.1

### Bug Fixes (February 2026)
- **Fixed**: Added weekly shift type consistency constraint (CRITICAL FIX)
  - Issue: "Erneut wurden einzelnen Schichten zwischen andere Schichten geplant"
  - Problem: Employees were assigned different shift types within the same week (e.g., F-F-S-S in one week)
  - Root cause: Missing constraint to enforce team-based model's core principle
  - Solution: Added constraint ensuring employees work only ONE shift type per week
  - Impact: Schedules now properly follow F → N → S rotation pattern with no intra-week changes
  - Details: See INTRA_WEEK_SHIFT_FIX.md for complete analysis and implementation
- **Fixed**: Rest time constraint penalties increased to prevent S→F and N→F violations
  - Previous penalties (50/500 points) were too low compared to other constraints
  - Solver was preferring rest time violations over other soft constraints
  - New penalties: Sunday→Monday 5000 points, Weekdays 50000 points
  - This ensures rest time violations only occur when absolutely necessary for feasibility
  - Issue: 7 forbidden transitions found in February schedule (S→F with only 8h rest)

## Version 2.0 - Python Edition (December 2025)

### Major Changes

#### Migration from .NET to Python ✅
- **Complete rewrite** of backend from C# to Python
- **New solver**: Google OR-Tools CP-SAT for optimal shift planning
- **Framework change**: ASP.NET Core → Flask
- **Same UI**: Web interface (HTML/CSS/JS) unchanged

#### Removed
- ❌ All .NET source code (C#, .csproj files)
- ❌ .NET solution and build files
- ❌ .NET-specific scripts and tooling
- ❌ Custom shift planning algorithm

#### Added
- ✅ Python implementation with OR-Tools
- ✅ Constraint Programming approach for scheduling
- ✅ Improved documentation for Python
- ✅ Sample data generation via CLI
- ✅ Flexible deployment options (Docker, systemd, etc.)

#### Benefits
- ✅ **Better solution quality**: OR-Tools finds optimal/near-optimal solutions
- ✅ **Easier maintenance**: Clearer separation of concerns
- ✅ **More flexible**: Easy to add new constraints
- ✅ **Platform independent**: No .NET runtime required
- ✅ **Open source**: Fully based on open-source technologies

### Documentation Updates
- 📝 Rewrote README.md for Python version
- 📝 Updated ARCHITECTURE.md with Python structure
- 📝 New USAGE_GUIDE.md with Python CLI/API
- 📝 Updated SAMPLE_DATA.md for Python
- 📝 Comprehensive SHIFT_PLANNING_ALGORITHM.md
- 📝 Updated Web UI system information

### Technical Details
- **Language**: Python 3.9+
- **Solver**: Google OR-Tools 9.8+
- **Web Framework**: Flask 3.0+
- **Database**: SQLite (unchanged)
- **Frontend**: Vanilla JavaScript (unchanged)

### Migration Path
See [MIGRATION.md](MIGRATION.md) for detailed migration information.

### Compatibility
- ✅ Database schema compatible with previous version
- ✅ REST API endpoints unchanged
- ✅ Web UI fully compatible
- ✅ All features preserved

---

## Version 1.3 (Previous .NET Version)

### Features
- Enhanced Springer Management
- Fairness Tracking
- Automatic Special Functions (BMT/BSB)
- Qualification Management
- Excel Export
- Flexible Scaling

### Technical
- ASP.NET Core 10.0
- Entity Framework Core
- SQLite Database
- Custom scheduling algorithm

---

**For detailed version history, see Git commit log.**

© 2025 Fritz Winter Eisengießerei GmbH & Co. KG
