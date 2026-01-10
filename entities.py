"""
Data models for the shift planning system.
Maps .NET entities to Python dataclasses.
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional, List
from enum import Enum


class AbsenceType(Enum):
    """
    Types of absence - OFFICIAL STANDARD CODES
    
    MANDATORY CODES:
    - U (Urlaub) = Vacation
    - AU (Arbeitsunfähigkeit / Krank) = Sick leave / Medical certificate
    - L (Lehrgang) = Training / Course
    
    FORBIDDEN: "V" and "K" must NOT be used
    """
    AU = "AU"  # Sick leave / Medical certificate (Arbeitsunfähigkeit)
    U = "U"   # Vacation (Urlaub)
    L = "L"   # Training / Course (Lehrgang)
    
    # Helper properties for display names
    @property
    def display_name(self) -> str:
        """Get display name for the absence type"""
        display_names = {
            "AU": "Krank / AU",
            "U": "Urlaub",
            "L": "Lehrgang"
        }
        return display_names.get(self.value, self.value)


class ShiftTypeCode(Enum):
    """Shift type codes"""
    FRUEH = "F"  # Early shift: 05:45-13:45
    SPAET = "S"  # Late shift: 13:45-21:45
    NACHT = "N"  # Night shift: 21:45-05:45
    ZWISCHENDIENST = "ZD"  # Intermediate shift: 08:00-16:00
    TA = "TA"  # Technical Assistant
    TD = "TD"  # Technical Service
    BMT = "BMT"  # Fire Alarm Technician: Mon-Fri, 06:00-14:00
    BSB = "BSB"  # Fire Safety Officer: Mon-Fri, 07:00-16:30 (9.5 hours)


@dataclass
class ShiftType:
    """Represents a shift type with timing and duration"""
    id: int
    code: str
    name: str
    start_time: str  # Format: "HH:MM"
    end_time: str  # Format: "HH:MM"
    color_code: Optional[str] = None
    hours: float = 8.0  # Duration in hours (daily)
    weekly_working_hours: float = 40.0  # Expected weekly working hours (standard work week default)
    min_staff_weekday: int = 3  # Minimum staff on weekdays
    max_staff_weekday: int = 5  # Maximum staff on weekdays
    min_staff_weekend: int = 2  # Minimum staff on weekends
    max_staff_weekend: int = 3  # Maximum staff on weekends
    works_monday: bool = True  # Works on Monday
    works_tuesday: bool = True  # Works on Tuesday
    works_wednesday: bool = True  # Works on Wednesday
    works_thursday: bool = True  # Works on Thursday
    works_friday: bool = True  # Works on Friday
    works_saturday: bool = False  # Works on Saturday
    works_sunday: bool = False  # Works on Sunday
    
    def works_on_date(self, d: date) -> bool:
        """Check if this shift type works on the given date"""
        weekday = d.weekday()  # Monday=0, Sunday=6
        return [
            self.works_monday,
            self.works_tuesday,
            self.works_wednesday,
            self.works_thursday,
            self.works_friday,
            self.works_saturday,
            self.works_sunday
        ][weekday]
    
    def get_duration_hours(self) -> float:
        """Calculate duration in hours"""
        # Parse time strings
        start_parts = self.start_time.split(":")
        end_parts = self.end_time.split(":")
        
        start_minutes = int(start_parts[0]) * 60 + int(start_parts[1])
        end_minutes = int(end_parts[0]) * 60 + int(end_parts[1])
        
        # Handle overnight shifts (e.g., night shift)
        if end_minutes <= start_minutes:
            end_minutes += 24 * 60
        
        duration_minutes = end_minutes - start_minutes
        return duration_minutes / 60.0
    
    def get_monthly_hours(self) -> float:
        """
        Calculate expected monthly hours assuming 4-week planning periods.
        
        Note: This is a simplified calculation. Actual months vary from 28-31 days,
        but the system uses 4-week planning periods for consistency.
        """
        return self.weekly_working_hours * 4.0


@dataclass
class Employee:
    """Represents an employee in the shift system"""
    id: int
    vorname: str  # First name
    name: str  # Last name
    personalnummer: str  # Personnel number
    email: Optional[str] = None
    geburtsdatum: Optional[date] = None  # Birth date
    funktion: Optional[str] = None  # Function/Role
    is_ferienjobber: bool = False  # Temporary worker
    is_brandmeldetechniker: bool = False  # BMT qualified (for legacy compatibility)
    is_brandschutzbeauftragter: bool = False  # BSB qualified (for legacy compatibility)
    is_td_qualified: bool = False  # TD (Tagdienst) qualified - combines BMT and BSB
    is_team_leader: bool = False  # Team leader
    team_id: Optional[int] = None
    
    @property
    def full_name(self) -> str:
        return f"{self.vorname} {self.name}"
    
    @property
    def can_do_td(self) -> bool:
        """Check if employee can perform TD (Tagdienst) function"""
        return self.is_td_qualified or self.is_brandmeldetechniker or self.is_brandschutzbeauftragter


@dataclass
class Team:
    """Represents a team of employees"""
    id: int
    name: str
    description: Optional[str] = None
    email: Optional[str] = None
    is_virtual: bool = False  # Virtual teams (e.g., "Fire Alarm System") for display only
    employees: List[Employee] = field(default_factory=list)
    allowed_shift_type_ids: List[int] = field(default_factory=list)  # Shift types this team can work (from TeamShiftAssignments)


@dataclass
class Absence:
    """
    Represents an employee absence.
    
    CRITICAL: Absences are AUTHORITATIVE and must ALWAYS override:
    - Regular shifts (F, S, N)
    - TD (Day Duty)
    - Any other assignments
    
    Absences MUST:
    - Be visible in all views
    - Persist through re-solving
    - Only be changed by Admin/Dispatcher
    """
    id: int
    employee_id: int
    absence_type: AbsenceType
    start_date: date
    end_date: date
    notes: Optional[str] = None
    is_locked: bool = True  # Absences are locked by default to prevent loss
    
    def overlaps_date(self, check_date: date) -> bool:
        """Check if absence overlaps with given date"""
        return self.start_date <= check_date <= self.end_date
    
    def get_code(self) -> str:
        """Get the absence code (U, AU, or L)"""
        return self.absence_type.value


@dataclass
class ShiftAssignment:
    """Represents a shift assignment to an employee"""
    id: int
    employee_id: int
    shift_type_id: int
    date: date
    is_manual: bool = False
    is_fixed: bool = False
    notes: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    modified_at: Optional[datetime] = None
    created_by: Optional[str] = None
    modified_by: Optional[str] = None


@dataclass
class VacationRequest:
    """Represents a vacation request from an employee"""
    id: int
    employee_id: int
    start_date: date
    end_date: date
    status: str = "InBearbeitung"  # InBearbeitung, Genehmigt, NichtGenehmigt
    notes: Optional[str] = None
    disponent_response: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    processed_by: Optional[str] = None


@dataclass
class VacationPeriod:
    """
    Represents a vacation/holiday period (Ferienzeit).
    E.g., Summer vacation, Christmas holidays, Easter break, etc.
    These periods are displayed at the top of calendar views.
    """
    id: int
    name: str  # e.g., "Sommerferien", "Weihnachtsferien", "Osterferien"
    start_date: date
    end_date: date
    color_code: Optional[str] = "#E8F5E9"  # Light green default
    created_at: datetime = field(default_factory=datetime.utcnow)
    modified_at: Optional[datetime] = None
    created_by: Optional[str] = None
    modified_by: Optional[str] = None
    
    def overlaps_date(self, check_date: date) -> bool:
        """Check if vacation period overlaps with given date"""
        return self.start_date <= check_date <= self.end_date


# Predefined shift types for the system
STANDARD_SHIFT_TYPES = [
    ShiftType(1, "F", "Frühdienst", "05:45", "13:45", "#FFD700", 8.0, 40.0, 3, 5, 2, 3, True, True, True, True, True, True, True),
    ShiftType(2, "S", "Spätdienst", "13:45", "21:45", "#FF6347", 8.0, 40.0, 3, 5, 2, 3, True, True, True, True, True, True, True),
    ShiftType(3, "N", "Nachtdienst", "21:45", "05:45", "#4169E1", 8.0, 40.0, 3, 3, 2, 3, True, True, True, True, True, True, True),
    ShiftType(4, "ZD", "Zwischendienst", "08:00", "16:00", "#90EE90", 8.0, 40.0, 3, 5, 2, 3, True, True, True, True, True, False, False),
    ShiftType(5, "BMT", "Brandmeldetechniker", "06:00", "14:00", "#FFA500", 8.0, 40.0, 1, 2, 0, 0, True, True, True, True, True, False, False),
    ShiftType(6, "BSB", "Brandschutzbeauftragter", "07:00", "16:30", "#9370DB", 9.5, 40.0, 1, 2, 0, 0, True, True, True, True, True, False, False),
]


def get_shift_type_by_code(code: str) -> Optional[ShiftType]:
    """Get shift type by code"""
    for shift_type in STANDARD_SHIFT_TYPES:
        if shift_type.code == code:
            return shift_type
    return None


def get_shift_type_by_id(shift_id: int) -> Optional[ShiftType]:
    """Get shift type by ID"""
    for shift_type in STANDARD_SHIFT_TYPES:
        if shift_type.id == shift_id:
            return shift_type
    return None
