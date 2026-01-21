"""
Lösungsversuche für Januar 2026 Schichtmodell

Dieses Skript testet verschiedene Lösungsansätze für die identifizierten Probleme.
WICHTIG: Alle getesteten Lösungen sind WEITERHIN INFEASIBLE!
Die Tests dokumentieren, dass auch angepasste Parameter das grundlegende
architektonische Problem nicht lösen können.

VERSUCH 1: Nacht-Schicht flexibler gestalten (Max=5 statt Max=3)
VERSUCH 2: Reduzierte Arbeitsstunden (44h statt 48h Woche) 
VERSUCH 3: Kombinierte Optimierungen (46h/Woche + flexible Nacht-Schicht)
"""

from datetime import date, timedelta
from entities import Employee, Team, ShiftType, Absence
from model import ShiftPlanningModel
from solver import ShiftPlanningSolver
from typing import List, Dict
import calendar


def erstelle_loesung_1_flexible_nachtschicht():
    """
    LÖSUNG 1: Nacht-Schicht flexibler gestalten
    
    Änderung: Nacht-Schicht Max von 3 auf 5 erhöht
    - Dies ermöglicht mehr Flexibilität bei der Besetzung
    - Teams können bei Bedarf mehr Personal in Nachtschicht einsetzen
    - Behält 48h/Woche bei
    """
    
    # Erstelle Schichttypen mit angepasster Nacht-Schicht
    shift_types = [
        ShiftType(
            id=1,
            code="F",
            name="Frühdienst",
            start_time="05:45",
            end_time="13:45",
            color_code="#FFD700",
            hours=8.0,
            weekly_working_hours=48.0,
            min_staff_weekday=4,
            max_staff_weekday=8,
            min_staff_weekend=2,
            max_staff_weekend=3,
            works_monday=True,
            works_tuesday=True,
            works_wednesday=True,
            works_thursday=True,
            works_friday=True,
            works_saturday=True,
            works_sunday=True
        ),
        ShiftType(
            id=2,
            code="S",
            name="Spätdienst",
            start_time="13:45",
            end_time="21:45",
            color_code="#FF6347",
            hours=8.0,
            weekly_working_hours=48.0,
            min_staff_weekday=3,
            max_staff_weekday=6,
            min_staff_weekend=2,
            max_staff_weekend=3,
            works_monday=True,
            works_tuesday=True,
            works_wednesday=True,
            works_thursday=True,
            works_friday=True,
            works_saturday=True,
            works_sunday=True
        ),
        ShiftType(
            id=3,
            code="N",
            name="Nachtdienst",
            start_time="21:45",
            end_time="05:45",
            color_code="#4169E1",
            hours=8.0,
            weekly_working_hours=48.0,
            min_staff_weekday=3,
            max_staff_weekday=5,  # GEÄNDERT von 3 auf 5
            min_staff_weekend=2,
            max_staff_weekend=3,
            works_monday=True,
            works_tuesday=True,
            works_wednesday=True,
            works_thursday=True,
            works_friday=True,
            works_saturday=True,
            works_sunday=True
        )
    ]
    
    return erstelle_testdaten(shift_types, "LÖSUNG 1: Flexible Nacht-Schicht (Max=5)")


def erstelle_loesung_2_reduzierte_stunden():
    """
    LÖSUNG 2: Reduzierte Arbeitsstunden
    
    Änderung: Wochenarbeitszeit von 48h auf 44h reduziert
    - Dies macht die Team-Rotation praktikabler
    - Reduziert Druck auf Besetzungsanforderungen
    - Behält Nacht-Schicht Min=Max=3 bei (ursprüngliche Anforderung)
    """
    
    # Erstelle Schichttypen mit reduzierter Wochenarbeitszeit
    shift_types = [
        ShiftType(
            id=1,
            code="F",
            name="Frühdienst",
            start_time="05:45",
            end_time="13:45",
            color_code="#FFD700",
            hours=8.0,
            weekly_working_hours=44.0,  # GEÄNDERT von 48h auf 44h
            min_staff_weekday=4,
            max_staff_weekday=8,
            min_staff_weekend=2,
            max_staff_weekend=3,
            works_monday=True,
            works_tuesday=True,
            works_wednesday=True,
            works_thursday=True,
            works_friday=True,
            works_saturday=True,
            works_sunday=True
        ),
        ShiftType(
            id=2,
            code="S",
            name="Spätdienst",
            start_time="13:45",
            end_time="21:45",
            color_code="#FF6347",
            hours=8.0,
            weekly_working_hours=44.0,  # GEÄNDERT von 48h auf 44h
            min_staff_weekday=3,
            max_staff_weekday=6,
            min_staff_weekend=2,
            max_staff_weekend=3,
            works_monday=True,
            works_tuesday=True,
            works_wednesday=True,
            works_thursday=True,
            works_friday=True,
            works_saturday=True,
            works_sunday=True
        ),
        ShiftType(
            id=3,
            code="N",
            name="Nachtdienst",
            start_time="21:45",
            end_time="05:45",
            color_code="#4169E1",
            hours=8.0,
            weekly_working_hours=44.0,  # GEÄNDERT von 48h auf 44h
            min_staff_weekday=3,
            max_staff_weekday=3,  # UNVERÄNDERT - Original-Anforderung
            min_staff_weekend=2,
            max_staff_weekend=3,
            works_monday=True,
            works_tuesday=True,
            works_wednesday=True,
            works_thursday=True,
            works_friday=True,
            works_saturday=True,
            works_sunday=True
        )
    ]
    
    return erstelle_testdaten(shift_types, "LÖSUNG 2: Reduzierte Stunden (44h/Woche)")


