-- Temporary test data for screenshots
-- This data should NOT be in the production application
-- Use this script to populate data before taking screenshots

-- Insert Teams
INSERT INTO Teams (Name, Description, Email) VALUES 
('Team Alpha', 'Frühschicht-Team', 'team-alpha@fritzwinter.de'),
('Team Beta', 'Spätschicht-Team', 'team-beta@fritzwinter.de'),
('Team Gamma', 'Nachtschicht-Team', 'team-gamma@fritzwinter.de');

-- Insert Employees (IsFerienjobber is required, default to 0)
INSERT INTO Employees (Vorname, Name, Personalnummer, Email, Geburtsdatum, Funktion, TeamId, IsSpringer, IsFerienjobber) VALUES
-- Team Alpha
('Max', 'Mustermann', 'MA001', 'max.mustermann@fritzwinter.de', '1985-05-15', 'Werkschutz', 1, 0, 0),
('Anna', 'Schmidt', 'MA002', 'anna.schmidt@fritzwinter.de', '1990-08-22', 'Werkschutz', 1, 0, 0),
('Peter', 'Müller', 'MA003', 'peter.mueller@fritzwinter.de', '1988-03-10', 'Brandmeldetechniker', 1, 0, 0),
('Lisa', 'Weber', 'MA004', 'lisa.weber@fritzwinter.de', '1992-11-05', 'Werkschutz', 1, 0, 0),
('Thomas', 'Wagner', 'MA005', 'thomas.wagner@fritzwinter.de', '1987-07-18', 'Werkschutz', 1, 0, 0),
-- Team Beta
('Julia', 'Becker', 'MA006', 'julia.becker@fritzwinter.de', '1991-02-28', 'Werkschutz', 2, 0, 0),
('Michael', 'Hoffmann', 'MA007', 'michael.hoffmann@fritzwinter.de', '1989-09-14', 'Werkschutz', 2, 0, 0),
('Sarah', 'Fischer', 'MA008', 'sarah.fischer@fritzwinter.de', '1993-06-07', 'Brandschutzbeauftragter', 2, 0, 0),
('Daniel', 'Richter', 'MA009', 'daniel.richter@fritzwinter.de', '1986-12-21', 'Werkschutz', 2, 0, 0),
('Laura', 'Klein', 'MA010', 'laura.klein@fritzwinter.de', '1994-04-16', 'Werkschutz', 2, 0, 0),
-- Team Gamma
('Markus', 'Wolf', 'MA011', 'markus.wolf@fritzwinter.de', '1990-10-09', 'Werkschutz', 3, 0, 0),
('Petra', 'Schröder', 'MA012', 'petra.schroeder@fritzwinter.de', '1988-01-25', 'Werkschutz', 3, 0, 0),
('Stefan', 'Neumann', 'MA013', 'stefan.neumann@fritzwinter.de', '1992-05-30', 'Werkschutz', 3, 0, 0),
('Claudia', 'Braun', 'MA014', 'claudia.braun@fritzwinter.de', '1987-08-12', 'Werkschutz', 3, 0, 0),
('Andreas', 'Zimmermann', 'MA015', 'andreas.zimmermann@fritzwinter.de', '1991-03-19', 'Werkschutz', 3, 0, 0),
-- Springer
('Frank', 'Krüger', 'MA016', 'frank.krueger@fritzwinter.de', '1985-11-08', 'Springer', NULL, 1, 0),
('Sabine', 'Hartmann', 'MA017', 'sabine.hartmann@fritzwinter.de', '1989-07-23', 'Springer', NULL, 1, 0);

-- Insert Shift Assignments for current week (Week 50, 2025: Dec 9-15)
-- Get ShiftType IDs: F=1 (Früh), S=2 (Spät), N=3 (Nacht)
-- IsSpringerAssignment and IsFixed are required

-- Monday 2025-12-09
INSERT INTO ShiftAssignments (EmployeeId, ShiftTypeId, Date, IsManual, IsSpringerAssignment, IsFixed, CreatedAt, CreatedBy) VALUES
(1, 1, '2025-12-09', 0, 0, 0, datetime('now'), 'System'), (2, 1, '2025-12-09', 0, 0, 0, datetime('now'), 'System'),
(3, 1, '2025-12-09', 0, 0, 0, datetime('now'), 'System'), (4, 1, '2025-12-09', 0, 0, 0, datetime('now'), 'System'),
(6, 2, '2025-12-09', 0, 0, 0, datetime('now'), 'System'), (7, 2, '2025-12-09', 0, 0, 0, datetime('now'), 'System'),
(8, 2, '2025-12-09', 0, 0, 0, datetime('now'), 'System'),
(11, 3, '2025-12-09', 0, 0, 0, datetime('now'), 'System'), (12, 3, '2025-12-09', 0, 0, 0, datetime('now'), 'System'),
(13, 3, '2025-12-09', 0, 0, 0, datetime('now'), 'System');

