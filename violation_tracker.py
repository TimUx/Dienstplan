"""
Violation Tracker for Shift Planning

Tracks all constraint violations and relaxations during shift planning.
Provides human-readable summaries for admin review.

Used when soft constraints are violated to meet mandatory requirements.
"""

from datetime import date
from typing import List, Dict, Any
from dataclasses import dataclass, field


@dataclass
class Violation:
    """Represents a single constraint violation"""
    category: str  # "max_staffing", "rest_time", "working_hours", etc.
    severity: str  # "INFO", "WARNING", "CRITICAL"
    date: date = None
    employee_id: int = None
    employee_name: str = None
    team_id: int = None
    team_name: str = None
    shift_type: str = None
    description: str = ""
    value_expected: Any = None
    value_actual: Any = None
    reason: str = ""  # Why this violation occurred (e.g., "absence", "team_rotation")


class ViolationTracker:
    """
    Tracks constraint violations during shift planning.
    
    Usage:
        tracker = ViolationTracker()
        tracker.add_violation("max_staffing", "WARNING", date=d, shift_type="F", 
                             description="Exceeded max staffing", ...)
        summary = tracker.get_summary()
    """
    
    def __init__(self):
        self.violations: List[Violation] = []
    
    def add_violation(
        self,
        category: str,
        severity: str,
        date: date = None,
        employee_id: int = None,
        employee_name: str = None,
        team_id: int = None,
        team_name: str = None,
        shift_type: str = None,
        description: str = "",
        value_expected: Any = None,
        value_actual: Any = None,
        reason: str = ""
    ):
        """Add a violation to the tracker"""
        violation = Violation(
            category=category,
            severity=severity,
            date=date,
            employee_id=employee_id,
            employee_name=employee_name,
            team_id=team_id,
            team_name=team_name,
            shift_type=shift_type,
            description=description,
            value_expected=value_expected,
            value_actual=value_actual,
            reason=reason
        )
        self.violations.append(violation)
    
    def get_violations(self) -> List[Violation]:
        """Get all recorded violations"""
        return self.violations
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Generate a comprehensive summary of all violations.
        
        Returns:
            Dictionary with categorized violations and statistics
        """
        if not self.violations:
            return {
                "total": 0,
                "by_severity": {},
                "by_category": {},
                "critical_violations": [],
                "warnings": [],
                "info": [],
                "message": "✅ Alle Regeln wurden eingehalten. Keine Abweichungen."
            }
        
        # Count by severity
        by_severity = {}
        for v in self.violations:
            by_severity[v.severity] = by_severity.get(v.severity, 0) + 1
        
        # Count by category
        by_category = {}
        for v in self.violations:
            by_category[v.category] = by_category.get(v.category, 0) + 1
        
        # Categorize violations
        critical = [v for v in self.violations if v.severity == "CRITICAL"]
        warnings = [v for v in self.violations if v.severity == "WARNING"]
        info = [v for v in self.violations if v.severity == "INFO"]
        
        # Format detailed violations
        def format_violation(v: Violation) -> str:
            parts = []
            if v.date:
                parts.append(f"Datum: {v.date.strftime('%d.%m.%Y')}")
            if v.employee_name:
                parts.append(f"Mitarbeiter: {v.employee_name}")
            if v.team_name:
                parts.append(f"Team: {v.team_name}")
            if v.shift_type:
                parts.append(f"Schicht: {v.shift_type}")
            parts.append(v.description)
            if v.value_expected is not None and v.value_actual is not None:
                parts.append(f"Erwartet: {v.value_expected}, Tatsächlich: {v.value_actual}")
            if v.reason:
                parts.append(f"Grund: {v.reason}")
            return " | ".join(parts)
        
        critical_formatted = [format_violation(v) for v in critical]
        warnings_formatted = [format_violation(v) for v in warnings]
        info_formatted = [format_violation(v) for v in info]
        
        # Generate summary message
        message_parts = []
        if critical:
            message_parts.append(f"⚠️ KRITISCH: {len(critical)} kritische Abweichungen gefunden!")
        if warnings:
            message_parts.append(f"⚠️ WARNUNG: {len(warnings)} Warnungen - Manuelle Prüfung empfohlen")
        if info:
            message_parts.append(f"ℹ️ INFO: {len(info)} Hinweise zur Planung")
        
        message = " | ".join(message_parts) if message_parts else "Abweichungen gefunden"
        
        return {
            "total": len(self.violations),
            "by_severity": by_severity,
            "by_category": by_category,
            "critical_violations": critical_formatted,
            "warnings": warnings_formatted,
            "info": info_formatted,
            "message": message,
            "details": {
                "critical": [self._violation_to_dict(v) for v in critical],
                "warnings": [self._violation_to_dict(v) for v in warnings],
                "info": [self._violation_to_dict(v) for v in info]
            }
        }
    
    def _violation_to_dict(self, v: Violation) -> Dict[str, Any]:
        """Convert violation to dictionary for JSON serialization"""
        return {
            "category": v.category,
            "severity": v.severity,
            "date": v.date.isoformat() if v.date else None,
            "employee_id": v.employee_id,
            "employee_name": v.employee_name,
            "team_id": v.team_id,
            "team_name": v.team_name,
            "shift_type": v.shift_type,
            "description": v.description,
            "value_expected": v.value_expected,
            "value_actual": v.value_actual,
            "reason": v.reason
        }
    
    def has_critical_violations(self) -> bool:
        """Check if there are any critical violations"""
        return any(v.severity == "CRITICAL" for v in self.violations)
    
    def has_violations(self) -> bool:
        """Check if there are any violations at all"""
        return len(self.violations) > 0
