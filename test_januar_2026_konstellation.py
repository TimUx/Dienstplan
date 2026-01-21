"""
Test scenario für Januar 2026 mit genauer Konstellation aus den Anforderungen:
- 3 Teams mit je 5 Mitarbeitern
- 3 Schichten: Früh (F), Spät (S), Nacht (N)
- 48h Arbeitswoche pro Mitarbeiter
- Spezifische Min/Max Besetzungen
- Schichtreihenfolge: Früh → Nacht → Spät

WICHTIG: Die Schichtreihenfolge Früh → Nacht → Spät (statt üblicher Früh → Spät → Nacht)
ist eine spezifische ANFORDERUNG und trägt zur Infeasibility bei, da sie die 
Ruhezeit-Constraints zwischen Schichten verschärft.

Dieser Test:
1. Berechnet ob ein Schichtmodell für Januar 2026 (31 Tage) gebaut werden kann
2. Überprüft ob jeder Mitarbeiter seine Mindest-Monatsstundenzahl erreicht
3. Analysiert warum keine Lösung gefunden werden kann
"""

from datetime import date, timedelta
from entities import Employee, Team, ShiftType, Absence
from model import ShiftPlanningModel
from solver import ShiftPlanningSolver
from typing import List, Dict
import calendar


def erstelle_januar_2026_konstellation():
    """
    Erstellt die exakte Test-Konstellation gemäß Anforderungen:
    
    Früh-Schicht:
    - 8h Tagesarbeit
    - Montag - Sonntag
    - 48h Arbeitswoche
    - Wochentage mindestens 4 maximal 8 Mitarbeiter
    - Wochenende mindestens 2 maximal 3 Mitarbeiter
    
    Spät-Schicht:
    - 8h Tagesarbeit
    - Montag - Sonntag
    - 48h Arbeitswoche
    - Wochentage mindestens 3 maximal 6 Mitarbeiter
    - Wochenende mindestens 2 maximal 3 Mitarbeiter
    
    Nacht-Schicht:
    - 8h Tagesarbeit
    - Montag - Sonntag
    - 48h Arbeitswoche
    - Wochentage mindestens 3 maximal 3 Mitarbeiter
    - Wochenende mindestens 2 maximal 3 Mitarbeiter
    
    Allgemeine Einstellungen:
    - Maximale aufeinanderfolgende Schichten: 6 (42 Tage)
    - Maximale aufeinanderfolgende Nachtschichten: 3 (31 Tage)
    - Gesetzliche Ruhezeit: 11 Stunden
    - Schichtreihenfolge: Früh → Nacht → Spät
    """
    
    # Erstelle Schichttypen gemäß Anforderungen
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
            max_staff_weekday=3,
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
    
    # Generiere Januar 2026 Datumsliste (31 Tage)
    start_date = date(2026, 1, 1)
    end_date = date(2026, 1, 31)
    dates = []
    current = start_date
    while current <= end_date:
        dates.append(current)
        current += timedelta(days=1)
    
    # Keine Abwesenheiten für diesen Test
    absences = []
    
    return employees, teams, start_date, end_date, dates, shift_types, absences


def berechne_anforderungen(dates: List[date], shift_types: List[ShiftType]) -> Dict:
    """
    Berechnet die Arbeitszeit-Anforderungen für den Planungszeitraum.
    """
    num_days = len(dates)
    num_weeks = num_days / 7.0
    weekly_hours = shift_types[0].weekly_working_hours
    monthly_hours = weekly_hours * num_weeks
    days_needed = monthly_hours / shift_types[0].hours
    
    # Zähle Wochentage und Wochenenden
    weekdays = sum(1 for d in dates if d.weekday() < 5)
    weekends = num_days - weekdays
    
    return {
        'num_days': num_days,
        'num_weeks': num_weeks,
        'weekly_hours': weekly_hours,
        'monthly_hours': monthly_hours,
        'days_needed_per_employee': days_needed,
        'weekdays': weekdays,
        'weekends': weekends,
        'first_weekday': calendar.day_name[dates[0].weekday()],
        'last_weekday': calendar.day_name[dates[-1].weekday()]
    }