-- Tuesday 2025-12-10
INSERT INTO ShiftAssignments (EmployeeId, ShiftTypeId, Date, IsManual, IsSpringerAssignment, IsFixed, CreatedAt, CreatedBy) VALUES
(5, 1, '2025-12-10', 0, 0, 0, datetime('now'), 'System'), (6, 1, '2025-12-10', 0, 0, 0, datetime('now'), 'System'),
(7, 1, '2025-12-10', 0, 0, 0, datetime('now'), 'System'), (8, 1, '2025-12-10', 0, 0, 0, datetime('now'), 'System'),
(9, 2, '2025-12-10', 0, 0, 0, datetime('now'), 'System'), (10, 2, '2025-12-10', 0, 0, 0, datetime('now'), 'System'),
(11, 2, '2025-12-10', 0, 0, 0, datetime('now'), 'System'),
(14, 3, '2025-12-10', 0, 0, 0, datetime('now'), 'System'), (15, 3, '2025-12-10', 0, 0, 0, datetime('now'), 'System'),
(1, 3, '2025-12-10', 0, 0, 0, datetime('now'), 'System');

-- Wednesday 2025-12-11
INSERT INTO ShiftAssignments (EmployeeId, ShiftTypeId, Date, IsManual, IsSpringerAssignment, IsFixed, CreatedAt, CreatedBy) VALUES
(12, 1, '2025-12-11', 0, 0, 0, datetime('now'), 'System'), (13, 1, '2025-12-11', 0, 0, 0, datetime('now'), 'System'),
(14, 1, '2025-12-11', 0, 0, 0, datetime('now'), 'System'), (15, 1, '2025-12-11', 0, 0, 0, datetime('now'), 'System'),
(2, 2, '2025-12-11', 0, 0, 0, datetime('now'), 'System'), (3, 2, '2025-12-11', 0, 0, 0, datetime('now'), 'System'),
(4, 2, '2025-12-11', 0, 0, 0, datetime('now'), 'System'),
(5, 3, '2025-12-11', 0, 0, 0, datetime('now'), 'System'), (6, 3, '2025-12-11', 0, 0, 0, datetime('now'), 'System'),
(7, 3, '2025-12-11', 0, 0, 0, datetime('now'), 'System');

-- Thursday 2025-12-12
INSERT INTO ShiftAssignments (EmployeeId, ShiftTypeId, Date, IsManual, IsSpringerAssignment, IsFixed, CreatedAt, CreatedBy) VALUES
(1, 1, '2025-12-12', 0, 0, 0, datetime('now'), 'System'), (2, 1, '2025-12-12', 0, 0, 0, datetime('now'), 'System'),
(3, 1, '2025-12-12', 0, 0, 0, datetime('now'), 'System'), (4, 1, '2025-12-12', 0, 0, 0, datetime('now'), 'System'),
(8, 2, '2025-12-12', 0, 0, 0, datetime('now'), 'System'), (9, 2, '2025-12-12', 0, 0, 0, datetime('now'), 'System'),
(10, 2, '2025-12-12', 0, 0, 0, datetime('now'), 'System'),
(11, 3, '2025-12-12', 0, 0, 0, datetime('now'), 'System'), (12, 3, '2025-12-12', 0, 0, 0, datetime('now'), 'System'),
(13, 3, '2025-12-12', 0, 0, 0, datetime('now'), 'System');

-- Friday 2025-12-13
INSERT INTO ShiftAssignments (EmployeeId, ShiftTypeId, Date, IsManual, IsSpringerAssignment, IsFixed, CreatedAt, CreatedBy) VALUES
(5, 1, '2025-12-13', 0, 0, 0, datetime('now'), 'System'), (6, 1, '2025-12-13', 0, 0, 0, datetime('now'), 'System'),
(7, 1, '2025-12-13', 0, 0, 0, datetime('now'), 'System'), (8, 1, '2025-12-13', 0, 0, 0, datetime('now'), 'System'),
(14, 2, '2025-12-13', 0, 0, 0, datetime('now'), 'System'), (15, 2, '2025-12-13', 0, 0, 0, datetime('now'), 'System'),
(1, 2, '2025-12-13', 0, 0, 0, datetime('now'), 'System'),
(2, 3, '2025-12-13', 0, 0, 0, datetime('now'), 'System'), (3, 3, '2025-12-13', 0, 0, 0, datetime('now'), 'System'),
(4, 3, '2025-12-13', 0, 0, 0, datetime('now'), 'System');