def erstelle_loesung_3_kombiniert():
    """
    LÖSUNG 3: Kombinierte Optimierungen
    
    Kombiniert beide Ansätze für maximale Flexibilität:
    - Flexible Nacht-Schicht (Max=5)
    - Leicht reduzierte Arbeitsstunden (46h statt 48h)
    """
    
    # Erstelle Schichttypen mit kombinierten Optimierungen
    shift_types = [
        ShiftType(
            id=1,
            code="F",
            name="Frühdienst",
            start_time="05:45",
            end_time="13:45",
            color_code="#FFD700",
            hours=8.0,
            weekly_working_hours=46.0,  # GEÄNDERT von 48h auf 46h
            min_staff_weekday=4,
            max_staff_weekday=8,
            min_staff_weekend=2,
            max_staff_weekend=3,
            works_monday=True,
            works_tuesday=True,
            works_wednesday=True,
            works_thursday=True,
            works_friday=True,
            works_saturday=True,
            works_sunday=True
        ),
        ShiftType(
            id=2,
            code="S",
            name="Spätdienst",
            start_time="13:45",
            end_time="21:45",
            color_code="#FF6347",
            hours=8.0,
            weekly_working_hours=46.0,  # GEÄNDERT von 48h auf 46h
            min_staff_weekday=3,
            max_staff_weekday=6,
            min_staff_weekend=2,
            max_staff_weekend=3,
            works_monday=True,
            works_tuesday=True,
            works_wednesday=True,
            works_thursday=True,
            works_friday=True,
            works_saturday=True,
            works_sunday=True
        ),
        ShiftType(
            id=3,
            code="N",
            name="Nachtdienst",
            start_time="21:45",
            end_time="05:45",
            color_code="#4169E1",
            hours=8.0,
            weekly_working_hours=46.0,  # GEÄNDERT von 48h auf 46h
            min_staff_weekday=3,
            max_staff_weekday=5,  # GEÄNDERT von 3 auf 5
            min_staff_weekend=2,
            max_staff_weekend=3,
            works_monday=True,
            works_tuesday=True,
            works_wednesday=True,
            works_thursday=True,
            works_friday=True,
            works_saturday=True,
            works_sunday=True
        )
    ]
    
    return erstelle_testdaten(shift_types, "LÖSUNG 3: Kombiniert (46h/Woche + Flex Nacht)")


def erstelle_testdaten(shift_types: List[ShiftType], beschreibung: str):
    """Erstellt die Testdaten mit den gegebenen Schichttypen"""
    
    # Erstelle 3 Teams mit je 5 Mitarbeitern
    teams = [
        Team(id=1, name="Team Alpha", description="Erstes Schicht-Team"),
        Team(id=2, name="Team Beta", description="Zweites Schicht-Team"),
        Team(id=3, name="Team Gamma", description="Drittes Schicht-Team")
    ]
    
    # Erstelle 15 Mitarbeiter (5 pro Team)
    employees = []
    emp_id = 1
    team_names = ["Alpha", "Beta", "Gamma"]
    
    for team_idx, team in enumerate(teams):
        for member_num in range(1, 6):
            employee = Employee(
                id=emp_id,
                vorname=f"Mitarbeiter_{team_names[team_idx]}",
                name=f"M{member_num}",
                personalnummer=f"{team_idx+1}{member_num:02d}",
                team_id=team.id,
                email=f"ma{emp_id}@test.de"
            )
            employees.append(employee)
            team.employees.append(employee)
            emp_id += 1
    
    # Setze erlaubte Schichttypen für jedes Team (alle können F, S, N arbeiten)
    for team in teams:
        team.allowed_shift_type_ids = [st.id for st in shift_types]
    
    # Januar 2026 Zeitraum
    start_date = date(2026, 1, 1)
    end_date = date(2026, 1, 31)
    
    # Keine Abwesenheiten
    absences = []
    
    return employees, teams, start_date, end_date, shift_types, absences, beschreibung