def analysiere_besetzungsanforderungen(dates: List[date], shift_types: List[ShiftType], 
                                       num_employees: int) -> Dict:
    """
    Analysiert ob die Besetzungsanforderungen mit der verfügbaren Anzahl 
    an Mitarbeitern erfüllbar sind.
    """
    weekdays = sum(1 for d in dates if d.weekday() < 5)
    weekends = len(dates) - weekdays
    
    results = {}
    for st in shift_types:
        # Berechne minimale und maximale Personentage
        min_person_days = (weekdays * st.min_staff_weekday) + (weekends * st.min_staff_weekend)
        max_person_days = (weekdays * st.max_staff_weekday) + (weekends * st.max_staff_weekend)
        
        # Berechne wie viele Tage jeder Mitarbeiter arbeiten müsste
        avg_days_per_person = min_person_days / num_employees
        
        results[st.code] = {
            'min_person_days': min_person_days,
            'max_person_days': max_person_days,
            'avg_days_per_person': avg_days_per_person,
            'min_weekday': st.min_staff_weekday,
            'max_weekday': st.max_staff_weekday,
            'min_weekend': st.min_staff_weekend,
            'max_weekend': st.max_staff_weekend
        }
    
    return results


def test_januar_2026_schichtmodell():
    """
    Haupttest: Überprüft ob ein Schichtmodell für Januar 2026 gebaut werden kann.
    """
    print("=" * 100)
    print("TEST: JANUAR 2026 SCHICHTMODELL - KONSTELLATION AUS ANFORDERUNGEN")
    print("=" * 100)
    
    # Erstelle Konstellation
    employees, teams, start_date, end_date, dates, shift_types, absences = erstelle_januar_2026_konstellation()
    
    # Ausgabe der Konfiguration
    print(f"\n{'='*100}")
    print("KONFIGURATION")
    print("=" * 100)
    print(f"\nTeams: {len(teams)}")
    for team in teams:
        print(f"  - {team.name}: {len(team.employees)} Mitarbeiter")
    
    print(f"\nGesamtanzahl Mitarbeiter: {len(employees)}")
    
    print(f"\nSchichttypen:")
    for st in shift_types:
        print(f"  - {st.name} ({st.code}):")
        print(f"      Arbeitszeit: {st.hours}h/Tag, {st.weekly_working_hours}h/Woche")
        print(f"      Wochentag: Min {st.min_staff_weekday}, Max {st.max_staff_weekday} Mitarbeiter")
        print(f"      Wochenende: Min {st.min_staff_weekend}, Max {st.max_staff_weekend} Mitarbeiter")
    
    print(f"\nPlanungszeitraum: {dates[0]} bis {dates[-1]} ({len(dates)} Tage)")
    
    # Berechne Anforderungen
    anforderungen = berechne_anforderungen(dates, shift_types)
    
    print(f"\n{'='*100}")
    print("ARBEITSZEITBERECHNUNG")
    print("=" * 100)
    print(f"Anzahl Tage: {anforderungen['num_days']}")
    print(f"Anzahl Wochen: {anforderungen['num_weeks']:.2f}")
    print(f"Wochenstunden: {anforderungen['weekly_hours']}h")
    print(f"Monatsstunden (Soll): {anforderungen['monthly_hours']:.1f}h")
    print(f"Benötigte Arbeitstage pro Mitarbeiter: {anforderungen['days_needed_per_employee']:.1f}")
    print(f"Wochentage: {anforderungen['weekdays']}")
    print(f"Wochenendtage: {anforderungen['weekends']}")
    print(f"Erster Tag: {anforderungen['first_weekday']}")
    print(f"Letzter Tag: {anforderungen['last_weekday']}")
    
    # Analysiere Besetzungsanforderungen
    besetzung = analysiere_besetzungsanforderungen(dates, shift_types, len(employees))
    
    print(f"\n{'='*100}")
    print("BESETZUNGSANFORDERUNGEN - ANALYSE")
    print("=" * 100)
    for shift_code, data in besetzung.items():
        print(f"\n{shift_code}-Schicht:")
        print(f"  Min Personentage gesamt: {data['min_person_days']}")
        print(f"  Max Personentage gesamt: {data['max_person_days']}")
        print(f"  Durchschnitt Tage/Person (bei Min-Besetzung): {data['avg_days_per_person']:.1f}")
        print(f"  Benötigte Stunden/Person (bei Min-Besetzung): {data['avg_days_per_person'] * 8:.1f}h")
    
    # Überprüfe Machbarkeit
    print(f"\n{'='*100}")
    print("MACHBARKEITSANALYSE")
    print("=" * 100)
    
    total_min_person_days = sum(data['min_person_days'] for data in besetzung.values())
    total_max_person_days = sum(data['max_person_days'] for data in besetzung.values())
    available_person_days = len(employees) * len(dates)
    
    print(f"\nGesamte Personentage (Min-Besetzung): {total_min_person_days}")
    print(f"Gesamte Personentage (Max-Besetzung): {total_max_person_days}")
    print(f"Verfügbare Personentage: {available_person_days}")
    print(f"Auslastung (Min): {(total_min_person_days / available_person_days * 100):.1f}%")
    print(f"Auslastung (Max): {(total_max_person_days / available_person_days * 100):.1f}%")
    
    # Theoretische Machbarkeit
    machbar = total_min_person_days <= available_person_days
    print(f"\nTheoretisch machbar: {'✓ JA' if machbar else '✗ NEIN'}")
    
    if not machbar:
        print("WARNUNG: Die Mindestbesetzungsanforderungen übersteigen die verfügbaren Personentage!")
        print("Eine Lösung ist UNMÖGLICH.")
        return None
    
    # Erstelle und löse Schichtplanungsmodell
    print(f"\n{'='*100}")
    print("SCHICHTPLANUNGSMODELL ERSTELLEN UND LÖSEN")
    print("=" * 100)
    
    # Globale Einstellungen gemäß Anforderungen
    global_settings = {
        'max_consecutive_shifts_weeks': 6,  # Maximale aufeinanderfolgende Schichten: 6 Wochen (42 Tage)
        'max_consecutive_night_shifts_weeks': 3,  # Maximale aufeinanderfolgende Nachtschichten: 3 Wochen (21 Tage)  
        'min_rest_hours': 11  # Gesetzliche Ruhezeit: 11 Stunden
    }
    
    print(f"\nGlobale Einstellungen:")
    print(f"  Max aufeinanderfolgende Schichten: {global_settings['max_consecutive_shifts_weeks']} Wochen")
    print(f"  Max aufeinanderfolgende Nachtschichten: {global_settings['max_consecutive_night_shifts_weeks']} Wochen")
    print(f"  Min Ruhezeit: {global_settings['min_rest_hours']} Stunden")
    print(f"  Schichtreihenfolge: Früh → Nacht → Spät")
    
    try:
        print(f"\nErstelle ShiftPlanningModel...")
        model = ShiftPlanningModel(
            employees=employees,
            teams=teams,
            start_date=start_date,
            end_date=end_date,
            absences=absences,
            shift_types=shift_types
        )
        
        print(f"Erstelle ShiftPlanningSolver (60 Sekunden Zeitlimit)...")
        solver = ShiftPlanningSolver(
            model, 
            time_limit_seconds=60, 
            num_workers=4,
            global_settings=global_settings
        )
        
        print(f"Füge Constraints hinzu...")
        solver.add_all_constraints()
        
        print(f"\nStarte Solver...")
        success = solver.solve()
        
        # Ausgabe des Ergebnisses
        print(f"\n{'='*100}")
        print("SOLVER ERGEBNIS")
        print("=" * 100)
        
        if success:
            print(f"\n✓✓✓ LÖSUNG GEFUNDEN ✓✓✓")
            print(f"\nDas Schichtmodell für Januar 2026 KANN gebaut werden!")
            
            # Extrahiere Lösung
            assignments, special_functions, complete_schedule = solver.extract_solution()
            print(f"\nGesamtanzahl Schichtzuweisungen: {len(assignments)}")
            
            # Analysiere Lösung
            print(f"\n{'='*100}")
            print("DETAILANALYSE DER LÖSUNG")
            print("=" * 100)
            
            # Zähle Arbeitstage und Stunden pro Mitarbeiter
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
            
            print(f"\nArbeitsstunden pro Mitarbeiter:")
            print(f"{'Mitarbeiter':<30} {'Tage':>6} {'Stunden':>8} {'Soll':>8} {'Diff':>8} {'F':>4} {'S':>4} {'N':>4}")
            print("-" * 100)
            
            total_hours = 0
            total_days = 0
            for emp_id, stats in employee_stats.items():
                soll_hours = anforderungen['monthly_hours']
                diff_hours = stats['hours'] - soll_hours
                diff_str = f"{diff_hours:+.1f}h"
                
                print(f"{stats['name']:<30} {stats['days']:>6} {stats['hours']:>8.1f}h {soll_hours:>7.1f}h {diff_str:>8} "
                      f"{stats['shifts']['F']:>4} {stats['shifts']['S']:>4} {stats['shifts']['N']:>4}")
                
                total_hours += stats['hours']
                total_days += stats['days']
            
            print("-" * 100)
            avg_hours = total_hours / len(employees)
            avg_days = total_days / len(employees)
            print(f"{'DURCHSCHNITT':<30} {avg_days:>6.1f} {avg_hours:>8.1f}h {anforderungen['monthly_hours']:>7.1f}h")
            
            # Überprüfe ob alle Mindestanforderungen erfüllt sind
            print(f"\n{'='*100}")
            print("ÜBERPRÜFUNG MINDESTANFORDERUNGEN")
            print("=" * 100)
            
            alle_erfuellt = True
            for emp_id, stats in employee_stats.items():
                if stats['hours'] < anforderungen['monthly_hours']:
                    print(f"✗ {stats['name']}: {stats['hours']:.1f}h < {anforderungen['monthly_hours']:.1f}h (Soll)")
                    alle_erfuellt = False
            
            if alle_erfuellt:
                print("✓ Alle Mitarbeiter erreichen ihre Mindest-Monatsstundenzahl!")
            else:
                print("✗ WARNUNG: Einige Mitarbeiter erreichen ihre Mindest-Monatsstundenzahl NICHT!")
            
            # Analysiere Besetzung pro Tag
            print(f"\n{'='*100}")
            print("BESETZUNGSANALYSE PRO TAG")
            print("=" * 100)
            
            daily_staffing = {d: {st.code: 0 for st in shift_types} for d in dates}
            for assignment in assignments:
                shift_type = next((st for st in shift_types if st.id == assignment.shift_type_id), None)
                if shift_type:
                    daily_staffing[assignment.date][shift_type.code] += 1
            
            print(f"\n{'Datum':<15} {'Tag':<10} {'F':>4} {'S':>4} {'N':>4}")
            print("-" * 50)
            
            for d in dates[:7]:  # Zeige erste Woche
                day_name = calendar.day_name[d.weekday()][:3]
                is_weekend = d.weekday() >= 5
                day_type = "WE" if is_weekend else "WT"
                
                f_count = daily_staffing[d]['F']
                s_count = daily_staffing[d]['S']
                n_count = daily_staffing[d]['N']
                
                print(f"{d} {day_name:<3} ({day_type:>2}) {f_count:>4} {s_count:>4} {n_count:>4}")
            
            print("...")
            
            # Überprüfe Min/Max Besetzung
            print(f"\n{'='*100}")
            print("ÜBERPRÜFUNG MIN/MAX BESETZUNG")
            print("=" * 100)
            
            besetzung_ok = True
            for d in dates:
                is_weekend = d.weekday() >= 5
                for st in shift_types:
                    count = daily_staffing[d][st.code]
                    min_req = st.min_staff_weekend if is_weekend else st.min_staff_weekday
                    max_req = st.max_staff_weekend if is_weekend else st.max_staff_weekday
                    
                    if count < min_req or count > max_req:
                        print(f"✗ {d} ({st.code}): {count} Mitarbeiter (Soll: {min_req}-{max_req})")
                        besetzung_ok = False
            
            if besetzung_ok:
                print("✓ Alle Besetzungsanforderungen (Min/Max) sind erfüllt!")
            
            print(f"\n{'='*100}")
            print("FAZIT")
            print("=" * 100)
            print(f"✓ Ein Schichtmodell für Januar 2026 KANN mit dieser Konstellation gebaut werden.")
            print(f"✓ Alle Constraints erfüllt: {'JA' if alle_erfuellt and besetzung_ok else 'TEILWEISE'}")
            print("=" * 100)
            
        else:
            print(f"\n✗✗✗ KEINE LÖSUNG MÖGLICH (INFEASIBLE) ✗✗✗")
            print(f"\nDas Schichtmodell für Januar 2026 kann NICHT gebaut werden!")
            
            # Get diagnostics from solver if available
            if hasattr(solver, 'diagnostics'):
                diagnostics = solver.diagnostics
                
                print(f"\n{'='*100}")
                print("DETAILLIERTE FEHLERANALYSE")
                print("=" * 100)
                
                if diagnostics.get('potential_issues'):
                    print(f"\n⚠️  Erkannte Probleme ({len(diagnostics['potential_issues'])}):")
                    for issue in diagnostics['potential_issues']:
                        print(f"  • {issue}")
            
            print(f"\n{'='*100}")
            print("GRUNDLEGENDE URSACHENANALYSE")
            print("=" * 100)
            print("Mögliche Ursachen:")
            print("  1. Team-Rotations-Constraints zu restriktiv (Früh → Nacht → Spät)")
            print("  2. Nacht-Schicht Min=Max=3 zu restriktiv für 3 Teams")
            print("     → Bei Rotation kann es sein, dass alle 3 Teams gleichzeitig Nacht haben müssten")
            print("  3. Arbeitsziel (48h/Woche × 4.43 Wochen = 212.6h/Monat) mit Team-Rotation nicht erreichbar")
            print("  4. Ruhezeit-Constraints (11 Stunden) im Konflikt mit Schichtwechseln")
            print("  5. Wochenendbesetzung (Min 2-3) im Konflikt mit Team-Rotation")
            
            print(f"\n{'='*100}")
            print("LÖSUNGSANSÄTZE")
            print("=" * 100)
            print("EMPFEHLUNG 1: Nacht-Schicht flexibler gestalten")
            print("  - Aktuell: Min=3, Max=3 (zu starr)")
            print("  - Vorschlag: Min=3, Max=5 (mehr Flexibilität)")
            print("  - Begründung: Bei fester Rotation F→N→S braucht man Flexibilität")
            print()
            print("EMPFEHLUNG 2: Reduziere Arbeitsstunden")
            print("  - Aktuell: 48h/Woche = 212.6h/Monat")
            print("  - Vorschlag: 44h/Woche = 195.0h/Monat")
            print("  - Begründung: Macht Team-Rotation praktikabler")
            print()
            print("EMPFEHLUNG 3: Aktiviere teamübergreifende Einsätze")
            print("  - Erlaubt Mitarbeiter temporär in anderen Teams zu arbeiten")
            print("  - Erhöht Flexibilität bei Besetzungsengpässen")
            print()
            print("EMPFEHLUNG 4: Größere Teams")
            print("  - Aktuell: 5 Mitarbeiter pro Team")
            print("  - Vorschlag: 6 Mitarbeiter pro Team")
            print("  - Begründung: Mehr Puffer für Abwesenheiten und Besetzung")
        
        return success
        
    except Exception as e:
        print(f"\n✗✗✗ FEHLER BEIM ERSTELLEN/LÖSEN DES MODELLS ✗✗✗")
        print(f"Fehler: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    success = test_januar_2026_schichtmodell()
    
    # Exit code basierend auf Ergebnis
    if success:
        print("\n✓ Test erfolgreich - Lösung gefunden")
        exit(0)
    else:
        print("\n✗ Test fehlgeschlagen - Keine Lösung möglich (INFEASIBLE)")
        exit(1)
