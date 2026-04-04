"""
PlanningReport – Einheitlicher Planungsbericht für das Dienstplansystem.

Kapselt alle relevanten Informationen eines abgeschlossenen Planungslaufs:
Planungsstatus, Mitarbeiterübersicht, Schichtzuweisungen, Regelverstöße und
relaxierte Constraints.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Dict, List, Literal, Optional, Tuple


# ---------------------------------------------------------------------------
# Supporting data classes
# ---------------------------------------------------------------------------

@dataclass
class AbsenceInfo:
    """Beschreibt eine Abwesenheit eines Mitarbeiters im Planungszeitraum."""

    employee_name: str          # Vollständiger Name, z. B. "Max Mustermann"
    absence_type: str           # Kurzcode, z. B. "AU", "U", "L" oder benutzerdefiniert
    start_date: date            # Erster Abwesenheitstag (inkl.)
    end_date: date              # Letzter Abwesenheitstag (inkl.)
    notes: Optional[str] = None # Optionale Anmerkungen zur Abwesenheit

    @property
    def duration_days(self) -> int:
        """Anzahl der Kalendertage (inkl. Start- und Endtag)."""
        return (self.end_date - self.start_date).days + 1


@dataclass
class UncoveredShift:
    """Dokumentiert eine nicht besetzte Schicht."""

    date: date          # Datum der unbesetzten Schicht
    shift_code: str     # Schichtcode, z. B. "F", "S", "N"
    reason: str         # Grund für fehlende Besetzung


@dataclass
class RuleViolation:
    """Beschreibt einen einzelnen Regelverstoß im Planungsergebnis."""

    rule_id: str
    """Eindeutige Regel-ID, z. B. \"H3_MINDESTBESETZUNG\"."""

    description: str
    """Kurzbeschreibung der Regel, z. B. \"Mindestbesetzung nicht erreicht\"."""

    severity: Literal["HARD", "SOFT_CRITICAL", "SOFT_MEDIUM", "SOFT_LOW"]
    """Schwere des Verstoßes."""

    affected_dates: List[date]
    """Datumsangaben, an denen der Verstoß auftritt."""

    cause: str
    """Ursache des Verstoßes, z. B. \"3 von 5 Mitarbeitern krank\"."""

    impact: str
    """Auswirkung des Verstoßes, z. B. \"Nur 2 statt 4 Mitarbeiter in Frühschicht am 2024-01-15\"."""

    cause_type: str = "UNKNOWN"
    """Strukturierte Ursachenkategorie: \"ABSENCE\", \"UNDERSTAFFING\", \"ROTATION_CONFLICT\", \"UNKNOWN\"."""


@dataclass
class RelaxedConstraint:
    """Beschreibt eine relaxierte (abgeschwächte) Planungsregel."""

    constraint_name: str    # Regelname, z. B. "Mindestbesetzung (H3)"
    reason: str             # Warum die Regel nicht eingehalten werden konnte
    description: str = ""   # Zusätzliche Details / Kontext


@dataclass
class AbsenceImpact:
    """Beschreibt die Abwesenheitsauswirkungen für einen einzelnen Planungstag."""

    date: date
    """Das analysierte Datum."""

    total_employees: int
    """Gesamtanzahl der Mitarbeiter im Planungszeitraum."""

    absent_count: int
    """Anzahl abwesender Mitarbeiter an diesem Tag."""

    absence_ratio: float
    """Anteil abwesender Mitarbeiter (0.0–1.0)."""

    affected_shift_codes: List[str]
    """Schichtcodes, für die die Mindestbesetzung durch Abwesenheiten gefährdet sein könnte."""

    min_staffing_reachable: bool
    """True, wenn die Mindestbesetzung aller Schichten trotz Abwesenheiten theoretisch erreichbar ist."""

    has_risk: bool
    """True, wenn der Puffer unter 20 % liegt (d. h. weniger als 20 % freie Mitarbeiterkapazität)."""

    available_count: int
    """Anzahl verfügbarer (nicht abwesender) Mitarbeiter an diesem Tag."""

    buffer_ratio: float
    """Pufferanteil: (verfügbare – Mindestbedarf) / verfügbare. Negativ bei Unterbesetzung."""


# ---------------------------------------------------------------------------
# PlanningReport
# ---------------------------------------------------------------------------

_SEVERITY_LABELS: Dict[str, str] = {
    "HARD": "HART",
    "SOFT_CRITICAL": "SOFT (KRITISCH)",
    "SOFT_MEDIUM": "SOFT (MITTEL)",
    "SOFT_LOW": "SOFT (NIEDRIG)",
}

_STATUS_LABELS: Dict[str, str] = {
    "OPTIMAL": "Optimal",
    "FEASIBLE": "Machbar (nicht bewiesen optimal)",
    "FALLBACK_L1": "Fallback-Stufe 1 (Mindestbesetzung relaxiert)",
    "FALLBACK_L2": "Fallback-Stufe 2 (Mindestbesetzung + Rotation relaxiert)",
    "EMERGENCY": "Notfallplan (Greedy-Algorithmus)",
}