def teste_loesung(name: str, erstelle_fn):
    """Testet eine Lösung"""
    print("\n" + "=" * 100)
    print(f"TEST: {name}")
    print("=" * 100)
    
    employees, teams, start_date, end_date, shift_types, absences, beschreibung = erstelle_fn()
    
    print(f"\n{beschreibung}")
    print(f"\nKonfiguration:")
    print(f"  - Teams: {len(teams)} × {len(teams[0].employees)} Mitarbeiter = {len(employees)} total")
    print(f"  - Zeitraum: {start_date} bis {end_date} (31 Tage)")
    
    print(f"\nSchichttypen:")
    for st in shift_types:
        print(f"  - {st.name} ({st.code}):")
        print(f"      {st.hours}h/Tag, {st.weekly_working_hours}h/Woche")
        print(f"      Wochentag: Min {st.min_staff_weekday}, Max {st.max_staff_weekday}")
        print(f"      Wochenende: Min {st.min_staff_weekend}, Max {st.max_staff_weekend}")
    
    # Berechne Anforderungen
    num_weeks = 31 / 7.0
    monthly_hours = shift_types[0].weekly_working_hours * num_weeks
    print(f"\nArbeitszeitberechnung:")
    print(f"  - Wochenstunden: {shift_types[0].weekly_working_hours}h")
    print(f"  - Monatsstunden (Soll): {monthly_hours:.1f}h")
    print(f"  - Benötigte Arbeitstage: {monthly_hours / 8:.1f}")
    
    # Erstelle und löse Modell
    print(f"\nErstelle Schichtplanungsmodell...")
    
    global_settings = {
        'max_consecutive_shifts_weeks': 6,
        'max_consecutive_night_shifts_weeks': 3,
        'min_rest_hours': 11
    }
    
    try:
        model = ShiftPlanningModel(
            employees=employees,
            teams=teams,
            start_date=start_date,
            end_date=end_date,
            absences=absences,
            shift_types=shift_types
        )
        
        solver = ShiftPlanningSolver(
            model,
            time_limit_seconds=120,  # 2 Minuten
            num_workers=4,
            global_settings=global_settings
        )
        
        print(f"Füge Constraints hinzu...")
        solver.add_all_constraints()
        
        print(f"Starte Solver (Zeitlimit: 120 Sekunden)...")
        success = solver.solve()
        
        if success:
            print(f"\n{'='*100}")
            print("✓✓✓ LÖSUNG GEFUNDEN ✓✓✓")
            print("=" * 100)
            
            # Extrahiere und analysiere Lösung
            assignments, special_functions, complete_schedule = solver.extract_solution()
            
            print(f"\nGesamtanzahl Schichtzuweisungen: {len(assignments)}")
            
            # Analysiere Arbeitsstunden pro Mitarbeiter
            employee_stats = {}
            for emp in employees:
                employee_stats[emp.id] = {
                    'name': emp.full_name,
                    'days': 0,
                    'hours': 0.0,
                    'shifts': {st.code: 0 for st in shift_types}
                }
            
            for assignment in assignments:
                emp_id = assignment.employee_id
                shift_type = next((st for st in shift_types if st.id == assignment.shift_type_id), None)
                if shift_type:
                    employee_stats[emp_id]['days'] += 1
                    employee_stats[emp_id]['hours'] += shift_type.hours
                    employee_stats[emp_id]['shifts'][shift_type.code] += 1
            
            print(f"\n{'Mitarbeiter':<30} {'Tage':>6} {'Stunden':>8} {'Soll':>8} {'Diff':>8} {'F':>4} {'S':>4} {'N':>4}")
            print("-" * 100)
            
            alle_erfuellt = True
            total_hours = 0
            for emp_id, stats in employee_stats.items():
                soll_hours = monthly_hours
                diff_hours = stats['hours'] - soll_hours
                diff_str = f"{diff_hours:+.1f}h"
                
                if stats['hours'] < soll_hours:
                    alle_erfuellt = False
                
                print(f"{stats['name']:<30} {stats['days']:>6} {stats['hours']:>8.1f}h {soll_hours:>7.1f}h {diff_str:>8} "
                      f"{stats['shifts']['F']:>4} {stats['shifts']['S']:>4} {stats['shifts']['N']:>4}")
                
                total_hours += stats['hours']
            
            avg_hours = total_hours / len(employees)
            print("-" * 100)
            print(f"{'DURCHSCHNITT':<30} {'':<6} {avg_hours:>8.1f}h {monthly_hours:>7.1f}h")
            
            if alle_erfuellt:
                print(f"\n✓ Alle Mitarbeiter erreichen ihre Mindest-Monatsstundenzahl!")
            else:
                print(f"\n⚠ Einige Mitarbeiter erreichen Mindest-Monatsstundenzahl nicht (aber Lösung ist gültig)")
            
            print(f"\n{'='*100}")
            print("FAZIT")
            print("=" * 100)
            print(f"✓ Ein Schichtmodell für Januar 2026 KANN mit dieser Konfiguration gebaut werden!")
            print(f"✓ Alle Constraints (Besetzung, Ruhezeit, etc.) sind erfüllt")
            print("=" * 100)
            
            return True
            
        else:
            print(f"\n{'='*100}")
            print("✗ INFEASIBLE - Auch diese Lösung funktioniert nicht")
            print("=" * 100)
            return False
            
    except Exception as e:
        print(f"\n✗ FEHLER: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Hauptfunktion - testet alle Lösungen"""
    
    print("=" * 100)
    print("LÖSUNGSTESTS FÜR JANUAR 2026 SCHICHTMODELL")
    print("=" * 100)
    print("\nDie Original-Konstellation war INFEASIBLE.")
    print("Wir testen nun verschiedene Lösungsansätze:")
    print()
    print("LÖSUNG 1: Nacht-Schicht flexibler (Max=5 statt 3)")
    print("LÖSUNG 2: Reduzierte Arbeitsstunden (44h statt 48h/Woche)")
    print("LÖSUNG 3: Kombiniert (46h/Woche + flexible Nacht-Schicht)")
    
    results = {}
    
    # Teste alle Lösungen
    results['Lösung 1'] = teste_loesung(
        "LÖSUNG 1: Flexible Nacht-Schicht",
        erstelle_loesung_1_flexible_nachtschicht
    )
    
    results['Lösung 2'] = teste_loesung(
        "LÖSUNG 2: Reduzierte Arbeitsstunden",
        erstelle_loesung_2_reduzierte_stunden
    )
    
    results['Lösung 3'] = teste_loesung(
        "LÖSUNG 3: Kombinierte Optimierungen",
        erstelle_loesung_3_kombiniert
    )
    
    # Zusammenfassung
    print("\n\n" + "=" * 100)
    print("ZUSAMMENFASSUNG ALLER TESTS")
    print("=" * 100)
    
    for name, success in results.items():
        status = "✓ ERFOLGREICH" if success else "✗ FEHLGESCHLAGEN"
        print(f"{name}: {status}")
    
    print("\n" + "=" * 100)
    print("EMPFEHLUNG")
    print("=" * 100)
    
    if results.get('Lösung 1'):
        print("✓ LÖSUNG 1 (Flexible Nacht-Schicht) wird EMPFOHLEN")
        print("  Vorteile:")
        print("  - Behält 48h Wochenarbeitszeit bei (ursprüngliche Anforderung)")
        print("  - Nur minimale Änderung: Nacht-Schicht Max von 3 auf 5")
        print("  - Bietet Flexibilität bei Besetzungsengpässen")
    elif results.get('Lösung 2'):
        print("✓ LÖSUNG 2 (Reduzierte Stunden) wird EMPFOHLEN")
        print("  Vorteile:")
        print("  - Behält Nacht-Schicht Constraint bei (Min=Max=3)")
        print("  - Reduziert Arbeitsdruck durch 44h statt 48h")
        print("  - Praktikablere Team-Rotation")
    elif results.get('Lösung 3'):
        print("✓ LÖSUNG 3 (Kombiniert) wird EMPFOHLEN")
        print("  Vorteile:")
        print("  - Kompromiss zwischen beiden Ansätzen")
        print("  - Maximale Flexibilität")
    else:
        print("✗ Keine der Lösungen war erfolgreich")
        print("  Weitere Anpassungen erforderlich")
    
    print("=" * 100)
    
    # Exit code basierend auf Erfolg
    if any(results.values()):
        return 0
    else:
        return 1


if __name__ == "__main__":
    exit(main())
