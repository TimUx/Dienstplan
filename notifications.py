"""
Notification system for the shift planning system.

This module defines notification triggers, recipients, and message payloads.
NO SMTP implementation - just the structure for notification triggers.

As per requirements:
- Notify when absences are entered after scheduling
- Notify when springer is automatically assigned
- Notify when no replacement is possible
- Notify when locked assignment prevents optimization
"""

from dataclasses import dataclass
from typing import List, Optional
from datetime import date
from entities import Employee, Absence


@dataclass
class NotificationTrigger:
    """Base class for notification triggers"""
    trigger_type: str
    timestamp: date
    description: str


@dataclass
class AbsenceAfterSchedulingNotification(NotificationTrigger):
    """
    Triggered when an absence (U, AU, L) is entered AFTER scheduling is complete.
    
    Recipients:
    - All Admins
    - All Dispatchers
    
    Payload:
    - Employee details (name, personnel number)
    - Absence type (U, AU, L)
    - Absence period (start_date, end_date)
    - Affected shift dates
    - Whether automatic replacement was attempted
    """
    employee: Employee
    absence: Absence
    affected_dates: List[date]
    schedule_month: str  # e.g., "January 2026"
    replacement_attempted: bool
    
    def __post_init__(self):
        super().__init__(
            trigger_type="absence_after_scheduling",
            timestamp=date.today(),
            description=(
                f"{self.employee.full_name} marked as {self.absence.get_code()} "
                f"from {self.absence.start_date} to {self.absence.end_date} "
                f"after schedule was already generated for {self.schedule_month}"
            )
        )
    
    def get_recipients(self) -> List[str]:
        """Return list of recipient roles"""
        return ["Admin", "Disponent"]
    
    def get_message_payload(self) -> dict:
        """Return message data for notification system"""
        return {
            "type": self.trigger_type,
            "employee_id": self.employee.id,
            "employee_name": self.employee.full_name,
            "personnel_number": self.employee.personalnummer,
            "absence_type": self.absence.get_code(),
            "absence_display": self.absence.absence_type.display_name,
            "start_date": self.absence.start_date.isoformat(),
            "end_date": self.absence.end_date.isoformat(),
            "affected_dates": [d.isoformat() for d in self.affected_dates],
            "schedule_month": self.schedule_month,
            "replacement_attempted": self.replacement_attempted,
            "notes": self.absence.notes
        }


@dataclass
class SpringerAssignedNotification(NotificationTrigger):
    """
    Triggered when a springer is automatically assigned to replace an absent employee.
    
    Recipients:
    - The springer (assigned employee)
    - All Admins
    - All Dispatchers
    
    Payload:
    - Springer details
    - Original employee details
    - Shift details (date, shift type)
    - Reason for replacement (absence type)
    """
    springer: Employee
    original_employee: Employee
    shift_date: date
    shift_code: str
    absence_reason: str  # U, AU, or L
    
    def __post_init__(self):
        super().__init__(
            trigger_type="springer_assigned",
            timestamp=date.today(),
            description=(
                f"Springer {self.springer.full_name} automatically assigned to "
                f"{self.shift_code} shift on {self.shift_date} "
                f"replacing {self.original_employee.full_name} ({self.absence_reason})"
            )
        )
    
    def get_recipients(self) -> List[str]:
        """Return list of recipient roles + specific springer"""
        return ["Admin", "Disponent", f"employee_{self.springer.id}"]
    
    def get_message_payload(self) -> dict:
        """Return message data for notification system"""
        return {
            "type": self.trigger_type,
            "springer_id": self.springer.id,
            "springer_name": self.springer.full_name,
            "springer_email": self.springer.email,
            "original_employee_id": self.original_employee.id,
            "original_employee_name": self.original_employee.full_name,
            "shift_date": self.shift_date.isoformat(),
            "shift_code": self.shift_code,
            "absence_reason": self.absence_reason
        }


@dataclass
class NoReplacementAvailableNotification(NotificationTrigger):
    """
    Triggered when no springer replacement is possible for an absent employee.
    
    Recipients:
    - All Admins
    - All Dispatchers
    
    Payload:
    - Absent employee details
    - Shift details (date, shift type, team)
    - Absence reason
    - Why no replacement was possible (all springers busy/absent, rest time violations, etc.)
    - Understaffing impact
    """
    employee: Employee
    shift_date: date
    shift_code: str
    team_name: str
    absence_reason: str
    reason_no_replacement: str
    understaffing_impact: str  # e.g., "Night shift: 2/3 required"
    
    def __post_init__(self):
        super().__init__(
            trigger_type="no_replacement_available",
            timestamp=date.today(),
            description=(
                f"NO REPLACEMENT AVAILABLE for {self.employee.full_name} "
                f"({self.shift_code} shift on {self.shift_date}). "
                f"Reason: {self.reason_no_replacement}"
            )
        )
    
    def get_recipients(self) -> List[str]:
        """Return list of recipient roles"""
        return ["Admin", "Disponent"]
    
    def get_message_payload(self) -> dict:
        """Return message data for notification system"""
        return {
            "type": self.trigger_type,
            "employee_id": self.employee.id,
            "employee_name": self.employee.full_name,
            "team_name": self.team_name,
            "shift_date": self.shift_date.isoformat(),
            "shift_code": self.shift_code,
            "absence_reason": self.absence_reason,
            "reason_no_replacement": self.reason_no_replacement,
            "understaffing_impact": self.understaffing_impact,
            "priority": "HIGH"
        }