@dataclass
class PlanningReport:
    """
    Einheitlicher Planungsbericht für einen abgeschlossenen Planungslauf.

    Enthält alle relevanten Informationen: Planungszeitraum, Status, Mitarbeiter-
    übersicht, Schichtzuweisungen, nicht besetzte Schichten, Regelverstöße und
    relaxierte Constraints.
    """

    # -- Planungszeitraum ---------------------------------------------------
    planning_period: Tuple[date, date]
    """(start_date, end_date) des Planungszeitraums."""

    # -- Status -------------------------------------------------------------
    status: Literal["OPTIMAL", "FEASIBLE", "FALLBACK_L1", "FALLBACK_L2", "EMERGENCY"]
    """Lösungsstatus des Solvers."""

    # -- Mitarbeiterübersicht -----------------------------------------------
    total_employees: int
    """Gesamtanzahl der Mitarbeiter im Planungszeitraum."""

    available_employees: int
    """Anzahl der voll verfügbaren Mitarbeiter (ohne Abwesenheiten)."""

    absent_employees: List[AbsenceInfo] = field(default_factory=list)
    """Abwesenheiten im Planungszeitraum (Name, Typ, Zeitraum)."""

    # -- Schichtzuweisungen -------------------------------------------------
    shifts_assigned: Dict[str, int] = field(default_factory=dict)
    """Anzahl zugewiesener Schichten pro Schichtcode, z. B. {\"F\": 45, \"S\": 42, \"N\": 38}."""

    uncovered_shifts: List[UncoveredShift] = field(default_factory=list)
    """Liste nicht besetzter Schichten."""

    # -- Regeln & Verstöße --------------------------------------------------
    rule_violations: List[RuleViolation] = field(default_factory=list)
    """Liste aller Regelverstöße im Planungsergebnis."""

    relaxed_constraints: List[RelaxedConstraint] = field(default_factory=list)
    """Constraints, die für die Planung relaxiert wurden."""

    # -- Abwesenheitsauswirkungen -------------------------------------------
    absence_impact: Dict[date, AbsenceImpact] = field(default_factory=dict)
    """Tagesweise Abwesenheitsauswirkungsanalyse (Datum → AbsenceImpact)."""

    # -- Solver-Metriken ----------------------------------------------------
    objective_value: float = 0.0
    """Gesamtstrafe des Solvers (niedrigere Werte sind besser)."""

    solver_time_seconds: float = 0.0
    """Laufzeit des Solvers in Sekunden."""

    # -----------------------------------------------------------------------
    # Computed properties
    # -----------------------------------------------------------------------

    @property
    def planning_days(self) -> int:
        """Anzahl der Planungstage (inkl. Start- und Endtag)."""
        return (self.planning_period[1] - self.planning_period[0]).days + 1

    @property
    def total_shifts_assigned(self) -> int:
        """Gesamtanzahl aller zugewiesenen Schichten."""
        return sum(self.shifts_assigned.values())

    @property
    def risk_days(self) -> List[AbsenceImpact]:
        """Tage mit Abwesenheitsrisiko (Puffer < 20 %)."""
        return [impact for impact in self.absence_impact.values() if impact.has_risk]

    @property
    def hard_violations(self) -> List[RuleViolation]:
        """Alle harten Regelverstöße."""
        return [v for v in self.rule_violations if v.severity == "HARD"]

    @property
    def soft_violations(self) -> List[RuleViolation]:
        """Alle weichen Regelverstöße (alle SOFT_* Schweregrade)."""
        return [v for v in self.rule_violations if v.severity.startswith("SOFT")]

    # -----------------------------------------------------------------------
    # Text summary
    # -----------------------------------------------------------------------

    def generate_text_summary(self) -> str:
        """
        Erzeugt einen lesbaren deutschen Planungsbericht als formatierten Text.

        Returns:
            Mehrzeiliger String mit Abschnittsüberschriften.
        """
        lines: List[str] = []

        def _heading(title: str) -> None:
            lines.append("")
            lines.append("=" * 60)
            lines.append(title)
            lines.append("=" * 60)

        def _subheading(title: str) -> None:
            lines.append("")
            lines.append(f"--- {title} ---")

        # ---- Kopfzeile -------------------------------------------------------
        start, end = self.planning_period
        lines.append("PLANUNGSBERICHT")
        lines.append(f"Zeitraum: {start.strftime('%d.%m.%Y')} – {end.strftime('%d.%m.%Y')} "
                     f"({self.planning_days} Tage)")

        # ---- Status ----------------------------------------------------------
        _heading("1. PLANUNGSSTATUS")
        status_label = _STATUS_LABELS.get(self.status, self.status)
        lines.append(f"Status:           {status_label}")
        lines.append(f"Solver-Laufzeit:  {self.solver_time_seconds:.1f} Sekunden")
        lines.append(f"Zielfunktionswert: {self.objective_value:.0f}")

        # ---- Mitarbeiter -----------------------------------------------------
        _heading("2. MITARBEITERÜBERSICHT")
        lines.append(f"Mitarbeiter gesamt:     {self.total_employees}")
        lines.append(f"Verfügbare Mitarbeiter: {self.available_employees}")
        lines.append(f"Abwesenheiten:          {len(self.absent_employees)}")

        if self.absent_employees:
            _subheading("Abwesenheiten im Detail")
            for a in self.absent_employees:
                date_range = (
                    f"{a.start_date.strftime('%d.%m.%Y')}"
                    if a.start_date == a.end_date
                    else f"{a.start_date.strftime('%d.%m.%Y')} – {a.end_date.strftime('%d.%m.%Y')}"
                )
                note = f" ({a.notes})" if a.notes else ""
                lines.append(f"  • {a.employee_name}: {a.absence_type}, {date_range}{note}")

        # ---- Schichtzuweisungen ---------------------------------------------
        _heading("3. SCHICHTZUWEISUNGEN")
        lines.append(f"Schichten gesamt: {self.total_shifts_assigned}")

        if self.shifts_assigned:
            _subheading("Zuweisungen pro Schichttyp")
            for code, count in sorted(self.shifts_assigned.items()):
                lines.append(f"  {code:6s}: {count} Schichten")

        if self.uncovered_shifts:
            _subheading(f"Nicht besetzte Schichten ({len(self.uncovered_shifts)})")
            for us in self.uncovered_shifts:
                lines.append(
                    f"  • {us.date.strftime('%d.%m.%Y')} – {us.shift_code}: {us.reason}"
                )
        else:
            lines.append("")
            lines.append("✓ Alle Schichten wurden besetzt.")

        # ---- Regelverstöße --------------------------------------------------
        _heading("4. REGELVERSTÖSSE")

        if not self.rule_violations:
            lines.append("✓ Keine Regelverstöße.")
        else:
            hard = self.hard_violations
            soft = self.soft_violations
            lines.append(f"Harte Verstöße:   {len(hard)}")
            lines.append(f"Weiche Verstöße:  {len(soft)}")

            if hard:
                _subheading(f"Harte Regelverstöße ({len(hard)})")
                for v in hard:
                    self._format_violation(v, lines)

            if soft:
                _subheading(f"Weiche Regelverstöße ({len(soft)})")
                for v in soft:
                    self._format_violation(v, lines)

        # ---- Relaxierte Constraints -----------------------------------------
        _heading("5. RELAXIERTE CONSTRAINTS")

        if not self.relaxed_constraints:
            lines.append("✓ Alle Planungsregeln wurden vollständig eingehalten.")
        else:
            lines.append(
                f"⚠ {len(self.relaxed_constraints)} Regel(n) mussten für die Planung "
                f"abgeschwächt werden:"
            )
            for rc in self.relaxed_constraints:
                lines.append(f"  • {rc.constraint_name}")
                lines.append(f"    Grund: {rc.reason}")
                if rc.description:
                    lines.append(f"    Details: {rc.description}")

        # ---- Abwesenheitsrisikotage -----------------------------------------
        _heading("6. ABWESENHEITSRISIKOTAGE")

        risk = self.risk_days
        if not risk:
            lines.append("✓ Keine Risikotage – ausreichend Puffer an allen Planungstagen.")
        else:
            lines.append(f"⚠ {len(risk)} Risikotag(e) mit weniger als 20 % freier Personalkapazität:")
            for impact in sorted(risk, key=lambda x: x.date):
                affected = ", ".join(impact.affected_shift_codes) if impact.affected_shift_codes else "–"
                min_ok = "✓" if impact.min_staffing_reachable else "✗"
                lines.append(
                    f"  • {impact.date.strftime('%d.%m.%Y')}: "
                    f"{impact.absent_count}/{impact.total_employees} abwesend "
                    f"({impact.absence_ratio*100:.0f}%), "
                    f"Puffer {impact.buffer_ratio*100:.0f}%, "
                    f"Mindestbesetzung erreichbar: {min_ok}, "
                    f"betroffene Schichten: {affected}"
                )

        # ---- Abschluss ------------------------------------------------------
        lines.append("")
        lines.append("=" * 60)
        lines.append("ENDE DES PLANUNGSBERICHTS")
        lines.append("=" * 60)

        return "\n".join(lines)

    # -----------------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------------

    @staticmethod
    def _format_violation(v: RuleViolation, lines: List[str]) -> None:
        """Fügt eine formatierte Regelverletzung zur Zeilenliste hinzu."""
        severity_label = _SEVERITY_LABELS.get(v.severity, v.severity)
        lines.append(f"  [{severity_label}] {v.rule_id}: {v.description}")
        lines.append(f"    Ursache:    {v.cause}")
        lines.append(f"    Auswirkung: {v.impact}")
        if v.affected_dates:
            if len(v.affected_dates) == 1:
                lines.append(f"    Datum:      {v.affected_dates[0].strftime('%d.%m.%Y')}")
            else:
                date_strs = ", ".join(d.strftime("%d.%m.%Y") for d in v.affected_dates[:5])
                suffix = f" (+{len(v.affected_dates) - 5} weitere)" if len(v.affected_dates) > 5 else ""
                lines.append(f"    Daten:      {date_strs}{suffix}")
