"""
Data models for the shift planning system.
Maps .NET entities to Python dataclasses.
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional, List
from enum import Enum


class AbsenceType(Enum):
    """Types of absence"""
    KRANK = "Krank"  # Sick leave
    URLAUB = "Urlaub"  # Vacation
    LEHRGANG = "Lehrgang"  # Training


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
    hours: float = 8.0  # Duration in hours
    
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
    is_springer: bool = False  # Backup worker
    is_ferienjobber: bool = False  # Temporary worker
    is_brandmeldetechniker: bool = False  # BMT qualified
    is_brandschutzbeauftragter: bool = False  # BSB qualified
    team_id: Optional[int] = None
    
    @property
    def full_name(self) -> str:
        return f"{self.vorname} {self.name}"


@dataclass
class Team:
    """Represents a team of employees"""
    id: int
    name: str
    description: Optional[str] = None
    email: Optional[str] = None
    employees: List[Employee] = field(default_factory=list)


@dataclass
class Absence:
    """Represents an employee absence"""
    id: int
    employee_id: int
    absence_type: AbsenceType
    start_date: date
    end_date: date
    notes: Optional[str] = None
    
    def overlaps_date(self, check_date: date) -> bool:
        """Check if absence overlaps with given date"""
        return self.start_date <= check_date <= self.end_date


@dataclass
class ShiftAssignment:
    """Represents a shift assignment to an employee"""
    id: int
    employee_id: int
    shift_type_id: int
    date: date
    is_manual: bool = False
    is_springer_assignment: bool = False
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


# Predefined shift types for the system
STANDARD_SHIFT_TYPES = [
    ShiftType(1, "F", "Frühdienst", "05:45", "13:45", "#FFD700", 8.0),
    ShiftType(2, "S", "Spätdienst", "13:45", "21:45", "#FF6347", 8.0),
    ShiftType(3, "N", "Nachtdienst", "21:45", "05:45", "#4169E1", 8.0),
    ShiftType(4, "ZD", "Zwischendienst", "08:00", "16:00", "#90EE90", 8.0),
    ShiftType(5, "BMT", "Brandmeldetechniker", "06:00", "14:00", "#FFA500", 8.0),
    ShiftType(6, "BSB", "Brandschutzbeauftragter", "07:00", "16:30", "#9370DB", 9.5),
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