@dataclass
class LockedAssignmentConflictNotification(NotificationTrigger):
    """
    Triggered when a locked (manual) assignment prevents optimization.
    
    Recipients:
    - All Admins
    - All Dispatchers
    
    Payload:
    - Details of the locked assignment
    - Optimization issue it causes
    - Suggestions for resolution
    """
    locked_type: str  # "team_shift", "employee_weekend", "td", "absence"
    entity_id: int  # employee_id or team_id
    entity_name: str
    locked_date_or_week: str
    locked_value: str
    conflict_description: str
    
    def __post_init__(self):
        super().__init__(
            trigger_type="locked_assignment_conflict",
            timestamp=date.today(),
            description=(
                f"Locked assignment for {self.entity_name} on {self.locked_date_or_week} "
                f"causes conflict: {self.conflict_description}"
            )
        )
    
    def get_recipients(self) -> List[str]:
        """Return list of recipient roles"""
        return ["Admin", "Disponent"]
    
    def get_message_payload(self) -> dict:
        """Return message data for notification system"""
        return {
            "type": self.trigger_type,
            "locked_type": self.locked_type,
            "entity_id": self.entity_id,
            "entity_name": self.entity_name,
            "locked_date_or_week": self.locked_date_or_week,
            "locked_value": self.locked_value,
            "conflict_description": self.conflict_description,
            "priority": "MEDIUM"
        }


class NotificationService:
    """
    Service to manage notification triggers.
    
    This is a structural definition only - no SMTP implementation.
    The actual email sending would be implemented separately.
    """
    
    def __init__(self):
        self.pending_notifications: List[NotificationTrigger] = []
    
    def trigger_absence_after_scheduling(
        self,
        employee: Employee,
        absence: Absence,
        affected_dates: List[date],
        schedule_month: str,
        replacement_attempted: bool
    ):
        """Queue notification for absence entered after scheduling"""
        notification = AbsenceAfterSchedulingNotification(
            employee=employee,
            absence=absence,
            affected_dates=affected_dates,
            schedule_month=schedule_month,
            replacement_attempted=replacement_attempted
        )
        self.pending_notifications.append(notification)
        return notification
    
    def trigger_springer_assigned(
        self,
        springer: Employee,
        original_employee: Employee,
        shift_date: date,
        shift_code: str,
        absence_reason: str
    ):
        """Queue notification for automatic springer assignment"""
        notification = SpringerAssignedNotification(
            springer=springer,
            original_employee=original_employee,
            shift_date=shift_date,
            shift_code=shift_code,
            absence_reason=absence_reason
        )
        self.pending_notifications.append(notification)
        return notification
    
    def trigger_no_replacement_available(
        self,
        employee: Employee,
        shift_date: date,
        shift_code: str,
        team_name: str,
        absence_reason: str,
        reason_no_replacement: str,
        understaffing_impact: str
    ):
        """Queue notification for failed replacement attempt"""
        notification = NoReplacementAvailableNotification(
            employee=employee,
            shift_date=shift_date,
            shift_code=shift_code,
            team_name=team_name,
            absence_reason=absence_reason,
            reason_no_replacement=reason_no_replacement,
            understaffing_impact=understaffing_impact
        )
        self.pending_notifications.append(notification)
        return notification
    
    def trigger_locked_assignment_conflict(
        self,
        locked_type: str,
        entity_id: int,
        entity_name: str,
        locked_date_or_week: str,
        locked_value: str,
        conflict_description: str
    ):
        """Queue notification for locked assignment conflicts"""
        notification = LockedAssignmentConflictNotification(
            locked_type=locked_type,
            entity_id=entity_id,
            entity_name=entity_name,
            locked_date_or_week=locked_date_or_week,
            locked_value=locked_value,
            conflict_description=conflict_description
        )
        self.pending_notifications.append(notification)
        return notification
    
    def get_pending_notifications(self) -> List[NotificationTrigger]:
        """Get all pending notifications"""
        return self.pending_notifications
    
    def clear_notifications(self):
        """Clear all pending notifications"""
        self.pending_notifications = []
    
    def send_notifications(self):
        """
        Placeholder for actual notification sending.
        
        In a real implementation, this would:
        1. Connect to SMTP server
        2. Lookup recipient email addresses
        3. Format email messages
        4. Send emails
        5. Log results
        
        For now, just print notification details.
        """
        for notification in self.pending_notifications:
            print(f"\n{'='*60}")
            print(f"NOTIFICATION: {notification.trigger_type}")
            print(f"{'='*60}")
            print(f"Description: {notification.description}")
            print(f"Recipients: {', '.join(notification.get_recipients())}")
            print(f"Payload:")
            for key, value in notification.get_message_payload().items():
                print(f"  {key}: {value}")
            print(f"{'='*60}\n")
        
        # In real implementation: actually send emails here
        # For now: just mark as sent by clearing
        self.clear_notifications()


# Global notification service instance
notification_service = NotificationService()