-- Saturday 2025-12-14 (Weekend - reduced staffing)
INSERT INTO ShiftAssignments (EmployeeId, ShiftTypeId, Date, IsManual, IsSpringerAssignment, IsFixed, CreatedAt, CreatedBy) VALUES
(9, 1, '2025-12-14', 0, 0, 0, datetime('now'), 'System'), (10, 1, '2025-12-14', 0, 0, 0, datetime('now'), 'System'),
(11, 2, '2025-12-14', 0, 0, 0, datetime('now'), 'System'), (12, 2, '2025-12-14', 0, 0, 0, datetime('now'), 'System'),
(13, 3, '2025-12-14', 0, 0, 0, datetime('now'), 'System'), (14, 3, '2025-12-14', 0, 0, 0, datetime('now'), 'System');

-- Sunday 2025-12-15 (Weekend - reduced staffing)
INSERT INTO ShiftAssignments (EmployeeId, ShiftTypeId, Date, IsManual, IsSpringerAssignment, IsFixed, CreatedAt, CreatedBy) VALUES
(15, 1, '2025-12-15', 0, 0, 0, datetime('now'), 'System'), (1, 1, '2025-12-15', 0, 0, 0, datetime('now'), 'System'),
(2, 2, '2025-12-15', 0, 0, 0, datetime('now'), 'System'), (3, 2, '2025-12-15', 0, 0, 0, datetime('now'), 'System'),
(4, 3, '2025-12-15', 0, 0, 0, datetime('now'), 'System'), (5, 3, '2025-12-15', 0, 0, 0, datetime('now'), 'System');

-- Insert some Absences (Urlaub = 0, Krank = 1, Lehrgang = 2)
INSERT INTO Absences (EmployeeId, Type, StartDate, EndDate, Notes) VALUES
(6, 0, '2025-12-16', '2025-12-20', 'Urlaub genehmigt'),
(7, 0, '2025-12-23', '2025-12-27', 'Weihnachtsurlaub'),
(8, 1, '2025-12-30', '2026-01-03', 'Krankschreibung');

-- Insert Vacation Requests (Status: InBearbeitung=0, Genehmigt=1, NichtGenehmigt=2)
INSERT INTO VacationRequests (EmployeeId, StartDate, EndDate, Status, CreatedAt, Notes) VALUES
(9, '2026-01-06', '2026-01-10', 0, datetime('now'), 'Familienurlaub'),
(10, '2026-02-10', '2026-02-14', 1, datetime('now'), 'Winterurlaub'),
(11, '2026-03-17', '2026-03-21', 2, datetime('now'), 'Kurzurlaub - nicht möglich wegen Personalengpass');

-- Need to create shift assignments first for shift exchanges
-- Insert Shift Exchanges (Status: Available=0, Pending=1, Approved=2, Rejected=3, Cancelled=4)
-- First create some future shift assignments for exchanges
INSERT INTO ShiftAssignments (EmployeeId, ShiftTypeId, Date, IsManual, IsSpringerAssignment, IsFixed, CreatedAt, CreatedBy) VALUES
(12, 1, '2025-12-18', 0, 0, 0, datetime('now'), 'System'),
(13, 2, '2025-12-19', 0, 0, 0, datetime('now'), 'System');

-- Now create shift exchanges referencing these assignments
INSERT INTO ShiftExchanges (OfferingEmployeeId, ShiftAssignmentId, Status, CreatedAt, OfferingReason) VALUES
((SELECT MAX(Id) - 1 FROM ShiftAssignments), (SELECT MAX(Id) - 1 FROM ShiftAssignments), 0, datetime('now'), 'Kann an diesem Tag nicht arbeiten'),
((SELECT MAX(Id) FROM ShiftAssignments), (SELECT MAX(Id) FROM ShiftAssignments), 1, datetime('now'), 'Tausch angefragt');

-- Update the pending exchange with requesting employee
UPDATE ShiftExchanges SET RequestingEmployeeId = 14 WHERE Status = 1;

-- Insert Email Settings (example SMTP configuration)
INSERT INTO EmailSettings (SmtpServer, SmtpPort, Protocol, SecurityProtocol, RequiresAuthentication, Username, Password, SenderEmail, SenderName, ReplyToEmail, IsActive, CreatedAt) VALUES
('smtp.fritzwinter.de', 587, 'SMTP', 'STARTTLS', 1, 'dienstplan@fritzwinter.de', 'SecurePassword123!', 'dienstplan@fritzwinter.de', 'Dienstplan System', 'it-support@fritzwinter.de', 1, datetime('now'));
